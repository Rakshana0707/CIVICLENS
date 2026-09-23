# CivicLens TN

## What is CivicLens TN?
CivicLens TN is an AI-powered public accountability and policy intelligence platform specifically focused on the state of Tamil Nadu. 

## Purpose of the Project
The goal of CivicLens TN is to enhance transparency and understanding of political processes, policy implementations, and civic issues. It aims to empower citizens, journalists, and researchers with AI-driven insights into state policies, political promises, public spending, and more.

## Major Planned Modules
- Budget Analysis
- Historical Scheme Intelligence
- Political Promise Analysis
- Tamil News Framing Analysis
- Representative Performance
- Political Funding Transparency
- Claim Verification
- Explainability
- Reinforcement-Learning Recommendation Module (Optional)

## Planned ML Categories
- Natural Language Processing (NLP) for Tamil news and text analysis
- Embedding Generation for semantic search and claim matching
- Classification & Information Extraction for promises and budget data
- Recommendation Systems

## Project Directory Structure
- `backend/`: Python-based backend application containing APIs, database models, NLP pipelines, and business logic.
- `frontend/`: User interface modules, pages, and components.
- `data/`: Data storage separated into raw, processed, and external datasets.
- `ml/`: Machine learning models, training scripts, evaluation metrics, and embeddings.
- `tests/`: Automated tests for ensuring code reliability.
- `docs/`: Project documentation and guidelines.
- `scripts/`: Utility and maintenance scripts.
- `config/`: Configuration files for the platform.

## Implementation Note
Implementation of the various modules (budget, promises, news, etc.) will be done incrementally. This repository currently contains the foundational structure.

## Setup and Development Guide

Follow these steps to set up the local development environment:

### 1. Create the Virtual Environment
Navigate to the project root and create a Python virtual environment:
```bash
python -m venv venv
```

### 2. Activate the Virtual Environment
- On **Windows**:
  ```bash
  .\venv\Scripts\activate
  ```
- On **macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies
The project maintains a separation between runtime and development dependencies.
To install the dependencies for development (which includes runtime dependencies):
```bash
pip install -r requirements-dev.txt
```
For a production environment, you would only run `pip install -r requirements.txt`.

### 4. Configure Environment Variables
Copy the example environment file and configure your local settings:
```bash
# On Windows
copy .env.example .env

# On macOS/Linux
cp .env.example .env
```
Ensure you do not commit the `.env` file to version control, as it may contain sensitive information.

### 5. Run the Project
*Note: The application modules are currently under development. At this foundation stage, there is no active server to run.*

In the future, you will be able to start the backend API using:
```bash
# Example for Flask API
flask run
```
