from typing import Dict, List

from llm_client import LLMClient


SYSTEM_SCORING_PROMPT = """你是面试评分官。请根据问题和回答进行0-100评分。
评分维度：
1) 回答完整性
2) 逻辑性
3) 岗位匹配度

返回JSON，格式如下：
{
  "results": [
    {
      "question_id": "xxx",
      "score": 88,
      "reason": "一句话说明"
    }
  ]
}
"""


SYSTEM_FEEDBACK_PROMPT = """你是面试教练。请针对每个问题给出1-2句简短改进建议。
返回JSON，格式如下：
{
  "feedback": [
    {
      "question_id": "xxx",
      "suggestion": "简短建议"
    }
  ]
}
"""


def _fallback_score(answer: str) -> int:
    text = answer.strip()
    if not text:
        return 20
    length = len(text)
    if length < 20:
        return 45
    if length < 50:
        return 62
    if length < 120:
        return 76
    if length < 220:
        return 85
    return 92


def _fallback_suggestion(answer: str) -> str:
    text = answer.strip()
    if not text:
        return "先给出明确结论，再补充1个真实经历和结果。"
    if len(text) < 40:
        return "回答偏短，建议补充具体场景、做法和量化结果。"
    if "我觉得" in text and "因为" not in text:
        return "建议增加“为什么这样做”的因果逻辑，提升说服力。"
    return "可再补充岗位相关案例，并用数据结果证明你的能力。"


def score_answers(role: str, qa_list: List[Dict[str, str]]) -> Dict:
    client = LLMClient()
    if client.available():
        user_prompt = f"岗位：{role}\n问答：{qa_list}"
        result = client.chat_json(SYSTEM_SCORING_PROMPT, user_prompt)
        if result and isinstance(result.get("results"), list):
            scored = []
            for item in result["results"]:
                qid = str(item.get("question_id", "")).strip()
                score = int(item.get("score", 0))
                reason = str(item.get("reason", "")).strip()
                scored.append(
                    {
                        "question_id": qid,
                        "score": max(0, min(100, score)),
                        "reason": reason or "模型未返回原因",
                    }
                )
            summary = _build_score_summary(scored)
            summary["engine"] = "llm"
            summary["llm_provider"] = client.provider
            return summary

    # 兜底评分
    scored = []
    for qa in qa_list:
        score = _fallback_score(qa["answer"])
        scored.append(
            {
                "question_id": qa["question_id"],
                "score": score,
                "reason": "基于回答完整度与表达清晰度的基础评分",
            }
        )
    summary = _build_score_summary(scored)
    summary["engine"] = "fallback"
    summary["llm_provider"] = client.provider
    summary["llm_error"] = client.last_error or "unknown llm error"
    return summary


def _build_score_summary(scored: List[Dict]) -> Dict:
    if not scored:
        return {"question_results": [], "average_score": 0, "role_fitness": 0}
    avg_score = round(sum(item["score"] for item in scored) / len(scored), 1)
    role_fitness = round(avg_score * 0.9 + 5, 1)
    role_fitness = max(0, min(100, role_fitness))
    return {
        "question_results": scored,
        "average_score": avg_score,
        "role_fitness": role_fitness,
    }


def generate_feedback(role: str, qa_list: List[Dict[str, str]]) -> Dict:
    client = LLMClient()
    if client.available():
        user_prompt = f"岗位：{role}\n问答：{qa_list}"
        result = client.chat_json(SYSTEM_FEEDBACK_PROMPT, user_prompt)
        if result and isinstance(result.get("feedback"), list):
            items = []
            for item in result["feedback"]:
                items.append(
                    {
                        "question_id": str(item.get("question_id", "")).strip(),
                        "suggestion": str(item.get("suggestion", "")).strip()
                        or "建议补充更具体的经历和结果。",
                    }
                )
            return {
                "feedback": items,
                "engine": "llm",
                "llm_provider": client.provider,
            }

    fallback = []
    for qa in qa_list:
        fallback.append(
            {
                "question_id": qa["question_id"],
                "suggestion": _fallback_suggestion(qa["answer"]),
            }
        )
    return {
        "feedback": fallback,
        "engine": "fallback",
        "llm_provider": client.provider,
        "llm_error": client.last_error or "unknown llm error",
    }
