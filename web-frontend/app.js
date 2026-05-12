const isLocalHost =
  window.location.hostname === "127.0.0.1" ||
  window.location.hostname === "localhost";
const API_BASE_URL = isLocalHost ? "http://127.0.0.1:8081" : "/api";

const DEFAULT_ROLES = [
  "店铺运营",
  "剪辑师",
  "新媒体运营",
  "短视频剪辑",
  "商品运营",
  "数据运营/分析师",
  "社交媒体运营",
];

const roleSelect = document.getElementById("role-select");
const submitBtn = document.getElementById("submit-btn");
const statusBox = document.getElementById("status");
const qaCard = document.getElementById("qa-card");
const qaForm = document.getElementById("qa-form");
const resultCard = document.getElementById("result-card");
const resultList = document.getElementById("result-list");
const summary = document.getElementById("summary");

let currentQuestions = [];

function setStatus(text, isError = false) {
  statusBox.textContent = text;
  statusBox.className = isError ? "status error" : "status";
}

function fillRoleOptions(roles) {
  roleSelect.innerHTML = "";
  roles.forEach((role) => {
    const option = document.createElement("option");
    option.value = role;
    option.textContent = role;
    roleSelect.appendChild(option);
  });
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `请求失败: ${res.status}`);
  }
  return res.json();
}

async function loadQuestions() {
  try {
    setStatus("正在加载问题...");
    resultCard.classList.add("hidden");
    const role = roleSelect.value;
    const data = await request(`/get_questions?role=${encodeURIComponent(role)}`);
    currentQuestions = data.questions || [];

    if (!currentQuestions.length) {
      throw new Error("该岗位暂无问题");
    }

    qaForm.innerHTML = "";
    currentQuestions.forEach((q, idx) => {
      const item = document.createElement("div");
      item.className = "qa-item";
      item.innerHTML = `
        <p><strong>Q${idx + 1}.</strong> ${q.text}</p>
        <textarea data-qid="${q.id}" placeholder="请输入你的回答"></textarea>
      `;
      qaForm.appendChild(item);
    });

    qaCard.classList.remove("hidden");
    const updatedAt = data.updated_at ? `，更新时间：${data.updated_at}` : "";
    setStatus(`已加载 ${currentQuestions.length} 个固定问题${updatedAt}`);
  } catch (err) {
    setStatus(err.message || "加载失败", true);
  }
}

function collectAnswers() {
  const answers = [];
  const textareas = qaForm.querySelectorAll("textarea[data-qid]");
  for (const input of textareas) {
    const answer = input.value.trim();
    if (!answer) {
      throw new Error("请先完成全部问题回答");
    }
    answers.push({ question_id: input.dataset.qid, answer });
  }
  return answers;
}

function renderResult(scoreData, feedbackData) {
  const feedbackMap = {};
  (feedbackData.feedback || []).forEach((item) => {
    feedbackMap[item.question_id] = item.suggestion;
  });

  const scoreEngine = scoreData.engine || "-";
  const feedbackEngine = feedbackData.engine || "-";
  const llmError = scoreData.llm_error || feedbackData.llm_error || "";
  summary.textContent = `平均分：${scoreData.average_score}，岗位适配度：${scoreData.role_fitness}，评分引擎：${scoreEngine}，建议引擎：${feedbackEngine}${llmError ? `，错误：${llmError}` : ""}`;
  resultList.innerHTML = "";

  (scoreData.question_results || []).forEach((item) => {
    const div = document.createElement("div");
    div.className = "result-item";
    div.innerHTML = `
      <p><strong>题目ID：</strong>${item.question_id}</p>
      <p><strong>分数：</strong>${item.score}</p>
      <p><strong>说明：</strong>${item.reason || "-"}</p>
      <p><strong>建议：</strong>${feedbackMap[item.question_id] || "-"}</p>
    `;
    resultList.appendChild(div);
  });
  resultCard.classList.remove("hidden");
}

async function submitAnswers() {
  try {
    if (!currentQuestions.length) {
      throw new Error("请先加载面试问题");
    }
    submitBtn.disabled = true;
    setStatus("正在评分...");
    const payload = {
      role: roleSelect.value,
      answers: collectAnswers(),
    };
    const scoreData = await request("/submit_answers", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const feedbackData = await request("/get_feedback", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderResult(scoreData, feedbackData);
    setStatus("评分完成");
  } catch (err) {
    setStatus(err.message || "提交失败", true);
  } finally {
    submitBtn.disabled = false;
  }
}

async function checkHealth() {
  try {
    const data = await request("/health");
    setStatus(`后端已连接，端口 ${data.port}`);
  } catch (err) {
    setStatus(`后端不可用：${err.message || "连接失败"}`, true);
  }
}

fillRoleOptions(DEFAULT_ROLES);
checkHealth();
roleSelect.addEventListener("change", loadQuestions);
submitBtn.addEventListener("click", submitAnswers);
if (DEFAULT_ROLES.length) {
  roleSelect.value = DEFAULT_ROLES[0];
  loadQuestions();
}
