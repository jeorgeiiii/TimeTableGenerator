# backend_api.py - Complete Working Version with Saved Timetables
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict
import sqlite3
import hashlib
from datetime import datetime, timedelta
import jwt
import uvicorn
import random
import json

app = FastAPI(title="SGSITS Timetable API")

# ============ CORS ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
SECRET_KEY = "your-secret-key-2024"
ALGORITHM = "HS256"

# Database setup
DB_PATH = "sgsits_timetable.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS teachers")
    cursor.execute("DROP TABLE IF EXISTS subjects")
    cursor.execute("DROP TABLE IF EXISTS timetable")
    cursor.execute("DROP TABLE IF EXISTS rooms")
    cursor.execute("DROP TABLE IF EXISTS saved_timetables")
    cursor.execute("DROP TABLE IF EXISTS student_groups")
    cursor.execute("DROP TABLE IF EXISTS course_assignments")
    cursor.execute("DROP TABLE IF EXISTS time_slots")
    cursor.execute("DROP TABLE IF EXISTS courses")
    cursor.execute("DROP TABLE IF EXISTS timetable_entries")
    
    # Users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Teachers table
    cursor.execute('''
        CREATE TABLE teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Rooms table
    cursor.execute('''
        CREATE TABLE rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT UNIQUE,
            room_name TEXT,
            capacity INTEGER,
            room_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Courses table
    cursor.execute('''
        CREATE TABLE courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT UNIQUE,
            course_name TEXT,
            credits INTEGER,
            hours_per_week INTEGER,
            department TEXT,
            semester INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Student groups table
    cursor.execute('''
        CREATE TABLE student_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_code TEXT UNIQUE,
            group_name TEXT,
            semester INTEGER,
            department TEXT,
            student_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Course assignments table
    cursor.execute('''
        CREATE TABLE course_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            teacher_id INTEGER,
            group_id INTEGER,
            semester INTEGER,
            hours_per_week INTEGER,
            FOREIGN KEY (course_id) REFERENCES courses(id),
            FOREIGN KEY (teacher_id) REFERENCES teachers(id),
            FOREIGN KEY (group_id) REFERENCES student_groups(id)
        )
    ''')
    
    # Time slots table
    cursor.execute('''
        CREATE TABLE time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_code TEXT,
            day_of_week INTEGER,
            day_name TEXT,
            start_time TEXT,
            end_time TEXT,
            is_break BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Timetable entries table
    cursor.execute('''
        CREATE TABLE timetable_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            group_id INTEGER,
            room_id INTEGER,
            slot_id INTEGER,
            course_id INTEGER,
            semester INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id),
            FOREIGN KEY (group_id) REFERENCES student_groups(id),
            FOREIGN KEY (room_id) REFERENCES rooms(id),
            FOREIGN KEY (slot_id) REFERENCES time_slots(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')
    
    # Saved timetables table (for sharing)
    cursor.execute('''
        CREATE TABLE saved_timetables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT,
            year INTEGER,
            section TEXT,
            timetable_data TEXT,
            generated_by INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (generated_by) REFERENCES users(id)
        )
    ''')
    
    print("✅ Tables created")
    
    # Insert default admin
    admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute("INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role) VALUES (?,?,?,?,?)",
                   ("admin", "admin@sgsits.edu", admin_pw, "Administrator", "admin"))
    
    # Insert sample teachers
    teachers = [
        ("Prof. Rahul Sharma", "rahul@sgsits.edu", "CSE"),
        ("Prof. Neha Verma", "neha@sgsits.edu", "CSE"),
        ("Prof. Amit Tiwari", "amit@sgsits.edu", "EE"),
        ("Prof. Priya Patel", "priya@sgsits.edu", "ME"),
        ("Prof. Sanjay Gupta", "sanjay@sgsits.edu", "CSE"),
        ("Prof. Vikram Singh", "vikram@sgsits.edu", "ECE"),
        ("Prof. Anjali Mehta", "anjali@sgsits.edu", "CE"),
        ("Prof. Rajesh Kumar", "rajesh@sgsits.edu", "IT"),
    ]
    for t in teachers:
        cursor.execute("INSERT OR IGNORE INTO teachers (name, email, department) VALUES (?,?,?)", t)
    
    # Insert sample rooms
    rooms = [
        ("R101", "Room 101", 60, "lecture"),
        ("R102", "Room 102", 50, "lecture"),
        ("R103", "Room 103", 50, "lecture"),
        ("R104", "Room 104", 55, "lecture"),
        ("R201", "Room 201", 80, "lecture"),
        ("R202", "Room 202", 70, "lecture"),
        ("R203", "Room 203", 65, "lecture"),
        ("LAB1", "Computer Lab 1", 40, "lab"),
        ("LAB2", "Computer Lab 2", 40, "lab"),
        ("LAB3", "Electronics Lab", 35, "lab"),
        ("LAB4", "Physics Lab", 40, "lab"),
        ("LAB5", "Chemistry Lab", 40, "lab"),
    ]
    for code, name, cap, rtype in rooms:
        cursor.execute("INSERT OR IGNORE INTO rooms (room_code, room_name, capacity, room_type) VALUES (?,?,?,?)",
                      (code, name, cap, rtype))
    
    # Insert sample courses
    courses = [
        ("CS301", "Data Structures", 4, 4, "CSE", 3),
        ("CS302", "Algorithms", 4, 4, "CSE", 3),
        ("EE201", "Circuit Theory", 3, 3, "EE", 2),
        ("ME101", "Engineering Mechanics", 3, 3, "ME", 1),
        ("CS101", "Programming in C", 3, 3, "CSE", 1),
    ]
    for code, name, credits, hours, dept, sem in courses:
        cursor.execute("INSERT OR IGNORE INTO courses (course_code, course_name, credits, hours_per_week, department, semester) VALUES (?,?,?,?,?,?)",
                      (code, name, credits, hours, dept, sem))
    
    # Insert sample student groups
    groups = [
        ("SEA", "SE Computer A", 3, "CSE", 60),
        ("SEB", "SE Computer B", 3, "CSE", 58),
        ("TEA", "TE Computer A", 5, "CSE", 55),
    ]
    for code, name, sem, dept, count in groups:
        cursor.execute("INSERT OR IGNORE INTO student_groups (group_code, group_name, semester, department, student_count) VALUES (?,?,?,?,?)",
                      (code, name, sem, dept, count))
    
    # Insert sample time slots
    days = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday")]
    times = [
        ("S1", "09:00", "10:00"), ("S2", "10:00", "11:00"), ("S3", "11:00", "12:00"),
        ("LUNCH", "12:00", "13:00"), ("S4", "14:00", "15:00"), ("S5", "15:00", "16:00"), ("S6", "16:00", "17:00")
    ]
    
    slot_id = 1
    for day_idx, day_name in days:
        for code, start, end in times:
            is_break = 1 if code == "LUNCH" else 0
            cursor.execute("INSERT OR IGNORE INTO time_slots (id, slot_code, day_of_week, day_name, start_time, end_time, is_break) VALUES (?,?,?,?,?,?,?)",
                          (slot_id, f"{day_name[:3]}{code}", day_idx, day_name, start, end, is_break))
            slot_id += 1
    
    # Insert sample course assignments
    # Get teacher IDs
    cursor.execute("SELECT id FROM teachers")
    teacher_ids = [row['id'] for row in cursor.fetchall()]
    
    # Get course IDs
    cursor.execute("SELECT id FROM courses")
    course_ids = [row['id'] for row in cursor.fetchall()]
    
    # Get group IDs
    cursor.execute("SELECT id FROM student_groups")
    group_ids = [row['id'] for row in cursor.fetchall()]
    
    if teacher_ids and course_ids and group_ids:
        assignments = [
            (course_ids[0], teacher_ids[0], group_ids[0], 3, 4),
            (course_ids[0], teacher_ids[0], group_ids[1], 3, 4),
            (course_ids[1], teacher_ids[1], group_ids[0], 3, 4),
            (course_ids[1], teacher_ids[1], group_ids[1], 3, 4),
        ]
        for course_id, teacher_id, group_id, sem, hours in assignments:
            cursor.execute("INSERT OR IGNORE INTO course_assignments (course_id, teacher_id, group_id, semester, hours_per_week) VALUES (?,?,?,?,?)",
                          (course_id, teacher_id, group_id, sem, hours))
    
    # Insert sample student users
    student_pw = hashlib.sha256("student123".encode()).hexdigest()
    students = [
        ("student1", "student1@sgsits.edu", student_pw, "John Student", "student"),
        ("student2", "student2@sgsits.edu", student_pw, "Jane Student", "student"),
        ("student", "student@sgsits.edu", student_pw, "Demo Student", "student"),
    ]
    for s in students:
        cursor.execute("INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role) VALUES (?,?,?,?,?)", s)
    
    # Insert sample teacher users
    teacher_pw = hashlib.sha256("teacher123".encode()).hexdigest()
    teacher_users = [
        ("teacher1", "teacher1@sgsits.edu", teacher_pw, "Prof. Rahul Sharma", "teacher"),
        ("teacher2", "teacher2@sgsits.edu", teacher_pw, "Prof. Neha Verma", "teacher"),
        ("teacher", "teacher@sgsits.edu", teacher_pw, "Demo Teacher", "teacher"),
    ]
    for t in teacher_users:
        cursor.execute("INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role) VALUES (?,?,?,?,?)", t)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with sample data")

init_db()

# ============ AUTH FUNCTIONS ============
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ============ AUTH ENDPOINTS ============
class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "student"

class TeacherData(BaseModel):
    name: str
    email: str
    department: str

class SubjectData(BaseModel):
    code: str
    name: str
    branch: str
    year: int
    teacher_id: int
    teacher2_id: Optional[int] = None

class TimetableGenerateRequest(BaseModel):
    branch: str
    year: int
    section: str

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    print(f"Login attempt for username: {request.username}")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (request.username, request.username))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user['password_hash'] != hash_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user['id'], user['username'], user['role'])
    print(f"Login successful for: {request.username}, role: {user['role']}")
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "full_name": user['full_name'],
            "role": user['role']
        }
    }

@app.post("/api/auth/signup")
async def signup(request: SignupRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (request.username, request.email))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="User already exists")
    
    cursor.execute(
        "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?,?,?,?,?)",
        (request.username, request.email, hash_password(request.password), request.full_name, request.role)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    token = create_token(user_id, request.username, request.role)
    return {"success": True, "token": token, "user": {"id": user_id, "username": request.username, "role": request.role}}

# ============ TEACHER ENDPOINTS ============
@app.post("/api/admin/teachers")
async def add_teacher(teacher: TeacherData, _=Depends(require_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO teachers (name, email, department) VALUES (?,?,?)",
                   (teacher.name, teacher.email, teacher.department))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Teacher {teacher.name} added"}

@app.get("/api/teachers")
async def get_teachers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teachers")
    teachers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"teachers": teachers}

# ============ SUBJECT ENDPOINTS ============
@app.post("/api/admin/subjects")
async def add_subject(subject: SubjectData, _=Depends(require_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subjects (code, name, branch, year, teacher_id, teacher2_id) VALUES (?,?,?,?,?,?)",
        (subject.code, subject.name, subject.branch, subject.year, subject.teacher_id, subject.teacher2_id)
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Subject {subject.name} added"}

@app.get("/api/subjects/{branch}/{year}")
async def get_subjects(branch: str, year: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, t1.name as teacher1_name, t2.name as teacher2_name 
        FROM subjects s
        LEFT JOIN teachers t1 ON s.teacher_id = t1.id
        LEFT JOIN teachers t2 ON s.teacher2_id = t2.id
        WHERE s.branch = ? AND s.year = ?
    ''', (branch, year))
    subjects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"subjects": subjects}

# ============ TIMETABLE GENERATION WITH SAVING ============
@app.post("/api/timetable/generate")
async def generate_timetable(request: TimetableGenerateRequest, current_user=Depends(require_admin)):
    """Generate timetable using the existing database schema and save for sharing"""

    conn = get_db()
    cursor = conn.cursor()

    # Map year to the correct abbreviation
    year_abbrev = {1: "FY", 2: "SY", 3: "TY", 4: "BTech"}
    year_display = year_abbrev.get(request.year, f"Year {request.year}")
    
    group_code = f"{request.branch}{request.year}{request.section}"
    
    # Get or create the student group
    cursor.execute("SELECT id FROM student_groups WHERE group_code = ?", (group_code,))
    group_row = cursor.fetchone()

    if not group_row:
        cursor.execute(""" 
            INSERT INTO student_groups (group_code, group_name, semester, department, student_count) 
            VALUES (?, ?, ?, ?, ?)
        """, (group_code, f"{request.branch} {year_display} Section {request.section}", 
              request.year, request.branch, 60))
        group_id = cursor.lastrowid
    else:
        group_id = group_row['id']

    # Clear existing timetable entries for this group
    cursor.execute("DELETE FROM timetable_entries WHERE group_id = ?", (group_id,))

    # Get course assignments for this group
    cursor.execute("""
        SELECT ca.*, c.course_code, c.course_name, t.name as teacher_name, t.id as teacher_id
        FROM course_assignments ca
        JOIN courses c ON ca.course_id = c.id
        JOIN teachers t ON ca.teacher_id = t.id
        WHERE ca.group_id = ? AND ca.semester = ?
    """, (group_id, request.year))

    assignments = cursor.fetchall()

    if not assignments:
        conn.close()
        return {"success": False, "message": "No course assignments found for this group. Please assign courses first."}

    # Get available time slots (excluding breaks)
    cursor.execute("SELECT id, day_name, start_time, end_time FROM time_slots WHERE is_break = 0 ORDER BY day_of_week, start_time")
    time_slots = cursor.fetchall()

    # Track teacher schedules to prevent conflicts
    teacher_schedule = {}
    room_schedule = {}
    assigned_count = 0
    timetable_entries_list = []

    # Get available rooms
    cursor.execute("SELECT id FROM rooms ORDER BY capacity DESC")
    available_rooms = [row['id'] for row in cursor.fetchall()]

    # Assign each course to time slots
    for assignment in assignments:
        teacher_id = assignment['teacher_id']
        course_id = assignment['course_id']
        hours_needed = assignment['hours_per_week']

        if teacher_id not in teacher_schedule:
            teacher_schedule[teacher_id] = set()

        slots_assigned = 0
        for slot in time_slots:
            if slots_assigned >= hours_needed:
                break

            slot_id = slot['id']

            if slot_id in teacher_schedule[teacher_id]:
                continue

            room_id = None
            for r_id in available_rooms:
                if r_id not in room_schedule:
                    room_schedule[r_id] = set()
                if slot_id not in room_schedule[r_id]:
                    room_id = r_id
                    break

            if room_id:
                cursor.execute("""
                    INSERT INTO timetable_entries (teacher_id, group_id, room_id, slot_id, course_id, semester)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (teacher_id, group_id, room_id, slot_id, course_id, request.year))

                teacher_schedule[teacher_id].add(slot_id)
                room_schedule[room_id].add(slot_id)
                
                timetable_entries_list.append({
                    'day': slot['day_name'],
                    'time_slot': f"{slot['start_time']}-{slot['end_time']}",
                    'subject_code': assignment['course_code'],
                    'subject_name': assignment['course_name'],
                    'teacher_name': assignment['teacher_name']
                })
                
                assigned_count += 1
                slots_assigned += 1

    # Save timetable data to saved_timetables table for sharing
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    time_slots_list = ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00',
                       '14:00-15:00', '15:00-16:00', '16:00-17:00']
    
    timetable_data = json.dumps({
        'branch': request.branch,
        'year': request.year,
        'section': request.section,
        'entries': timetable_entries_list,
        'days': days,
        'time_slots': time_slots_list,
        'generated_at': datetime.now().isoformat()
    })
    
    cursor.execute('''
        INSERT OR REPLACE INTO saved_timetables (branch, year, section, timetable_data, generated_by, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (request.branch, request.year, request.section, timetable_data, current_user.get('user_id', 1)))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Timetable generated and saved for {request.branch} Year {request.year} Section {request.section}",
        "assignments": assigned_count
    }

@app.get("/api/timetable/view/{branch}/{year}/{section}")
async def view_timetable(branch: str, year: int, section: str, current_user=Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    # First check if there's a saved timetable
    cursor.execute('''
        SELECT timetable_data, generated_at 
        FROM saved_timetables 
        WHERE branch = ? AND year = ? AND section = ? AND is_active = 1
        ORDER BY generated_at DESC LIMIT 1
    ''', (branch, year, section))
    
    saved = cursor.fetchone()
    
    if saved:
        # Return saved timetable
        data = json.loads(saved['timetable_data'])
        days = data.get('days', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
        time_slots = data.get('time_slots', ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', 
                                              '14:00-15:00', '15:00-16:00', '16:00-17:00'])
        
        # Build matrix from saved entries
        matrix = {day: {slot: '—' for slot in time_slots} for day in days}
        
        for entry in data.get('entries', []):
            day = entry.get('day')
            slot = entry.get('time_slot')
            if day and slot and day in matrix and slot in matrix[day]:
                matrix[day][slot] = f"{entry.get('subject_code', '')}<br>({entry.get('teacher_name', '')})"
        
        # Add lunch break
        for day in days:
            if '12:00-13:00' in matrix[day]:
                matrix[day]['12:00-13:00'] = '🍽️ LUNCH BREAK'
        
        return {
            "branch": branch,
            "year": year,
            "section": section,
            "days": days,
            "time_slots": time_slots,
            "entries": data.get('entries', []),
            "timetable": matrix
        }
    
    # Fallback to querying timetable_entries table directly
    year_abbrev = {1: "FY", 2: "SY", 3: "TY", 4: "BTech"}
    group_code = f"{branch}{year}{section}"
    
    cursor.execute("SELECT id FROM student_groups WHERE group_code = ?", (group_code,))
    group_row = cursor.fetchone()

    if not group_row:
        conn.close()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        time_slots = ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', 
                      '14:00-15:00', '15:00-16:00', '16:00-17:00']
        matrix = {day: {slot: '—' for slot in time_slots} for day in days}
        for day in days:
            matrix[day]['12:00-13:00'] = '🍽️ LUNCH BREAK'
        return {
            "branch": branch,
            "year": year,
            "section": section,
            "days": days,
            "time_slots": time_slots,
            "entries": [],
            "timetable": matrix
        }

    group_id = group_row['id']

    cursor.execute('''
        SELECT te.*, ts.day_name, ts.start_time, ts.end_time, ts.is_break,
               c.course_code, c.course_name, t.name as teacher_name, r.room_code
        FROM timetable_entries te
        JOIN time_slots ts ON te.slot_id = ts.id
        JOIN courses c ON te.course_id = c.id
        JOIN teachers t ON te.teacher_id = t.id
        JOIN rooms r ON te.room_id = r.id
        WHERE te.group_id = ?
        ORDER BY ts.day_of_week, ts.start_time
    ''', (group_id,))

    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    time_slots = ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00',
                  '14:00-15:00', '15:00-16:00', '16:00-17:00']

    matrix = {day: {slot: '—' for slot in time_slots} for day in days}

    for entry in entries:
        day = entry['day_name']
        time_slot = f"{entry['start_time']}-{entry['end_time']}"
        if time_slot in matrix[day]:
            if entry['is_break']:
                matrix[day][time_slot] = '🍽️ LUNCH BREAK'
            else:
                matrix[day][time_slot] = f"{entry['course_code']}<br>({entry['teacher_name']})"

    return {
        "branch": branch,
        "year": year,
        "section": section,
        "days": days,
        "time_slots": time_slots,
        "entries": entries,
        "timetable": matrix
    }

# ============ ROOMS ENDPOINTS ============
@app.get("/api/rooms")
async def get_rooms():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, room_code, room_name, capacity, room_type FROM rooms")
    rooms = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"rooms": rooms}

# ============ BRANCHES ============
@app.get("/api/branches")
async def get_branches():
    return {"branches": [
        {"code": "CSE", "name": "Computer Science & Engineering"},
        {"code": "EE", "name": "Electrical Engineering"},
        {"code": "ME", "name": "Mechanical Engineering"},
        {"code": "ECE", "name": "Electronics & Communication"},
        {"code": "CE", "name": "Civil Engineering"},
        {"code": "IT", "name": "Information Technology"}
    ]}

# ============ TIMETABLE HISTORY ============
@app.get("/api/timetable/history")
async def get_timetable_history(current_user=Depends(require_admin)):
    """Get all saved timetables (admin only)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, branch, year, section, generated_at, is_active
        FROM saved_timetables
        ORDER BY generated_at DESC
    ''')
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"history": history}

@app.get("/")
async def root():
    return {"message": "SGSITS Timetable API is running", "status": "healthy"}

if __name__ == "__main__":
    print("="*50)
    print("🚀 SGSITS Timetable API Server")
    print("="*50)
    print("📍 API: http://localhost:8000")
    print("📍 Docs: http://localhost:8000/docs")
    print("="*50)
    print("🔐 Login Credentials:")
    print("   Admin:    admin / admin123")
    print("   Teacher:  teacher1 / teacher123")
    print("   Student:  student1 / student123")
    print("="*50)
    print("✅ Features:")
    print("   - Monday-Friday timetable (5 days)")
    print("   - Teacher conflict prevention")
    print("   - Timetable saved and shared across all roles")
    print("   - Teachers and students can view generated timetables")
    print("   - Lunch break at 12:00-13:00")
    print("="*50)
    uvicorn.run(app, host="0.0.0.0", port=8000)