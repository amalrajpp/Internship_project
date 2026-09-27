Streamlit Dashboard for Meetings

Overview
- Streamlit app that connects to an existing backend API to display meetings, transcripts, summaries, decisions, action items, participants, and analytics.
- Includes RAG-based assistant UI that sends natural-language questions to a semantic search / RAG endpoint and shows grounded answers with source meetings.

Setup
1. Create a Python virtualenv and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set environment variables (recommended via a `.env` file):
- `API_BASE_URL` — base URL for your backend API (e.g. `http://localhost:8000/api`)

Optional endpoints used by the app (the app is defensive; adapt as needed):
- POST `{API_BASE_URL}/auth/login` -> {"access_token": "..."}
- GET `{API_BASE_URL}/meetings`
- GET `{API_BASE_URL}/meetings/{id}`
- POST `{API_BASE_URL}/meetings/upload` (multipart/form-data)
- POST `{API_BASE_URL}/rag/query` -> accepts `question` and returns `answer`, `sources`

Run

```bash
streamlit run app.py
```

Testing & Verification
- Log in via the Login sidebar and ensure token is accepted.
- Upload a meeting file and verify it appears in the Meetings list.
- Select a meeting and verify transcript, summary, decisions, action items, participants and analytics appear.
- Use the "RAG Assistant" to ask questions; confirm answers include source meeting IDs and snippets.

Notes
- The app expects the backend to return JSON structures. Adjust the `api_client.py` to match your API's exact payload shapes.
