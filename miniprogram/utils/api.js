const { BASE_URL } = require("./config");

function request({ url, method = "GET", data = null }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      timeout: 30000,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }
        reject(new Error(res.data?.error || `HTTP ${res.statusCode}`));
      },
      fail(err) {
        reject(err);
      },
    });
  });
}

function getQuestions(role) {
  return request({ url: `/get_questions?role=${encodeURIComponent(role)}` });
}

function submitAnswers(payload) {
  return request({ url: "/submit_answers", method: "POST", data: payload });
}

function getFeedback(payload) {
  return request({ url: "/get_feedback", method: "POST", data: payload });
}

module.exports = {
  getQuestions,
  submitAnswers,
  getFeedback,
};
