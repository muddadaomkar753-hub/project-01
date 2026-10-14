# AlphabetAI Attendance & Classroom Management System

An enterprise-ready, mobile-responsive face-recognition attendance and classroom management system built with Python (FastAPI, OpenCV YuNet & SFace) and a modern HTML5/WebRTC frontend.

---

## 🌟 Key Features

1. **Intelligent Face Recognition & Vector Similarity**:
   - **YuNet**: Real-time neural network face detection and 5-point landmark alignment.
   - **SFace**: Deep cosine similarity embedding extraction producing 128-dimensional biometric vectors.
   - **Quality Assessment**: Real-time image sharpness (Laplacian variance) and illumination checks.
2. **AlphabetAI Smart Roster & Sorting Engine**:
   - **Natural Sequential Roll Number Sorting**: E.g. `CS-01`, `CS-02`, `CS-10`, `CS-100`.
   - **Alphabetical A–Z / Z–A Sorting**: By Student Last Name, First Name.
   - **Status Priority Sorting**: `Present` → `Late` → `Absent` → `Unmarked`.
   - **Alphabet Quick-Jump Index Bar**: One-tap jump to students by letter (`A`, `B`, `C` ... `Z`).
3. **Live Camera Scanner (Desktop & Android Mobile)**:
   - Live bounding box overlay displaying match name, roll number, and confidence percentage.
   - Front and rear camera flipping for mobile / Android devices.
   - Synthesized Web Audio chime on verified match.
   - Duplicate match suppression (prevents redundant logging within sessions).
4. **Teacher Proctoring & Audit Dashboard**:
   - Live attendance KPI counters (Total, Present, Late, Absent, Attendance %).
   - One-tap quick status overrides (`P` / `L` / `A`).
   - Digital session locking.
   - One-click formal A–Z attendance register export to CSV.

---

## 🚀 Quick Start Guide

### 1. Launch the Server
From the project directory:

```powershell
python run_server.py
```

You will see:
```text
=================================================================
🚀 AlphabetAI Attendance System Server Starting...
=================================================================
👉 Local Access:   http://localhost:8000
📱 Android Access: http://192.168.x.x:8000
=================================================================
```

### 2. Open on Desktop
Navigate to [http://localhost:8000](http://localhost:8000) in your web browser (Chrome, Edge, Firefox).

---

## 📱 How to Connect an Android Phone Camera

There are two primary ways to connect your Android device:

### Option A: Mobile Browser Scanner (Direct WebRTC)
1. Ensure your Android phone and PC are connected to the **same Wi-Fi network**.
2. Run `python run_server.py` and note the `Android Access` IP address (e.g., `http://192.168.1.15:8000`).
3. On your Android phone, open Chrome or Edge and go to that address.
4. Tap **Start Camera Feed** and allow camera permission.
5. Use the **Flip (Front / Rear)** button to switch to the high-resolution rear classroom camera.
6. The phone will continuously scan entering students and mark attendance in real time.

> **Note on Chrome Camera Permissions on LAN**:  
> If Android Chrome restricts camera access on plain HTTP over LAN, enable this once in Chrome:  
> 1. In Android Chrome, visit `chrome://flags/#unsafely-treat-insecure-origin-as-secure`  
> 2. Add your server address (e.g., `http://192.168.1.15:8000`) and tap **Enable**.  
> 3. Relaunch Chrome.

### Option B: External IP Webcam / DroidCam
If using DroidCam or IP Webcam app to turn your phone into a webcam for your PC:
- Install DroidCam client on PC and select the DroidCam source in browser permissions.

---

## 🛠️ API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /api/health` | GET | Health and model initialization status |
| `GET /api/students` | GET | List enrolled students (supports `sort_by` and `letter`) |
| `POST /api/students/enroll` | POST | Enroll student with face photo, metadata, and 128-d vector |
| `DELETE /api/students/{id}` | DELETE | Remove enrolled student |
| `GET /api/sessions/current` | GET | Current session details and live KPI counts |
| `POST /api/sessions/lock` | POST | Lock or unlock attendance session |
| `POST /api/attendance/scan` | POST | Submit camera frame for face detection and attendance logging |
| `GET /api/attendance/records` | GET | Live attendance roster with sorting and filters |
| `POST /api/attendance/override` | POST | Teacher manual override (Present, Late, Absent, Excused) |
| `GET /api/attendance/export` | GET | Download formal A–Z attendance sheet in CSV format |

---

## 🧪 Testing

Run the included automated test suite:

```powershell
python test_system.py
```
