# WeeklySAUpdate

This repo contains utilities for weekly partner status updates and outreach.

## Installation

1. Ensure Python 3.12+ is available.
2. Install the required packages:
   ```bash
   pip install -r requirement.txt
   pip install openai google-search-results python-dotenv
   ```

## Environment Variables

PGAgent and other scripts expect the following keys:

- `OPENAI_API_KEY` – OpenAI API token
- `SERPAPI_KEY` – SerpAPI token for Google search

Set them in your shell or create a `.env` file:

```bash
export OPENAI_API_KEY=your-openai-key
export SERPAPI_KEY=your-serpapi-key
# or in .env
OPENAI_API_KEY=your-openai-key
SERPAPI_KEY=your-serpapi-key
```

## Running the Streamlit App

Launch the email builder with:

```bash
streamlit run PartnerStatusEmail.py
```

Open the provided URL (usually `http://localhost:8501`) to build your weekly
partner-status email.
