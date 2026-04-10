# reset_db.py - Updated to use correct database name
import sqlite3
import os
import hashlib

# CHANGE THIS LINE - use the same database name as backend_api.py
DB_PATH = "sgsits_timetable.db"  # Changed from "timetable.db"

# Delete old database
if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
        print(f"✅ Old database deleted: {DB_PATH}")
    except PermissionError:
        print("❌ Database is locked. Please stop the backend server first (Ctrl+C)")
        exit(1)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Create new database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ============ CREATE ALL TABLES ============

# Users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT CHECK(role IN ('admin', 'teacher', 'student')) DEFAULT 'student',
        is_active BOOLEAN DEFAULT 1,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Teachers table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        teacher_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        department TEXT NOT NULL,
        designation TEXT,
        specialization TEXT,
        max_hours_per_day INTEGER DEFAULT 6,
        max_hours_per_week INTEGER DEFAULT 24,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
''')

# Student groups
cursor.execute('''
    CREATE TABLE IF NOT EXISTS student_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_code TEXT UNIQUE NOT NULL,
        group_name TEXT NOT NULL,
        semester INTEGER NOT NULL,
        department TEXT NOT NULL,
        academic_year TEXT,
        student_count INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Courses
cursor.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_code TEXT UNIQUE NOT NULL,
        course_name TEXT NOT NULL,
        description TEXT,
        credits INTEGER DEFAULT 3,
        hours_per_week INTEGER DEFAULT 3,
        is_lab BOOLEAN DEFAULT 0,
        department TEXT,
        semester INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Course assignments
cursor.execute('''
    CREATE TABLE IF NOT EXISTS course_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        semester INTEGER NOT NULL,
        academic_year TEXT NOT NULL,
        hours_per_week INTEGER,
        is_lab BOOLEAN DEFAULT 0,
        preferred_room TEXT,
        priority INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
        FOREIGN KEY (group_id) REFERENCES student_groups(id) ON DELETE CASCADE
    )
''')

# Rooms
cursor.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT UNIQUE NOT NULL,
        room_name TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        room_type TEXT DEFAULT 'lecture',
        building TEXT,
        has_projector BOOLEAN DEFAULT 0,
        has_ac BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Time slots
cursor.execute('''
    CREATE TABLE IF NOT EXISTS time_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_code TEXT UNIQUE NOT NULL,
        slot_name TEXT NOT NULL,
        day_of_week INTEGER NOT NULL,
        day_name TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        is_break BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Timetable entries
cursor.execute('''
    CREATE TABLE IF NOT EXISTS timetable_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_assignment_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        room_id INTEGER NOT NULL,
        slot_id INTEGER NOT NULL,
        semester INTEGER NOT NULL,
        academic_year TEXT NOT NULL,
        status TEXT DEFAULT 'scheduled',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_assignment_id) REFERENCES course_assignments(id) ON DELETE CASCADE,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
        FOREIGN KEY (group_id) REFERENCES student_groups(id) ON DELETE CASCADE,
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY (slot_id) REFERENCES time_slots(id) ON DELETE CASCADE,
        UNIQUE(teacher_id, slot_id, academic_year),
        UNIQUE(room_id, slot_id, academic_year),
        UNIQUE(group_id, slot_id, academic_year)
    )
''')

# Saved timetables table (for sharing)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS saved_timetables (
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

# ============ INSERT SAMPLE DATA ============

# 1. Users (with hashed passwords)
users = [
    ('admin', 'admin@timetable.com', hash_password('admin123'), 'System Administrator', 'admin'),
    ('student1', 'student1@timetable.com', hash_password('student123'), 'John Doe', 'student'),
    ('student2', 'student2@timetable.com', hash_password('student123'), 'Jane Smith', 'student'),
    ('teacher1', 'teacher1@timetable.com', hash_password('teacher123'), 'Prof. Abhijeet', 'teacher'),
    ('teacher2', 'teacher2@timetable.com', hash_password('teacher123'), 'Prof. Subhit', 'teacher'),
]

for username, email, pwd_hash, name, role in users:
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (username, email, pwd_hash, name, role))

# 2. Teachers
teachers = [
    ('T001', 'Prof. Abhijeet', 'teacher1@timetable.com', 'CSE', 'Professor', 'Electrical', 6, 24),
    ('T002', 'Prof. Subhit', 'teacher2@timetable.com', 'Mathematics', 'Professor', 'Applied Math', 6, 24),
    ('T003', 'Prof. Sharma', 'teacher3@timetable.com', 'Physics', 'Professor', 'Quantum', 5, 20),
]

for code, name, email, dept, desig, spec, max_day, max_week in teachers:
    cursor.execute('''
        INSERT OR IGNORE INTO teachers (teacher_code, name, email, department, designation, specialization, max_hours_per_day, max_hours_per_week)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (code, name, email, dept, desig, spec, max_day, max_week))

# 3. Student groups
groups = [
    ('SEA', 'SE Computer A', 3, 'CSE', '2024-2025', 60),
    ('SEB', 'SE Computer B', 3, 'CSE', '2024-2025', 58),
    ('TEA', 'TE Computer A', 5, 'CSE', '2024-2025', 55),
]

for code, name, sem, dept, year, count in groups:
    cursor.execute('''
        INSERT OR IGNORE INTO student_groups (group_code, group_name, semester, department, academic_year, student_count)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (code, name, sem, dept, year, count))

# 4. Courses
courses = [
    ('BEE101', 'Basic Electrical Engineering', 'Electrical circuits basics', 3, 3, 0, 'CSE', 3),
    ('MATH201', 'Mathematics 2', 'Calculus and Algebra', 4, 4, 0, 'Mathematics', 3),
    ('CS201', 'Data Structures', 'Data structures and algorithms', 4, 4, 0, 'CSE', 5),
    ('CS201L', 'Data Structures Lab', 'Programming lab', 1, 2, 1, 'CSE', 5),
]

for code, name, desc, credits, hours, lab, dept, sem in courses:
    cursor.execute('''
        INSERT OR IGNORE INTO courses (course_code, course_name, description, credits, hours_per_week, is_lab, department, semester)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (code, name, desc, credits, hours, lab, dept, sem))

# 5. Course assignments
assignments = [
    (1, 1, 1, 3, '2024-2025', 3, 0, None, 1),
    (1, 1, 2, 3, '2024-2025', 3, 0, None, 1),
    (2, 2, 1, 3, '2024-2025', 4, 0, None, 2),
    (2, 2, 2, 3, '2024-2025', 4, 0, None, 2),
    (3, 1, 3, 5, '2024-2025', 4, 0, None, 2),
    (4, 1, 3, 5, '2024-2025', 2, 1, None, 3),
]

for course_id, teacher_id, group_id, sem, year, hours, lab, room, priority in assignments:
    cursor.execute('''
        INSERT OR IGNORE INTO course_assignments 
        (course_id, teacher_id, group_id, semester, academic_year, hours_per_week, is_lab, preferred_room, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (course_id, teacher_id, group_id, sem, year, hours, lab, room, priority))

# 6. Rooms
rooms = [
    ('R101', 'Room 101', 60, 'lecture', 'Main', 1, 1),
    ('R102', 'Room 102', 50, 'lecture', 'Main', 0, 0),
    ('R201', 'Room 201', 80, 'lecture', 'Main', 1, 1),
    ('LAB1', 'Computer Lab 1', 40, 'lab', 'Lab Block', 1, 1),
]

for code, name, cap, rtype, building, proj, ac in rooms:
    cursor.execute('''
        INSERT OR IGNORE INTO rooms (room_code, room_name, capacity, room_type, building, has_projector, has_ac)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (code, name, cap, rtype, building, proj, ac))

# 7. Time slots (Monday to Friday)
days = [(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday')]
times = [
    ('S1', '09:00', '10:00'), ('S2', '10:00', '11:00'), ('S3', '11:00', '12:00'),
    ('S4', '12:00', '13:00'), ('S5', '14:00', '15:00'), ('S6', '15:00', '16:00'),
    ('S7', '16:00', '17:00'),
]

slot_id = 1
for day_idx, day_name in days:
    for code, start, end in times:
        is_break = 1 if code == "S4" else 0  # Lunch break at 12:00-13:00
        cursor.execute('''
            INSERT OR IGNORE INTO time_slots (id, slot_code, slot_name, day_of_week, day_name, start_time, end_time, is_break)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (slot_id, f"{day_name[:3]}{code}", f"{day_name[:3]} {start}-{end}", day_idx, day_name, start, end, is_break))
        slot_id += 1

conn.commit()
conn.close()

print("=" * 50)
print("✅ Database reset successfully!")
print("=" * 50)
print("\n📋 Default Users Created:")
print("   Admin:     username='admin', password='admin123'")
print("   Student:   username='student1', password='student123'")
print("   Student:   username='student2', password='student123'")
print("   Teacher:   username='teacher1', password='teacher123'")
print("   Teacher:   username='teacher2', password='teacher123'")
print("\n📊 Tables created:")
print("   - users, teachers, student_groups")
print("   - courses, course_assignments")
print("   - rooms, time_slots, timetable_entries")
print("   - saved_timetables")
print("=" * 50)