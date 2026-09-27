Mock FastAPI backend for the Streamlit Meetings Dashboard

Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Endpoints (mocked)
- POST `/api/auth/login` -> {"access_token": "mock-token-123"}
- GET `/api/meetings` -> list of meetings
- GET `/api/meetings/{id}` -> meeting details
- POST `/api/meetings/upload` -> multipart upload file + form `title`, `date`
- POST `/api/rag/query` -> body `{"question": "...", "top_k": 3}` returns `{answer, sources}`

The server persists meetings to `data.json` in this folder.
