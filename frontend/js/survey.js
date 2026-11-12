const QUESTIONS = [
  "میزان رضایت شما از کیفیت غذا",
  "میزان رضایت شما از حجم غذا",
  "میزان رضایت شما از تنوع منوی غذایی",
  "میزان رضایت شما از اقلام همراه غذا",
  "میزان رضایت شما از بسته‌بندی غذا و اقلام خوراکی همراه با غذا",
  "میزان رضایت شما از وضعیت بهداشت و نظافت رستوران",
  "میزان رضایت شما از رعایت موارد بهداشتی توسط متصدیان رستوران",
  "میزان رضایت شما از نحوه برخورد متصدیان رستوران",
  "میزان رضایت شما از چیدمان میز و صندلی رستوران",
  "میزان رضایت شما از زمان شروع و پایان سرو غذا",
  "میزان رضایت کلی شما از وضعیت غذا و رستوران",
];
const OPTIONS = [
  { value: 4, label: "خیلی خوب" },
  { value: 3, label: "خوب" },
  { value: 2, label: "متوسط" },
  { value: 1, label: "ضعیف" },
];
const form = document.getElementById("surveyForm");
const container = document.getElementById("questionsContainer");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");
const feedbackEl = document.getElementById("feedback");
const charCount = document.getElementById("charCount");
const submitBtn = document.getElementById("submitBtn");
const formError = document.getElementById("formError");
const surveyApp = document.getElementById("surveyApp");
const thanksPage = document.getElementById("thanksPage");
const participantIdDisplay = document.getElementById("participantIdDisplay");
const toast = document.getElementById("toast");
let submitting = false;

function createClientToken() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === "x" ? r : (r & 3 | 8)).toString(16);
  });
}

const CLIENT_TOKEN_KEY = "survey_client_token";
let clientToken = localStorage.getItem(CLIENT_TOKEN_KEY);
if (!clientToken) {
  clientToken = createClientToken();
  localStorage.setItem(CLIENT_TOKEN_KEY, clientToken);
}

const answers = {};

function buildQuestions() {
  QUESTIONS.forEach((text, idx) => {
    const qNum = idx + 1;
    const card = document.createElement("div");
    card.className = "card question-card";
    card.dataset.q = qNum;
    card.innerHTML = `
      <div class="q-title"><span class="q-number">${toPersianNum(qNum)}</span>${text}</div>
      <div class="options">
        ${OPTIONS.map(opt => `
          <label class="option">
            <input type="radio" name="q${qNum}" value="${opt.value}" required />
            <span class="option-label"><span>${opt.label}</span><span class="option-score">${toPersianNum(opt.value)}</span></span>
          </label>`).join("")}
      </div>`;
    container.appendChild(card);
    card.querySelectorAll("input").forEach(input => {
      input.addEventListener("change", () => {
        answers[qNum] = parseInt(input.value, 10);
        card.classList.add("answered");
        card.classList.remove("error");
        updateProgress();
        saveDraft();
      });
    });
  });
}
function toPersianNum(n) {
  return String(n).replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);
}
function updateProgress() {
  const answered = Object.keys(answers).length;
  progressFill.style.width = (answered / 11) * 100 + "%";
  progressText.textContent = `${toPersianNum(answered)} از ۱۱`;
}
function saveDraft() {
  try { localStorage.setItem("survey_draft", JSON.stringify({ answers, feedback: feedbackEl.value })); } catch(e) {}
}
function loadDraft() {
  try {
    const raw = localStorage.getItem("survey_draft");
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data.answers) {
      Object.entries(data.answers).forEach(([q, val]) => {
        const input = document.querySelector(`input[name="q${q}"][value="${val}"]`);
        if (input) { input.checked = true; answers[q] = val; input.closest(".question-card").classList.add("answered"); }
      });
    }
    if (data.feedback) { feedbackEl.value = data.feedback; charCount.textContent = toPersianNum(data.feedback.length); }
    updateProgress();
  } catch(e) {}
}

function showAlreadyVoted() {
  clearDraft();
  surveyApp.classList.add("hidden");
  document.querySelector(".site-header")?.classList.add("hidden");
  thanksPage.textContent =
    "با تشکر؛ شما قبلاً رأی خود را ثبت کرده‌اید.";
  thanksPage.classList.remove("hidden");
  window.scrollTo(0, 0);
}

function clearDraft() { try { localStorage.removeItem("survey_draft"); } catch(e) {} }
feedbackEl.addEventListener("input", () => {
  charCount.textContent = toPersianNum(feedbackEl.value.length);
  saveDraft();
});
function showToast(msg, type = "success") {
  toast.textContent = msg;
  toast.className = "toast show " + type;
  setTimeout(() => toast.classList.remove("show"), 3500);
}
function validate() {
  let valid = true;
  formError.textContent = "";
  document.querySelectorAll(".question-card").forEach(card => {
    if (!answers[card.dataset.q]) { card.classList.add("error"); valid = false; }
    else card.classList.remove("error");
  });
  if (!valid) {
    formError.textContent = "لطفاً به تمام سؤالات پاسخ دهید.";
    document.querySelector(".question-card.error")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  return valid;
}
form.addEventListener("submit", async e => {
  e.preventDefault();
  if (submitting || !validate()) return;
  submitting = true;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner"></span> در حال ارسال...';
  formError.textContent = "";
  const payload = {
    q1: answers[1], q2: answers[2], q3: answers[3], q4: answers[4], q5: answers[5],
    q6: answers[6], q7: answers[7], q8: answers[8], q9: answers[9], q10: answers[10], q11: answers[11],
    feedback: feedbackEl.value.trim() || null,
  };
  try {
    const res = await fetch("/api/survey/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Client-Token": clientToken
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.status === 409) {
      localStorage.setItem("survey_voted", "1");
      showAlreadyVoted();
      return;
    }
    if (!res.ok || !data.success) throw new Error(data.detail || data.message || "خطا در ثبت نظرسنجی");
    localStorage.setItem("survey_voted", "1");
    clearDraft();
    participantIdDisplay.textContent = data.participant_id ? "مشارکت‌کننده " + data.participant_id : "—";
    surveyApp.classList.add("hidden");
    document.querySelector(".site-header").classList.add("hidden");
    thanksPage.classList.remove("hidden");
    window.scrollTo(0, 0);
  } catch (err) {
    formError.textContent = err.message || "خطای شبکه. لطفاً دوباره تلاش کنید. اطلاعات شما حفظ شده است.";
    showToast("ارسال ناموفق بود", "error");
  } finally {
    submitting = false;
    submitBtn.disabled = false;
    submitBtn.textContent = "ثبت و ارسال نظرسنجی";
  }
});
if (localStorage.getItem("survey_voted") === "1") {
  showAlreadyVoted();
} else {
  buildQuestions();
  loadDraft();
  updateProgress();
}
