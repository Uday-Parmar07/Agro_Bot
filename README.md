# Agrobot

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)

---

## Overview

Agrobot is an AI-powered agricultural assistant platform designed to empower farmers with personalized, data-driven insights to optimize crop yields, resource usage, and sustainable farming practices. Leveraging state-of-the-art AI models deployed on Groq Cloud, Agrobot delivers real-time recommendations for crop selection, irrigation scheduling, fertilizer application, and pest management.

## Features

- Personalized crop recommendations based on soil, environmental, and user-input data.
- Dynamic farming calendar with actionable tasks and alerts.
- Real-time monitoring and management of crop health.
- Integration with IoT sensors and weather data for adaptive advice.
- Scalable architecture supporting thousands of concurrent users.
- Multilingual support and mobile-friendly interface.

## Technology Stack

- **Backend:** FastAPI, SQLAlchemy, Groq Cloud AI inference
- **Frontend:** React, Lucide React icons
- **Database:** SQLite (development), PostgreSQL (production-ready)
- **AI Models:** Llama-3 series via Groq Cloud
- **APIs:** OpenWeatherMap, Pinecone for vector search

## How to Run?

### Backend

1. cd backend
2. python -m venv venv
3. **On Linux/Macos** source venv/bin/activate
4. **On Windows** venv\Scripts\activate    
5. pip install -r requirements.txt
6. uvicorn app.main:app

### Frontend

1. cd frontend
2. npm install
3.  npm start


## Usage

1. Sign up and complete the onboarding questionnaire.
2. Receive AI-generated personalized farming recommendations.
3. Add and monitor crops using the dashboard.
4. Get real-time alerts and updates based on sensor and weather data.

## API Endpoints

- `/api/auth`: Authentication routes (signup, login, user info)
- `/api/questionnaire`: Submit and complete questionnaire data
- `/api/recommendations`: Generate and fetch AI recommendations

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests for improvements or bug fixes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please contact me at my mail : "nirwana12anubhav@gmail.com"

