import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ChevronLeft, ChevronRight, Check, Loader } from 'lucide-react';
import ApiService from '../services/api';
import './Questionnaire.css';

const Questionnaire = () => {
  const [currentSet, setCurrentSet] = useState(1);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);
  const [generatingRecommendations, setGeneratingRecommendations] = useState(false);
  
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const refillMode = new URLSearchParams(location.search).get('refill') === '1';

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
          question: 'What is the average rainfall in your area? (mm per year)',
          type: 'number',
          placeholder: 'Enter average rainfall (optional)'
        },
        {
          id: 'average_temperature',
          question: 'What is the average temperature in your area? (°C)',
          type: 'number',
          placeholder: 'Enter average temperature (optional)'
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

  const handleNext = async () => {
    setLoading(true);
    
    try {
      // Submit current set answers
      await ApiService.submitQuestionnaireSet(
        currentSet,
        answers[currentSet] || {},
        user.id
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
      
      console.log('=== Starting questionnaire completion ===');
      console.log('User ID:', user.id);
      console.log('All answers:', answers);
      
      // Complete questionnaire
      console.log('Step 1: Completing questionnaire...');
      const completeResponse = await ApiService.completeQuestionnaire({
        user_id: user.id,
        soil_physical: answers[1] || {},
        soil_fertility: answers[2] || {},
        moisture_irrigation: answers[3] || {},
        environmental: answers[4] || {},
        organic_practices: answers[5] || {}
      });
      
      console.log('✅ Questionnaire completed:', completeResponse);

      // Generate AI recommendations
      console.log('Step 2: Generating AI recommendations...');
      try {
        const recommendations = await ApiService.generateRecommendations();
        console.log('✅ AI recommendations generated successfully:', recommendations);
      } catch (aiError) {
        console.error('❌ AI recommendation error:', aiError);
        console.error('Error details:', aiError.response?.data);
      }

      // Update user state
      console.log('Step 3: Updating user state...');
      updateUser({
        ...user,
        onboarding_completed: true,
        is_new_user: false
      });

      console.log('Step 4: Navigating to dashboard...');
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

  const isSetComplete = () => {
    const currentQuestions = questionSets[currentSet].questions;
    const currentAnswers = answers[currentSet] || {};
    
    return currentQuestions.every(question => {
      if (question.conditional) {
        const conditionalValue = currentAnswers[question.conditional];
        if (!conditionalValue) return true; // Skip if conditional not met
      }
      
      // For required questions, check if answer exists
      if (question.type === 'checkbox') {
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
                <div key={question.id} className="question-item">
                  <label className="question-label">
                    {question.question}
                  </label>
                  
                  {question.type === 'select' && (
                    <select
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

                  {(question.type === 'text' || question.type === 'number') && (
                    <input
                      type={question.type}
                      value={answers[currentSet]?.[question.id] || ''}
                      onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                      placeholder={question.placeholder}
                      className="question-input"
                    />
                  )}
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
          disabled={!isSetComplete() || loading}
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
