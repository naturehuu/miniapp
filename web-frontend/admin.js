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

const roleSelect = document.getElementById("admin-role-select");
const refreshBtn = document.getElementById("refresh-btn");
const generateBtn = document.getElementById("generate-btn");
const saveBtn = document.getElementById("save-btn");
const addQuestionBtn = document.getElementById("add-question-btn");
const statusBox = document.getElementById("admin-status");
const questionForm = document.getElementById("question-form");

let editorQuestions = [];

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

function renderEditor() {
  questionForm.innerHTML = "";
  editorQuestions.forEach((q, idx) => {
    const item = document.createElement("div");
    item.className = "qa-item";
    item.innerHTML = `
      <div class="topbar">
        <p><strong>问题 ${idx + 1}</strong></p>
        <button type="button" class="danger-btn" data-action="remove" data-index="${idx}">删除</button>
      </div>
      <textarea data-action="text" data-index="${idx}" placeholder="请输入问题内容">${q.text || ""}</textarea>
    `;
    questionForm.appendChild(item);
  });
}

function normalizeEditorQuestions() {
  const textareas = questionForm.querySelectorAll("textarea[data-action='text']");
  const normalized = [];
  textareas.forEach((ta, idx) => {
    const text = ta.value.trim();
    if (text) {
      normalized.push({ id: `q${idx + 1}`, text });
    }
  });
  return normalized;
}

async function loadSavedQuestions() {
  try {
    refreshBtn.disabled = true;
    setStatus("正在加载已保存题目...");
    const role = roleSelect.value;
    const data = await request(`/admin/questions?role=${encodeURIComponent(role)}`);
    editorQuestions = data.questions || [];
    renderEditor();
    setStatus(`已加载 ${editorQuestions.length} 条，更新时间：${data.updated_at || "-"}`);
  } catch (err) {
    setStatus(err.message || "加载失败", true);
  } finally {
    refreshBtn.disabled = false;
  }
}

async function generateQuestions() {
  try {
    generateBtn.disabled = true;
    setStatus("正在调用 AI 生成题目...");
    const role = roleSelect.value;
    const data = await request("/admin/generate_questions", {
      method: "POST",
      body: JSON.stringify({ role, count: 6 }),
    });
    editorQuestions = data.questions || [];
    renderEditor();
    const err = data.llm_error ? `，错误：${data.llm_error}` : "";
    setStatus(`生成完成，来源：${data.engine || "-"}，模型：${data.llm_provider || "-"}${err}`);
  } catch (err) {
    setStatus(err.message || "生成失败", true);
  } finally {
    generateBtn.disabled = false;
  }
}

async function saveQuestions() {
  try {
    saveBtn.disabled = true;
    const role = roleSelect.value;
    const questions = normalizeEditorQuestions();
    if (!questions.length) {
      throw new Error("至少保留 1 个问题");
    }
    const data = await request("/admin/save_questions", {
      method: "POST",
      body: JSON.stringify({ role, questions }),
    });
    editorQuestions = data.questions || [];
    renderEditor();
    setStatus(`保存成功，共 ${editorQuestions.length} 条，更新时间：${data.updated_at || "-"}`);
  } catch (err) {
    setStatus(err.message || "保存失败", true);
  } finally {
    saveBtn.disabled = false;
  }
}

function addQuestion() {
  editorQuestions.push({ id: `q${editorQuestions.length + 1}`, text: "" });
  renderEditor();
}

function onFormClick(e) {
  const target = e.target;
  if (!target || target.dataset.action !== "remove") {
    return;
  }
  const idx = Number(target.dataset.index);
  if (!Number.isInteger(idx) || idx < 0 || idx >= editorQuestions.length) {
    return;
  }
  editorQuestions.splice(idx, 1);
  renderEditor();
}

fillRoleOptions(DEFAULT_ROLES);
roleSelect.addEventListener("change", loadSavedQuestions);
refreshBtn.addEventListener("click", loadSavedQuestions);
generateBtn.addEventListener("click", generateQuestions);
saveBtn.addEventListener("click", saveQuestions);
addQuestionBtn.addEventListener("click", addQuestion);
questionForm.addEventListener("click", onFormClick);

if (DEFAULT_ROLES.length) {
  roleSelect.value = DEFAULT_ROLES[0];
  loadSavedQuestions();
}
