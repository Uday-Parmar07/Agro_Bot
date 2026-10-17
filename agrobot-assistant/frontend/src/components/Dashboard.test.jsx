import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from './Dashboard';
import ApiService from '../services/api';

jest.mock('../services/api', () => ({
  getFarms: jest.fn(), getLatestRecommendations: jest.fn(), getWeatherOverview: jest.fn(),
  getUserQuestionnaireResponses: jest.fn(), getFarmCrops: jest.fn(), getFarmAssessment: jest.fn(),
}));
jest.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: { full_name: 'Farmer' } }) }));
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key) => key }) }));
jest.mock('./CropMonitor', () => () => null);
jest.mock('./MandiPriceTeaser', () => () => null);
jest.mock('./WeatherWidget', () => () => null);
jest.mock('./dashboard/DecisionWidgets', () => {
  const actual = jest.requireActual('./dashboard/DecisionWidgets');
  return Object.fromEntries(Object.entries(actual).map(([key, value]) => [key, key === 'StatusCards' ? value : () => null]));
});

const assessment = (score) => ({
  score, status: 'estimated', explanation: 'Based on your saved observations.', components: { soil_top_layer: 5 },
});
const mount = () => render(<MemoryRouter><Dashboard /></MemoryRouter>);

beforeEach(() => {
  jest.resetAllMocks();
  ApiService.getFarms.mockResolvedValue([{ id: 1, name: 'Farm One' }, { id: 2, name: 'Farm Two' }]);
  ApiService.getLatestRecommendations.mockRejectedValue(new Error('Unavailable'));
  ApiService.getWeatherOverview.mockResolvedValue(null);
  ApiService.getUserQuestionnaireResponses.mockResolvedValue({});
  ApiService.getFarmCrops.mockResolvedValue([]);
});

test('shows assessment from saved details even when recommendations are unavailable', async () => {
  ApiService.getFarmAssessment.mockResolvedValue(assessment(8.3));
  mount();
  expect(await screen.findByText('8.3')).toBeInTheDocument();
  expect(screen.getByText('Estimated soil screening score')).toBeInTheDocument();
  expect(screen.queryByText('Farm health not assessed')).not.toBeInTheDocument();
});

test('zero is an assessed score, not missing data', async () => {
  ApiService.getFarmAssessment.mockResolvedValue(assessment(0));
  mount();
  expect(await screen.findByText('0.0')).toBeInTheDocument();
  expect(screen.queryByText('Farm health not assessed')).not.toBeInTheDocument();
});

test('incomplete assessments identify the actual missing answers', async () => {
  ApiService.getFarmAssessment.mockResolvedValue({ score: null, status: 'insufficient_data', missing_fields: ['earthworms_present'] });
  mount();
  expect(await screen.findByText('Still needed: earthworms present.')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Complete assessment' })).toHaveAttribute('href', '/questionnaire?refill=1&farm_id=1&section=soil-physical');
});

test('a failed assessment request shows a retry message instead of asking for details again', async () => {
  ApiService.getFarmAssessment.mockRejectedValue(new Error('Unavailable'));
  mount();
  expect(await screen.findByRole('alert')).toHaveTextContent('Reload the page to retry');
  expect(screen.queryByRole('link', { name: 'Complete assessment' })).not.toBeInTheDocument();
});

test('switching farms shows the new farm assessment', async () => {
  let resolveSecond;
  ApiService.getFarmAssessment.mockResolvedValueOnce(assessment(8.3))
    .mockImplementationOnce(() => new Promise((resolve) => { resolveSecond = resolve; }));
  mount();
  await screen.findByText('8.3');
  fireEvent.change(screen.getByRole('combobox', { name: 'Choose farm' }), { target: { value: '2' } });
  await waitFor(() => expect(ApiService.getFarmAssessment).toHaveBeenLastCalledWith(2));
  expect(screen.queryByText('8.3')).not.toBeInTheDocument();
  await act(async () => resolveSecond(assessment(5)));
  expect(await screen.findByText('5.0')).toBeInTheDocument();
});
