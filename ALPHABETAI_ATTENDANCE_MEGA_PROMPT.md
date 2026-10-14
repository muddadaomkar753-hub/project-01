# MEGA PROMPT: AlphabetAI — Intelligent Face-Recognition Attendance & Classroom Management System

## 1. Project Overview & Objective
Build "AlphabetAI Attendance", an enterprise-ready, mobile-responsive Progressive Web Application (PWA) and backend system designed for schools, universities, and training academies. The system automates attendance logging using computer vision and facial recognition, intelligently organizes student rosters (A–Z alphabetization and roll-number sequencing), and provides a secure dashboard for teachers with anti-spoofing and audit controls.

---

## 2. Core Architecture & Tech Stack

### Frontend / Mobile-First Client
- **Framework**: Next.js 14 (App Router) / React, TypeScript, Tailwind CSS, Lucide React / Heroicons.
- **PWA Support**: Offline-capable service workers, installable on Android & iOS.
- **Client-Side Vision / Camera**:
  - HTML5 WebRTC `getUserMedia` with automatic rear/front camera switching.
  - Face-api.js or MediaPipe for client-side face landmark detection, bounding box overlay, and liveness challenge (blink, head turn, smile) before server verification.

### Backend / AI Engine
- **Backend Framework**: Python 3.11+ (FastAPI) or Node.js (TypeScript) with a dedicated Python microservice for AI processing.
- **Face Recognition Pipeline**:
  - Detection: RetinaFace / MTCNN / MediaPipe Face Mesh.
  - Recognition & Embeddings: InsightFace (ArcFace) or `face_recognition` (dlib) producing 128-d or 512-d feature vectors.
  - Vector Similarity Search: FAISS or pgvector for fast cosine similarity lookup across large class sizes (<100ms response).
  - Liveness / Anti-Spoofing: Passive texture analysis (MiniFASNet) + active challenge-response to prevent photo and screen playback attacks.

### Database & Storage
- **Database**: PostgreSQL (with `pgvector` extension) or SQLite (for local/offline deployment).
- **ORM**: Prisma (Node/Next) or SQLAlchemy / Tortoise (FastAPI).
- **Storage**: S3-compatible storage or encrypted local disk for avatar thumbnails; option to store **only encrypted mathematical vector embeddings** and discard raw face images for GDPR/FERPA compliance.

---

## 3. Detailed Functional Modules

### Module 1: Student Self-Registration & Admin Onboarding
1. **Student Profile**: First Name, Last Name, Student ID / Roll Number, Email, Class/Section, Department, Contact Info.
2. **Face Enrollment Flow**:
   - Multi-angle capture (Front, Left 30°, Right 30°, Slight Smile).
   - Real-time quality check: Lighting score, blur detection (Laplacian variance), and alignment guidance.
   - Generates and averages normalized face embeddings.
3. **Batch Import**: CSV/Excel student roster import with invitation links for self-capture via mobile phone camera.

### Module 2: The "AlphabetAI" Smart Roster & Sorting Engine
1. **Dynamic Sorting**:
   - **Alphabetical (A–Z / Z–A)**: Sort by Last Name, First Name (handling multi-part names and locale-aware collation).
   - **Sequential Roll Number**: Natural sorting (e.g., `CS-01`, `CS-02`, `CS-10`).
   - **Status-based**: Unmarked → Present → Late → Absent.
2. **Smart Filters & Grouping**: Filter by Class, Batch, Academic Term, Attendance Range (<75% defaulters), or Date Range.
3. **Alphabet Index Bar**: Quick-jump index navigation bar (A, B, C... Z) for rapid roster scrolling on mobile screens.

### Module 3: Live Face Recognition Attendance Scanner (Mobile & Kiosk)
1. **Single-Scan Mode (Mobile)**:
   - Teacher holds mobile camera in front of entering students.
   - Green bounding box with recognized student name, roll number, and match confidence score (e.g., `John Doe (CS-102) - 98.4%`).
   - Audible affirmative chime and haptic feedback on successful recognition.
2. **Kiosk Mode (Wall-mounted Tablet / Laptop)**:
   - Continuous scanning loop with duplicate check (prevents re-scanning the same student within the same lecture session).
   - Instant attendance status update: Automatically marked as "Present" or "Late" based on class start time thresholds.
3. **Offline Mode**:
   - Downloads daily session roster and cached vector embeddings to IndexedDB.
   - Logs timestamps offline; synchronizes with server when connectivity is restored.

### Module 4: Teacher Verification & Proctor Dashboard
1. **Real-time Session Monitor**:
   - Live attendance counter (e.g., `42 / 50 Present - 84%`).
   - One-tap manual override (Present, Late, Absent, Excused) with reason note.
   - Low-Confidence Review Queue: Any match below 85% confidence is flagged for quick teacher sign-off with side-by-side photo comparison.
2. **Session Sign-Off**: Teacher digital signature or 4-digit PIN verification to lock attendance records after lecture conclusion.
3. **Audit Log**: Immutable ledger of who marked or updated attendance, timestamp, and verification method (Face / Manual).

### Module 5: Analytics, Reports & Alerts
1. **Defaulter Alerts**: Automatic red-flagging of students falling below statutory thresholds (e.g., 75% attendance).
2. **One-Click Export**:
   - Formal A–Z attendance sheet in Excel (.xlsx), CSV, and printable PDF.
   - Daily, weekly, and monthly consolidated registers.
3. **Automated Notifications**: Email/SMS trigger to absentee students or parents (configurable).

---

## 4. Security, Privacy & Compliance Guidelines

1. **Privacy by Design (GDPR / FERPA compliant)**:
   - User consent opt-in during registration.
   - Vector-only storage mode: Store non-reversible float arrays, never unencrypted biometric photos.
   - Encryption at rest (AES-256) and in transit (TLS 1.3).
2. **Role-Based Access Control (RBAC)**:
   - `Super Admin`: System setup, school configuration, user permissions.
   - `Teacher / Proctor`: Initiate attendance sessions, verify, override, and export.
   - `Student`: View personal attendance record, submit absence excuses, update avatar/face.
3. **Spoofing Defense**:
   - Active blink/movement challenges on enrollment.
   - Passive anti-spoofing to reject flat printouts and digital screens.

---

## 5. Target Project Directory Structure

```text
alphabetai-attendance/
├── client/                     # Next.js 14 Frontend PWA
│   ├── public/                 # Static assets, PWA manifest, sound effects
│   ├── src/
│   │   ├── app/                # App Router (pages: /attendance, /students, /roster, /reports)
│   │   ├── components/         # CameraCapture, FaceScanner, AlphabetRoster, StatCard
│   │   ├── hooks/              # useCamera, useFaceDetection, useOfflineSync
│   │   ├── lib/                # API client, IndexedDB storage, audio triggers
│   │   └── types/              # TypeScript interfaces (Student, Session, Record)
│   ├── package.json
│   └── tailwind.config.ts
├── server/                     # FastAPI Backend & AI Pipeline
│   ├── app/
│   │   ├── api/                # Endpoints (auth, students, attendance, sessions, reports)
│   │   ├── core/               # Config, security, JWT authentication
│   │   ├── db/                 # Database models, migrations, pgvector schema
│   │   ├── services/
│   │   │   ├── face_engine.py  # RetinaFace + InsightFace extraction & matching
│   │   │   ├── liveness.py     # Anti-spoofing verification
│   │   │   ├── sorting.py      # AlphabetAI A-Z & roll-number ordering algorithms
│   │   │   └── exporter.py     # Excel & PDF generation
│   │   └── main.py             # FastAPI entrypoint
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml          # Multi-container setup (Client, API, Postgres/pgvector)
├── .env.example
└── README.md                   # Setup, installation, and deployment instructions
```

---

## 6. Execution Instructions
Generate the project starting with:
1. Complete Database Schema (SQL / Prisma).
2. Backend core APIs and the Face Recognition Service with cosine similarity matching.
3. Next.js PWA with camera view, face detection bounding box, and the AlphabetAI sorted roster interface.
4. Export scripts and docker-compose deployment configuration.
