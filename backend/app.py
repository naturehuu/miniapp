import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from llm_client import normalize_answers
from question_service import generate_questions
from question_store import (
    get_questions_by_role,
    get_supported_roles,
    save_questions_by_role,
)
from scoring_service import generate_feedback, score_answers


ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH, override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = Flask(__name__)
CORS(app)
logger = logging.getLogger("app")


@app.get("/health")
def health():
    return jsonify(
        {
            "ok": True,
            "llm_provider": os.getenv("LLM_PROVIDER", "mock"),
            "port": os.getenv("FLASK_PORT", "5000"),
        }
    )


@app.get("/get_questions")
def get_questions():
    role = request.args.get("role", "").strip()
    if not role:
        return jsonify({"error": "role is required"}), 400

    role_data = get_questions_by_role(role)
    questions = role_data.get("questions", [])
    logger.info(
        "get_questions role=%s count=%s engine=store",
        role,
        len(questions),
    )
    return jsonify(
        {
            "role": role,
            "questions": questions,
            "supported_roles": get_supported_roles(),
            "engine": "store",
            "updated_at": role_data.get("updated_at", ""),
        }
    )


@app.post("/submit_answers")
def submit_answers():
    data = request.get_json(silent=True) or {}
    role = str(data.get("role", "")).strip()
    answers = data.get("answers", [])
    if not role:
        return jsonify({"error": "role is required"}), 400
    if not isinstance(answers, list):
        return jsonify({"error": "answers must be list"}), 400

    role_data = get_questions_by_role(role)
    questions = role_data.get("questions", [])
    qa_list = normalize_answers(answers, questions)
    result = score_answers(role, qa_list)
    return jsonify(result)


@app.post("/get_feedback")
def get_feedback():
    data = request.get_json(silent=True) or {}
    role = str(data.get("role", "")).strip()
    answers = data.get("answers", [])
    if not role:
        return jsonify({"error": "role is required"}), 400
    if not isinstance(answers, list):
        return jsonify({"error": "answers must be list"}), 400

    role_data = get_questions_by_role(role)
    questions = role_data.get("questions", [])
    qa_list = normalize_answers(answers, questions)
    result = generate_feedback(role, qa_list)
    return jsonify(result)


@app.get("/admin/questions")
def admin_get_questions():
    role = request.args.get("role", "").strip()
    if not role:
        return jsonify({"error": "role is required"}), 400
    role_data = get_questions_by_role(role)
    return jsonify(
        {
            "role": role,
            "questions": role_data.get("questions", []),
            "updated_at": role_data.get("updated_at", ""),
            "supported_roles": get_supported_roles(),
        }
    )


@app.post("/admin/generate_questions")
def admin_generate_questions():
    data = request.get_json(silent=True) or {}
    role = str(data.get("role", "")).strip()
    try:
        count = int(data.get("count", 6))
    except (TypeError, ValueError):
        return jsonify({"error": "count must be integer"}), 400
    if not role:
        return jsonify({"error": "role is required"}), 400

    result = generate_questions(role=role, count=count)
    logger.info(
        "admin_generate_questions role=%s count=%s engine=%s provider=%s llm_error=%s",
        role,
        count,
        result.get("engine", "fallback"),
        result.get("llm_provider", "mock"),
        result.get("llm_error", ""),
    )
    return jsonify(result)


@app.post("/admin/save_questions")
def admin_save_questions():
    data = request.get_json(silent=True) or {}
    role = str(data.get("role", "")).strip()
    questions = data.get("questions", [])
    if not role:
        return jsonify({"error": "role is required"}), 400
    if not isinstance(questions, list):
        return jsonify({"error": "questions must be list"}), 400
    if not questions:
        return jsonify({"error": "questions must not be empty"}), 400

    saved = save_questions_by_role(role, questions)
    logger.info("admin_save_questions role=%s count=%s", role, len(saved["questions"]))
    return jsonify(
        {
            "ok": True,
            "role": role,
            "questions": saved["questions"],
            "updated_at": saved["updated_at"],
        }
    )


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
