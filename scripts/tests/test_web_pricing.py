"""Verify serving parity with the published native fixture, not market accuracy."""

import hashlib
import itertools
import json
import math
import shutil
import subprocess
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "web"
KEYS = ["quantity.total_edible_weight_g", "composition.chocolate_type",
        "composition.recipe_class", "composition.nuts_presence", "identity.retailer"]


@pytest.fixture(scope="module")
def model():
    if not (APP / "node_modules" / "tsx").exists() or not (APP / "model-cache" / "model.json").exists():
        pytest.skip("Prepare the pinned web model and run npm ci before web serving tests")
    reference = json.loads((APP / "pricing-model.json").read_text())
    for name, entry in reference["files"].items():
        data = (APP / "model-cache" / name).read_bytes()
        assert len(data) == entry["byteLength"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    return json.loads((APP / "model-cache" / "model.json").read_text())


def probe(script, inputs, cwd=APP):
    result = subprocess.run(
        ["node", "--conditions=react-server", "--import", str(APP / "node_modules" / "tsx" / "dist" / "loader.mjs"),
         str(APP / "scripts" / script)], cwd=cwd, input=json.dumps(inputs), text=True,
        capture_output=True, check=True, timeout=60,
    )
    return json.loads(result.stdout)


def product(**updates):
    values = {"scope": "single_pack_chocolate_bar", **dict(zip(KEYS, [100, "dark", "plain", "unknown", "Waitrose"]))}
    return {**values, **updates}


def test_web_predictions_and_each_shap_value_match_native_fixture(model):
    pre = model["preprocessing"]
    # Boundary and interior weights, plus every admitted categorical combination.
    grid = itertools.product([50, 70.71067811865474, 70.71067811865477, 100, 125, 150],
                             *(pre["categories"][key] for key in KEYS[1:]))
    inputs = [{"scope": "single_pack_chocolate_bar", **dict(zip(KEYS, row))} for row in grid]
    x = np.array([[math.log(row[KEYS[0]])] + [pre["categories"][key].index(row[key]) for key in KEYS[1:]] for row in inputs])
    booster = lgb.Booster(model_str=model["booster"])
    expected = booster.predict(x, raw_score=True, num_threads=1, num_iteration=model["tree_count"])
    shap = booster.predict(x, pred_contrib=True, num_threads=1, num_iteration=model["tree_count"])
    outputs = probe("pricing-probe.ts", inputs)
    assert len(outputs) == len(inputs) == 324
    for i, (row, result) in enumerate(zip(inputs, outputs)):
        assert "error" not in result
        assert result["fixture"] is True
        assert result["releaseReady"] is False
        assert result["priceBasis"] == "regular-consumer-price-1"
        assert result["interval"] is None
        assert result["predictedLog"] == pytest.approx(expected[i], abs=1e-12)
        assert result["referenceLog"] == pytest.approx(shap[i, -1], abs=1e-12)
        assert [v["shapLog"] for v in result["attributions"]] == pytest.approx(shap[i, :-1], abs=1e-12)
        assert result["packGbp"] == pytest.approx(math.exp(expected[i]) * row[KEYS[0]] / 100)
        assert result["referencePackGbp"] + sum(v["packGbp"] for v in result["attributions"]) == pytest.approx(result["packGbp"], abs=1e-10)
        assert result["referencePercent"] + sum(v["percent"] for v in result["families"]) == pytest.approx(100, abs=1e-10)
        assert result["reconstructionError"] == pytest.approx(0, abs=1e-12)
        assert result["reconciliationError"] == pytest.approx(0, abs=1e-10)


def test_unsupported_inputs_and_price_leakage_are_rejected(model):
    cases = [product(**{KEYS[0]: value}) for value in [49, 151, 0, "100", None, True]]
    cases += [product(**{KEYS[1]: "ruby"}), product(**{KEYS[2]: "assortment"}),
              product(**{KEYS[3]: "absent"}), product(**{KEYS[4]: "Tesco"}),
              product(scope="multipack"), product(packPrice=3.50), product(brand="Example")]
    assert all("error" in result for result in probe("pricing-probe.ts", cases))


def test_signed_allocation_cancellation_negative_and_near_zero(model):
    cases = [{"reference": 1, "contributions": [0.2, -0.2], "raw": 1},
             {"reference": 1, "contributions": [-0.3], "raw": 0.7},
             {"reference": 1, "contributions": [1e-12], "raw": 1 + 1e-12},
             {"reference": 1, "contributions": [0.2], "raw": 4}]
    results = probe("pricing-allocation-probe.ts", cases)
    assert results[0]["referencePercent"] == 100
    assert results[0]["percentages"] == pytest.approx([20, -20])
    assert results[1]["referencePercent"] > 100
    assert results[1]["percentages"][0] < 0
    assert results[2]["percentages"][0] == pytest.approx(1e-10, abs=1e-20)
    assert "error" in results[3]


def test_prediction_api_input_errors_and_private_response(model):
    cases = [{"body": json.dumps(product())}, {"body": "{"}, {"body": " " * 4097},
             {"body": json.dumps(product()), "headers": {"Content-Type": "text/plain"}},
             {"body": json.dumps(product()), "headers": {"Content-Type": "application/json", "Origin": "https://elsewhere.test"}},
             {"body": json.dumps(product(**{KEYS[4]: "Tesco"}))},
             {"body": json.dumps(product()), "headers": {"Content-Type": "application/json", "Host": "127.0.0.1:3000", "Origin": "http://127.0.0.1:3000"}}]
    results = probe("pricing-route-probe.ts", cases)
    assert [r["status"] for r in results] == [200, 400, 413, 400, 403, 422, 200]
    assert all(r["cacheControl"] == "no-store" for r in results)
    assert results[0]["body"]["fixture"] is True


@pytest.mark.parametrize("corrupt", [False, True])
def test_missing_or_corrupt_model_is_unavailable_without_paths(model, tmp_path, corrupt):
    if corrupt:
        cache = tmp_path / "model-cache"
        shutil.copytree(APP / "model-cache", cache)
        with (cache / "model.json").open("ab") as handle:
            handle.write(b" ")
    result = probe("pricing-route-probe.ts", [{"body": json.dumps(product())}], cwd=tmp_path)[0]
    assert result["status"] == 503
    assert result["body"]["error"]["code"] == "MODEL_UNAVAILABLE"
    assert str(tmp_path) not in json.dumps(result)
