# AI Job Search Assistant

A Python and Streamlit application designed to help job seekers analyze resumes, understand job requirements, and organize their job applications.

## Features

- **Resume Upload:** Upload resumes in PDF and DOCX formats.
- **Keyword Coverage:** Compare resume keywords with a job description to identify potential skill gaps. This is keyword-based analysis, not an official ATS score.
- **AI-Powered Career Advice:** Generate role-specific feedback and interview preparation suggestions using the Gemini API.
- **Job Description Analyzer:** Analyze job requirements to distinguish essential and preferred skills.
- **Downloadable Reports:** Download analysis results for later reference.
- **Job Application Tracker:** Organize application details and export records to CSV.

## Technology Stack

- Python
- Streamlit
- Google Gemini API
- SQLite
- Pandas
- PyPDF
- python-docx

## Getting Started

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd "AI JOB SEARCH ASSISTANT"
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with the repository URL.

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure the Gemini API key

Create `.streamlit/secrets.toml` and add your own API key:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
```

Never commit this file or publish your API key.

### 5. Run the application

```powershell
python -m streamlit run app.py
```

Open the local URL shown in the terminal.

## Limitations

- AI features require a valid Gemini API key and available API quota.
- AI results may vary and should be reviewed before use.
- Keyword coverage is not an official ATS score or a prediction of hiring outcomes.
- Feature behavior should be verified in the target environment before production use.

## Future Improvements

- Automated job discovery and filtering
- Enhanced resume-to-job matching
- Persistent application tracking
- Improved error handling and testing
- Cloud deployment

## Security

API keys, local databases, virtual environments, and backup files should not be committed to the public repository.

## Status

Personal project under development.
