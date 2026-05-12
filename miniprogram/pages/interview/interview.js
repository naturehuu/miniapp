const { getQuestions, submitAnswers, getFeedback } = require("../../utils/api");

Page({
  data: {
    roles: [
      "店铺运营",
      "剪辑师",
      "新媒体运营",
      "短视频剪辑",
      "商品运营",
      "数据运营/分析师",
      "社交媒体运营",
    ],
    roleIndex: -1,
    selectedRole: "",
    questions: [],
    answers: {},
    loading: false,
    submitting: false,
    resultReady: false,
    questionResults: [],
    averageScore: 0,
    roleFitness: 0,
    feedbackMap: {},
  },

  onLoad() {
    if (!this.data.roles.length) {
      return;
    }
    this.setData(
      {
        roleIndex: 0,
        selectedRole: this.data.roles[0],
      },
      () => {
        this.loadQuestions();
      }
    );
  },

  onRoleChange(e) {
    const idx = Number(e.detail.value);
    this.setData({
      roleIndex: idx,
      selectedRole: this.data.roles[idx],
      resultReady: false,
      questions: [],
      answers: {},
      questionResults: [],
      feedbackMap: {},
    });
    this.loadQuestions();
  },

  async loadQuestions() {
    const role = this.data.selectedRole;
    if (!role) {
      wx.showToast({ title: "请先选择岗位", icon: "none" });
      return;
    }
    this.setData({ loading: true });
    try {
      const res = await getQuestions(role);
      this.setData({
        questions: res.questions || [],
        answers: {},
        resultReady: false,
      });
    } catch (err) {
      wx.showToast({ title: err.message || "加载失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  onAnswerInput(e) {
    const qid = e.currentTarget.dataset.questionId;
    const value = e.detail.value;
    const next = { ...this.data.answers, [qid]: value };
    this.setData({ answers: next });
  },

  async submit() {
    const { selectedRole, questions, answers } = this.data;
    if (!selectedRole || !questions.length) {
      wx.showToast({ title: "请先加载问题", icon: "none" });
      return;
    }

    const payloadAnswers = questions.map((q) => ({
      question_id: q.id,
      answer: answers[q.id] || "",
    }));
    const emptyCount = payloadAnswers.filter((a) => !a.answer.trim()).length;
    if (emptyCount > 0) {
      wx.showToast({ title: "请先完成所有回答", icon: "none" });
      return;
    }

    this.setData({ submitting: true });
    try {
      const payload = { role: selectedRole, answers: payloadAnswers };
      const scoreRes = await submitAnswers(payload);
      const feedbackRes = await getFeedback(payload);
      const feedbackMap = {};
      (feedbackRes.feedback || []).forEach((f) => {
        feedbackMap[f.question_id] = f.suggestion;
      });

      this.setData({
        resultReady: true,
        questionResults: scoreRes.question_results || [],
        averageScore: scoreRes.average_score || 0,
        roleFitness: scoreRes.role_fitness || 0,
        feedbackMap,
      });
      wx.showToast({ title: "评分完成", icon: "success" });
    } catch (err) {
      wx.showToast({ title: err.message || "提交失败", icon: "none" });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
