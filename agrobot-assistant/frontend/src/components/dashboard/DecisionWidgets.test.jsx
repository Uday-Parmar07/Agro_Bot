import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import '../../i18n';

import { CropRecommendationsGrid, FarmSummary, StatusCards } from './DecisionWidgets';
import { cultivatedCropSummary, farmerSelectedCrops } from '../../utils/dashboard';


const baseRecommendation = {
  status: 'success',
  generation_mode: 'model_with_explanation',
  coverage: { model_supported_crop_count: 22 },
  data_quality: { level: 'medium', estimated_features: [], warnings: [] },
  recommended_crops: [],
};

const crop = (source) => ({
  crop_slug: 'rice',
  crop_name: 'Rice',
  rank: 1,
  candidate_sources: [source],
  model_probability: source === 'xgboost' ? 0.72 : null,
  overall_suitability_score: 72,
  suitability_band: 'medium',
  warnings: [],
  matched_conditions: [],
  source_references: [],
  explanation: {
    why_recommended: ['Validated model candidate'],
    next_actions: ['Obtain a soil test'],
  },
});

test('renders a model-backed crop with product score only in technical details', () => {
  render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, recommended_crops: [crop('xgboost')] }} onRefresh={() => {}} />);
  expect(screen.getByText('ML model')).toBeInTheDocument();
  expect(screen.getByText(/Product ranking score/)).toBeInTheDocument();
});

test('renders a knowledge-backed crop distinctly', () => {
  render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, recommended_crops: [crop('knowledge_base')] }} onRefresh={() => {}} />);
  expect(screen.getByText('Crop knowledge')).toBeInTheDocument();
});

test('shows estimated soil warning', () => {
  const recommendation = {
    ...baseRecommendation,
    data_quality: { level: 'low', estimated_features: ['N', 'P', 'K', 'pH'] },
    global_warnings: [{ code: 'ESTIMATED_SOIL_VALUES', message: 'NPK or pH values were estimated.' }],
  };
  render(<CropRecommendationsGrid recommendation={recommendation} onRefresh={() => {}} />);
  expect(screen.getByText('NPK or pH values were estimated.')).toBeInTheDocument();
});

test('shows template fallback and keeps refresh available', () => {
  const onRefresh = jest.fn();
  render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, generation_mode: 'template_fallback' }} onRefresh={onRefresh} />);
  expect(screen.getByText(/Detailed AI explanations are temporarily unavailable/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /Generate \/ refresh/ }));
  expect(onRefresh).toHaveBeenCalled();
});

test('renders no reliable recommendation state', () => {
  render(
    <CropRecommendationsGrid
      recommendation={{ ...baseRecommendation, status: 'no_reliable_recommendation', disclaimer: 'No supported crop passed.' }}
      onRefresh={() => {}}
    />
  );
  expect(screen.getByText('We need more information')).toBeInTheDocument();
  expect(screen.getByText('No supported crop passed.')).toBeInTheDocument();
});

test('does not render a zero-score crop', () => {
  render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, recommended_crops: [{ ...crop('xgboost'), overall_suitability_score: 0 }] }} onRefresh={() => {}} />);
  expect(screen.queryByRole('heading', { name: 'Rice' })).not.toBeInTheDocument();
  expect(screen.getByText('We need more information')).toBeInTheDocument();
});

test('one eligible crop renders exactly one crop card', () => {
  const { container } = render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, recommended_crops: [crop('xgboost')] }} onRefresh={() => {}} />);
  expect(container.querySelectorAll('.recommendation-card')).toHaveLength(1);
});

test('renders preliminary matches separately without precise score in the card', () => {
  render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, status: 'preliminary', recommended_crops: [], preliminary_crops: [{ ...crop('xgboost'), recommendation_status: 'preliminary', overall_suitability_score: 44 }] }} onRefresh={() => {}} />);
  expect(screen.getByText('Preliminary matches')).toBeInTheDocument();
  expect(screen.getByText('Suitability: Preliminary')).toBeInTheDocument();
  expect(screen.queryByText('44 / 100')).not.toBeInTheDocument();
});

test('renders a coded global warning once and not inside the crop card', () => {
  const warning = { code: 'ESTIMATED_SOIL_VALUES', message: 'NPK or pH values were estimated.' };
  const { container } = render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, global_warnings: [warning], recommended_crops: [{ ...crop('xgboost'), crop_specific_warnings: [] }] }} onRefresh={() => {}} />);
  expect(screen.getAllByText('NPK or pH values were estimated.')).toHaveLength(1);
  expect(container.querySelector('.recommendation-card')).not.toHaveTextContent('NPK or pH values were estimated.');
});

test('technical details are collapsed by default', () => {
  const { container } = render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, recommended_crops: [crop('xgboost')] }} onRefresh={() => {}} />);
  const details = container.querySelector('details.technical-details');
  expect(details).toBeInTheDocument();
  expect(details).not.toHaveAttribute('open');
});

test('shows unavailable season validation honestly', () => {
  render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, recommended_crops: [{ ...crop('xgboost'), validation_coverage: { season: 'not_available' }, validation_coverage_summary: { verified_checks: 0, unavailable_checks: 1, failed_checks: 0 } }] }} onRefresh={() => {}} />);
  expect(screen.getByText(/Could not verify: season/)).toBeInTheDocument();
});

test('missing sowing date and soil test show farm-scoped questionnaire actions', () => {
  const recommendation = {
    ...baseRecommendation,
    missing_inputs: [
      { field: 'intended_sowing_date', importance: 'high', action_route: '/questionnaire?refill=1&farm_id=7&section=environment&field=intended_sowing_date' },
      { field: 'soil_test', importance: 'high', action_route: '/questionnaire?refill=1&farm_id=7&section=soil-fertility&field=soil_test_done' },
    ],
    recommended_crops: [crop('xgboost')],
  };
  render(<CropRecommendationsGrid recommendation={recommendation} onRefresh={() => {}} />);
  expect(screen.getByRole('link', { name: 'Add sowing date' })).toHaveAttribute('href', expect.stringContaining('farm_id=7'));
  expect(screen.getByRole('link', { name: 'Add soil-test values' })).toHaveAttribute('href', expect.stringContaining('section=soil-fertility'));
  expect(screen.queryByRole('button', { name: /Generate \/ refresh/ })).not.toBeInTheDocument();
});

test('model and knowledge source labels remain distinct', () => {
  render(<CropRecommendationsGrid recommendation={{ ...baseRecommendation, recommended_crops: [crop('knowledge_base'), { ...crop('xgboost'), crop_slug: 'maize', crop_name: 'Maize', rank: 2 }] }} onRefresh={() => {}} />);
  expect(screen.getByText('Crop knowledge')).toBeInTheDocument();
  expect(screen.getByText('ML model')).toBeInTheDocument();
});

test('cultivated crop summary never reads recommendation results', () => {
  const recommendation = { recommended_crops: [crop('xgboost')] };
  expect(cultivatedCropSummary([])).toBeNull();
  expect(cultivatedCropSummary([{ name: 'Wheat' }], recommendation)).toBe('Wheat');
  expect(farmerSelectedCrops([
    { crop_name: 'Papaya', added_by: 'recommendation' },
    { crop_name: 'Wheat', added_by: 'user' },
  ])).toEqual([{ crop_name: 'Wheat', added_by: 'user' }]);
});

test('legacy API crop remains readable without new metadata', () => {
  const legacy = { crop_name: 'Legacy Rice', candidate_sources: [], overall_suitability_score: null };
  render(<CropRecommendationsGrid recommendation={{ status: 'success', recommended_crops: [legacy] }} onRefresh={() => {}} />);
  expect(screen.getByRole('heading', { name: 'Legacy Rice' })).toBeInTheDocument();
  expect(screen.getByText('Legacy source unknown')).toBeInTheDocument();
});

test('farm health and empty cultivated crops are actionable without fabricated scores', () => {
  const onAddCrop = jest.fn();
  render(<>
    <StatusCards score={null} soilStatus="Not assessed" alertCount={0} taskCount={0} assessmentRoute="/questionnaire?farm_id=7" />
    <FarmSummary summary={{ location: 'Pune', soilType: 'loamy', farmSize: '2 acre', season: 'rabi', mainCrops: null }} onAddCrop={onAddCrop} />
  </>);
  expect(screen.getByText('Farm health not assessed')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Complete assessment' })).toHaveAttribute('href', '/questionnaire?farm_id=7');
  expect(screen.getByText('No crops selected')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Add crop' }));
  expect(onAddCrop).toHaveBeenCalled();
});
