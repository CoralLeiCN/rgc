"""Exercise reviewed product taxonomy reuse and its evidence/eligibility boundary."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import test_standardization as standardization_fixtures
from chocolate_silver import build_silver_dataset
from chocolate_standardization.identity import empty_mappings, load_identity_mappings
from chocolate_standardization.pipeline import build_standardized_dataset

ROOT = Path(__file__).resolve().parents[2]

class FamilyMappingTests:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.fixture = standardization_fixtures.ChocolateStandardizationTests()
        self.fixture.initialize(tmp_path)
        self.fixture.prepare()

    def mappings(self, physical=False):
        source = self.fixture.source_listing()
        latest = next((item for item in source['captures'] if item['capture_id'] == source['latest_capture_id']))
        document = empty_mappings()
        document['families'] = {'fixture-dark-range': {'label': 'Fixture dark range', 'definition': 'Related fixture dark chocolate variants across sellers.'}}
        assignment = {'mapping_id': 'fixture-example-identity', 'selector': {field: source.get(field) for field in ('source_key', 'source_product_id', 'source_variant_id', 'name')}, 'family_id': 'fixture-dark-range', 'reviewed_by': 'Codex fixture reviewer', 'reason': 'Reviewed source product name and consumer pack evidence.', 'evidence': [{'capture_id': latest['capture_id'], 'pointer': '/raw_record/identity/name'}]}
        if physical:
            document['physical_products'] = {'fixture-dark-200g': {'label': 'Fixture dark chocolate 200g', 'family_id': 'fixture-dark-range'}}
            assignment['variant_id'] = 'fixture-dark-200g'
        document['assignments'] = [assignment]
        return document

    def build(self, document, reviews=None, output=None):
        return build_standardized_dataset(self.fixture.deduplicated, output or self.fixture.output, family_mappings=document, reviews=reviews)

    def test_family_only_maps_product_and_candidate_without_reviewing_other_fields(self):
        document = self.mappings()
        report = self.build(document)
        product = self.fixture.rows()[0]
        candidate = self.fixture.rows('training-candidates')[0]
        family = product['attributes']['identity.product_family_id']
        assert (family['value'], family['review_status'], family['method']) == ('fixture-dark-range', 'reviewed', 'reviewed_identity_mapping')
        assert candidate['family_id'] == 'fixture-dark-range'
        assert candidate['variant_id'] is None
        assert candidate['target']['regular_price_per_100g_gbp'] is None
        assert product['review_status'] == 'unreviewed'
        assert product['attributes']['identity.boundary_status']['status'] == 'unknown'
        assert 'physical_identity_and_family_unreviewed' in candidate['exclusion_reasons']
        assert report['counts']['eligible_model_inputs'] == 0
        packet = self.fixture.rows('family-review-packets')[0]
        assert packet['members'][0]['reasons'] == ['physical_product_unresolved']
        assert json.loads((self.fixture.output / 'family-mappings.json').read_text()) == document
        manifest = json.loads((self.fixture.output / 'manifest.json').read_text())
        assert manifest['identity_mappings_sha256'] == hashlib.sha256((self.fixture.output / 'family-mappings.json').read_bytes()).hexdigest()

    def test_full_mapping_with_separate_feature_and_price_reviews_yields_eligible_input(self):
        reviews = self.fixture.reviews()
        reviews['products']['example'].pop('family_id')
        reviews['products']['example'].pop('variant_id')
        report = self.build(self.mappings(physical=True), reviews=reviews)
        assert report['counts']['eligible_model_inputs'] == 1
        candidate = self.fixture.rows('model-inputs')[0]
        assert candidate['family_id'] == 'fixture-dark-range'
        assert candidate['variant_id'] == 'fixture-dark-200g'
        assert self.fixture.rows('family-review-packets') == []

    def test_changed_name_does_not_reuse_old_review(self):
        document = self.mappings()
        document['assignments'][0]['selector']['name'] = 'A previous product name'
        report = self.build(document)
        assert self.fixture.rows('training-candidates')[0]['family_id'] is None
        assert report['product_identity_mapping']['applied_assignments'] == 0
        assert 'family_unresolved' in self.fixture.rows('family-review-packets')[0]['members'][0]['reasons']

    def test_conflicting_family_decisions_preserve_conflict_and_queue(self):
        document = self.mappings()
        document['families']['fixture-other-range'] = {'label': 'Other range', 'definition': 'A conflicting reviewed interpretation.'}
        second = deepcopy(document['assignments'][0])
        second.update(mapping_id='conflicting-decision', family_id='fixture-other-range')
        document['assignments'].append(second)
        report = self.build(document)
        family = self.fixture.rows()[0]['attributes']['identity.product_family_id']
        assert (family['status'], family['value'], family['review_status']) == ('conflict', None, 'needs_review')
        assert self.fixture.rows('training-candidates')[0]['family_id'] is None
        assert report['product_identity_mapping']['conflicting_listings'] == 1

    def test_product_review_cannot_silently_replace_accepted_registry(self):
        for field in ('family_id', 'attributes'):
            reviews = self.fixture.reviews()
            reviews['products']['example'].pop('family_id')
            if field == 'family_id':
                reviews['products']['example']['family_id'] = 'other-family'
            else:
                reviews['products']['example']['attributes']['identity.product_family_id'] = {'value': 'other-family', 'reviewed_by': 'Fixture reviewer', 'reason': 'Conflicting identity review.', 'evidence': deepcopy(self.mappings()['assignments'][0]['evidence'])}
            with pytest.raises(ValueError, match='contradicts its registered identity mapping'):
                self.build(self.mappings(), reviews=reviews)

    def test_source_selector_reuses_mapping_after_canonical_listing_id_changes(self):
        document = self.mappings()
        source = self.fixture.source_listing()
        source['listing_id'] = 'new-canonical-listing'
        source['source_listing_ids'].append('new-canonical-listing')
        path = self.fixture.deduplicated / 'products.jsonl'
        data = (json.dumps(source, sort_keys=True) + '\n').encode()
        path.write_bytes(data)
        manifest_path = self.fixture.deduplicated / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['managed_files']['products.jsonl'] = {'byte_length': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        manifest_path.write_text(json.dumps(manifest))
        self.build(document)
        assert self.fixture.rows('training-candidates')[0]['family_id'] == 'fixture-dark-range'
        assert self.fixture.rows()[0]['listing_id'] == 'new-canonical-listing'

    def test_mapping_evidence_must_resolve_inside_the_matched_listing(self):
        for change in ('capture_id', 'pointer'):
            document = self.mappings()
            document['assignments'][0]['evidence'][0][change] = 'unknown' if change == 'capture_id' else '/raw_record/missing'
            with pytest.raises(ValueError, match='Identity mapping evidence'):
                self.build(document)

    def test_registry_requires_valid_references_and_preserves_untrimmed_raw_names(self):
        document = self.mappings()
        document['assignments'][0]['selector']['name'] = ' Original source spacing '
        assert load_identity_mappings(document) == document
        invalid = deepcopy(document)
        invalid['assignments'][0]['family_id'] = 'unregistered-family'
        with pytest.raises(ValueError, match='undefined family'):
            load_identity_mappings(invalid)
        invalid = self.mappings(physical=True)
        invalid['physical_products']['fixture-dark-200g']['family_id'] = 'unregistered-family'
        with pytest.raises(ValueError, match='registered family'):
            load_identity_mappings(invalid)

    def test_silver_publishes_mapping_inputs_and_packets_and_preserves_source_bytes(self):
        document = self.mappings()
        before = self.fixture.snapshot(self.fixture.archive)
        output = self.fixture.base / 'silver'
        report = build_silver_dataset(self.fixture.archive, output, family_mappings=document)
        assert self.fixture.snapshot(self.fixture.archive) == before
        assert report['product_identity_mapping']['applied_assignments'] == 1
        candidate = self.fixture.rows('training-candidates', directory=output)[0]
        assert candidate['family_id'] == 'fixture-dark-range'
        assert (output / 'family-review-packets.jsonl').is_file()
        assert json.loads((output / 'family-mappings.json').read_text()) == document
