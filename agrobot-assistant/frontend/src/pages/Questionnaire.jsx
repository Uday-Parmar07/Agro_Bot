import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ChevronLeft, ChevronRight, Check, Loader } from 'lucide-react';
import ApiService from '../services/api';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import './Questionnaire.css';

const QUESTIONNAIRE_SECTION_TO_SET = {
  'soil-physical': 1,
  'soil-fertility': 2,
  irrigation: 3,
  environment: 4,
  practices: 5,
};

const Questionnaire = () => {
  const location = useLocation();
  const query = new URLSearchParams(location.search);
  const requestedSection = query.get('section');
  const requestedField = query.get('field');
  const refillMode = query.get('refill') === '1';
  const [currentSet, setCurrentSet] = useState(QUESTIONNAIRE_SECTION_TO_SET[requestedSection] || 1);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(false);
  const [showWelcome, setShowWelcome] = useState(!refillMode);
  const [generatingRecommendations, setGeneratingRecommendations] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState(null);
  
  const { user, updateUser } = useAuth();
  const voice = useVoiceRecorder();
  const navigate = useNavigate();

  useEffect(() => {
    if (!refillMode && !user?.is_new_user && user?.onboarding_completed) {
      navigate('/dashboard');
    }
  }, [user, navigate, refillMode]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowWelcome(false);
    }, 3000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const loadFarmContext = async () => {
      try {
        const farmList = await ApiService.getFarms();
        const requestedFarmId = Number(new URLSearchParams(location.search).get('farm_id'));
        const selected = farmList.find((farm) => farm.id === requestedFarmId) || farmList[0];
        setFarms(farmList);
        setSelectedFarmId(selected?.id || null);
        if (refillMode && selected?.id) {
          const saved = await ApiService.getUserQuestionnaireResponses(selected.id);
          const restored = {};
          Object.entries(saved || {}).forEach(([key, value]) => {
            restored[Number(key.replace('set_', ''))] = value;
          });
          setAnswers(restored);
        }
      } catch (error) {
        console.error('Unable to load farm questionnaire context:', error);
      }
    };
    loadFarmContext();
  }, [location.search, refillMode]);

  useEffect(() => {
    if (requestedSection && QUESTIONNAIRE_SECTION_TO_SET[requestedSection]) {
      setCurrentSet(QUESTIONNAIRE_SECTION_TO_SET[requestedSection]);
    }
  }, [requestedSection]);

  useEffect(() => {
    if (showWelcome || !requestedField) return undefined;
    const timer = setTimeout(() => {
      const target = document.getElementById(`question-${requestedField}`)
        || document.querySelector(`[data-question-id="${requestedField}"] input, [data-question-id="${requestedField}"] select`);
      target?.focus();
    }, 0);
    return () => clearTimeout(timer);
  }, [showWelcome, requestedField, currentSet]);

  const questionSets = {
    1: {
      title: "🧪 Soil Physical Properties",
      questions: [
        {
          id: 'soil_texture',
          question: 'What is the texture of your soil?',
          type: 'select',
          options: [
            { value: 'sandy', label: 'Sandy' },
            { value: 'loamy', label: 'Loamy' },
            { value: 'clayey', label: 'Clayey' },
            { value: 'silty', label: 'Silty' },
            { value: 'dont_know', label: "Don't Know" }
          ]
        },
        {
          id: 'water_retention',
          question: 'Does your soil retain water for a long time or does it drain quickly?',
          type: 'select',
          options: [
            { value: 'retains_long', label: 'Retains water for long time' },
            { value: 'drains_quickly', label: 'Drains quickly' },
            { value: 'moderate', label: 'Moderate drainage' }
          ]
        },
        {
          id: 'soil_top_layer',
          question: 'Is the top layer of your soil dark and crumbly or hard and compact?',
          type: 'select',
          options: [
            { value: 'dark_crumbly', label: 'Dark and crumbly' },
            { value: 'hard_compact', label: 'Hard and compact' },
            { value: 'mixed', label: 'Mixed condition' }
          ]
        }
      ]
    },
    2: {
      title: "🌱 Soil Fertility & Nutrients",
      questions: [
        {
          id: 'soil_test_done',
          question: 'Have you ever done a soil test?',
          type: 'radio',
          options: [
            { value: true, label: 'Yes' },
            { value: false, label: 'No' }
          ]
        },
        {
          id: 'npk_nitrogen',
          question: 'If yes, Nitrogen level (N):',
          type: 'number',
          conditional: 'soil_test_done',
          placeholder: 'Enter nitrogen level (kg/ha)'
        },
        {
          id: 'npk_phosphorus',
          question: 'Phosphorus level (P):',
          type: 'number',
          conditional: 'soil_test_done',
          placeholder: 'Enter phosphorus level (kg/ha)'
        },
        {
          id: 'npk_potassium',
          question: 'Potassium level (K):',
          type: 'number',
          conditional: 'soil_test_done',
          placeholder: 'Enter potassium level (kg/ha)'
        },
        {
          id: 'soil_ph',
          question: 'Soil pH level:',
          type: 'number',
          conditional: 'soil_test_done',
          placeholder: 'Enter soil pH (e.g., 6.5)'
        },
        {
          id: 'soil_test_date',
          question: 'When was this soil test performed?',
          type: 'date',
          conditional: 'soil_test_done',
          optional: true
        },
        {
          id: 'yellowing_slow_growth',
          question: 'Have you noticed yellowing or slow growth in crops recently?',
          type: 'radio',
          options: [
            { value: true, label: 'Yes' },
            { value: false, label: 'No' }
          ]
        },
        {
          id: 'fertilizer_type',
          question: 'What type of fertilizers have you been using?',
          type: 'select',
          options: [
            { value: 'organic', label: 'Organic' },
            { value: 'chemical', label: 'Chemical' },
            { value: 'both', label: 'Both' },
            { value: 'none', label: 'None' }
          ]
        }
      ]
    },
    3: {
      title: "💧 Moisture & Irrigation",
      questions: [
        {
          id: 'irrigation_type',
          question: 'How do you irrigate your land?',
          type: 'select',
          options: [
            { value: 'canal', label: 'Canal' },
            { value: 'borewell', label: 'Borewell' },
            { value: 'drip', label: 'Drip Irrigation' },
            { value: 'rainfed', label: 'Rainfed' },
            { value: 'sprinkler', label: 'Sprinkler' }
          ]
        },
        {
          id: 'watering_frequency',
          question: 'How often does your field get water?',
          type: 'select',
          options: [
            { value: 'daily', label: 'Daily' },
            { value: 'weekly', label: 'Weekly' },
            { value: 'bi_weekly', label: 'Bi-weekly' },
            { value: 'monthly', label: 'Monthly' },
            { value: 'rainfed', label: 'Only during rain' }
          ]
        },
        {
          id: 'water_availability',
          question: 'How reliable is water availability for the intended crop?',
          type: 'select',
          options: [
            { value: 'assured', label: 'Assured throughout the crop cycle' },
            { value: 'seasonal', label: 'Seasonal' },
            { value: 'limited', label: 'Limited' },
            { value: 'rainfed', label: 'Rainfall only' },
            { value: 'not_sure', label: 'Not sure' }
          ]
        }
      ]
    },
    4: {
      title: "🌍 Environmental & Regional",
      questions: [
        {
          id: 'state',
          question: 'In which state is your farm located?',
          type: 'text',
          placeholder: 'Enter your state'
        },
        {
          id: 'district',
          question: 'In which district is your farm located?',
          type: 'text',
          placeholder: 'Enter your district'
        },
        {
          id: 'average_rainfall',
          question: 'What is the average annual rainfall in your area? (millimetres per year)',
          type: 'number',
          placeholder: 'Enter average rainfall (optional)',
          helpText: 'Used as farm context only. The current crop model dataset does not document a matching rainfall period.',
          optional: true
        },
        {
          id: 'average_temperature',
          question: 'What is the average temperature in your area? (°C)',
          type: 'number',
          placeholder: 'Enter average temperature (optional)',
          optional: true
        },
        {
          id: 'total_area',
          question: 'What is the total area of all your fields combined?',
          type: 'number',
          placeholder: 'Enter total area'
        },
        {
          id: 'area_unit',
          question: 'Area unit:',
          type: 'select',
          options: [
            { value: 'acre', label: 'Acre' },
            { value: 'hectare', label: 'Hectare' },
            { value: 'bigha', label: 'Bigha' }
          ]
        },
        {
          id: 'season',
          question: 'Which growing season are you planning for?',
          type: 'select',
          options: [
            { value: 'kharif', label: 'Kharif' },
            { value: 'rabi', label: 'Rabi' },
            { value: 'zaid', label: 'Zaid' },
            { value: 'year_round', label: 'Year-round' },
            { value: 'not_sure', label: 'Not sure' }
          ]
        },
        {
          id: 'intended_sowing_date',
          question: 'Intended sowing date (optional)',
          type: 'date',
          optional: true
        }
      ]
    },
    5: {
      title: "🌿 Organic Matter & Practices",
      questions: [
        {
          id: 'uses_organic_matter',
          question: 'Do you use compost, green manure, or animal dung in your field?',
          type: 'radio',
          options: [
            { value: true, label: 'Yes' },
            { value: false, label: 'No' }
          ]
        },
        {
          id: 'organic_matter_types',
          question: 'Which organic matter do you use?',
          type: 'checkbox',
          conditional: 'uses_organic_matter',
          options: [
            { value: 'compost', label: 'Compost' },
            { value: 'green_manure', label: 'Green Manure' },
            { value: 'animal_dung', label: 'Animal Dung' }
          ]
        },
        {
          id: 'crop_residue_practice',
          question: 'Do you leave crop residues in the field or burn them?',
          type: 'select',
          options: [
            { value: 'leave_in_field', label: 'Leave in field' },
            { value: 'burn', label: 'Burn them' },
            { value: 'remove', label: 'Remove from field' },
            { value: 'compost', label: 'Make compost' }
          ]
        },
        {
          id: 'earthworms_present',
          question: 'Have you noticed earthworms in your soil recently?',
          type: 'radio',
          options: [
            { value: true, label: 'Yes' },
            { value: false, label: 'No' }
          ]
        },
        {
          id: 'previous_crop',
          question: 'What crop was previously grown here?',
          type: 'text',
          optional: true,
          placeholder: 'Enter crop name or Not sure'
        },
        {
          id: 'farmer_goal',
          question: 'What is your main goal for the next crop?',
          type: 'select',
          options: [
            { value: 'food_security', label: 'Household food security' },
            { value: 'market_sale', label: 'Market sale' },
            { value: 'soil_improvement', label: 'Soil improvement' },
            { value: 'lower_water_use', label: 'Lower water use' },
            { value: 'not_sure', label: 'Not sure' }
          ]
        }
      ]
    }
  };

  const handleAnswerChange = (questionId, value) => {
    setAnswers(prev => ({
      ...prev,
      [currentSet]: {
        ...prev[currentSet],
        [questionId]: value
      }
    }));
  };

  const handleFarmChange = async (farmId) => {
    setSelectedFarmId(farmId);
    setCurrentSet(1);
    try {
      const saved = await ApiService.getUserQuestionnaireResponses(farmId);
      const restored = {};
      Object.entries(saved || {}).forEach(([key, value]) => {
        restored[Number(key.replace('set_', ''))] = value;
      });
      setAnswers(restored);
    } catch (error) {
      setAnswers({});
    }
  };

  const handleNext = async () => {
    setLoading(true);
    
    try {
      // Submit current set answers
      await ApiService.submitQuestionnaireSet(
        currentSet,
        answers[currentSet] || {},
        user.id,
        selectedFarmId
      );

      if (currentSet < 5) {
        setCurrentSet(currentSet + 1);
      } else {
        // Complete questionnaire
        await handleComplete();
      }
    } catch (error) {
      console.error('Error submitting answers:', error);
    }
    
    setLoading(false);
  };

  const handleComplete = async () => {
    try {
      setGeneratingRecommendations(true);
      
      // Complete questionnaire
      await ApiService.completeQuestionnaire({
        user_id: user.id,
        farm_id: selectedFarmId,
        soil_physical: answers[1] || {},
        soil_fertility: answers[2] || {},
        moisture_irrigation: answers[3] || {},
        environmental: answers[4] || {},
        organic_practices: answers[5] || {}
      });
      
      // Generate AI recommendations
      try {
        await ApiService.generateRecommendations(selectedFarmId);
      } catch (aiError) {
        console.error('❌ AI recommendation error:', aiError);
        console.error('Error details:', aiError.response?.data);
      }

      // Update user state
      updateUser({
        ...user,
        onboarding_completed: true,
        is_new_user: false
      });

      navigate('/dashboard');
    } catch (error) {
      console.error('❌ Error completing questionnaire:', error);
      console.error('Error response:', error.response?.data);
      alert('Error: ' + (error.response?.data?.detail || error.message));
    } finally {
      setGeneratingRecommendations(false);
    }
  };

  const handlePrevious = () => {
    if (currentSet > 1) {
      setCurrentSet(currentSet - 1);
    }
  };

  const handleVoiceForQuestion = async (questionId) => {
    if (!voice.recording) {
      await voice.start();
      return;
    }
    const transcript = await voice.stop();
    setVoiceTranscript(transcript);
    if (transcript) {
      handleAnswerChange(questionId, transcript);
    }
  };

  const isSetComplete = () => {
    const currentQuestions = questionSets[currentSet].questions;
    const currentAnswers = answers[currentSet] || {};
    
    return currentQuestions.every(question => {
      if (question.conditional) {
        const conditionalValue = currentAnswers[question.conditional];
        if (!conditionalValue) return true; // Skip if conditional not met
      }
      
      // For required questions, check if answer exists
      if (question.type === 'checkbox' || question.optional) {
        return true; // Checkbox questions are optional
      }
      
      return currentAnswers[question.id] !== undefined && currentAnswers[question.id] !== '';
    });
  };

  if (showWelcome) {
    return (
      <div className="welcome-screen">
        <div className="welcome-content">
          <h1>Welcome to AgroBot! 🌱</h1>
          <p>Let's get to know your farm better to provide personalized recommendations.</p>
          <div className="welcome-animation">
            <div className="pulse-circle"></div>
          </div>
        </div>
      </div>
    );
  }

  if (generatingRecommendations) {
    return (
      <div className="welcome-screen">
        <div className="welcome-content">
          <Loader className="animate-spin mx-auto mb-4" size={48} />
          <h1>Generating Your Personalized Recommendations</h1>
          <p>Our AI is analyzing your farm data to create the perfect farming plan...</p>
          <div className="welcome-animation">
            <div className="pulse-circle"></div>
          </div>
        </div>
      </div>
    );
  }

  const currentQuestionSet = questionSets[currentSet];

  return (
    <div className="questionnaire-container">
      <div className="questionnaire-header">
        {farms.length > 1 && (
          <label className="questionnaire-farm-select">
            Farm
            <select value={selectedFarmId || ''} onChange={(event) => handleFarmChange(Number(event.target.value))}>
              {farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
            </select>
          </label>
        )}
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${(currentSet / 5) * 100}%` }}
          ></div>
        </div>
        <div className="step-indicator">
          Step {currentSet} of 5
        </div>
      </div>

      <div className="questionnaire-content">
        <div className="question-set">
          <h2>{currentQuestionSet.title}</h2>
          
          <div className="questions">
            {currentQuestionSet.questions.map((question) => {
              const shouldShow = !question.conditional || 
                answers[currentSet]?.[question.conditional];
              
              if (!shouldShow) return null;

              return (
                <div key={question.id} className="question-item" data-question-id={question.id}>
                  <label className="question-label">
                    {question.question}
                  </label>
                  
                  {question.type === 'select' && (
                    <select
                      id={`question-${question.id}`}
                      value={answers[currentSet]?.[question.id] || ''}
                      onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                      className="question-select"
                    >
                      <option value="">Select an option</option>
                      {question.options.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  )}

                  {question.type === 'radio' && (
                    <div className="radio-group">
                      {question.options.map((option) => (
                        <label key={option.value} className="radio-option">
                          <input
                            id={`question-${question.id}-${option.value}`}
                            type="radio"
                            name={question.id}
                            value={option.value}
                            checked={answers[currentSet]?.[question.id] === option.value}
                            onChange={(e) => handleAnswerChange(question.id, option.value)}
                          />
                          <span className="radio-label">{option.label}</span>
                        </label>
                      ))}
                    </div>
                  )}

                  {question.type === 'checkbox' && (
                    <div className="checkbox-group">
                      {question.options.map((option) => (
                        <label key={option.value} className="checkbox-option">
                          <input
                            type="checkbox"
                            checked={(answers[currentSet]?.[question.id] || []).includes(option.value)}
                            onChange={(e) => {
                              const currentValues = answers[currentSet]?.[question.id] || [];
                              const newValues = e.target.checked
                                ? [...currentValues, option.value]
                                : currentValues.filter(v => v !== option.value);
                              handleAnswerChange(question.id, newValues);
                            }}
                          />
                          <span className="checkbox-label">{option.label}</span>
                        </label>
                      ))}
                    </div>
                  )}

                  {(question.type === 'text' || question.type === 'number' || question.type === 'date') && (
                    <div className="voice-input-row">
                      <input
                        id={`question-${question.id}`}
                        type={question.type}
                        value={answers[currentSet]?.[question.id] || ''}
                        onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                        placeholder={question.placeholder}
                        className="question-input"
                      />
                      {question.type !== 'date' && <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => handleVoiceForQuestion(question.id)}
                      >
                        {voice.recording ? 'Use transcript' : 'Voice'}
                      </button>}
                    </div>
                  )}
                  {question.helpText && <p className="question-help">{question.helpText}</p>}
                  {voice.error && <p className="voice-note">{voice.error}</p>}
                  {voiceTranscript && <p className="voice-note">Transcript: {voiceTranscript}</p>}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="questionnaire-footer">
        <button
          onClick={handlePrevious}
          disabled={currentSet === 1}
          className="btn btn-secondary"
        >
          <ChevronLeft size={20} />
          Previous
        </button>

        <button
          onClick={handleNext}
          disabled={!selectedFarmId || !isSetComplete() || loading}
          className="btn btn-primary"
        >
          {loading ? (
            <>
              <Loader className="animate-spin" size={20} />
              Saving...
            </>
          ) : currentSet === 5 ? (
            <>
              Complete & Generate AI Plan
              <Check size={20} />
            </>
          ) : (
            <>
              Next
              <ChevronRight size={20} />
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default Questionnaire;
