import os
import io
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from .db import (
    init_db,
    create_student,
    get_student_by_id,
    get_student_by_roll,
    get_all_students,
    delete_student,
    get_or_create_today_session,
    lock_session,
    unlock_session,
    mark_attendance,
    get_session_attendance
)
from .services.face_engine import face_engine
from .services.sorting import sort_students, filter_by_alphabet
from .services.exporter import export_attendance_to_csv

app = FastAPI(
    title="AlphabetAI Attendance API",
    description="Intelligent Face-Recognition Attendance & Classroom Management System",
    version="1.0.0"
)

# Enable CORS for cross-origin requests (e.g. mobile browsers / Android)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas
class EnrollRequest(BaseModel):
    name: str
    roll_number: str
    class_name: Optional[str] = "CS-A"
    department: Optional[str] = "Computer Science"
    image_base64: str

class ScanRequest(BaseModel):
    image_base64: str

class OverrideRequest(BaseModel):
    student_id: int
    status: str  # Present, Late, Absent, Excused
    note: Optional[str] = ""

class LockSessionRequest(BaseModel):
    lock: bool

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()
    get_or_create_today_session()
    print("[API] Database initialized & session active.")

# Health endpoint
@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "system": "AlphabetAI Attendance",
        "models_loaded": face_engine.detector is not None,
        "timestamp": datetime.now().isoformat()
    }

# Students endpoints
@app.get("/api/students")
def list_students(
    sort_by: str = Query("roll_asc", description="Sort by: roll_asc, roll_desc, name_asc, name_desc"),
    letter: Optional[str] = Query(None, description="A-Z filter")
):
    students = get_all_students()
    if letter:
        students = filter_by_alphabet(students, letter)
    sorted_students = sort_students(students, sort_by=sort_by)
    # Strip raw embedding from client response
    safe_list = []
    for s in sorted_students:
        safe_copy = dict(s)
        safe_copy.pop("embedding", None)
        safe_list.append(safe_copy)
    return {"total": len(safe_list), "students": safe_list}

@app.post("/api/students/enroll")
def enroll_student(data: EnrollRequest):
    if not data.name or not data.roll_number:
        raise HTTPException(status_code=400, detail="Name and Roll Number are required.")
    
    # Check if roll number already exists
    existing = get_student_by_roll(data.roll_number)
    if existing:
        raise HTTPException(status_code=400, detail=f"Roll number {data.roll_number} is already enrolled.")

    # Decode image and extract face embeddings
    img = face_engine.decode_base64_image(data.image_base64)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image data provided.")

    embedding, bbox, quality = face_engine.detect_and_extract_feature(img)
    if embedding is None:
        raise HTTPException(
            status_code=422,
            detail=quality.get("error", "No face detected in photo. Please ensure face is centered with good lighting.")
        )

    # Save to database
    # Keep avatar thumbnail
    avatar_thumb = data.image_base64 if len(data.image_base64) < 150000 else ""
    created = create_student(
        name=data.name,
        roll_number=data.roll_number,
        class_name=data.class_name or "CS-A",
        department=data.department or "Computer Science",
        embedding=embedding,
        avatar_base64=avatar_thumb
    )
    
    clean_student = dict(created)
    clean_student.pop("embedding", None)
    
    return {
        "success": True,
        "message": f"Student {data.name} enrolled successfully.",
        "student": clean_student,
        "bbox": bbox,
        "quality": quality
    }

@app.delete("/api/students/{student_id}")
def remove_student(student_id: int):
    success = delete_student(student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found.")
    return {"success": True, "message": "Student removed successfully."}

# Session endpoints
@app.get("/api/sessions/current")
def get_current_session():
    session = get_or_create_today_session()
    records = get_session_attendance(session["id"])
    
    total = len(records)
    present = sum(1 for r in records if r.get("status") == "Present")
    late = sum(1 for r in records if r.get("status") == "Late")
    absent = sum(1 for r in records if r.get("status") == "Absent")
    rate = round((present + late) / total * 100, 1) if total > 0 else 0.0

    return {
        "session": session,
        "stats": {
            "total_students": total,
            "present_count": present,
            "late_count": late,
            "absent_count": absent,
            "attendance_rate": rate
        }
    }

@app.post("/api/sessions/lock")
def toggle_session_lock(data: LockSessionRequest):
    session = get_or_create_today_session()
    if data.lock:
        lock_session(session["id"])
        msg = "Session locked by teacher."
    else:
        unlock_session(session["id"])
        msg = "Session unlocked."
    return {"success": True, "is_locked": data.lock, "message": msg}

# Attendance Scanning & Matching
@app.post("/api/attendance/scan")
def scan_attendance_frame(data: ScanRequest):
    session = get_or_create_today_session()
    if session.get("is_locked"):
        raise HTTPException(status_code=403, detail="Attendance session is locked by the teacher. Unlock to resume scanning.")

    img = face_engine.decode_base64_image(data.image_base64)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid frame image.")

    # Detect face in frame
    embedding, bbox, quality = face_engine.detect_and_extract_feature(img)
    if embedding is None:
        return {
            "recognized": False,
            "message": "No face detected in camera view",
            "bbox": None
        }

    # Retrieve all enrolled students
    enrolled = get_all_students()
    if not enrolled:
        return {
            "recognized": False,
            "message": "No students currently enrolled in the system",
            "bbox": bbox
        }

    # Match face against enrolled database
    match = face_engine.match_student(embedding, enrolled, threshold=0.363)
    if not match:
        return {
            "recognized": False,
            "message": "Unrecognized face",
            "bbox": bbox,
            "quality": quality
        }

    student_id = match["student_id"]
    
    # Mark student attendance
    status = "Present"
    marked = mark_attendance(
        session_id=session["id"],
        student_id=student_id,
        status=status,
        confidence=float(match["similarity_score"]),
        verification_mode="face",
        note=f"Matched via AI camera ({match['confidence_percentage']}%)"
    )

    return {
        "recognized": True,
        "student": match,
        "bbox": bbox,
        "status": status,
        "marked_at": marked["timestamp"],
        "confidence": match["confidence_percentage"]
    }

# Live Attendance Records (Sorted according to AlphabetAI rules)
@app.get("/api/attendance/records")
def list_attendance_records(
    sort_by: str = Query("roll_asc", description="Sorting: roll_asc, roll_desc, name_asc, name_desc, status"),
    letter: Optional[str] = Query(None, description="A-Z initial letter filter")
):
    session = get_or_create_today_session()
    records = get_session_attendance(session["id"])
    
    if letter:
        records = filter_by_alphabet(records, letter)
        
    sorted_records = sort_students(records, sort_by=sort_by)
    return {
        "session_id": session["id"],
        "is_locked": bool(session.get("is_locked")),
        "total": len(sorted_records),
        "records": sorted_records
    }

# Teacher Manual Override
@app.post("/api/attendance/override")
def teacher_override(data: OverrideRequest):
    session = get_or_create_today_session()
    valid_statuses = ["Present", "Late", "Absent", "Excused"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")

    student = get_student_by_id(data.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    result = mark_attendance(
        session_id=session["id"],
        student_id=data.student_id,
        status=data.status,
        confidence=1.0,
        verification_mode="manual",
        note=data.note or "Teacher manual override"
    )
    return {"success": True, "record": result}

# Export Attendance Register (CSV)
@app.get("/api/attendance/export")
def export_attendance():
    session = get_or_create_today_session()
    records = get_session_attendance(session["id"])
    csv_content = export_attendance_to_csv(session, records)
    
    filename = f"AlphabetAI_Attendance_{session['session_date']}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Static file serving: Serve frontend directly from project root or static folder
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(WORKSPACE_DIR, "static")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

# Mount static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_file):
        index_file = os.path.join(WORKSPACE_DIR, "index.html")
    return FileResponse(index_file)

@app.get("/{filename:path}")
def serve_file(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(file_path):
        file_path = os.path.join(WORKSPACE_DIR, filename)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")
