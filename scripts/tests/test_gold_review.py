"""Verify user-directed Gold review annotations without changing source or eligibility."""
import importlib.util
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest
from chocolate_gold import (
    REVIEW_IDENTITY_FIELDS,
    REVIEW_SCHEMA_VERSION,
    TABLES,
    checksum,
    json_bytes,
    parquet_bytes,
    read_json,
    read_parquet,
    row_bytes,
    rows,
    training_schema,
)
from chocolate_gold import (
    build_legacy_gold_dataset as build_gold_dataset,
)
from chocolate_gold import (
    mark_legacy_gold_reviewed as mark_gold_reviewed,
)
from chocolate_gold import (
    verified_gold_storage as verified_gold,
)
from review_chocolate_gold import main as review_main
from test_gold import GoldFixture

ROOT = Path(__file__).resolve().parents[2]

class GoldReviewArgumentsTests(GoldFixture):

    def test_explicit_authority_and_reason_are_required_before_loading(self):
        for (reviewed_by, reason) in (('', 'request'), ('user', '  '), (None, 'request')):
            with pytest.raises(ValueError, match='explicit user-request'):
                mark_gold_reviewed(self.root / 'missing', self.output, reviewed_by, reason)

    def test_cli_dependency_failure_is_reported(self):
        with patch('review_chocolate_gold.mark_gold_reviewed', side_effect=ImportError('fixture missing Arrow')):
            with redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as error:
                code = review_main(['--gold-root', str(self.root), '--reviewed-by', 'Fixture User', '--reason', 'Review all rows.'])
        assert code == 2
        assert output.getvalue() == ''
        assert 'fixture missing Arrow' in error.getvalue()

@pytest.mark.skipif(not importlib.util.find_spec('pyarrow') is not None, reason='optional PyArrow gold dependency unavailable')
class GoldReviewParquetTests(GoldFixture):

    def build_source(self, candidates=None):
        candidates = [self.observation(1), self.observation(2, eligible=True)] if candidates is None else candidates
        self.snapshot(candidates)
        (_, source) = build_gold_dataset(self.silver, self.output)
        return (candidates, source)

    def mark(self, source, reason='Mark everything in Gold as reviewed.'):
        return mark_gold_reviewed(source, self.output, 'Fixture User', reason)

    def rewrite_reviewed_table(self, destination, name, mutate):
        manifest = read_json((destination / 'manifest.json').read_bytes())
        design = read_json((destination / 'inputs/model-design.json').read_bytes())
        schema = training_schema(design, REVIEW_SCHEMA_VERSION)
        values = read_parquet((destination / name).read_bytes(), schema)
        mutate(values)
        (data, _) = parquet_bytes(values, schema)
        self.change_manifest(destination, name, data)
        manifest = read_json((destination / 'manifest.json').read_bytes())
        manifest['tables'][name]['logical_sha256'] = checksum(row_bytes(values))
        (destination / 'manifest.json').write_bytes(json_bytes(manifest))
        return (manifest, values)

    def rebind_identity(self, destination, manifest):
        manifest['dataset_version'] = 'gold-' + checksum(json_bytes({name: manifest[name] for name in REVIEW_IDENTITY_FIELDS}))[:24]
        report = read_json((destination / 'report.json').read_bytes())
        report['dataset_version'] = manifest['dataset_version']
        report_bytes = json_bytes(report)
        (destination / 'report.json').write_bytes(report_bytes)
        manifest['managed_files']['report.json'] = {'sha256': checksum(report_bytes), 'byte_length': len(report_bytes)}
        (destination / 'manifest.json').write_bytes(json_bytes(manifest))

    def test_all_tables_annotated_source_unchanged_and_loader_preserves_original_rows(self):
        (candidates, source) = self.build_source()
        (source_before, silver_before) = (self.tree_bytes(source), self.tree_bytes(self.silver))
        source_inputs = verified_gold(source)[2]
        (report, destination) = self.mark(source)
        assert source != destination
        assert self.tree_bytes(source) == source_before
        assert self.tree_bytes(self.silver) == silver_before
        schema = training_schema(read_json(source_inputs['model-design.json']), REVIEW_SCHEMA_VERSION)
        for (name, source_name) in TABLES.items():
            values = read_parquet((destination / name).read_bytes(), schema)
            original = rows(source_inputs[source_name])
            assert values == [{**row, 'review_status': 'reviewed', 'review_basis': 'user_instruction'} for row in original]
        assert verified_gold(destination) == verified_gold(source)
        assert rows(verified_gold(destination)[2]['training-candidates.jsonl']) == candidates
        assert report['counts'] == {'training_candidates': 2, 'eligible_model_inputs': 1}
        assert report['reviewed_counts'] == report['counts']
        assert report['source_row_values_preserved']
        assert report['eligibility_preserved']
        assert not report['review_provenance']['evidence_validation_performed']
        assert not report['release_ready']
        assert (destination / 'inputs/parent-gold-manifest.json').read_bytes() == source_before['manifest.json']
        assert report['parent_gold_dataset_version'] == source.name

    def test_nulls_and_empty_eligible_view_remain_unmodified(self):
        (candidates, source) = self.build_source([self.observation(1)])
        (report, destination) = self.mark(source)
        assert report['counts'] == {'training_candidates': 1, 'eligible_model_inputs': 0}
        inputs = verified_gold(destination)[2]
        assert rows(inputs['training-candidates.jsonl']) == candidates
        assert inputs['model-inputs.jsonl'] == b''
        schema = training_schema(read_json(inputs['model-design.json']), REVIEW_SCHEMA_VERSION)
        assert not schema.field('review_status').nullable
        assert read_parquet((destination / 'model-inputs.parquet').read_bytes(), schema) == []
        assert candidates[0]['target']['regular_price_per_100g_gbp'] is None
        assert candidates[0]['family_id'] is None
        assert not candidates[0]['model_eligible']

    def test_identical_replay_and_changed_reason_are_distinct_immutable_snapshots(self):
        (_, source) = self.build_source()
        (first_report, first) = self.mark(source)
        before = self.tree_bytes(first)
        assert self.mark(source) == (first_report, first)
        assert self.tree_bytes(first) == before
        (_, second) = self.mark(source, 'User requested another separately recorded review decision.')
        assert first != second
        assert self.tree_bytes(first) == before
        (first / 'report.json').write_bytes(b'changed')
        with pytest.raises(ValueError, match='refusing to overwrite'):
            self.mark(source)
        assert (first / 'report.json').read_bytes() == b'changed'

    def test_new_annotation_on_reviewed_source_retains_parent_and_original_values(self):
        (_, source) = self.build_source()
        (_, first) = self.mark(source)
        before = self.tree_bytes(first)
        (_, second) = self.mark(first, 'User requested a new review annotation after the earlier one.')
        assert verified_gold(second) == verified_gold(source)
        assert (second / 'inputs/parent-gold-manifest.json').read_bytes() == before['manifest.json']
        assert self.tree_bytes(first) == before

    def test_source_corruption_overlap_and_output_links_are_rejected(self):
        (_, source) = self.build_source()
        for output in (source, source / 'reviewed'):
            with pytest.raises(ValueError, match='separate from its source'):
                mark_gold_reviewed(source, output, 'Fixture User', 'Review all rows.')
        link = self.root / 'review-link'
        link.symlink_to(self.output, target_is_directory=True)
        with pytest.raises(ValueError, match='symlinked directories'):
            mark_gold_reviewed(source, link, 'Fixture User', 'Review all rows.')
        (source / 'training-data.parquet').write_bytes(b'changed')
        with pytest.raises(ValueError, match='Gold checksum mismatch'):
            self.mark(source)

    def test_changed_source_values_cannot_pass_using_recomputed_child_hashes(self):
        (_, source) = self.build_source()
        (_, destination) = self.mark(source)
        (manifest, values) = self.rewrite_reviewed_table(destination, 'training-data.parquet', lambda values: values[0]['predictors'].update({'composition.cocoa_percentage': 90.0}))
        stripped = [{name: value for (name, value) in row.items() if name not in ('review_status', 'review_basis')} for row in values]
        manifest['tables']['training-data.parquet']['source_fields_logical_sha256'] = checksum(row_bytes(stripped))
        (destination / 'manifest.json').write_bytes(json_bytes(manifest))
        with pytest.raises(ValueError, match='changed parent source row values'):
            verified_gold(destination)

    def test_annotation_report_counts_and_provenance_tampering_are_rejected(self):
        (_, source) = self.build_source()
        (_, destination) = self.mark(source)
        original = self.tree_bytes(destination)
        self.rewrite_reviewed_table(destination, 'training-data.parquet', lambda values: values[0].update(review_basis='evidence_review'))
        with pytest.raises(ValueError, match='user-instruction annotation'):
            verified_gold(destination)
        for (path, data) in original.items():
            (destination / path).write_bytes(data)
        for (key, value) in (('reviewed_counts', {'training_candidates': 9, 'eligible_model_inputs': 1}), ('review_provenance', {'evidence_validation_performed': True}), ('source_row_values_preserved', False)):
            report = read_json(original['report.json'])
            report[key] = value
            self.change_manifest(destination, 'report.json', json_bytes(report))
            with pytest.raises(ValueError, match='review report disagrees'):
                verified_gold(destination)
        for (path, data) in original.items():
            (destination / path).write_bytes(data)
        manifest = read_json(original['manifest.json'])
        manifest['review_provenance']['evidence_validation_performed'] = True
        (destination / 'manifest.json').write_bytes(json_bytes(manifest))
        with pytest.raises(ValueError, match='review provenance'):
            verified_gold(destination)

    def test_parent_manifest_and_copied_input_metadata_are_checked(self):
        (_, source) = self.build_source()
        (_, destination) = self.mark(source)
        parent_path = 'inputs/parent-gold-manifest.json'
        parent = read_json((destination / parent_path).read_bytes())
        parent['managed_files']['inputs/quality-report.json']['sha256'] = '0' * 64
        parent_bytes = json_bytes(parent)
        self.change_manifest(destination, parent_path, parent_bytes)
        manifest = read_json((destination / 'manifest.json').read_bytes())
        manifest['source_gold_manifest_sha256'] = checksum(parent_bytes)
        self.rebind_identity(destination, manifest)
        with pytest.raises(ValueError, match='changed copied source input'):
            verified_gold(destination)

    def test_cli_success_records_the_explicit_request(self):
        (_, source) = self.build_source([self.observation(1)])
        with redirect_stdout(io.StringIO()) as output:
            code = review_main(['--gold-root', str(source), '--output', str(self.output), '--reviewed-by', 'Fixture User', '--reason', 'Review every row now.'])
        assert code == 0
        result = read_json(output.getvalue())
        assert result['review_provenance']['reason'] == 'Review every row now.'
        assert result['counts'] == {'training_rows': 1}
        from chocolate_gold import verified_gold as population_loader
        population_loader(result['output'])
