const API = "";
let charts = {};
let currentPage = "dashboard";
const loginView = document.getElementById("loginView");
const dashboardView = document.getElementById("dashboardView");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const loginWait = document.getElementById("loginWait");
const loginBtn = document.getElementById("loginBtn");
const toast = document.getElementById("toast");
const pageTitle = document.getElementById("pageTitle");
const menuToggle = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");

function toPersian(n) { return String(n).replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]); }
function showToast(msg, type = "success") {
  toast.textContent = msg; toast.className = "toast show " + type;
  setTimeout(() => toast.classList.remove("show"), 3500);
}
async function api(path, options = {}) {
  const opts = { credentials: "include", headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options };
  if (opts.body && typeof opts.body === "object") opts.body = JSON.stringify(opts.body);
  const res = await fetch(API + path, opts);
  if (res.status === 401) { showLogin(); throw new Error("نشست منقضی شده"); }
  return res;
}
async function checkAuth() {
  try {
    const res = await fetch("/api/admin/check", { credentials: "include" });
    const data = await res.json();
    if (data.authenticated) { showDashboard(); loadPage("dashboard"); } else showLogin();
  } catch { showLogin(); }
}
function showLogin() { loginView.classList.remove("hidden"); dashboardView.classList.add("hidden"); }
function showDashboard() { loginView.classList.add("hidden"); dashboardView.classList.remove("hidden"); }
document.getElementById("togglePass").addEventListener("click", () => {
  const inp = document.getElementById("password");
  inp.type = inp.type === "password" ? "text" : "password";
});
loginForm.addEventListener("submit", async e => {
  e.preventDefault();
  loginError.textContent = ""; loginWait.classList.add("hidden");
  loginBtn.disabled = true; loginBtn.innerHTML = '<span class="spinner"></span> در حال بررسی...';
  try {
    const res = await fetch("/api/admin/login", {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: document.getElementById("password").value }),
    });
    const data = await res.json();
    if (!data.success) {
      loginError.textContent = data.message || "خطا در ورود";
      if (data.wait_seconds > 0) {
        let remaining = data.wait_seconds;
        loginWait.classList.remove("hidden");
        loginWait.textContent = `لطفاً ${toPersian(remaining)} ثانیه صبر کنید`;
        const timer = setInterval(() => {
          remaining--;
          if (remaining <= 0) { clearInterval(timer); loginWait.classList.add("hidden"); loginBtn.disabled = false; }
          else loginWait.textContent = `لطفاً ${toPersian(remaining)} ثانیه صبر کنید`;
        }, 1000);
        return;
      }
    } else { showDashboard(); loadPage("dashboard"); showToast("ورود موفق"); }
  } catch { loginError.textContent = "خطای ارتباط با سرور"; }
  finally { loginBtn.disabled = false; loginBtn.textContent = "ورود به پنل"; }
});
document.querySelectorAll(".nav-item").forEach(btn => {
  btn.addEventListener("click", () => {
    const page = btn.dataset.page;
    if (page === "logout") { doLogout(); return; }
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
    btn.classList.add("active"); loadPage(page);
    sidebar.classList.remove("open"); sidebarOverlay.classList.remove("show");
  });
});
menuToggle.addEventListener("click", () => { sidebar.classList.toggle("open"); sidebarOverlay.classList.toggle("show"); });
sidebarOverlay.addEventListener("click", () => { sidebar.classList.remove("open"); sidebarOverlay.classList.remove("show"); });
async function doLogout() {
  try { await api("/api/admin/logout", { method: "POST" }); } catch {}
  showLogin(); showToast("خروج موفق");
}
const titles = {
  dashboard: "داشبورد اصلی", responses: "تمام نظرسنجی‌ها", averages: "آمار و میانگین‌ها",
  questions: "گزارش سؤالات", feedbacks: "پیشنهادها و انتقادات", quality: "تحلیل کیفیت خدمات",
  health: "سلامت فنی سامانه", exports: "خروجی گزارش‌ها", backup: "نسخه پشتیبان", security: "تنظیمات امنیتی",
};
function loadPage(page) {
  currentPage = page; pageTitle.textContent = titles[page] || page;
  document.querySelectorAll(".page-content").forEach(el => el.classList.add("hidden"));
  const el = document.getElementById("page-" + page);
  if (el) { el.classList.remove("hidden"); Object.values(charts).forEach(c => c.destroy()); charts = {}; renderers[page]?.(el); }
}
const renderers = {
  async dashboard(el) {
    el.innerHTML = `<div class="text-center" style="padding:2rem">در حال بارگذاری...</div>`;
    try {
      const [stats, health] = await Promise.all([
        api("/api/admin/stats").then(r => r.json()),
        api("/api/admin/health").then(r => r.json()),
      ]);
      el.innerHTML = `
        <div class="stats-grid">
          <div class="stat-card highlight"><div class="value">${toPersian(stats.total_responses)}</div><div class="label">کل نظرسنجی‌ها</div></div>
          <div class="stat-card"><div class="value">${toPersian(stats.average_score)}</div><div class="label">میانگین رضایت کلی</div></div>
          <div class="stat-card"><div class="value">${toPersian(stats.satisfaction_percent)}٪</div><div class="label">درصد رضایت کلی</div></div>
          <div class="stat-card"><div class="value">${toPersian(stats.feedback_count)}</div><div class="label">پیشنهادها و انتقادات</div></div>
          <div class="stat-card"><div class="value">${toPersian(stats.today_count)}</div><div class="label">ثبت‌شده امروز</div></div>
          <div class="stat-card"><div class="value">${toPersian(health.score)}</div><div class="label">امتیاز سلامت فنی</div></div>
        </div>
        <div class="charts-grid">
          <div class="chart-card"><h3>میانگین ۱۱ سؤال</h3><div class="chart-container"><canvas id="chartAverages"></canvas></div></div>
          <div class="chart-card"><h3>توزیع گزینه‌ها</h3><div class="chart-container"><canvas id="chartDist"></canvas></div></div>
        </div>
        <div class="charts-grid"><div class="chart-card" style="grid-column:1/-1"><h3>روند ثبت نظرسنجی‌ها (۳۰ روز اخیر)</h3><div class="chart-container"><canvas id="chartTrend"></canvas></div></div></div>`;
      const [avgs, dist, trend] = await Promise.all([
        api("/api/admin/question-averages").then(r => r.json()),
        api("/api/admin/distribution").then(r => r.json()),
        api("/api/admin/trend?days=30").then(r => r.json()),
      ]);
      charts.avg = new Chart(document.getElementById("chartAverages"), {
        type: "bar", data: { labels: avgs.map(a => a.label), datasets: [{ label: "میانگین", data: avgs.map(a => a.average), backgroundColor: "rgba(23,105,170,0.7)", borderRadius: 6 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 4, ticks: { stepSize: 1 } }, x: { ticks: { font: { size: 10 }, maxRotation: 45 } } } },
      });
      charts.dist = new Chart(document.getElementById("chartDist"), {
        type: "doughnut", data: { labels: dist.labels, datasets: [{ data: dist.values, backgroundColor: ["#DC4B4B", "#F59E0B", "#42A5F5", "#21A675"] }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
      });
      charts.trend = new Chart(document.getElementById("chartTrend"), {
        type: "line", data: { labels: trend.map(t => t.date), datasets: [{ label: "تعداد", data: trend.map(t => t.count), borderColor: "#1769AA", backgroundColor: "rgba(23,105,170,0.1)", fill: true, tension: 0.3 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
      });
    } catch (e) { el.innerHTML = `<p style="color:var(--error)">خطا در بارگذاری: ${e.message}</p>`; }
  },
  async responses(el) {
    el.innerHTML = `
      <div class="filters">
        <input type="text" id="searchId" placeholder="جست‌وجو شناسه..." />
        <input type="date" id="dateFrom" /><input type="date" id="dateTo" />
        <button class="btn btn-primary" id="btnSearch" style="padding:0.55rem 1rem">جست‌وجو</button>
      </div>
      <div class="table-wrap"><table><thead><tr><th>شناسه مشارکت‌کننده</th><th>تاریخ ثبت</th><th>میانگین امتیاز</th><th>وضعیت</th><th>عملیات</th></tr></thead>
      <tbody id="respBody"><tr><td colspan="5" class="text-center">در حال بارگذاری...</td></tr></tbody></table></div>
      <div class="pagination" id="respPagination"></div>
      <div id="detailModal" class="hidden" style="margin-top:1.5rem"></div>`;
    let page = 1;
    async function load(p = 1) {
      page = p;
      const params = new URLSearchParams({ page, per_page: 15 });
      const sid = document.getElementById("searchId").value.trim();
      const df = document.getElementById("dateFrom").value;
      const dt = document.getElementById("dateTo").value;
      if (sid) params.set("search_id", sid);
      if (df) params.set("date_from", df);
      if (dt) params.set("date_to", dt);
      const data = await api("/api/admin/responses?" + params).then(r => r.json());
      const tbody = document.getElementById("respBody");
      if (!data.items.length) tbody.innerHTML = `<tr><td colspan="5" class="text-center">موردی یافت نشد</td></tr>`;
      else tbody.innerHTML = data.items.map(r => `
        <tr><td><strong>${r.participant_id}</strong></td>
        <td>${r.created_at?.replace("T", " ").slice(0, 19) || "—"}</td>
        <td>${toPersian(r.average_score)}</td>
        <td><span class="badge badge-success">ثبت‌شده</span></td>
        <td><button class="btn btn-outline" style="padding:0.3rem 0.7rem;font-size:0.8rem" onclick="window._showDetail('${r.participant_id}')">مشاهده</button></td></tr>`).join("");
      const pag = document.getElementById("respPagination");
      let html = "";
      for (let i = 1; i <= data.pages; i++) html += `<button class="${i === page ? "active" : ""}" data-p="${i}">${toPersian(i)}</button>`;
      pag.innerHTML = html;
      pag.querySelectorAll("button").forEach(b => b.addEventListener("click", () => load(+b.dataset.p)));
      window._respItems = data.items;
    }
    window._showDetail = pid => {
      const item = (window._respItems || []).find(x => x.participant_id === pid);
      if (!item) return;
      const labels = ["کیفیت غذا","حجم غذا","تنوع منو","اقلام همراه","بسته‌بندی","بهداشت رستوران","بهداشت متصدیان","برخورد متصدیان","چیدمان","زمان سرو","رضایت کلی"];
      const modal = document.getElementById("detailModal");
      modal.classList.remove("hidden");
      modal.innerHTML = `<div class="card"><h3 style="margin-bottom:1rem">جزئیات مشارکت‌کننده ${item.participant_id}</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:0.5rem;margin-bottom:1rem">
          ${labels.map((l, i) => `<div style="background:#f8fafc;padding:0.6rem;border-radius:8px;text-align:center"><div style="font-size:0.75rem;color:var(--text)">${l}</div><div style="font-weight:700;color:var(--navy)">${toPersian(item.answers["q"+(i+1)])}</div></div>`).join("")}
        </div>
        ${item.feedback ? `<p style="background:#f0f9ff;padding:0.75rem;border-radius:8px"><strong>پیشنهاد/انتقاد:</strong> ${item.feedback}</p>` : "<p style='color:var(--text)'>بدون پیشنهاد یا انتقاد</p>"}
      </div>`;
    };
    document.getElementById("btnSearch").addEventListener("click", () => load(1));
    load(1);
  },
  async averages(el) {
    el.innerHTML = `<div class="text-center" style="padding:2rem">در حال بارگذاری...</div>`;
    const avgs = await api("/api/admin/question-averages").then(r => r.json());
    const stats = await api("/api/admin/stats").then(r => r.json());
    el.innerHTML = `
      <div class="stats-grid mb-2">
        <div class="stat-card highlight"><div class="value">${toPersian(stats.average_score)}</div><div class="label">میانگین کلی (از ۴)</div></div>
        <div class="stat-card"><div class="value">${toPersian(stats.satisfaction_percent)}٪</div><div class="label">درصد رضایت</div></div>
      </div>
      <div class="table-wrap"><table><thead><tr><th>سؤال</th><th>میانگین</th><th>درصد رضایت</th><th>تعداد پاسخ</th></tr></thead>
      <tbody>${avgs.map(a => `<tr><td>${a.label}</td><td><strong>${toPersian(a.average)}</strong></td><td>${toPersian(a.satisfaction_percent)}٪</td><td>${toPersian(a.count)}</td></tr>`).join("")}</tbody></table></div>
      <div class="chart-card mt-3"><h3>نمودار درصد رضایت</h3><div class="chart-container"><canvas id="chartSat"></canvas></div></div>`;
    charts.sat = new Chart(document.getElementById("chartSat"), {
      type: "bar", data: { labels: avgs.map(a => a.label), datasets: [{ label: "درصد رضایت", data: avgs.map(a => a.satisfaction_percent), backgroundColor: "rgba(33,166,117,0.7)", borderRadius: 6 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } },
    });
  },
  async questions(el) { renderers.averages(el); },
  async feedbacks(el) {
    el.innerHTML = `
      <div class="filters"><input type="text" id="fbSearch" placeholder="جست‌وجو در متن..." style="min-width:200px" />
      <button class="btn btn-primary" id="fbBtn" style="padding:0.55rem 1rem">جست‌وجو</button></div>
      <div id="fbList"><div class="text-center" style="padding:2rem">در حال بارگذاری...</div></div>
      <div class="pagination" id="fbPagination"></div>`;
    let page = 1;
    async function load(p = 1) {
      page = p;
      const params = new URLSearchParams({ page, per_page: 10 });
      const s = document.getElementById("fbSearch").value.trim();
      if (s) params.set("search", s);
      const data = await api("/api/admin/feedbacks?" + params).then(r => r.json());
      const list = document.getElementById("fbList");
      if (!data.items.length) list.innerHTML = `<div class="card text-center">هیچ پیشنهادی ثبت نشده است</div>`;
      else list.innerHTML = data.items.map(f => `
        <div class="card" style="margin-bottom:0.75rem">
          <div class="flex justify-between items-center" style="margin-bottom:0.5rem">
            <strong>مشارکت‌کننده ${f.participant_id}</strong>
            <span style="font-size:0.8rem;color:var(--text)">${f.created_at?.replace("T"," ").slice(0,16)}</span>
          </div>
          <p style="white-space:pre-wrap">${f.feedback}</p>
          <div style="margin-top:0.5rem;font-size:0.85rem;color:var(--primary)">میانگین امتیاز: ${toPersian(f.average_score)}</div>
        </div>`).join("");
      const pag = document.getElementById("fbPagination");
      let html = "";
      for (let i = 1; i <= data.pages; i++) html += `<button class="${i === page ? "active" : ""}" data-p="${i}">${toPersian(i)}</button>`;
      pag.innerHTML = html;
      pag.querySelectorAll("button").forEach(b => b.addEventListener("click", () => load(+b.dataset.p)));
    }
    document.getElementById("fbBtn").addEventListener("click", () => load(1));
    load(1);
  },
  async quality(el) {
    const avgs = await api("/api/admin/question-averages").then(r => r.json());
    el.innerHTML = `
      <div class="card mb-2"><h3 style="margin-bottom:1rem">تحلیل کیفیت خدمات</h3>
      <p style="color:var(--text);margin-bottom:1rem">میانگین امتیاز هر حوزه از مقیاس ۱ تا ۴ محاسبه شده است. درصد رضایت = (میانگین ÷ ۴) × ۱۰۰</p></div>
      <div class="stats-grid">${avgs.map(a => `
        <div class="stat-card"><div class="value">${toPersian(a.average)}</div><div class="label">${a.label}</div>
        <div style="font-size:0.8rem;color:var(--primary);margin-top:0.25rem">${toPersian(a.satisfaction_percent)}٪ رضایت</div></div>`).join("")}</div>
      <div class="chart-card mt-3"><h3>مقایسه کیفیت خدمات</h3><div class="chart-container" style="height:320px"><canvas id="chartQuality"></canvas></div></div>`;
    charts.q = new Chart(document.getElementById("chartQuality"), {
      type: "radar", data: { labels: avgs.map(a => a.label), datasets: [{ label: "میانگین", data: avgs.map(a => a.average), backgroundColor: "rgba(23,105,170,0.2)", borderColor: "#1769AA", pointBackgroundColor: "#1769AA" }] },
      options: { responsive: true, maintainAspectRatio: false, scales: { r: { min: 0, max: 4, ticks: { stepSize: 1 } } } },
    });
  },
  async health(el) {
    const h = await api("/api/admin/health").then(r => r.json());
    const stats = await api("/api/admin/stats").then(r => r.json());
    el.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card highlight"><div class="value">${toPersian(h.score)}</div><div class="label">امتیاز سلامت فنی (۰–۱۰۰)</div></div>
        <div class="stat-card"><div class="value">${h.status}</div><div class="label">وضعیت کلی</div></div>
        <div class="stat-card"><div class="value">${toPersian(h.success_rate)}٪</div><div class="label">نرخ موفقیت درخواست‌ها</div></div>
        <div class="stat-card"><div class="value">${h.db_healthy ? "سالم" : "نامطلوب"}</div><div class="label">سلامت پایگاه داده</div></div>
      </div>
      <div class="card mt-3"><h3 style="margin-bottom:1rem">جزئیات فنی</h3>
        <table><tbody>
          <tr><td>تعداد کل درخواست‌ها</td><td>${toPersian(h.total_requests)}</td></tr>
          <tr><td>تعداد خطاها</td><td>${toPersian(h.error_count)}</td></tr>
          <tr><td>خطاهای ۲۴ ساعت اخیر</td><td>${toPersian(h.recent_errors_24h)}</td></tr>
          <tr><td>آخرین پشتیبان‌گیری</td><td>${h.last_backup ? h.last_backup.replace("T"," ").slice(0,19) : "—"}</td></tr>
          <tr><td>وضعیت پشتیبان</td><td>${h.backup_ok ? "موفق" : "نیازمند بررسی"}</td></tr>
          <tr><td>زمان آخرین بررسی</td><td>${h.checked_at?.replace("T"," ").slice(0,19)}</td></tr>
        </tbody></table></div>
      <div class="card mt-3"><h3 style="margin-bottom:0.75rem">دو شاخص مستقل</h3>
        <div class="stats-grid">
          <div class="stat-card"><div class="value">${toPersian(stats.satisfaction_percent)}٪</div><div class="label">رضایت کاربران از غذا و رستوران</div></div>
          <div class="stat-card"><div class="value">${toPersian(h.score)}</div><div class="label">سلامت فنی سامانه</div></div>
        </div></div>`;
  },
  async exports(el) {
    el.innerHTML = `<div class="card"><h3 style="margin-bottom:1rem">خروجی گزارش‌ها</h3>
      <p style="color:var(--text);margin-bottom:1.5rem">گزارش‌ها بر اساس داده‌های واقعی پایگاه داده تولید می‌شوند.</p>
      <div class="flex gap-1" style="flex-wrap:wrap">
        <a class="btn btn-primary" href="/api/admin/export/csv" target="_blank">دانلود CSV</a>
        <a class="btn btn-primary" href="/api/admin/export/excel" target="_blank">دانلود Excel</a>
        <a class="btn btn-primary" href="/api/admin/export/pdf" target="_blank">دانلود PDF</a>
      </div></div>`;
  },
  async backup(el) {
    el.innerHTML = `<div class="card"><h3 style="margin-bottom:1rem">نسخه پشتیبان</h3>
      <p style="color:var(--text);margin-bottom:1.25rem">ایجاد نسخه پشتیبان از پایگاه داده نظرسنجی‌ها.</p>
      <button class="btn btn-primary" id="btnBackup">ایجاد پشتیبان جدید</button>
      <p id="backupResult" class="mt-2"></p></div>`;
    document.getElementById("btnBackup").addEventListener("click", async () => {
      const btn = document.getElementById("btnBackup");
      btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> در حال ایجاد...';
      try {
        const res = await api("/api/admin/backup", { method: "POST" });
        const data = await res.json();
        document.getElementById("backupResult").innerHTML = `<span style="color:var(--success)">پشتیبان با موفقیت ایجاد شد: ${data.filename} (${toPersian(Math.round(data.size/1024))} کیلوبایت)</span>`;
        showToast("پشتیبان ایجاد شد");
      } catch (e) {
        document.getElementById("backupResult").innerHTML = `<span style="color:var(--error)">خطا: ${e.message}</span>`;
      } finally { btn.disabled = false; btn.textContent = "ایجاد پشتیبان جدید"; }
    });
  },
  async security(el) {
    el.innerHTML = `<div class="card"><h3 style="margin-bottom:1rem">تغییر رمز عبور</h3>
      <form id="changePassForm">
        <div class="form-group"><label>رمز فعلی</label><input type="password" id="oldPass" required style="width:100%;padding:0.75rem;border:2px solid #e2e8f0;border-radius:8px" /></div>
        <div class="form-group"><label>رمز جدید (حداقل ۱۲ کاراکتر)</label><input type="password" id="newPass" required minlength="12" style="width:100%;padding:0.75rem;border:2px solid #e2e8f0;border-radius:8px" /></div>
        <div class="form-group"><label>تکرار رمز جدید</label><input type="password" id="newPass2" required minlength="12" style="width:100%;padding:0.75rem;border:2px solid #e2e8f0;border-radius:8px" /></div>
        <button type="submit" class="btn btn-primary">تغییر رمز</button>
        <p id="passMsg" class="mt-2"></p>
      </form></div>
      <div class="card mt-3"><h3 style="margin-bottom:0.75rem">نکات امنیتی</h3>
        <ul style="padding-right:1.25rem;color:var(--text);font-size:0.95rem">
          <li>رمز عبور با الگوریتم bcrypt هش می‌شود و هرگز به صورت خام ذخیره نمی‌گردد.</li>
          <li>نشست مدیریت پس از ۸ ساعت منقضی می‌شود.</li>
          <li>تلاش‌های ناموفق ورود باعث قفل موقت با تأخیر تصاعدی می‌شود.</li>
          <li>هیچ اطلاعات شخصی کاربران (IP، دستگاه و ...) ذخیره نمی‌شود.</li>
        </ul></div>`;
    document.getElementById("changePassForm").addEventListener("submit", async e => {
      e.preventDefault();
      const oldP = document.getElementById("oldPass").value;
      const newP = document.getElementById("newPass").value;
      const newP2 = document.getElementById("newPass2").value;
      const msg = document.getElementById("passMsg");
      if (newP !== newP2) { msg.innerHTML = `<span style="color:var(--error)">رمز جدید و تکرار آن یکسان نیستند</span>`; return; }
      try {
        const res = await api("/api/admin/change-password", { method: "POST", body: { old_password: oldP, new_password: newP } });
        const data = await res.json();
        msg.innerHTML = `<span style="color:var(--success)">${data.message}</span>`;
        showToast("رمز تغییر کرد – لطفاً دوباره وارد شوید");
        setTimeout(() => doLogout(), 2000);
      } catch (err) { msg.innerHTML = `<span style="color:var(--error)">${err.message || "خطا"}</span>`; }
    });
  },
};
checkAuth();
