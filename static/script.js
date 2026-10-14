// ========================================================
// AlphabetAI Attendance System - Client Engine
// ========================================================

const API_BASE = ""; // Relative to host (works on localhost & mobile LAN IP)

// DOM Elements - Scanner
const video = document.getElementById("camera");
const overlayCanvas = document.getElementById("overlayCanvas");
const captureCanvas = document.getElementById("captureCanvas");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const flipBtn = document.getElementById("flipBtn");
const scanOnceBtn = document.getElementById("scanOnceBtn");
const autoScanToggle = document.getElementById("autoScanToggle");
const placeholder = document.getElementById("placeholder");
const matchBanner = document.getElementById("matchBanner");
const matchAvatar = document.getElementById("matchAvatar");
const matchName = document.getElementById("matchName");
const matchDetail = document.getElementById("matchDetail");
const liveFeedList = document.getElementById("liveFeedList");
const streamCountBadge = document.getElementById("streamCountBadge");

// Session & KPI Elements
const sessionStatusBadge = document.getElementById("sessionStatusBadge");
const lockSessionBtn = document.getElementById("lockSessionBtn");
const exportCsvBtn = document.getElementById("exportCsvBtn");
const kpiTotal = document.getElementById("kpiTotal");
const kpiPresent = document.getElementById("kpiPresent");
const kpiLate = document.getElementById("kpiLate");
const kpiAbsent = document.getElementById("kpiAbsent");
const kpiRate = document.getElementById("kpiRate");

// Roster Elements
const rosterTableBody = document.getElementById("rosterTableBody");
const rosterSearchInput = document.getElementById("rosterSearchInput");
const sortSelect = document.getElementById("sortSelect");
const alphabetNav = document.getElementById("alphabetNav");
const refreshRosterBtn = document.getElementById("refreshRosterBtn");

// Enrollment Elements
const enrollCamera = document.getElementById("enrollCamera");
const enrollImgPreview = document.getElementById("enrollImgPreview");
const enrollCameraPlaceholder = document.getElementById("enrollCameraPlaceholder");
const startEnrollCamBtn = document.getElementById("startEnrollCamBtn");
const snapEnrollBtn = document.getElementById("snapEnrollBtn");
const uploadEnrollBtn = document.getElementById("uploadEnrollBtn");
const enrollFileInput = document.getElementById("enrollFileInput");
const enrollForm = document.getElementById("enrollForm");
const enrollFeedback = document.getElementById("enrollFeedback");
const qualityScoreText = document.getElementById("qualityScoreText");

// App State
let stream = null;
let enrollStream = null;
let facingMode = "user";
let isScanning = false;
let autoScanTimer = null;
let activeLetter = "ALL";
let currentSessionLocked = false;
let allRecordsCache = [];
const recentlyScanned = new Map(); // student_id -> timestamp to avoid continuous duplicate alert spam

// ========================================================
// Audio Feedback (Synthesized chime via Web Audio API)
// ========================================================
function playChime() {
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = "sine";
    // Uplifting two-tone chime (880Hz A5 -> 1320Hz E6)
    osc.frequency.setValueAtTime(880, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1320, audioCtx.currentTime + 0.15);

    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start();
    osc.stop(audioCtx.currentTime + 0.4);
  } catch (e) {
    console.warn("Audio playback not allowed without interaction:", e);
  }
}

// ========================================================
// Camera Stream Controls (Mobile-Responsive & WebRTC)
// ========================================================
async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    alert("Camera API unavailable. Access this page via HTTPS or localhost.");
    return;
  }

  startBtn.disabled = true;
  startBtn.textContent = "Connecting...";

  try {
    stopCamera(false);

    stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: { ideal: facingMode },
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    });

    video.srcObject = stream;
    await video.play();

    video.classList.add("active");
    placeholder.style.display = "none";
    startBtn.textContent = "Camera Running";
    stopBtn.disabled = false;
    scanOnceBtn.disabled = false;

    // Start auto-scan loop
    if (autoScanToggle.checked) {
      startAutoScanLoop();
    }

    stream.getVideoTracks()[0].addEventListener("ended", () => {
      stopCamera();
    });

  } catch (error) {
    console.error("Camera error:", error);
    alert("Could not access camera: " + error.message);
    placeholder.style.display = "flex";
    startBtn.textContent = "Start Camera Feed";
    startBtn.disabled = false;
  }
}

function stopCamera(updateUI = true) {
  stopAutoScanLoop();
  clearOverlay();

  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
  }

  video.pause();
  video.srcObject = null;
  video.classList.remove("active");

  if (updateUI) {
    placeholder.style.display = "flex";
    startBtn.textContent = "Start Camera Feed";
    startBtn.disabled = false;
    stopBtn.disabled = true;
    scanOnceBtn.disabled = true;
  }
}

async function flipCamera() {
  facingMode = facingMode === "user" ? "environment" : "user";
  if (stream) {
    await startCamera();
  }
}

// ========================================================
// Face Detection & Real-Time Canvas Bounding Box
// ========================================================
function clearOverlay() {
  const ctx = overlayCanvas.getContext("2d");
  ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
}

function drawBoundingBox(bbox, label, isSuccess) {
  if (!bbox || !video.videoWidth) return;

  overlayCanvas.width = video.clientWidth;
  overlayCanvas.height = video.clientHeight;

  const ctx = overlayCanvas.getContext("2d");
  ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

  // Scale from native video dimensions to rendered canvas size
  const scaleX = overlayCanvas.width / video.videoWidth;
  const scaleY = overlayCanvas.height / video.videoHeight;

  const [x, y, w, h] = bbox;
  const rx = x * scaleX;
  const ry = y * scaleY;
  const rw = w * scaleX;
  const rh = h * scaleY;

  // Box Styling
  ctx.lineWidth = 3;
  ctx.strokeStyle = isSuccess ? "#10b981" : "#f59e0b";
  ctx.fillStyle = isSuccess ? "rgba(16, 185, 129, 0.2)" : "rgba(245, 158, 11, 0.2)";

  // Draw rounded rect
  ctx.beginPath();
  ctx.roundRect(rx, ry, rw, rh, 8);
  ctx.stroke();
  ctx.fill();

  // Label banner
  if (label) {
    ctx.font = "bold 14px -apple-system, sans-serif";
    const textWidth = ctx.measureText(label).width;
    const bannerH = 26;
    const bannerW = textWidth + 16;

    ctx.fillStyle = isSuccess ? "#10b981" : "#f59e0b";
    ctx.beginPath();
    ctx.roundRect(rx, Math.max(0, ry - bannerH - 4), bannerW, bannerH, 4);
    ctx.fill();

    ctx.fillStyle = "#ffffff";
    ctx.fillText(label, rx + 8, Math.max(18, ry - 10));
  }
}

// ========================================================
// Frame Capture & API Recognition Call
// ========================================================
async function scanCurrentFrame() {
  if (isScanning || !video.videoWidth || currentSessionLocked) return;

  isScanning = true;

  try {
    captureCanvas.width = video.videoWidth;
    captureCanvas.height = video.videoHeight;
    const ctx = captureCanvas.getContext("2d");
    ctx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);

    const base64Image = captureCanvas.toDataURL("image/jpeg", 0.85);

    const res = await fetch(`${API_BASE}/api/attendance/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_base64: base64Image })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 403) {
        alert("Session is locked by teacher.");
      }
      return;
    }

    const data = await res.json();

    if (data.recognized && data.student) {
      const student = data.student;
      const label = `${student.name} (${student.roll_number}) - ${data.confidence}%`;
      drawBoundingBox(data.bbox, label, true);

      // Check duplicate suppression (15s cooldown for chime/banner)
      const lastScanned = recentlyScanned.get(student.student_id) || 0;
      const now = Date.now();

      if (now - lastScanned > 15000) {
        recentlyScanned.set(student.student_id, now);
        playChime();
        showMatchBanner(student, data.confidence);
        addToLiveFeed(student, data.confidence);
        loadSessionStats();
        loadRosterRecords();
      }
    } else if (data.bbox) {
      drawBoundingBox(data.bbox, "Unrecognized Student", false);
    } else {
      clearOverlay();
    }

  } catch (err) {
    console.warn("Scan frame error:", err);
  } finally {
    isScanning = false;
  }
}

function startAutoScanLoop() {
  stopAutoScanLoop();
  autoScanTimer = setInterval(() => {
    if (stream && video.videoWidth && autoScanToggle.checked) {
      scanCurrentFrame();
    }
  }, 750);
}

function stopAutoScanLoop() {
  if (autoScanTimer) {
    clearInterval(autoScanTimer);
    autoScanTimer = null;
  }
}

// ========================================================
// Match Notifications & Live Stream Feed
// ========================================================
function showMatchBanner(student, confidence) {
  matchName.textContent = `${student.name} (${student.roll_number})`;
  matchDetail.textContent = `Marked Present • Confidence: ${confidence}% • ${new Date().toLocaleTimeString()}`;
  matchBanner.classList.add("active");

  setTimeout(() => {
    matchBanner.classList.remove("active");
  }, 5000);
}

function addToLiveFeed(student, confidence) {
  const existingEmpty = liveFeedList.querySelector("p");
  if (existingEmpty) existingEmpty.remove();

  const item = document.createElement("div");
  item.className = "feed-item";
  item.innerHTML = `
    <div class="feed-item-left">
      <span class="feed-badge">${student.roll_number}</span>
      <div>
        <div class="feed-name">${student.name}</div>
        <div class="feed-time">Confidence: ${confidence}% • Just now</div>
      </div>
    </div>
    <span class="status-pill present">Present</span>
  `;

  liveFeedList.prepend(item);

  // Keep max 15 items in feed
  while (liveFeedList.children.length > 15) {
    liveFeedList.removeChild(liveFeedList.lastChild);
  }

  const count = liveFeedList.children.length;
  streamCountBadge.textContent = `${count} Checked In`;
}

// ========================================================
// Session & KPI Management
// ========================================================
async function loadSessionStats() {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/current`);
    if (!res.ok) return;
    const data = await res.json();

    const stats = data.stats;
    kpiTotal.textContent = stats.total_students;
    kpiPresent.textContent = stats.present_count;
    kpiLate.textContent = stats.late_count;
    kpiAbsent.textContent = stats.absent_count;
    kpiRate.textContent = `${stats.attendance_rate}%`;

    currentSessionLocked = !!data.session.is_locked;
    updateLockBadge(currentSessionLocked);
  } catch (err) {
    console.error("Session stats error:", err);
  }
}

function updateLockBadge(isLocked) {
  if (isLocked) {
    sessionStatusBadge.textContent = "🔒 Session Locked";
    sessionStatusBadge.className = "session-badge locked";
    lockSessionBtn.textContent = "🔓 Unlock Session";
  } else {
    sessionStatusBadge.textContent = "● Active Session";
    sessionStatusBadge.className = "session-badge";
    lockSessionBtn.textContent = "🔒 Lock Session";
  }
}

async function toggleSessionLock() {
  try {
    const nextState = !currentSessionLocked;
    const res = await fetch(`${API_BASE}/api/sessions/lock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lock: nextState })
    });
    if (res.ok) {
      currentSessionLocked = nextState;
      updateLockBadge(currentSessionLocked);
      alert(nextState ? "Attendance session is now locked." : "Attendance session unlocked.");
    }
  } catch (err) {
    alert("Error locking session: " + err.message);
  }
}

// ========================================================
// AlphabetAI Roster & Sorting Engine
// ========================================================
function setupAlphabetNav() {
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
  alphabetNav.innerHTML = `<button class="letter-btn all-btn active" data-letter="ALL">ALL</button>`;

  letters.forEach(letter => {
    const btn = document.createElement("button");
    btn.className = "letter-btn";
    btn.dataset.letter = letter;
    btn.textContent = letter;
    alphabetNav.appendChild(btn);
  });

  alphabetNav.addEventListener("click", e => {
    const btn = e.target.closest(".letter-btn");
    if (!btn) return;
    document.querySelectorAll(".letter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeLetter = btn.dataset.letter;
    loadRosterRecords();
  });
}

async function loadRosterRecords() {
  try {
    const sortVal = sortSelect.value;
    const url = new URL(`${window.location.origin}${API_BASE}/api/attendance/records`);
    url.searchParams.set("sort_by", sortVal);
    if (activeLetter !== "ALL") {
      url.searchParams.set("letter", activeLetter);
    }

    const res = await fetch(url);
    if (!res.ok) return;
    const data = await res.json();
    allRecordsCache = data.records;
    renderRosterTable(allRecordsCache);
  } catch (err) {
    console.error("Roster load error:", err);
  }
}

function renderRosterTable(records) {
  const filterQuery = rosterSearchInput.value.trim().toLowerCase();
  const filtered = records.filter(r => {
    if (!filterQuery) return true;
    return r.name.toLowerCase().includes(filterQuery) ||
           r.roll_number.toLowerCase().includes(filterQuery) ||
           (r.department && r.department.toLowerCase().includes(filterQuery));
  });

  if (filtered.length === 0) {
    rosterTableBody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: #94a3b8; padding: 30px;">
          No matching student records found.
        </td>
      </tr>
    `;
    return;
  }

  rosterTableBody.innerHTML = filtered.map(r => {
    const initials = r.name.split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase();
    const avatarHtml = r.avatar_base64 
      ? `<img src="${r.avatar_base64}" alt="${r.name}">`
      : initials;
      
    const statusClass = (r.status || "absent").toLowerCase();
    const isAi = r.verification_mode === "face";
    const verifBadge = isAi
      ? `<span style="color: #047857; font-weight: 600;">🤖 AI Face (${roundPercent(r.confidence)}%)</span>`
      : `<span style="color: #64748b;">${r.verification_mode || 'Manual'}</span>`;

    return `
      <tr class="student-row">
        <td>
          <div class="student-cell">
            <div class="student-avatar">${avatarHtml}</div>
            <div>
              <div style="font-weight: 700;">${r.name}</div>
              <small style="color: #64748b;">${r.class_name || ''}</small>
            </div>
          </div>
        </td>
        <td><strong style="color: #173fc5;">${r.roll_number}</strong></td>
        <td>${r.department || 'Computer Science'}</td>
        <td><span class="status-pill ${statusClass}">${r.status}</span></td>
        <td>${verifBadge}</td>
        <td>
          <div class="quick-actions">
            <button class="mini-btn p" onclick="handleOverride(${r.student_id}, 'Present')" title="Mark Present">P</button>
            <button class="mini-btn l" onclick="handleOverride(${r.student_id}, 'Late')" title="Mark Late">L</button>
            <button class="mini-btn a" onclick="handleOverride(${r.student_id}, 'Absent')" title="Mark Absent">A</button>
          </div>
        </td>
        <td>
          <button class="mini-btn" style="color: #ef4444;" onclick="handleDeleteStudent(${r.student_id})" title="Remove Student">🗑</button>
        </td>
      </tr>
    `;
  }).join("");
}

function roundPercent(val) {
  if (!val) return 0;
  return Math.round(val * 100);
}

// Teacher Quick Status Override
window.handleOverride = async function(studentId, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/api/attendance/override`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId, status: newStatus, note: "Teacher manual override" })
    });
    if (res.ok) {
      loadSessionStats();
      loadRosterRecords();
    } else {
      const err = await res.json();
      alert("Override failed: " + err.detail);
    }
  } catch (err) {
    alert("Override error: " + err.message);
  }
};

window.handleDeleteStudent = async function(studentId) {
  if (!confirm("Are you sure you want to delete this enrolled student?")) return;
  try {
    const res = await fetch(`${API_BASE}/api/students/${studentId}`, { method: "DELETE" });
    if (res.ok) {
      loadSessionStats();
      loadRosterRecords();
    }
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
};

// ========================================================
// Student Enrollment Flow (Camera & Photo Upload)
// ========================================================
let enrolledImageBase64 = "";

async function startEnrollCamera() {
  try {
    enrollStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } }
    });
    enrollCamera.srcObject = enrollStream;
    enrollCamera.style.display = "block";
    enrollImgPreview.style.display = "none";
    enrollCameraPlaceholder.style.display = "none";
    snapEnrollBtn.disabled = false;
    startEnrollCamBtn.textContent = "Camera Active";
  } catch (err) {
    alert("Could not start enrollment camera: " + err.message);
  }
}

function takeEnrollSnapshot() {
  if (!enrollStream) return;
  captureCanvas.width = enrollCamera.videoWidth;
  captureCanvas.height = enrollCamera.videoHeight;
  const ctx = captureCanvas.getContext("2d");
  ctx.drawImage(enrollCamera, 0, 0);

  enrolledImageBase64 = captureCanvas.toDataURL("image/jpeg", 0.9);
  enrollImgPreview.src = enrolledImageBase64;
  enrollImgPreview.style.display = "block";
  enrollCamera.style.display = "none";

  // Stop camera track
  enrollStream.getTracks().forEach(t => t.stop());
  enrollStream = null;
  startEnrollCamBtn.textContent = "Restart Camera";
  snapEnrollBtn.disabled = true;

  qualityScoreText.textContent = "Photo captured ready for registration.";
}

function handlePhotoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(event) {
    enrolledImageBase64 = event.target.result;
    enrollImgPreview.src = enrolledImageBase64;
    enrollImgPreview.style.display = "block";
    enrollCamera.style.display = "none";
    enrollCameraPlaceholder.style.display = "none";
    qualityScoreText.textContent = "Photo uploaded ready for registration.";
  };
  reader.readAsDataURL(file);
}

enrollForm.addEventListener("submit", async e => {
  e.preventDefault();
  if (!enrolledImageBase64) {
    alert("Please capture or upload a clear face photo first.");
    return;
  }

  const submitBtn = document.getElementById("submitEnrollBtn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Processing Face Embedding...";
  enrollFeedback.textContent = "";

  try {
    const payload = {
      name: document.getElementById("enrollName").value.trim(),
      roll_number: document.getElementById("enrollRoll").value.trim(),
      class_name: document.getElementById("enrollClass").value.trim(),
      department: document.getElementById("enrollDept").value.trim(),
      image_base64: enrolledImageBase64
    };

    const res = await fetch(`${API_BASE}/api/students/enroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (res.ok) {
      enrollFeedback.style.color = "#10b981";
      enrollFeedback.textContent = `✓ Successfully enrolled ${payload.name} (${payload.roll_number})!`;
      enrollForm.reset();
      enrolledImageBase64 = "";
      enrollImgPreview.style.display = "none";
      enrollCameraPlaceholder.style.display = "block";
      qualityScoreText.textContent = "-";

      loadSessionStats();
      loadRosterRecords();
    } else {
      enrollFeedback.style.color = "#ef4444";
      enrollFeedback.textContent = `✗ Enrollment failed: ${data.detail || "Unable to extract face"}`;
    }
  } catch (err) {
    enrollFeedback.style.color = "#ef4444";
    enrollFeedback.textContent = `✗ Network error: ${err.message}`;
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "✓ Register Student & Extract Face Embedding";
  }
});

// ========================================================
// Navigation Tab Switching
// ========================================================
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

    btn.classList.add("active");
    const targetPane = document.getElementById(btn.dataset.tab);
    if (targetPane) targetPane.classList.add("active");

    if (btn.dataset.tab === "rosterPane") {
      loadRosterRecords();
    }
  });
});

// ========================================================
// Event Listeners Initialization
// ========================================================
startBtn.addEventListener("click", startCamera);
stopBtn.addEventListener("click", () => stopCamera());
flipBtn.addEventListener("click", flipCamera);
scanOnceBtn.addEventListener("click", scanCurrentFrame);
autoScanToggle.addEventListener("change", () => {
  if (autoScanToggle.checked && stream) {
    startAutoScanLoop();
  } else {
    stopAutoScanLoop();
  }
});

lockSessionBtn.addEventListener("click", toggleSessionLock);
exportCsvBtn.addEventListener("click", () => {
  window.location.href = `${API_BASE}/api/attendance/export`;
});

sortSelect.addEventListener("change", loadRosterRecords);
rosterSearchInput.addEventListener("input", () => renderRosterTable(allRecordsCache));
refreshRosterBtn.addEventListener("click", () => {
  loadSessionStats();
  loadRosterRecords();
});

startEnrollCamBtn.addEventListener("click", startEnrollCamera);
snapEnrollBtn.addEventListener("click", takeEnrollSnapshot);
uploadEnrollBtn.addEventListener("click", () => enrollFileInput.click());
enrollFileInput.addEventListener("change", handlePhotoUpload);

window.addEventListener("pagehide", () => stopCamera(false));

// Initial App Boot
setupAlphabetNav();
loadSessionStats();
loadRosterRecords();