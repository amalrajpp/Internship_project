import json
import uuid
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data.json"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_data() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: List[Dict[str, Any]]):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class LoginPayload(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(p: LoginPayload):
    # Mock auth: accept any username/password and return a fake token
    return {"access_token": "mock-token-123"}


@app.get("/api/meetings")
def list_meetings():
    data = load_data()
    # Return lightweight meeting list
    return [{"id": m.get("id"), "title": m.get("title"), "date": m.get("date"), "participants": m.get("participants")} for m in data]


@app.get("/api/meetings/{meeting_id}")
def get_meeting(meeting_id: str):
    data = load_data()
    for m in data:
        if m.get("id") == meeting_id:
            return m
    raise HTTPException(status_code=404, detail="Meeting not found")


@app.post("/api/meetings/upload")
def upload_meeting(file: UploadFile = File(None), title: str = Form(None), date: str = Form(None)):
    data = load_data()
    new_id = f"m{uuid.uuid4().hex[:8]}"
    transcript = None
    if file is not None:
        content = file.file.read().decode("utf-8", errors="ignore")
        transcript = content
    meeting = {
        "id": new_id,
        "title": title or f"Uploaded {new_id}",
        "date": date or "",
        "participants": [],
        "transcript": transcript or "",
        "summary": "",
        "decisions": [],
        "action_items": [],
        "analytics": {}
    }
    data.append(meeting)
    save_data(data)
    return meeting


@app.post("/api/rag/query")
def rag_query(question: Dict[str, Any]):
    # Accept body like {"question": "...", "top_k": 3}
    q = question.get("question")
    top_k = int(question.get("top_k", 5))
    if not q:
        raise HTTPException(status_code=400, detail="Question is required")
    data = load_data()
    docs = [m.get("transcript", "") or m.get("summary", "") for m in data]
    if not any(docs):
        return {"answer": "No documents indexed.", "sources": []}

    # Lightweight token-overlap semantic search (no heavy deps)
    def tokenize(text: str):
        return re.findall(r"\\w+", (text or "").lower())

    q_tokens = set(tokenize(q))
    scores = []
    for i, doc in enumerate(docs):
        doc_tokens = tokenize(doc)
        if not doc_tokens:
            scores.append((i, 0.0))
            continue
        overlap = len(q_tokens.intersection(doc_tokens))
        score = overlap / max(1, len(set(doc_tokens)))
        scores.append((i, float(score)))

    scores.sort(key=lambda x: x[1], reverse=True)
    sources = []
    combined_snippets = []
    for idx, score in scores[:top_k]:
        if score <= 0:
            continue
        m = data[idx]
        snippet = (m.get("transcript") or m.get("summary") or "")[:400]
        sources.append({"meeting_id": m.get("id"), "date": m.get("date"), "snippet": snippet, "score": score})
        combined_snippets.append(snippet)

    if combined_snippets:
        answer = "Based on the retrieved meetings, here are relevant excerpts:\n\n" + "\n\n---\n\n".join(combined_snippets)
    else:
        answer = "No relevant content found."
    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
