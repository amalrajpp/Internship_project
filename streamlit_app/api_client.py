import os
import requests
from typing import Optional, Dict, Any
from requests import Response
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")

class APIError(Exception):
    pass


def _handle_response(r: Response) -> Any:
    try:
        data = r.json()
    except ValueError:
        r.raise_for_status()
    if not r.ok:
        msg = data.get("detail") if isinstance(data, dict) else r.text
        raise APIError(msg)
    return data


def login(username: str, password: str) -> Dict[str, Any]:
    url = f"{API_BASE}/auth/login"
    r = requests.post(url, json={"username": username, "password": password})
    return _handle_response(r)


def list_meetings(token: Optional[str] = None, params: Dict[str, Any] = None):
    url = f"{API_BASE}/meetings"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get(url, headers=headers, params=params)
    return _handle_response(r)


def get_meeting(meeting_id: str, token: Optional[str] = None):
    url = f"{API_BASE}/meetings/{meeting_id}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get(url, headers=headers)
    return _handle_response(r)


def upload_meeting(file_obj, metadata: Dict[str, Any] = None, token: Optional[str] = None):
    url = f"{API_BASE}/meetings/upload"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    files = {"file": file_obj}
    data = metadata or {}
    r = requests.post(url, headers=headers, files=files, data=data)
    return _handle_response(r)


def rag_query(question: str, token: Optional[str] = None, top_k: int = 5):
    url = f"{API_BASE}/rag/query"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"} if token else {"Content-Type": "application/json"}
    payload = {"question": question, "top_k": top_k}
    r = requests.post(url, headers=headers, json=payload)
    return _handle_response(r)
