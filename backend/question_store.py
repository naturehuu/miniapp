import copy
import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List

from question_bank import ROLE_QUESTIONS


STORE_PATH = os.path.join(os.path.dirname(__file__), "data", "questions_store.json")
_LOCK = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_questions(raw: List[dict]) -> List[Dict[str, str]]:
    questions = []
    seen = set()
    for i, item in enumerate(raw, start=1):
        text = str(item.get("text", "")).strip()
        if not text or text in seen:
            continue
        qid = str(item.get("id", "")).strip() or f"q{i}"
        questions.append({"id": qid, "text": text})
        seen.add(text)
    return questions


def _default_store() -> Dict:
    now = _utc_now()
    role_map = {}
    for role, questions in ROLE_QUESTIONS.items():
        role_map[role] = {
            "updated_at": now,
            "questions": _normalize_questions(questions),
        }
    return {"roles": role_map}


def _ensure_store_file() -> None:
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    if not os.path.exists(STORE_PATH):
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(_default_store(), f, ensure_ascii=False, indent=2)


def _read_store_unlocked() -> Dict:
    _ensure_store_file()
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("roles"), dict):
                return data
    except Exception:
        pass
    data = _default_store()
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def _write_store_unlocked(data: Dict) -> None:
    _ensure_store_file()
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_supported_roles() -> List[str]:
    with _LOCK:
        data = _read_store_unlocked()
        roles = list(data.get("roles", {}).keys())
    return roles


def get_questions_by_role(role: str) -> Dict:
    with _LOCK:
        data = _read_store_unlocked()
        role_map = data.get("roles", {})
        role_data = role_map.get(role)
        if not role_data:
            role_map[role] = {"updated_at": _utc_now(), "questions": []}
            _write_store_unlocked(data)
            role_data = role_map[role]
    return copy.deepcopy(role_data)


def save_questions_by_role(role: str, questions: List[dict]) -> Dict:
    normalized = _normalize_questions(questions)
    with _LOCK:
        data = _read_store_unlocked()
        role_map = data.setdefault("roles", {})
        role_map[role] = {"updated_at": _utc_now(), "questions": normalized}
        _write_store_unlocked(data)
    return {"updated_at": role_map[role]["updated_at"], "questions": normalized}
