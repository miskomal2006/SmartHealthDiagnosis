const API = "http://127.0.0.1:5000/api";

function $(id) {
  return document.getElementById(id);
}

function setToken(token) {
  sessionStorage.setItem("token", token);
}

function getToken() {
  return sessionStorage.getItem("token");
}

function getRole() {
  return sessionStorage.getItem("role");
}

function logout() {
  sessionStorage.clear();
  window.location.href = "login.html";
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: "Bearer " + getToken(),
  };
}

function showLoader(show) {
  const loader = $("loader");
  if (!loader) return;
  loader.classList.toggle("hidden", !show);
}

function showToast(message, type = "info") {
  const toast = $("toast");
  if (!toast) return;
  toast.className = `toast ${type}`;
  toast.textContent = typeof message === "string" ? message : JSON.stringify(message);
  setTimeout(() => {
    toast.className = "toast hidden";
  }, 2500);
}

function normalizeError(data, fallback) {
  if (!data) return fallback;
  if (typeof data.error === "string") return data.error;
  if (data.error && typeof data.error === "object") return Object.values(data.error).flat().join(", ");
  return fallback;
}

function protectRoute() {
  const token = getToken();
  const publicPages = ["", "index.html", "login.html", "register.html", "forgot-password.html"];
  const page = window.location.pathname.split("/").pop();

  if (!token && !publicPages.includes(page)) {
    window.location.href = "login.html";
  }
}

async function registerUser(e) {
  e.preventDefault();
  showLoader(true);
  try {
    const res = await fetch(API + "/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: $("regName").value.trim(),
        email: $("regEmail").value.trim(),
        password: $("regPassword").value,
        role: $("regRole").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Registration failed"), "error");
      return;
    }
    showToast("Registered successfully", "success");
    setTimeout(() => {
      window.location.href = "login.html";
    }, 700);
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  } finally {
    showLoader(false);
  }
}

async function login(e) {
  e.preventDefault();
  showLoader(true);
  try {
    const res = await fetch(API + "/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: $("loginEmail").value.trim(),
        password: $("loginPassword").value,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Login failed"), "error");
      return;
    }

    setToken(data.token);
    sessionStorage.setItem("role", data.role);
    sessionStorage.setItem("name", data.name || "");
    window.location.href = "dashboard.html";
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  } finally {
    showLoader(false);
  }
}

async function resetPassword(e) {
  e.preventDefault();
  showLoader(true);
  try {
    const res = await fetch(API + "/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: $("fpEmail").value.trim(),
        password: $("fpPassword").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Password reset failed"), "error");
      return;
    }
    showToast("Password updated", "success");
    setTimeout(() => {
      window.location.href = "login.html";
    }, 700);
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  } finally {
    showLoader(false);
  }
}

function attachBmiCalculator() {
  const heightInput = $("height");
  const weightInput = $("weight");
  const bmiInput = $("bmi");
  if (!heightInput || !weightInput || !bmiInput) return;

  const recalc = () => {
    const h = Number(heightInput.value);
    const w = Number(weightInput.value);
    if (h > 0 && w > 0) {
      const bmi = w / ((h / 100) * (h / 100));
      bmiInput.value = bmi.toFixed(1);
    } else {
      bmiInput.value = "";
    }
  };

  heightInput.addEventListener("input", recalc);
  weightInput.addEventListener("input", recalc);
}

async function submitDiagnosis(e) {
  e.preventDefault();
  showLoader(true);

  const symptoms = [];
  document.querySelectorAll(".symptom-group input:checked").forEach((cb) => symptoms.push(cb.value));

  const payload = {
    disease_target: $("diseaseType").value,
    patient: {
      full_name: $("fullName") ? $("fullName").value.trim() : "",
      age: Number($("age").value || 0),
      gender: $("gender").value,
      bmi: Number($("bmi").value || 0),
      blood_group: $("bloodGroup") ? $("bloodGroup").value.trim() : "",
      location: $("location") ? $("location").value.trim() : "",
      height: $("height") && $("height").value ? Number($("height").value) : null,
      weight: $("weight") && $("weight").value ? Number($("weight").value) : null,
    },
    vitals: {
      temperature: Number($("temperature").value || 0),
      heart_rate: Number($("heartRate").value || 0),
      bp_systolic: Number($("bpSys").value || 0),
      bp_diastolic: Number($("bpDia").value || 0),
      respRate: Number($("respRate").value || 0),
      spo2: Number($("spo2").value || 0),
    },
    symptoms,
    metadata: {
      severity: $("severity").value,
      duration_days: Number($("duration").value || 0),
    },
    medicalHistory: $("medicalHistory") ? $("medicalHistory").value : "",
    smoking: $("smoking") ? $("smoking").value : "",
    alcohol: $("alcohol") ? $("alcohol").value : "",
    activity: $("activity") ? $("activity").value : "",
    sleep: $("sleep") && $("sleep").value ? Number($("sleep").value) : null,
    stress: $("stress") && $("stress").value ? Number($("stress").value) : null,
  };

  try {
    const res = await fetch(API + "/predict", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Prediction failed"), "error");
      return;
    }
    sessionStorage.setItem("latestResult", JSON.stringify(data));
    window.location.href = "result.html";
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  } finally {
    showLoader(false);
  }
}

async function deleteReport(id) {
  if (!confirm("Delete this report?")) return;
  try {
    const res = await fetch(API + "/report/" + id, {
      method: "DELETE",
      headers: authHeaders(),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Delete failed"), "error");
      return;
    }
    showToast("Deleted", "success");
    loadDashboard();
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  }
}

async function generatePDF(id) {
  if (!id) {
    showToast("Diagnosis ID missing", "error");
    return;
  }
  try {
    const res = await fetch(API + "/report/" + id, { headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Failed to generate report"), "error");
      return;
    }
    window.open(data.download_url, "_blank");
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  }
}

function generateLatestPDF() {
  const id = Number(sessionStorage.getItem("latestDiagnosisId"));
  generatePDF(id);
}

function updateResultActionState() {
  const consent = $("aiConsent");
  const saveBtn = $("savePdfBtn");
  const newDiagnosisLink = $("newDiagnosisLink");
  if (!consent) return;

  const enabled = consent.checked;
  if (saveBtn) saveBtn.disabled = !enabled;
  if (newDiagnosisLink) {
    newDiagnosisLink.classList.toggle("disabled-action", !enabled);
    newDiagnosisLink.setAttribute("aria-disabled", String(!enabled));
  }
}

function requireConsentAndGeneratePdf() {
  const consent = $("aiConsent");
  if (!consent || !consent.checked) {
    showToast("Please check AI consent first", "error");
    return;
  }
  generateLatestPDF();
}

function requireConsentAndGoDiagnosis(event) {
  const consent = $("aiConsent");
  if (!consent || !consent.checked) {
    if (event) event.preventDefault();
    showToast("Please check AI consent first", "error");
    return false;
  }
  return true;
}

function configureDashboard(role) {
  const newDiagnosisBtn = $("newDiagnosisBtn");
  if (newDiagnosisBtn) {
    newDiagnosisBtn.classList.toggle("hidden", role !== "patient");
  }

  const thirdCardTitle = $("thirdCardTitle");
  if (thirdCardTitle) {
    thirdCardTitle.innerText = role === "admin" ? "User Management" : "Health Summary";
  }

  const riskRow = $("totalRiskRow");
  const totalDiagnosisRow = $("totalDiagnosis") ? $("totalDiagnosis").parentElement : null;
  const suggestionsTitle = $("doctorSuggestionsTitle");
  const suggestionsBox = $("patientSuggestions");
  const adminUserList = $("adminUserList");
  const showPatientSummary = role === "patient";
  if (riskRow) riskRow.classList.toggle("hidden", !showPatientSummary);
  if (totalDiagnosisRow) totalDiagnosisRow.classList.toggle("hidden", role === "admin");
  if (suggestionsTitle) suggestionsTitle.classList.toggle("hidden", !showPatientSummary);
  if (suggestionsBox) suggestionsBox.classList.toggle("hidden", !showPatientSummary);
  if (adminUserList) adminUserList.classList.toggle("hidden", role !== "admin");

  if (role !== "doctor") return;

  const firstCard = document.querySelector(".dash-card.highlight");
  if (!firstCard) return;

  firstCard.classList.remove("highlight");
  firstCard.classList.add("doctor-comment-card");
  firstCard.innerHTML = `
    <h3>Patient Comment Box</h3>
    <label for="doctorReportSelect"><strong>Select Report</strong></label>
    <select id="doctorReportSelect"></select>
    <label for="doctorSuggestion"><strong>Suggestion</strong></label>
    <textarea id="doctorSuggestion" rows="6" placeholder="Write your recommendation for the selected patient report..."></textarea>
    <button class="btn" onclick="saveDoctorSuggestion()">Save Suggestion</button>
  `;
}

function populateDoctorReportOptions(reports) {
  const reportSelect = $("doctorReportSelect");
  if (!reportSelect) return;

  reportSelect.innerHTML = "";

  if (!reports.length) {
    reportSelect.innerHTML = `<option value="">No reports available</option>`;
    return;
  }

  reports.forEach((report, index) => {
    const id = Number(report[0]);
    const patientName = report[1] || "Unknown Patient";
    const disease = report[2] || "-";
    const option = document.createElement("option");
    option.value = String(id);
    option.text = `${patientName} - ${disease} (ID: ${id})`;
    if (index === 0) option.selected = true;
    reportSelect.appendChild(option);
  });
}

function setDoctorSuggestionTarget(diagnosisId) {
  const reportSelect = $("doctorReportSelect");
  if (!reportSelect) return;
  reportSelect.value = String(diagnosisId);
}

function renderPatientSuggestions(suggestions) {
  const box = $("patientSuggestions");
  if (!box) return;

  if (!suggestions || !suggestions.length) {
    box.innerHTML = "No suggestions yet.";
    return;
  }

  const latest = suggestions[0];
  const diagnosisId = latest[0];
  const disease = latest[1] || "-";
  const suggestion = latest[2] || "-";
  const doctorName = latest[3] || "Doctor";

  box.innerHTML = `
    <p><strong>Latest for Report #${diagnosisId}</strong></p>
    <p>Disease: ${disease}</p>
    <p>By: Dr. ${doctorName}</p>
    <p>${suggestion}</p>
  `;
}

function renderAdminUserList(users) {
  const list = $("adminUserList");
  if (!list) return;

  if (!users || !users.length) {
    list.innerHTML = "<p>No users found.</p>";
    return;
  }

  list.innerHTML = "";
  users.forEach((user) => {
    const id = Number(user[0]);
    const name = user[1] || "-";
    const email = user[2] || "-";
    const role = user[3] || "-";
    const isActive = Boolean(user[4]);

    const row = document.createElement("div");
    row.className = "admin-user-item";
    row.innerHTML = `
      <p><strong>${name}</strong> (${role})</p>
      <p>${email}</p>
      <p>Status: ${isActive ? "Active" : "Blocked"}</p>
      <button class="btn outline" onclick="toggleUserStatus(${id}, ${isActive})">${isActive ? "Block" : "Activate"}</button>
      <button class="btn admin-delete-btn" onclick="deleteUserByAdmin(${id})">Delete User</button>
      <hr>
    `;
    list.appendChild(row);
  });
}

async function toggleUserStatus(userId, currentStatus) {
  const targetStatus = !currentStatus;
  try {
    const res = await fetch(API + "/admin/users/" + userId + "/status", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ is_active: targetStatus }),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Failed to update user status"), "error");
      return;
    }
    showToast(targetStatus ? "User activated" : "User blocked", "success");
    loadDashboard();
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  }
}

async function deleteUserByAdmin(userId) {
  if (!confirm("Delete this user?")) return;
  try {
    const res = await fetch(API + "/admin/users/" + userId, {
      method: "DELETE",
      headers: authHeaders(),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Failed to delete user"), "error");
      return;
    }
    showToast("User deleted", "success");
    loadDashboard();
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  }
}

async function saveDoctorSuggestion() {
  const role = getRole();
  if (role !== "doctor") return;

  const reportSelect = $("doctorReportSelect");
  const suggestionInput = $("doctorSuggestion");
  if (!reportSelect || !suggestionInput) return;

  const diagnosisId = Number(reportSelect.value);
  const suggestion = suggestionInput.value.trim();
  if (!diagnosisId) {
    showToast("Please select a report", "error");
    return;
  }
  if (!suggestion) {
    showToast("Please write a suggestion", "error");
    return;
  }

  showLoader(true);
  try {
    const res = await fetch(API + "/doctor/suggest/" + diagnosisId, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ suggestion }),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Failed to save suggestion"), "error");
      return;
    }
    suggestionInput.value = "";
    showToast("Suggestion saved", "success");
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  } finally {
    showLoader(false);
  }
}

function loadResultPage() {
  const raw = sessionStorage.getItem("latestResult");
  if (!raw) return;

  const result = JSON.parse(raw);
  if ($("predictedDisease")) $("predictedDisease").innerText = result.predicted_disease || "-";
  if ($("riskProbability")) $("riskProbability").innerText = `${result.confidence || 0}%`;
  if ($("severityStage")) $("severityStage").innerText = result.risk_level || "-";
  if ($("confidenceLevel")) $("confidenceLevel").innerText = result.risk_level || "-";
  if ($("diseaseCategory")) $("diseaseCategory").innerText = result.risk_level || "-";

  sessionStorage.setItem("latestDiagnosisId", result.diagnosis_id);

  const explanation = $("explanation");
  if (explanation) {
    explanation.innerHTML = "";
    (result.explanation || []).forEach((item) => {
      const li = document.createElement("li");
      li.innerText = item;
      explanation.appendChild(li);
    });
  }

  const consent = $("aiConsent");
  if (consent) {
    consent.addEventListener("change", updateResultActionState);
    updateResultActionState();
  }
}

function renderTableRows(container, records, options = {}) {
  const showDoctorAction = Boolean(options.showDoctorAction);
  const showAdminDeletePdf = Boolean(options.showAdminDeletePdf);
  container.innerHTML = "";
  records.forEach((record) => {
    const id = Number(record[0]);
    const disease = record[2] || record[1];
    const confidence = record[3] || record[2] || 0;
    const risk = record[4] || record[3] || "-";
    const patientName = record[1] || "Unknown Patient";
    const row = document.createElement("div");
    const suggestBtn = showDoctorAction
      ? `<button class="btn outline" onclick="setDoctorSuggestionTarget(${id})">Comment on This Report</button>`
      : "";
    const adminDeletePdfBtn = showAdminDeletePdf
      ? `<button class="btn admin-delete-btn" onclick="deletePdfByAdmin(${id})">Delete PDF</button>`
      : "";
    row.innerHTML = `
      <p><strong>Patient:</strong> ${patientName}</p>
      <p><strong>${disease}</strong></p>
      <p>Confidence: ${confidence}%</p>
      <p>Risk: ${risk}</p>
      <button class="btn" onclick="generatePDF(${id})">Download PDF</button>
      ${suggestBtn}
      ${adminDeletePdfBtn}
      <hr>
    `;
    container.appendChild(row);
  });
}

async function deletePdfByAdmin(diagnosisId) {
  if (getRole() !== "admin") return;
  if (!confirm("Delete PDF for this report?")) return;
  try {
    const res = await fetch(API + "/admin/report/" + diagnosisId + "/pdf", {
      method: "DELETE",
      headers: authHeaders(),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(normalizeError(data, "Failed to delete PDF"), "error");
      return;
    }
    showToast("PDF deleted", "success");
    loadDashboard();
  } catch (error) {
    showToast("Unable to connect to backend", "error");
  }
}

async function loadDashboard() {
  const role = getRole();
  const token = getToken();
  if (!token || !role) {
    logout();
    return;
  }

  configureDashboard(role);

  const container = $("cardContent2");
  if (!container) return;

  try {
    if (role === "patient") {
      const [historyRes, suggestionsRes] = await Promise.all([
        fetch(API + "/history", { headers: authHeaders() }),
        fetch(API + "/patient/suggestions", { headers: authHeaders() }),
      ]);
      const data = await historyRes.json();
      const suggestionsData = await suggestionsRes.json();
      if (!historyRes.ok) throw new Error(normalizeError(data, "Failed to load history"));
      if (!suggestionsRes.ok) throw new Error(normalizeError(suggestionsData, "Failed to load suggestions"));
      const history = data.history || [];
      const suggestions = suggestionsData.suggestions || [];
      if (history.length > 0) {
        const last = history[0];
        if ($("dashDisease")) $("dashDisease").innerText = last[1];
        if ($("dashConfidence")) $("dashConfidence").innerText = `${last[2]}%`;
        if ($("dashRisk")) $("dashRisk").innerText = last[3];
      }
      container.innerHTML = "";
      history.forEach((record) => {
        const id = Number(record[0]);
        const div = document.createElement("div");
        div.innerHTML = `
          <p><strong>${record[1]}</strong></p>
          <p>Confidence: ${record[2]}%</p>
          <p>Risk: ${record[3]}</p>
          <button class="btn" onclick="generatePDF(${id})">Download PDF</button>
          <button class="btn outline" onclick="deleteReport(${id})">Delete</button>
          <hr>
        `;
        container.appendChild(div);
      });
      if ($("totalDiagnosis")) $("totalDiagnosis").innerText = history.length;
      const riskyCount = history.filter((record) => String(record[3]).toLowerCase() !== "low").length;
      if ($("totalRiskDiagnosis")) $("totalRiskDiagnosis").innerText = riskyCount;
      renderPatientSuggestions(suggestions);
      return;
    }

    if (role === "doctor") {
      const res = await fetch(API + "/doctor/reports", { headers: authHeaders() });
      const data = await res.json();
      if (!res.ok) throw new Error(normalizeError(data, "Failed to load reports"));
      const reports = data.reports || [];
      populateDoctorReportOptions(reports);
      renderTableRows(container, reports, { showDoctorAction: true });
      if ($("totalDiagnosis")) $("totalDiagnosis").innerText = reports.length;
      return;
    }

    if (role === "admin") {
      const [overviewRes, recordsRes, usersRes] = await Promise.all([
        fetch(API + "/admin/overview", { headers: authHeaders() }),
        fetch(API + "/admin/all-records", { headers: authHeaders() }),
        fetch(API + "/admin/users", { headers: authHeaders() }),
      ]);
      const overview = await overviewRes.json();
      const recordsData = await recordsRes.json();
      const usersData = await usersRes.json();
      if (!overviewRes.ok) throw new Error(normalizeError(overview, "Failed to load overview"));
      if (!recordsRes.ok) throw new Error(normalizeError(recordsData, "Failed to load records"));
      if (!usersRes.ok) throw new Error(normalizeError(usersData, "Failed to load users"));
      if ($("dashDisease")) $("dashDisease").innerText = `Users: ${overview.total_users}`;
      if ($("dashConfidence")) $("dashConfidence").innerText = `Patients: ${overview.patients}`;
      if ($("dashRisk")) $("dashRisk").innerText = `Doctors: ${overview.doctors}`;
      renderTableRows(container, recordsData.records || [], { showAdminDeletePdf: true });
      renderAdminUserList(usersData.users || []);
      return;
    }
  } catch (error) {
    showToast(error.message || "Failed to load dashboard", "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  protectRoute();
  attachBmiCalculator();
  if (document.querySelector(".dash-wrapper")) loadDashboard();
  if (document.body.classList.contains("result-page")) loadResultPage();
});
