"""Exercise immutable experimental runs and silver integrity/readiness gates."""
import importlib.util
import json
import math
from pathlib import Path

import pytest
from dataset_contracts import resolve_contract_root
from train_chocolate_model import (
    CONTRACTS,
    build_model_run,
    checksum,
    json_bytes,
    write_run,
)

ROOT = Path(__file__).resolve().parents[2]

class TrainingRunTests:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path.resolve()
        self.silver = self.root / 'silver'
        self.output = self.root / 'models'
        self.silver.mkdir()

    def test_silver_training_run_preserves_identity_decisions(self):
        self.snapshot()
        decisions = json_bytes({'mapping_format_version': 'chocolate-family-mappings-1'})
        (self.silver / 'family-mappings.json').write_bytes(decisions)
        path = self.silver / 'manifest.json'
        manifest = json.loads(path.read_bytes())
        manifest['managed_files']['family-mappings.json'] = {'sha256': checksum(decisions), 'byte_length': len(decisions)}
        path.write_bytes(json_bytes(manifest))
        (report, destination) = build_model_run(self.silver, self.output, 'bar')
        assert not report['regression_fitted']
        assert (destination / 'inputs/family-mappings.json').read_bytes() == decisions

    def observation(self, i):
        predictors = {'identity.product_group': 'bar', 'identity.source_role': 'retail', 'identity.brand': 'Fixture Brand', 'identity.retailer': 'Fixture Seller', 'composition.chocolate_type': 'dark', 'composition.cocoa_percentage': 30 + i, 'composition.nuts_presence': 'absent', 'dietary.vegan_claim': 'present', 'certifications.fairtrade_claim': 'present', 'certifications.organic_claim': 'present', 'quantity.total_edible_weight_g': 100}
        price = round(math.exp(1 + 0.02 * i + 0.002 * (i % 3 - 1)), 8)
        logged = math.log(price)
        return {'observation_id': str(i), 'listing_id': 'listing-' + str(i), 'variant_id': 'variant-' + str(i), 'family_id': 'family-' + str(i), 'comparable_group': 'bar', 'source_role': 'retail', 'model_eligible': True, 'exclusion_reasons': [], 'predictors': predictors, 'target': {'regular_price_per_100g_gbp': price, 'log_regular_price_per_100g_gbp': logged}, 'dataset_version': 'silver-fixture', 'source_dataset_version': 'raw-fixture', 'schema_version': 'chocolate-schema-1'}

    def snapshot(self, observations=None, *, candidates=None):
        observations = observations or []
        candidates = observations if candidates is None else candidates
        files = {n: (resolve_contract_root(offline=True) / n).read_bytes() for n in CONTRACTS}
        files['quality-report.json'] = json_bytes({'status': 'complete_snapshot', 'dataset_version': 'silver-fixture', 'counts': {'training_candidates': len(candidates), 'eligible_model_inputs': len(observations)}})
        files['model-inputs.jsonl'] = b''.join((json.dumps(r).encode() + b'\n' for r in observations))
        files['training-candidates.jsonl'] = b''.join((json.dumps(r).encode() + b'\n' for r in candidates))
        prices = []
        for row in candidates:
            mass = row['predictors']['quantity.total_edible_weight_g']
            unit_price = row['target']['regular_price_per_100g_gbp']
            regular = unit_price * mass / 100 if unit_price is not None else None
            prices.append({**{name: row[name] for name in ('observation_id', 'listing_id', 'source_role', 'dataset_version', 'source_dataset_version', 'schema_version')}, 'regular_price': regular, 'displayed_price': regular * 0.8 if regular else 1, 'reference_price': regular * 1.3 if regular else None, 'promotion_status': 'promotional', 'currency': 'GBP', 'tax_basis': 'consumer_tax_included', 'total_edible_weight_g': mass, 'review_status': 'reviewed', 'quantity_status': 'reviewed', 'model_eligible': row['model_eligible'], 'available': True, 'observed_at': '2026-10-03T12:00:00+01:00'})
        files['prices.jsonl'] = b''.join((json.dumps(price).encode() + b'\n' for price in prices))
        manifest = {'manifest_format_version': 'chocolate-silver-manifest-1', 'schema_version': 'chocolate-schema-1', 'dataset_version': 'silver-fixture', 'source_dataset_version': 'raw-fixture', 'contract_sha256': {n: checksum(files[n]) for n in CONTRACTS}, 'managed_files': {n: {'sha256': checksum(b), 'byte_length': len(b)} for (n, b) in files.items()}}
        for (name, data) in files.items():
            (self.silver / name).write_bytes(data)
        (self.silver / 'manifest.json').write_bytes(json_bytes(manifest))

    def test_empty_realistic_snapshot_reports_readiness_without_model(self):
        self.snapshot()
        original = {p.name: p.read_bytes() for p in self.silver.iterdir()}
        (report, destination) = build_model_run(self.silver, self.output, 'bar')
        assert report['status'] == 'unavailable'
        assert 'no_reviewed_eligible_observations_in_group' in report['blockers']
        assert not report['regression_fitted']
        assert not report['release_ready']
        assert not (destination / 'model.json').exists()
        assert original == {p.name: p.read_bytes() for p in self.silver.iterdir()}
        (second_report, second_destination) = build_model_run(self.silver, self.output, 'bar')
        assert second_report == report
        assert second_destination == destination
        manifest = json.loads((destination / 'manifest.json').read_bytes())
        for (name, metadata) in manifest['managed_files'].items():
            assert checksum((destination / name).read_bytes()) == metadata['sha256']

    def test_corrupt_input_is_rejected_before_any_model_run(self):
        self.snapshot()
        (self.silver / 'model-inputs.jsonl').write_text('{}\n')
        with pytest.raises(ValueError, match='checksum mismatch'):
            build_model_run(self.silver, self.output, 'bar')
        assert not self.output.exists()

    def replace_prices(self, prices):
        data = b''.join((json.dumps(price).encode() + b'\n' for price in prices))
        (self.silver / 'prices.jsonl').write_bytes(data)
        manifest_path = self.silver / 'manifest.json'
        manifest = json.loads(manifest_path.read_bytes())
        manifest['managed_files']['prices.jsonl'] = {'sha256': checksum(data), 'byte_length': len(data)}
        manifest_path.write_bytes(json_bytes(manifest))

    def test_checksummed_price_context_must_match_the_regular_consumer_target(self):
        for changes in ({'tax_basis': 'unknown'}, {'currency': 'EUR'}, {'regular_price': 12}, {'total_edible_weight_g': 200}, {'review_status': 'unreviewed'}, {'listing_id': 'another-listing'}):
            self.snapshot([self.observation(1)])
            prices = [json.loads(line) for line in (self.silver / 'prices.jsonl').read_bytes().splitlines()]
            prices[0].update(changes)
            self.replace_prices(prices)
            with pytest.raises(ValueError, match='price|mass|provenance'):
                build_model_run(self.silver, self.output, 'bar')
            assert not self.output.exists()

    def test_training_prices_need_unique_matching_observation_ids(self):
        self.snapshot([self.observation(1)])
        prices = [json.loads(line) for line in (self.silver / 'prices.jsonl').read_bytes().splitlines()]
        for modified in ([], prices * 2, [{**prices[0], 'observation_id': 'another-observation'}]):
            self.replace_prices(modified)
            with pytest.raises(ValueError, match='observation'):
                build_model_run(self.silver, self.output, 'bar')
            assert not self.output.exists()

    def test_valid_hashes_cannot_override_eligibility(self):
        bad = self.observation(1)
        bad['model_eligible'] = False
        self.snapshot([bad])
        with pytest.raises(ValueError, match='reviewed eligible silver candidates'):
            build_model_run(self.silver, self.output, 'bar')

    def test_repeated_listing_requires_cross_sectional_review(self):
        (first, repeat) = (self.observation(1), self.observation(2))
        repeat.update(listing_id=first['listing_id'], variant_id=first['variant_id'], family_id=first['family_id'])
        self.snapshot([first, repeat, self.observation(3)])
        (report, destination) = build_model_run(self.silver, self.output, 'bar')
        assert 'repeated_listing_observations_require_reviewed_cross_sectional_selection' in report['blockers']
        assert not (destination / 'model.json').exists()

    def test_immutable_run_refuses_modified_result(self):
        destination = write_run(self.output, 'example-run', {'report.json': b'{}\n'})
        (destination / 'report.json').write_bytes(b'changed')
        with pytest.raises(ValueError, match='refusing to overwrite'):
            write_run(self.output, 'example-run', {'report.json': b'{}\n'})
        assert (destination / 'report.json').read_bytes() == b'changed'

    def test_output_cannot_overlap_input_or_follow_symlink(self):
        self.snapshot()
        with pytest.raises(ValueError, match='separate from silver'):
            build_model_run(self.silver, self.silver / 'models', 'bar')
        self.output.symlink_to(self.silver, target_is_directory=True)
        with pytest.raises(ValueError):
            build_model_run(self.silver, self.output, 'bar')

    @pytest.mark.skipif(not importlib.util.find_spec('numpy') is not None, reason='optional NumPy modeling dependency unavailable')
    def test_reviewed_fixture_fits_and_keeps_artifact_versions_and_split(self):
        self.snapshot([self.observation(i) for i in range(1, 31)])
        (report, destination) = build_model_run(self.silver, self.output, 'bar')
        assert report['regression_fitted']
        assert report['status'] == 'experimental_fitted'
        assert not report['release_ready']
        model = json.loads((destination / 'model.json').read_bytes())
        assert model['source_dataset_version'] == 'raw-fixture'
        assert model['dataset_version'] == 'silver-fixture'
        assert model['model_design_version'] == 'chocolate-pricing-design-3'
        assert model['price_target_policy']['price_basis'] == 'regular'
        assert model['price_target_policy']['tax_basis'] == 'consumer_tax_included'
        assert report['price_target_policy'] == model['price_target_policy']
        assert 'identity.source_role' not in model['feature_subset']
        assert not set(report['split']['training_families']) & set(report['split']['validation_families'])
        assert 'validation_results' in model
        assert (destination / 'inputs/model-inputs.jsonl').read_bytes() == (self.silver / 'model-inputs.jsonl').read_bytes()
        assert not model['prediction_intervals_available']
        assert not model['release_ready']

    @pytest.mark.skipif(not importlib.util.find_spec('pyarrow') is not None, reason='optional PyArrow dependency unavailable')
    def test_gold_input_preserves_empty_eligibility_and_run_provenance(self):
        from chocolate_gold import build_gold_dataset
        self.snapshot()
        (gold_report, gold) = build_gold_dataset(self.silver, self.root / 'gold')
        (report, destination) = build_model_run(None, self.output, 'bar', gold_root=gold)
        assert report['status'] == 'unavailable'
        assert report['input_kind'] == 'gold'
        assert report['gold_dataset_version'] == gold_report['dataset_version']
        assert report['dataset_version'] == 'silver-fixture'
        assert not report['regression_fitted']
        assert (destination / 'inputs/gold-manifest.json').read_bytes() == (gold / 'manifest.json').read_bytes()
        assert (destination / 'inputs/silver-manifest.json').read_bytes() == (self.silver / 'manifest.json').read_bytes()

    @pytest.mark.skipif(not (importlib.util.find_spec('numpy') is not None and importlib.util.find_spec('pyarrow') is not None), reason='optional NumPy/PyArrow dependencies unavailable')
    def test_gold_can_train_independently_of_original_silver(self):
        import shutil

        from chocolate_gold import build_gold_dataset
        self.snapshot([self.observation(i) for i in range(1, 31)])
        (gold_report, gold) = build_gold_dataset(self.silver, self.root / 'gold')
        shutil.rmtree(self.silver)
        (report, destination) = build_model_run(None, self.output, 'bar', gold_root=gold)
        assert report['regression_fitted']
        model = json.loads((destination / 'model.json').read_bytes())
        assert model['input_kind'] == 'gold'
        assert model['gold_dataset_version'] == gold_report['dataset_version']
        assert model['source_dataset_version'] == 'raw-fixture'
        assert not model['release_ready']

    @pytest.mark.skipif(not importlib.util.find_spec('pyarrow') is not None, reason='optional PyArrow dependency unavailable')
    def test_bulk_gold_review_does_not_promote_missing_targets_into_training(self):
        from chocolate_gold import build_gold_dataset, mark_gold_reviewed
        candidate = self.observation(1)
        candidate.update(model_eligible=False, family_id=None, variant_id=None, target={'regular_price_per_100g_gbp': None, 'log_regular_price_per_100g_gbp': None}, exclusion_reasons=['regular_unit_price_missing_or_invalid', 'physical_identity_and_family_unreviewed'])
        self.snapshot(candidates=[candidate])
        (_, original) = build_gold_dataset(self.silver, self.root / 'gold')
        (_, reviewed) = mark_gold_reviewed(original, self.root / 'reviewed-gold', 'task-user', 'User requested bulk review')
        (report, destination) = build_model_run(None, self.output, 'bar', gold_root=reviewed)
        assert report['counts']['training_rows'] == 1
        assert not report['regression_fitted']
        assert report['blockers']
        assert not report['gold_review_provenance']['evidence_validation_performed']
        assert report['gold_review_provenance']['reviewed_by'] == 'task-user'
        assert not (destination / 'model.json').exists()

    @pytest.mark.skipif(not (importlib.util.find_spec('numpy') is not None and importlib.util.find_spec('pyarrow') is not None), reason='optional NumPy/PyArrow dependencies unavailable')
    def test_bulk_reviewed_gold_preserves_valid_training_and_review_provenance(self):
        import shutil

        from chocolate_gold import build_gold_dataset, mark_gold_reviewed
        self.snapshot([self.observation(i) for i in range(1, 31)])
        (_, original) = build_gold_dataset(self.silver, self.root / 'gold')
        (_, reviewed) = mark_gold_reviewed(original, self.root / 'reviewed-gold', 'task-user', 'User requested bulk review')
        shutil.rmtree(self.silver)
        shutil.rmtree(original)
        (report, destination) = build_model_run(None, self.output, 'bar', gold_root=reviewed)
        assert report['regression_fitted']
        assert not report['release_ready']
        model = json.loads((destination / 'model.json').read_bytes())
        assert model['gold_review_provenance'] == report['gold_review_provenance']
        assert model['gold_review_provenance']['review_basis'] == 'user_instruction'
        assert (destination / 'inputs/gold-manifest.json').read_bytes() == (reviewed / 'manifest.json').read_bytes()
