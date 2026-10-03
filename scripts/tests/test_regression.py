"""Verify experimental fitting and held-out coverage with synthetic fixtures."""
import importlib.util
import math
from collections import Counter
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import chocolate_regression as regression
import pytest
from chocolate_model import PRICE_TARGET_POLICY, ModelContractError
from chocolate_regression import evaluate_regression, fit_regression

ROOT = Path(__file__).resolve().parents[2]

@pytest.mark.skipif(not importlib.util.find_spec('numpy') is not None, reason='optional NumPy modeling dependency unavailable')
class ChocolateRegressionTests:

    def design(self):
        return {'model_design_version': 'synthetic-chocolate-design-1', 'schema_version': 'chocolate-schema-1', 'target': {**PRICE_TARGET_POLICY, 'name': 'log_regular_gbp_per_100g', 'currency': 'GBP', 'unit': 'GBP_per_100g', 'quantity_attribute': 'quantity.total_edible_weight_g', 'base_quantity': 100}, 'predictors': {'composition.cocoa_percentage': {'type': 'numeric', 'transform': 'identity', 'required': True, 'missing_policy': 'reject', 'minimum': 0, 'maximum': 100, 'unit': '%'}}}

    def row(self, identifier, family, cocoa, log_price, *, brand='Brand A', retailer='Shop A', role='retail', group='bar'):
        return {'observation_id': identifier, 'listing_id': 'listing-' + identifier, 'variant_id': 'variant-' + identifier, 'family_id': family, 'comparable_group': group, 'source_role': role, 'model_eligible': True, 'target': {'regular_price_per_100g_gbp': math.exp(log_price), 'log_regular_price_per_100g_gbp': log_price}, 'predictors': {'composition.cocoa_percentage': cocoa, 'identity.brand': brand, 'identity.retailer': retailer, 'identity.source_role': role}}

    def training(self):
        rows = []
        for index in range(32):
            cocoa = 20 + 2 * index
            noise = (0.02, -0.02, -0.02, 0.02)[index % 4]
            rows.append(self.row('train-%02d' % index, 'family-%02d' % (index // 2), cocoa, 0.2 + 0.012 * cocoa + noise, brand='Brand A' if index % 2 == 0 else 'Brand B'))
        return rows

    def fit(self, rows=None, design=None, **options):
        return fit_regression(self.training() if rows is None else rows, self.design() if design is None else design, bootstrap_replicates=options.pop('bootstrap_replicates', 60), **options)

    def categorical(self):
        return {'type': 'categorical', 'transform': 'identity', 'required': True, 'missing_policy': 'reject', 'reference': 'training_mode'}

    def test_recovers_analytic_noisy_line_and_declares_experimental_limits(self):
        model = self.fit()
        estimates = {row['column']: row for row in model['coefficients']}
        assert estimates['intercept']['beta'] == pytest.approx(0.2, abs=10 ** (-12), rel=0)
        assert estimates['composition.cocoa_percentage']['beta'] == pytest.approx(0.012, abs=10 ** (-12), rel=0)
        assert estimates['composition.cocoa_percentage']['conditional_difference_percent'] == pytest.approx(100 * math.expm1(0.012), abs=10 ** (-12), rel=0)
        assert estimates['intercept']['conditional_difference_percent'] is None
        assert model['training_metrics']['MAE_log_price'] == pytest.approx(0.02, abs=10 ** (-12), rel=0)
        assert model['rank_diagnostics']['rank'] == 2
        assert model['rank_diagnostics']['residual_degrees_of_freedom'] == 30
        assert model['training_support']['families'] == 16
        assert model['regression_fitted']
        assert not model['release_ready']
        assert not model['prediction_intervals_available']
        assert model['estimate_type'] == 'conditional_median_price'
        assert model['training_metrics']['prediction_interval_coverage'] is None

    def test_bootstrap_is_reproducible_and_invariant_to_input_order(self):
        first = self.fit(random_seed=41)
        second = self.fit(list(reversed(self.training())), random_seed=41)
        assert first == second
        assert first['uncertainty']['coefficient_confidence_intervals_available']
        assert first['uncertainty']['successful_replicates'] == 60
        for coefficient in first['coefficients']:
            (lower, upper) = coefficient['confidence_interval_beta']
            assert lower <= coefficient['beta']
            assert upper >= coefficient['beta']

    def test_bootstrap_resamples_every_listing_in_each_drawn_family_together(self):
        matrices = []
        original = regression._fit_matrix

        def observed_fit(np, features, targets):
            matrices.append(np.asarray(features).copy())
            return original(np, features, targets)
        with patch.object(regression, '_fit_matrix', side_effect=observed_fit):
            self.fit(bootstrap_replicates=20)
        assert len(matrices) == 21
        for matrix in matrices[1:]:
            counts = Counter((float(value) for value in matrix[:, 1]))
            for index in range(16):
                assert counts[20 + 4 * index] == counts[22 + 4 * index]

    def test_rank_deficient_resamples_are_counted_and_suppress_intervals(self):
        design = self.design()
        design['predictors']['identity.brand'] = self.categorical()
        rows = [self.row('rare-%02d' % index, 'rare-family-%02d' % (index // 2), 20 + index, 0.2 + 0.012 * (20 + index), brand='Rare' if index < 2 else 'Common') for index in range(20)]
        model = self.fit(rows, design, bootstrap_replicates=200, random_seed=41)
        uncertainty = model['uncertainty']
        assert uncertainty['failed_replicates'] > 40
        assert uncertainty['successful_replicates'] + uncertainty['failed_replicates'] == 200
        assert not uncertainty['coefficient_confidence_intervals_available']
        assert any(('rank deficient' in reason for reason in uncertainty['failure_reasons']))
        assert all((row['confidence_interval_beta'] is None for row in model['coefficients']))

    def test_bootstrap_configuration_is_typed_and_can_explicitly_disable_intervals(self):
        assert not self.fit(bootstrap_replicates=0)['uncertainty']['coefficient_confidence_intervals_available']
        for (replicates, seed) in ((True, 41), (-1, 41), (20, True), (20, -1)):
            with pytest.raises(ModelContractError):
                self.fit(bootstrap_replicates=replicates, random_seed=seed)

    def test_full_rank_and_residual_degrees_of_freedom_are_required(self):
        design = self.design()
        design['predictors']['quantity.total_edible_weight_g'] = {'type': 'numeric', 'transform': 'identity', 'required': True, 'missing_policy': 'reject'}
        rows = self.training()
        for row in rows:
            row['predictors']['quantity.total_edible_weight_g'] = 2 * row['predictors']['composition.cocoa_percentage']
        with pytest.raises(ModelContractError, match='rank deficient'):
            self.fit(rows, design)
        with pytest.raises(ModelContractError, match='more training observations'):
            self.fit([self.training()[0], self.training()[2]])
        rows = self.training()
        for row in rows:
            row['family_id'] = 'one-family'
        with pytest.raises(ModelContractError, match='at least two reviewed training families'):
            self.fit(rows)

    def test_numerically_unstable_full_rank_matrix_is_rejected(self):
        rows = self.training()
        for (index, row) in enumerate(rows):
            row['predictors']['composition.cocoa_percentage'] = 50 + index * 1e-10
        with pytest.raises(ModelContractError, match='numerically unstable'):
            self.fit(rows)

    def test_context_role_removal_preserves_review_and_role_stratification(self):
        rows = self.training()
        design = self.design()
        design['predictors']['identity.source_role'] = self.categorical()
        design['predictors']['identity.retailer'] = self.categorical()
        for (index, row) in enumerate(rows):
            role = 'brand' if index % 2 else 'retail'
            row['source_role'] = role
            row['predictors'].update({'identity.source_role': role, 'identity.retailer': role + ' shop'})
        with pytest.raises(ModelContractError, match='rank deficient'):
            self.fit(rows, design)
        design['model'] = {'context_only_predictors': ['identity.source_role'], 'active_predictors': ['composition.cocoa_percentage', 'identity.retailer']}
        model = self.fit(rows, design)
        assert 'identity.source_role' not in model['feature_subset']
        assert 'identity.source_role' in model['eligibility_design']['predictors']
        assert model['context_only_predictors'] == ['identity.source_role']
        holdout = self.row('brand-holdout', 'new-family', 50, 1, role='brand', retailer='brand shop')
        report = evaluate_regression([holdout], model, rows)
        assert report['by_source_role']['brand']['supported_observations'] == 1
        holdout['predictors']['identity.source_role'] = 'unknown'
        with pytest.raises(ModelContractError, match='unresolved'):
            evaluate_regression([holdout], model, rows)

    def test_source_role_context_cannot_disagree_with_reviewed_predictor(self):
        design = self.design()
        design['predictors']['identity.source_role'] = self.categorical()
        design['model'] = {'context_only_predictors': ['identity.source_role']}
        rows = self.training()
        rows[0]['predictors']['identity.source_role'] = 'brand'
        with pytest.raises(ModelContractError, match='disagrees'):
            self.fit(rows, design)

    def test_seller_listing_repeats_are_rejected_instead_of_implicitly_weighted(self):
        rows = self.training()
        repeated = deepcopy(rows[0])
        repeated['observation_id'] = 'later-capture'
        with pytest.raises(ModelContractError, match='one observation per seller listing'):
            self.fit(rows + [repeated])

    def test_unsupported_holdout_coverage_preserves_training_and_input_metadata(self):
        (training, design) = (self.training(), self.design())
        design['predictors']['identity.brand'] = self.categorical()
        (original_training, original_design) = (deepcopy(training), deepcopy(design))
        model = self.fit(training, design)
        original_model = deepcopy(model)
        holdout = [self.row('supported', 'heldout-a', 50, 1), self.row('new-brand', 'heldout-b', 50, 1, brand='Brand C'), self.row('large', 'heldout-c', 99, 1)]
        original_holdout = deepcopy(holdout)
        result = evaluate_regression(holdout, model, training)
        assert result['validation_observations'] == 3
        assert result['supported_observations'] == 1
        assert result['unsupported_observations'] == 2
        assert result['coverage'] == pytest.approx(1 / 3, abs=10 ** (-7), rel=0)
        reasons = {item['observation_id']: item['reason'] for item in result['unsupported']}
        assert 'unseen training level' in reasons['new-brand']
        assert 'outside its training range' in reasons['large']
        assert result['by_brand']['Brand C']['coverage'] == 0
        assert result['by_brand']['Brand C']['metrics'] is None
        assert training == original_training
        assert design == original_design
        assert model == original_model
        assert holdout == original_holdout

    def test_all_unsupported_holdout_has_no_error_score(self):
        training = self.training()
        model = self.fit(training)
        result = evaluate_regression([self.row('large', 'heldout', 99, 1)], model, training)
        assert result['status'] == 'no_supported_holdout'
        assert result['coverage'] == 0
        assert result['metrics'] is None
        assert result['baseline']['metrics'] is None

    def test_invalid_holdout_is_rejected_before_support_rejection(self):
        training = self.training()
        model = self.fit(training)
        invalid = self.row('invalid', 'heldout', 99, 1)
        invalid['model_eligible'] = False
        with pytest.raises(ModelContractError, match='eligibility gate'):
            evaluate_regression([invalid], model, training)
        invalid['model_eligible'] = True
        invalid['predictors']['composition.cocoa_percentage'] = 101
        with pytest.raises(ModelContractError, match='above its declared maximum'):
            evaluate_regression([invalid], model, training)

    def test_validation_family_leakage_and_modified_baseline_snapshot_are_rejected(self):
        training = self.training()
        model = self.fit(training)
        holdout = self.row('heldout', training[0]['family_id'], 50, 1)
        with pytest.raises(ModelContractError, match='families overlap'):
            evaluate_regression([holdout], model, training)
        modified = deepcopy(training)
        modified[0]['target'] = {'regular_price_per_100g_gbp': 10, 'log_regular_price_per_100g_gbp': math.log(10)}
        holdout['family_id'] = 'independent-heldout'
        with pytest.raises(ModelContractError, match='immutable snapshot'):
            evaluate_regression([holdout], model, modified)

    def test_same_variant_cannot_evade_holdout_isolation_with_a_new_family_label(self):
        training = self.training()
        model = self.fit(training)
        holdout = self.row('heldout', 'new-family', 50, 1)
        holdout['variant_id'] = training[0]['variant_id']
        with pytest.raises(ModelContractError, match='cannot span validation families'):
            evaluate_regression([holdout], model, training)

    def test_price_scale_predictions_and_training_group_median_baseline_are_distinct(self):
        rows = [self.row('median-%d' % index, 'median-family-%d' % index, 50, math.log(price)) for (index, price) in enumerate((1, 2, 8, 16))]
        model = self.fit(rows)
        assert model['columns'] == ['intercept']
        assert model['training_support']['dropped_constant_terms'] == {'composition.cocoa_percentage': 'constant_in_training'}
        holdout = self.row('heldout', 'independent-heldout', 50, math.log(6))
        result = evaluate_regression([holdout], model, rows)
        assert result['predictions'][0]['predicted_median_price_per_100g_gbp'] == pytest.approx(4, abs=10 ** (-7), rel=0)
        assert result['baseline']['group_medians']['bar'] == pytest.approx(5, abs=10 ** (-7), rel=0)
        assert result['metrics']['MAE_GBP_per_100g'] == pytest.approx(2, abs=10 ** (-7), rel=0)
        assert result['metrics']['RMSE_GBP_per_100g'] == pytest.approx(2, abs=10 ** (-7), rel=0)
        assert result['metrics']['MAE_log_price'] == pytest.approx(math.log(1.5), abs=10 ** (-7), rel=0)
        assert result['metrics']['RMSE_log_price'] == pytest.approx(math.log(1.5), abs=10 ** (-7), rel=0)
        assert result['baseline']['metrics']['MAE_GBP_per_100g'] == pytest.approx(1, abs=10 ** (-7), rel=0)
        assert result['predictions'][0]['prediction_interval'] is None

    def test_baseline_never_learns_an_unseen_group_from_validation(self):
        training = self.training()
        model = self.fit(training)
        holdout = self.row('new-group', 'independent-heldout', 50, 1, group='baking_chocolate')
        result = evaluate_regression([holdout], model, training)
        assert result['supported_observations'] == 1
        assert result['baseline']['supported_observations'] == 0
        assert 'baking_chocolate' not in result['baseline']['group_medians']
        assert result['baseline']['metrics'] is None

    def test_unsupported_design_extensions_are_explicit_failures(self):
        cases = [lambda design: design['target'].update(currency='USD'), lambda design: design.update(model={'context_only_predictors': ['identity.brand']}), lambda design: design.update(model={'interaction_terms': ['brand*cocoa']}), lambda design: design.update(model={'ridge_alpha': 1}), lambda design: design.update(model={'regularization': {'method': 'ridge'}}), lambda design: design.update(model={'estimator': 'ridge'}), lambda design: design['predictors'].update({'target': self.categorical()})]
        for change in cases:
            design = self.design()
            change(design)
            with pytest.raises(ModelContractError):
                self.fit(design=design)
