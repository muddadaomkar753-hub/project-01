import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "attendance.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Students table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_number TEXT UNIQUE NOT NULL,
        class_name TEXT DEFAULT 'General',
        department TEXT DEFAULT 'Computer Science',
        embedding TEXT NOT NULL,
        avatar_base64 TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_date TEXT NOT NULL,
        course_name TEXT DEFAULT 'Attendance Session',
        teacher_name TEXT DEFAULT 'Instructor',
        is_locked INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)
    
    # Attendance records table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present', 'Late', 'Absent', 'Excused')),
        confidence REAL DEFAULT 1.0,
        verification_mode TEXT DEFAULT 'face',
        timestamp TEXT NOT NULL,
        note TEXT DEFAULT '',
        FOREIGN KEY (session_id) REFERENCES sessions (id),
        FOREIGN KEY (student_id) REFERENCES students (id),
        UNIQUE(session_id, student_id)
    )
    """)
    
    conn.commit()
    conn.close()

# Student operations
def create_student(name: str, roll_number: str, class_name: str, department: str, embedding: List[float], avatar_base64: str = "") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    embedding_json = json.dumps(embedding)
    
    cursor.execute("""
        INSERT INTO students (name, roll_number, class_name, department, embedding, avatar_base64, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name.strip(), roll_number.strip().upper(), class_name.strip(), department.strip(), embedding_json, avatar_base64, now))
    
    student_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_student_by_id(student_id)

def get_student_by_id(student_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(row)
        data['embedding'] = json.loads(data['embedding'])
        return data
    return None

def get_student_by_roll(roll_number: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE roll_number = ?", (roll_number.strip().upper(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(row)
        data['embedding'] = json.loads(data['embedding'])
        return data
    return None

def get_all_students() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, roll_number, class_name, department, avatar_base64, created_at, embedding FROM students")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        item['embedding'] = json.loads(item['embedding'])
        result.append(item)
    return result

def delete_student(student_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance_records WHERE student_id = ?", (student_id,))
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# Session operations
def get_or_create_today_session(course_name: str = "Class Session", teacher_name: str = "Prof. Proctor") -> Dict[str, Any]:
    today_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_date = ? ORDER BY id DESC LIMIT 1", (today_str,))
    row = cursor.fetchone()
    
    if not row:
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO sessions (session_date, course_name, teacher_name, is_locked, created_at)
            VALUES (?, ?, ?, 0, ?)
        """, (today_str, course_name, teacher_name, now))
        session_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        
    conn.close()
    return dict(row)

def lock_session(session_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET is_locked = 1 WHERE id = ?", (session_id,))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def unlock_session(session_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET is_locked = 0 WHERE id = ?", (session_id,))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

# Attendance records
def mark_attendance(session_id: int, student_id: int, status: str = "Present", confidence: float = 1.0, verification_mode: str = "face", note: str = "") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    # Upsert attendance record
    cursor.execute("""
        INSERT INTO attendance_records (session_id, student_id, status, confidence, verification_mode, timestamp, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id, student_id) DO UPDATE SET
            status = excluded.status,
            confidence = excluded.confidence,
            verification_mode = excluded.verification_mode,
            timestamp = excluded.timestamp,
            note = excluded.note
    """, (session_id, student_id, status, confidence, verification_mode, now, note))
    
    conn.commit()
    conn.close()
    return {"session_id": session_id, "student_id": student_id, "status": status, "confidence": confidence, "timestamp": now}

def get_session_attendance(session_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Join students and attendance_records for this session
    cursor.execute("""
        SELECT 
            s.id AS student_id,
            s.name,
            s.roll_number,
            s.class_name,
            s.department,
            s.avatar_base64,
            COALESCE(ar.status, 'Absent') AS status,
            COALESCE(ar.confidence, 0.0) AS confidence,
            COALESCE(ar.verification_mode, 'unmarked') AS verification_mode,
            COALESCE(ar.timestamp, '') AS timestamp,
            COALESCE(ar.note, '') AS note
        FROM students s
        LEFT JOIN attendance_records ar 
            ON s.id = ar.student_id AND ar.session_id = ?
    """, (session_id,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
