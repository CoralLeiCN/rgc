"""Verify extraction origin checks against the browser's requested host."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "apps" / "web"


def test_extraction_accepts_requested_host_and_rejects_foreign_origins():
    loader = APP / "node_modules" / "tsx" / "dist" / "loader.mjs"
    if not loader.exists() or not shutil.which("node"):
        pytest.skip("Run npm ci before web extraction route tests")
    cases = [
        {"Host": "127.0.0.1:3000", "Origin": "http://127.0.0.1:3000"},
        {"Host": "localhost:3000", "Origin": "http://localhost:3000"},
        {"Origin": "http://localhost:3000"},
        {"Host": "127.0.0.1:3000"},
        {"Host": "127.0.0.1:3000", "Origin": "https://elsewhere.test"},
        {"Host": "127.0.0.1:3000", "Origin": "http://localhost:3000"},
        {"Host": "127.0.0.1:3000", "Origin": "http://127.0.0.1:3001"},
        {"Host": "127.0.0.1:3000", "Origin": "https://elsewhere.test",
         "X-Forwarded-Host": "elsewhere.test"},
    ]
    result = subprocess.run(
        ["node", "--conditions=react-server", "--import", str(loader),
         str(APP / "scripts" / "extraction-route-probe.ts")],
        cwd=APP, input=json.dumps([{"headers": headers} for headers in cases]),
        text=True, capture_output=True, check=True, timeout=30,
    )
    outputs = json.loads(result.stdout)
    assert [item["status"] for item in outputs] == [200] * 4 + [403] * 4
    assert [item["providerCalls"] for item in outputs] == [1] * 4 + [0] * 4
    assert all(item["body"]["provider"] == "codex" for item in outputs[:4])
    assert all(item["body"]["error"]["code"] == "INVALID_ORIGIN" for item in outputs[4:])
