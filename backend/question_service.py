import random
import time
from typing import Dict, List

from llm_client import LLMClient
from question_bank import COMMON_QUESTIONS, ROLE_QUESTIONS


SYSTEM_DYNAMIC_QUESTION_PROMPT = """你是面试官，请根据岗位生成面试问题。
要求：
1) 问题适合高职/大专学生求职场景
2) 包含通用素质题和岗位技能题
3) 每题简短清晰，避免重复
4) 返回严格JSON格式：
{
  "questions": [
    {"id": "q1", "text": "问题内容"}
  ]
}
"""


def _clean_questions(raw: List[dict], count: int) -> List[Dict[str, str]]:
    cleaned: List[Dict[str, str]] = []
    seen = set()
    for i, item in enumerate(raw, start=1):
        text = str(item.get("text", "")).strip()
        if not text or text in seen:
            continue
        qid = str(item.get("id", "")).strip() or f"q{i}"
        cleaned.append({"id": qid, "text": text})
        seen.add(text)
        if len(cleaned) >= count:
            break
    return cleaned


def _fallback_dynamic_questions(role: str, count: int, session_key: str) -> List[Dict[str, str]]:
    # Keep some consistency during a short time window while still changing over time.
    minute_bucket = int(time.time() // 300)  # 5-minute window
    seed_text = f"{role}|{session_key}|{minute_bucket}"
    rng = random.Random(seed_text)

    common_pool = list(COMMON_QUESTIONS)
    role_pool = list(ROLE_QUESTIONS.get(role, []))
    rng.shuffle(common_pool)
    rng.shuffle(role_pool)

    # Prefer role-specific questions while keeping some general interview questions.
    common_take = min(3, max(2, count // 3))
    role_take = max(0, count - common_take)

    picked = role_pool[:role_take] + common_pool[:common_take]
    if len(picked) < count:
        extra_pool = role_pool[role_take:] + common_pool[common_take:]
        picked.extend(extra_pool[: max(0, count - len(picked))])

    rng.shuffle(picked)
    return picked[:count]


def generate_questions(role: str, count: int = 6, session_key: str = "") -> Dict:
    count = max(4, min(12, int(count)))
    client = LLMClient()

    if client.available():
        user_prompt = (
            f"岗位：{role}\n"
            f"请生成 {count} 个面试问题。\n"
            "要求覆盖：自我认知、求职动机、岗位技能、抗压协作、数据或结果导向。"
        )
        result = client.chat_json(
            SYSTEM_DYNAMIC_QUESTION_PROMPT,
            user_prompt,
            max_tokens=420,
            enable_thinking=False,
        )
        if result and isinstance(result.get("questions"), list):
            questions = _clean_questions(result["questions"], count)
            if questions:
                return {
                    "questions": questions,
                    "engine": "llm",
                    "llm_provider": client.provider,
                }

    questions = _fallback_dynamic_questions(role, count, session_key)
    return {
        "questions": questions,
        "engine": "fallback",
        "llm_provider": client.provider,
        "llm_error": client.last_error or "dynamic question generation failed",
    }
