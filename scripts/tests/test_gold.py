"""Check typed pass-through gold values, provenance, and immutable replay."""
import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest
from build_chocolate_gold import main as gold_main
from chocolate_gold import (
    CONTRACTS,
    PYARROW_VERSION,
    arrow_runtime,
    checksum,
    json_bytes,
    read_json,
    read_parquet,
    row_bytes,
    rows,
    training_schema,
    verified_silver,
)
from chocolate_gold import (
    build_legacy_gold_dataset as build_gold_dataset,
)
from chocolate_gold import (
    verified_gold_storage as verified_gold,
)
from dataset_contracts import resolve_contract_root

ROOT = Path(__file__).resolve().parents[2]

class GoldFixture:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path.resolve()
        self.silver = self.root / 'silver'
        self.output = self.root / 'gold'
        self.silver.mkdir()

    def observation(self, number, eligible=False):
        design = json.loads((resolve_contract_root(offline=True) / 'model-design.json').read_bytes())
        predictors = {name: None for name in design['predictors']}
        predictors.update({'identity.brand': 'Chocolat café 😀', 'identity.retailer': 'Fixture Shop', 'identity.product_group': 'bar', 'identity.source_role': 'retail', 'composition.cocoa_percentage': 70.0, 'quantity.total_edible_weight_g': 100.0, 'certifications.organic_claim': 'absent'})
        return {'observation_id': 'observation-' + str(number), 'listing_id': 'listing-' + str(number), 'variant_id': 'variant-' + str(number) if eligible else None, 'family_id': 'family-' + str(number) if eligible else None, 'comparable_group': 'bar', 'source_role': 'retail', 'model_eligible': eligible, 'exclusion_reasons': [] if eligible else ['fixture_unreviewed', 'fixture_unsupported'], 'predictors': predictors, 'target': {'regular_price_per_100g_gbp': 2.5 if eligible else None, 'log_regular_price_per_100g_gbp': 0.9162907318741551 if eligible else None}, 'dataset_version': 'silver-fixture', 'source_dataset_version': 'raw-fixture', 'schema_version': 'chocolate-schema-1'}

    def snapshot(self, candidates=(), eligible=None):
        if eligible is None:
            eligible = [row for row in candidates if row['model_eligible']]
        files = {name: (resolve_contract_root(offline=True) / name).read_bytes() for name in CONTRACTS}
        files['quality-report.json'] = json_bytes({'status': 'complete_snapshot', 'dataset_version': 'silver-fixture', 'counts': {'training_candidates': len(candidates), 'eligible_model_inputs': len(eligible)}})
        files['training-candidates.jsonl'] = b''.join((json.dumps(row, indent=0, ensure_ascii=False).replace('\n', ' ').encode() + b'\n' for row in candidates))
        files['model-inputs.jsonl'] = b''.join((json.dumps(row, ensure_ascii=False).encode() + b'\n' for row in eligible))
        files['prices.jsonl'] = b''.join((json.dumps({'observation_id': row['observation_id'], 'observed_at': '2026-10-03T12:00:00+01:00'}).encode() + b'\n' for row in candidates))
        files['unrelated-source-evidence.bin'] = 'Original evidence: chocolat noir.\n'.encode()
        manifest = {'manifest_format_version': 'chocolate-silver-manifest-1', 'schema_version': 'chocolate-schema-1', 'dataset_version': 'silver-fixture', 'source_dataset_version': 'raw-fixture', 'evidence_reference_base': 'Source silver source-listings; raw archive artifact paths.', 'contract_sha256': {name: checksum(files[name]) for name in CONTRACTS}, 'managed_files': {name: {'sha256': checksum(data), 'byte_length': len(data)} for (name, data) in files.items()}}
        for (name, data) in files.items():
            (self.silver / name).write_bytes(data)
        (self.silver / 'manifest.json').write_bytes(json_bytes(manifest))
        return manifest

    def tree_bytes(self, root):
        return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob('*') if path.is_file()}

    def change_manifest(self, root, name, data):
        (root / name).write_bytes(data)
        manifest = read_json((root / 'manifest.json').read_bytes())
        manifest['managed_files'][name] = {'sha256': checksum(data), 'byte_length': len(data)}
        (root / 'manifest.json').write_bytes(json_bytes(manifest))

class GoldIntegrityTests(GoldFixture):

    def test_every_managed_source_file_is_checked_before_arrow(self):
        self.snapshot()
        (self.silver / 'unrelated-source-evidence.bin').write_text('changed')
        with pytest.raises(ValueError, match='Silver checksum mismatch'):
            build_gold_dataset(self.silver, self.output)
        assert not self.output.exists()

    def test_combined_manifest_and_contract_hashes_are_required(self):
        self.snapshot()
        path = self.silver / 'manifest.json'
        manifest = read_json(path.read_bytes())
        manifest['contract_sha256']['model-design.json'] = '0' * 64
        path.write_bytes(json_bytes(manifest))
        with pytest.raises(ValueError, match='contract checksum mismatch'):
            verified_silver(self.silver)
        manifest['manifest_format_version'] = 'chocolate-standardized-manifest-1'
        path.write_bytes(json_bytes(manifest))
        with pytest.raises(ValueError, match='combined chocolate silver'):
            verified_silver(self.silver)

    def test_source_managed_path_cannot_escape_or_follow_a_link(self):
        self.snapshot()
        outside = self.root / 'outside.json'
        outside.write_bytes(b'{}\n')
        path = self.silver / 'manifest.json'
        manifest = read_json(path.read_bytes())
        manifest['managed_files']['../outside.json'] = {'sha256': checksum(outside.read_bytes()), 'byte_length': 3}
        path.write_bytes(json_bytes(manifest))
        with pytest.raises(ValueError, match='escapes or links'):
            verified_silver(self.silver)
        self.snapshot()
        evidence = self.silver / 'unrelated-source-evidence.bin'
        data = evidence.read_bytes()
        evidence.unlink()
        outside.write_bytes(data)
        evidence.symlink_to(outside)
        with pytest.raises(ValueError, match='escapes or links'):
            verified_silver(self.silver)

    def test_output_overlap_and_linked_parent_are_rejected_before_dependencies(self):
        self.snapshot()
        for output in (self.silver, self.silver / 'gold', self.root):
            with pytest.raises(ValueError, match='separate from silver'):
                build_gold_dataset(self.silver, output)
        link = self.root / 'output-link'
        link.symlink_to(self.root, target_is_directory=True)
        with pytest.raises(ValueError, match='symlinked directories'):
            build_gold_dataset(self.silver, link / 'gold')

    def test_source_eligibility_and_quality_counts_cannot_be_bypassed(self):
        candidate = self.observation(1)
        self.snapshot([candidate], [candidate])
        with pytest.raises(ValueError, match='reviewed eligible silver candidates'):
            build_gold_dataset(self.silver, self.output)
        self.snapshot([candidate])
        quality = read_json((self.silver / 'quality-report.json').read_bytes())
        quality['counts']['training_candidates'] = 5
        self.change_manifest(self.silver, 'quality-report.json', json_bytes(quality))
        with pytest.raises(ValueError, match='quality counts disagree'):
            build_gold_dataset(self.silver, self.output)

    def test_missing_unknown_fields_and_invalid_types_fail_without_discard(self):
        mutations = [lambda row: row.update(new_feature='unrecognized'), lambda row: row.pop('source_dataset_version'), lambda row: row['predictors'].update(new_feature='unrecognized'), lambda row: row['predictors'].pop('composition.cocoa_percentage'), lambda row: row['target'].update(new_target=1.0), lambda row: row['predictors'].update({'composition.cocoa_percentage': True}), lambda row: row.update(model_eligible=0), lambda row: row.update(dataset_version='different-source'), lambda row: row.update(exclusion_reasons=[None])]
        for mutate in mutations:
            candidate = self.observation(1)
            mutate(candidate)
            self.snapshot([candidate])
            with pytest.raises(ValueError):
                build_gold_dataset(self.silver, self.output)
        assert not self.output.exists()

    def test_cli_reports_dependency_failure_and_nonzero_exit(self):
        self.snapshot()
        with patch('chocolate_gold.arrow_runtime', side_effect=ImportError('fixture missing Arrow')):
            with redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as error:
                result = gold_main(['--silver-root', str(self.silver), '--output', str(self.output)])
        assert result == 2
        assert output.getvalue() == ''
        assert 'fixture missing Arrow' in error.getvalue()

@pytest.mark.skipif(not importlib.util.find_spec('pyarrow') is not None, reason='optional PyArrow gold dependency unavailable')
class GoldParquetTests(GoldFixture):

    def test_family_decisions_survive_gold_and_bulk_review(self):
        from chocolate_gold import mark_legacy_gold_reviewed as mark_gold_reviewed
        self.snapshot([self.observation(1)])
        decisions = json_bytes({'mapping_format_version': 'chocolate-family-mappings-1', 'families': {'fixture-family': {'label': 'Fixture range'}}})
        self.change_manifest(self.silver, 'family-mappings.json', decisions)
        (_, original) = build_gold_dataset(self.silver, self.output)
        (_, _, inputs) = verified_gold(original)
        assert inputs['family-mappings.json'] == decisions
        (_, reviewed) = mark_gold_reviewed(original, self.root / 'reviewed', 'task-user', 'User requested review')
        (_, _, reviewed_inputs) = verified_gold(reviewed)
        assert reviewed_inputs['family-mappings.json'] == decisions
        self.change_manifest(reviewed, 'inputs/family-mappings.json', b'{}\n')
        with pytest.raises(ValueError, match='copied source input'):
            verified_gold(reviewed)

    def test_candidates_are_lossless_and_empty_model_inputs_have_explicit_types(self):
        candidates = [self.observation(1), self.observation(2)]
        candidates[1]['predictors']['composition.cocoa_percentage'] = None
        candidates[1]['predictors']['quantity.total_edible_weight_g'] = None
        source = self.snapshot(candidates)
        before = self.tree_bytes(self.silver)
        (report, destination) = build_gold_dataset(self.silver, self.output)
        schema = training_schema(read_json((self.silver / 'model-design.json').read_bytes()))
        assert read_parquet((destination / 'training-data.parquet').read_bytes(), schema) == candidates
        assert read_parquet((destination / 'model-inputs.parquet').read_bytes(), schema) == []
        (pa, pq) = arrow_runtime()
        empty = pq.ParquetFile(destination / 'model-inputs.parquet').read()
        assert empty.schema.field('predictors').type.field('composition.cocoa_percentage').type == pa.float64()
        assert empty.schema.field('predictors').type.field('identity.brand').type == pa.string()
        assert empty.schema.field('exclusion_reasons').type.value_type == pa.string()
        assert report['counts'] == {'training_candidates': 2, 'eligible_model_inputs': 0}
        assert report['gold_ready_for_loading']
        assert report['row_values_preserved']
        assert not report['release_ready']
        assert report['exclusion_counts'] == {'fixture_unreviewed': 2, 'fixture_unsupported': 2}
        assert self.tree_bytes(self.silver) == before
        (verified_source, source_bytes, inputs) = verified_gold(destination)
        assert verified_source == source
        assert source_bytes == before['manifest.json']
        assert rows(inputs['training-candidates.jsonl']) == candidates
        assert inputs['training-candidates.jsonl'] != before['training-candidates.jsonl']
        assert inputs['model-inputs.jsonl'] == b''
        assert not (destination / 'inputs/training-candidates.jsonl').exists()
        for name in (*CONTRACTS, 'quality-report.json', 'prices.jsonl'):
            assert inputs[name] == before[name]
        manifest = read_json((destination / 'manifest.json').read_bytes())
        assert manifest['pyarrow_version'] == PYARROW_VERSION
        assert manifest['dataset_version'] == report['dataset_version']
        assert manifest['silver_dataset_version'] == 'silver-fixture'
        assert manifest['tables']['training-data.parquet']['logical_sha256'] == checksum(row_bytes(candidates))
        assert set(manifest['managed_files']) == set(self.tree_bytes(destination)) - {'manifest.json'}

    def test_reviewed_rows_are_copied_without_filtering_other_candidates(self):
        (candidate, eligible) = (self.observation(1), self.observation(2, eligible=True))
        eligible['predictors']['quantity.total_edible_weight_g'] = 100
        self.snapshot([candidate, eligible])
        (report, destination) = build_gold_dataset(self.silver, self.output)
        (_, _, inputs) = verified_gold(destination)
        assert report['counts'] == {'training_candidates': 2, 'eligible_model_inputs': 1}
        assert rows(inputs['training-candidates.jsonl']) == [candidate, eligible]
        assert rows(inputs['model-inputs.jsonl']) == [eligible]
        assert rows(inputs['model-inputs.jsonl'])[0]['dataset_version'] == 'silver-fixture'

    def test_identical_replay_verifies_and_mutated_snapshot_is_never_overwritten(self):
        self.snapshot([self.observation(1)])
        (first_report, destination) = build_gold_dataset(self.silver, self.output)
        before = self.tree_bytes(destination)
        (second_report, second_destination) = build_gold_dataset(self.silver, self.output)
        assert (first_report, destination) == (second_report, second_destination)
        assert self.tree_bytes(destination) == before
        (destination / 'training-data.parquet').write_bytes(b'changed')
        with pytest.raises(ValueError, match='refusing to overwrite'):
            build_gold_dataset(self.silver, self.output)
        assert (destination / 'training-data.parquet').read_bytes() == b'changed'

    def test_changed_contract_is_a_distinct_immutable_gold_version(self):
        self.snapshot([self.observation(1)])
        (_, first) = build_gold_dataset(self.silver, self.output)
        original = self.tree_bytes(first)
        design_path = self.silver / 'model-design.json'
        design = read_json(design_path.read_bytes())
        design['fixture_note'] = 'New compatible source design bytes.'
        design_bytes = json_bytes(design)
        self.change_manifest(self.silver, 'model-design.json', design_bytes)
        manifest_path = self.silver / 'manifest.json'
        manifest = read_json(manifest_path.read_bytes())
        manifest['contract_sha256']['model-design.json'] = checksum(design_bytes)
        manifest_path.write_bytes(json_bytes(manifest))
        (_, second) = build_gold_dataset(self.silver, self.output)
        assert first != second
        assert self.tree_bytes(first) == original
        assert verified_gold(second)[2]['model-design.json'] == design_bytes

    def test_loader_checks_parquet_hash_logical_hash_and_schema(self):
        self.snapshot([self.observation(1)])
        (_, destination) = build_gold_dataset(self.silver, self.output)
        original = self.tree_bytes(destination)
        (destination / 'training-data.parquet').write_bytes(b'changed')
        with pytest.raises(ValueError, match='Gold checksum mismatch'):
            verified_gold(destination)
        (destination / 'training-data.parquet').write_bytes(original['training-data.parquet'])
        manifest_path = destination / 'manifest.json'
        manifest = read_json(manifest_path.read_bytes())
        manifest['tables']['training-data.parquet']['logical_sha256'] = '0' * 64
        manifest_path.write_bytes(json_bytes(manifest))
        with pytest.raises(ValueError, match='logical row checksum mismatch'):
            verified_gold(destination)
        manifest_path.write_bytes(original['manifest.json'])
        (pa, pq) = arrow_runtime()
        sink = pa.BufferOutputStream()
        pq.write_table(pa.table({'unexpected': ['silently dropped?']}), sink)
        self.change_manifest(destination, 'training-data.parquet', sink.getvalue().to_pybytes())
        with pytest.raises(ValueError, match='Parquet schema differs'):
            verified_gold(destination)

    def test_loader_requires_preserved_report_counts_and_source_inputs(self):
        self.snapshot([self.observation(1)])
        (_, destination) = build_gold_dataset(self.silver, self.output)
        original = self.tree_bytes(destination)
        report = read_json(original['report.json'])
        report['counts']['eligible_model_inputs'] = 1
        self.change_manifest(destination, 'report.json', json_bytes(report))
        with pytest.raises(ValueError, match='report disagrees'):
            verified_gold(destination)
        self.change_manifest(destination, 'report.json', original['report.json'])
        self.change_manifest(destination, 'inputs/profile.json', b'{}\n')
        with pytest.raises(ValueError, match='copied input differs'):
            verified_gold(destination)

    def test_cli_returns_snapshot_report_and_empty_snapshot_is_loadable(self):
        self.snapshot()
        with redirect_stdout(io.StringIO()) as output:
            result = gold_main(['--silver-root', str(self.silver), '--output', str(self.output)])
        assert result == 0
        response = read_json(output.getvalue())
        assert response['counts'] == {'training_rows': 0}
        assert response['gold_ready_for_loading']
        assert not response['release_ready']
        assert Path(response['report_path']).is_file()
        from chocolate_gold import verified_gold as population_loader
        assert population_loader(Path(response['output']))[2]['training-candidates.jsonl'] == b''

    def test_finite_numeric_values_must_survive_arrow_precision(self):
        candidate = self.observation(1)
        candidate['predictors']['quantity.total_edible_weight_g'] = 2 ** 54 + 1
        self.snapshot([candidate])
        with pytest.raises(ValueError, match='roundtrip changed|exactly representable'):
            build_gold_dataset(self.silver, self.output)
        assert not self.output.exists()
