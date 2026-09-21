# backend_api.py - Complete SGSITS Timetable API v4.0
# Matches all frontend API calls exactly

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict
from contextlib import asynccontextmanager
import sqlite3
import hashlib
from datetime import datetime, timedelta
import jwt
import uvicorn
import json
import random
from curriculum_data import build_subject_rows
from teachers_data import build_teacher_rows
from test_teachers_data import build_test_teacher_rows

# ============================================================
# CONFIG
# ============================================================
DB_PATH = "sgsits_timetable.db"
SECRET_KEY = "your-secret-key-change-this-to-32-chars!!"
ALGORITHM = "HS256"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIME_SLOTS = [
    "10:00-11:00", "11:00-12:00", "12:00-13:00",
    "13:00-14:00",
    "15:00-16:00", "16:00-17:00", "17:00-18:00"
]
LUNCH_SLOT = "13:00-14:00"

# Fixed lab scheduling policy (also used by the capacity warning in assign_subject):
# every lab course gets 3 sessions/week, each a single 1-hour slot, so a lab
# subject never appears twice back-to-back on the same day. (Set
# LAB_SESSION_SLOTS = 2 to go back to 2-hour lab blocks.)
LAB_SESSIONS_PER_WEEK = 3
LAB_SESSION_SLOTS = 1

# No theory subject is scheduled more than this many periods/week, even if its
# hours_per_week says more - a scheduling policy, like the lab one above, not
# a per-subject configurable value.
MAX_THEORY_SESSIONS_PER_WEEK = 3

# Recommended cap on a group's TOTAL weekly lab sessions across all its lab
# courses combined (checked as a warning in assign_subject). Only one lab is
# scheduled per day (generate_timetable), and each lab course needs
# LAB_SESSIONS_PER_WEEK (3) distinct days - so 2 lab courses already need 6
# lab-days out of a 5-day week. Keeping the total to 3-4 sessions/week (i.e.
# effectively one lab course per group) is what actually fits.
MAX_RECOMMENDED_LAB_SESSIONS_PER_WEEK = 4

# ============================================================
# MIGRATIONS
# Runs on every startup. Adds any missing columns automatically.
# Rule: whenever you add a column to CREATE TABLE, also add it here.
# ============================================================
MIGRATIONS = [
    # (table, column, sql_definition)
    ("subjects",           "credits",            "INTEGER DEFAULT 3"),
    ("subjects",           "hours_per_week",      "INTEGER DEFAULT 3"),
    ("subjects",           "is_lab",              "BOOLEAN DEFAULT 0"),
    ("subjects",           "teacher_id",          "INTEGER"),
    ("subjects",           "teacher2_id",         "INTEGER"),
    ("subjects",           "semester",            "INTEGER DEFAULT 1"),
    ("subjects",           "branch",              "TEXT"),
    ("subjects",           "year",                "INTEGER DEFAULT 1"),
    ("subjects",           "is_elective",         "BOOLEAN DEFAULT 0"),

    ("teachers",           "designation",         "TEXT"),
    ("teachers",           "specialization",      "TEXT"),
    ("teachers",           "max_hours_per_day",   "INTEGER DEFAULT 6"),
    ("teachers",           "max_hours_per_week",  "INTEGER DEFAULT 24"),
    ("teachers",           "is_active",           "BOOLEAN DEFAULT 1"),

    ("rooms",              "building",            "TEXT"),
    ("rooms",              "floor",               "INTEGER"),
    ("rooms",              "has_projector",       "BOOLEAN DEFAULT 0"),
    ("rooms",              "has_whiteboard",      "BOOLEAN DEFAULT 1"),
    ("rooms",              "has_ac",              "BOOLEAN DEFAULT 0"),
    ("rooms",              "has_computers",       "BOOLEAN DEFAULT 0"),
    ("rooms",              "is_lab",              "BOOLEAN DEFAULT 0"),
    ("rooms",              "room_type",           "TEXT DEFAULT 'lecture'"),
    ("rooms",              "is_active",           "BOOLEAN DEFAULT 1"),

    ("courses",            "description",         "TEXT"),
    ("courses",            "theory_hours",        "INTEGER DEFAULT 2"),
    ("courses",            "lab_hours",           "INTEGER DEFAULT 1"),
    ("courses",            "is_lab",              "BOOLEAN DEFAULT 0"),
    ("courses",            "is_elective",         "BOOLEAN DEFAULT 0"),
    ("courses",            "department",          "TEXT"),
    ("courses",            "semester",            "INTEGER"),

    ("course_assignments", "theory_hours",        "INTEGER DEFAULT 2"),
    ("course_assignments", "lab_hours",           "INTEGER DEFAULT 1"),
    ("course_assignments", "is_lab",              "BOOLEAN DEFAULT 0"),
    ("course_assignments", "priority",            "INTEGER DEFAULT 1"),
    ("course_assignments", "is_elective",         "BOOLEAN DEFAULT 0"),
    ("course_assignments", "academic_year",       "TEXT DEFAULT '2024-2025'"),
    ("course_assignments", "hours_per_week",      "INTEGER DEFAULT 3"),

    ("student_groups",     "academic_year",       "TEXT"),
    ("student_groups",     "student_count",       "INTEGER DEFAULT 0"),
    ("student_groups",     "is_active",           "BOOLEAN DEFAULT 1"),
    ("student_groups",     "room_id",             "INTEGER"),

    ("timetable_entries",  "academic_year",       "TEXT DEFAULT '2024-2025'"),
    ("timetable_entries",  "status",              "TEXT DEFAULT 'scheduled'"),
    ("timetable_entries",  "week_number",         "INTEGER DEFAULT 1"),
    ("timetable_entries",  "batch",               "TEXT"),

    ("saved_timetables",   "generated_by",        "INTEGER"),
    ("saved_timetables",   "is_active",           "BOOLEAN DEFAULT 1"),

    ("users",              "is_active",           "BOOLEAN DEFAULT 1"),

    ("conflict_log",       "severity",            "TEXT DEFAULT 'warning'"),
    ("conflict_log",       "resolved",            "BOOLEAN DEFAULT 0"),
    ("conflict_log",       "resolved_at",         "TIMESTAMP"),
    ("conflict_log",       "teacher_id",          "INTEGER"),
    ("conflict_log",       "group_id",            "INTEGER"),
    ("conflict_log",       "room_id",             "INTEGER"),
    ("conflict_log",       "slot_id",             "INTEGER"),

    ("holidays",           "is_optional",         "BOOLEAN DEFAULT 0"),
    ("holidays",           "description",         "TEXT"),

    ("time_slots",         "duration",            "INTEGER DEFAULT 60"),
    ("time_slots",         "slot_type",           "TEXT DEFAULT 'lecture'"),
    ("time_slots",         "is_break",            "BOOLEAN DEFAULT 0"),
    ("time_slots",         "is_active",           "BOOLEAN DEFAULT 1"),
]


def run_migrations(conn):
    """Check every table for missing columns and ALTER TABLE to add them."""
    cursor = conn.cursor()
    migrated = 0

    for table, column, definition in MIGRATIONS:
        # Skip if table doesn't exist yet (init_db will create it)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if not cursor.fetchone():
            continue

        # Check existing columns
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {row["name"] for row in cursor.fetchall()}

        if column not in existing:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                print(f"  ✅ Migration: added {table}.{column}")
                migrated += 1
            except Exception as e:
                print(f"  ⚠️  Migration failed {table}.{column}: {e}")

    conn.commit()
    if migrated:
        print(f"✅ Migrations complete: {migrated} column(s) added")
    else:
        print("✅ Schema up to date, no migrations needed")


def sync_rooms(conn):
    """
    Runs on every startup (unlike _insert_sample_data, which only seeds an
    empty database) so the room set below reaches an already-running database
    too, not just a fresh one. INSERT OR IGNORE + the UPDATE are both
    idempotent, so re-running this on every startup is safe.
    """
    cursor = conn.cursor()
    for code, name, cap, rtype, building, floor, proj, board, ac, comp, is_lab in [
        ("ATC 201", "ATC 201", 60, "lecture", "ATC", 2, 1, 1, 1, 0, 0),
        ("ATC 202", "ATC 202", 60, "lecture", "ATC", 2, 1, 1, 1, 0, 0),
        ("ATC 203", "ATC 203", 60, "lecture", "ATC", 2, 1, 1, 1, 0, 0),
        ("ATC 204", "ATC 204", 60, "lecture", "ATC", 2, 1, 1, 1, 0, 0),
        ("ATC 205", "ATC 205", 60, "lecture", "ATC", 2, 1, 1, 1, 0, 0),
        ("ATC 206", "ATC 206", 60, "lecture", "ATC", 2, 1, 1, 1, 0, 0),
        ("ATC 301", "ATC 301", 60, "lecture", "ATC", 3, 1, 1, 1, 0, 0),
        ("ATC 302", "ATC 302", 60, "lecture", "ATC", 3, 1, 1, 1, 0, 0),
        ("ATC 303", "ATC 303", 60, "lecture", "ATC", 3, 1, 1, 1, 0, 0),
        ("ATC 304", "ATC 304", 60, "lecture", "ATC", 3, 1, 1, 1, 0, 0),
        ("ATC 305", "ATC 305", 60, "lecture", "ATC", 3, 1, 1, 1, 0, 0),
        ("ATC 306", "ATC 306", 60, "lecture", "ATC", 3, 1, 1, 1, 0, 0),
        ("ATC 307", "ATC 307", 60, "lecture", "ATC", 3, 1, 1, 1, 0, 0),
        ("LT 001", "LT 001", 80, "lecture", "LT", 0, 1, 1, 1, 0, 0),
        ("LT 002", "LT 002", 80, "lecture", "LT", 0, 1, 1, 1, 0, 0),
        ("LT 101", "LT 101", 80, "lecture", "LT", 1, 1, 1, 1, 0, 0),
        ("LT 102", "LT 102", 80, "lecture", "LT", 1, 1, 1, 1, 0, 0),
        ("LT 201", "LT 201", 80, "lecture", "LT", 2, 1, 1, 1, 0, 0),
        ("LT 202", "LT 202", 80, "lecture", "LT", 2, 1, 1, 1, 0, 0),
        ("LT 301", "LT 301", 80, "lecture", "LT", 3, 1, 1, 1, 0, 0),
        ("LT 302", "LT 302", 80, "lecture", "LT", 3, 1, 1, 1, 0, 0),
        ("LT 401", "LT 401", 80, "lecture", "LT", 4, 1, 1, 1, 0, 0),
        ("LT 402", "LT 402", 80, "lecture", "LT", 4, 1, 1, 1, 0, 0),
        ("LB01", "Lab 01", 40, "lab", "Lab Block", 1, 1, 0, 0, 1, 1),
        ("LB02", "Lab 02", 40, "lab", "Lab Block", 1, 1, 0, 0, 1, 1),
        ("LB03", "Lab 03", 40, "lab", "Lab Block", 1, 1, 0, 0, 1, 1),
    ]:
        cursor.execute(
            "INSERT OR IGNORE INTO rooms (room_code,room_name,capacity,room_type,building,floor,has_projector,has_whiteboard,has_ac,has_computers,is_lab,is_active) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
            (code, name, cap, rtype, building, floor, proj, board, ac, comp, is_lab))

    # Retire the old default room set (superseded by ATC/LT/LB above) without
    # deleting the rows outright, so historical timetable_entries referencing
    # them by room_id don't dangle.
    cursor.execute(
        "UPDATE rooms SET is_active=0 WHERE room_code IN ('R101','R102','R201','LAB1','LAB2','LAB3','AUD1')"
    )
    conn.commit()


def dedupe_course_assignments(conn):
    """
    One-time cleanup for data created before assign_subject was fixed to
    replace (rather than add to) a course's teacher: any (course_id, group_id)
    pair with more than one course_assignments row - which made that subject
    get scheduled several times as many hours as intended, piling up on the
    same day - is collapsed down to just its most recent row. Runs on every
    startup; a no-op once cleaned up.
    """
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM course_assignments
        WHERE id NOT IN (
            SELECT MAX(id) FROM course_assignments GROUP BY course_id, group_id
        )
    ''')
    removed = cursor.rowcount
    conn.commit()
    if removed:
        print(f"✅ Cleaned up {removed} duplicate course_assignment(s) (same subject, multiple teachers)")


def backfill_subject_electives(conn):
    """
    subjects.is_elective was added by a migration (default 0), so any subject
    already loaded from curriculum_data.py before that column existed kept
    the wrong default even though the curriculum data says it's an elective
    (e.g. "Department Elective - I"). Re-checks every code load_curriculum
    would generate against the current curriculum data and corrects any
    mismatch. Runs on every startup; a no-op once caught up.
    """
    rows = build_subject_rows()
    cursor = conn.cursor()
    updated = 0
    for code, _name, _b, _y, _sem, _credits, _hours, _is_lab, is_elective in rows:
        cursor.execute(
            "UPDATE subjects SET is_elective=? WHERE code=? AND is_elective!=?",
            (is_elective, code, is_elective))
        updated += cursor.rowcount
    conn.commit()
    if updated:
        print(f"✅ Backfilled is_elective on {updated} existing subject(s)")


def dedupe_subjects_by_name(conn):
    """
    One-time cleanup for subjects that ended up duplicated under two
    different codes for the same branch/year/semester/name - e.g. an admin
    manually added the real "CO3210 Constitution Of India" while
    load_curriculum's own "EE-S3-06 Constitution of India" placeholder also
    existed (load_curriculum's own dedup only checked by code, so it never
    saw the name collision - now fixed there too, but the two rows this
    already created still need cleaning up). For each duplicate group, keeps
    whichever row already has a teacher assigned (real admin work), or the
    lowest id if none/multiple do, and removes the rest. Runs on every
    startup; a no-op once there's nothing left to clean up.
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT branch, year, semester, lower(trim(name)) AS norm_name
        FROM subjects
        GROUP BY branch, year, semester, norm_name
        HAVING COUNT(*) > 1
    ''')
    groups = cursor.fetchall()
    removed = 0
    for branch, year, semester, norm_name in groups:
        cursor.execute('''
            SELECT id FROM subjects
            WHERE branch=? AND year=? AND semester=? AND lower(trim(name))=?
            ORDER BY (teacher_id IS NULL) ASC, id ASC
        ''', (branch, year, semester, norm_name))
        ids = [r["id"] for r in cursor.fetchall()]
        for loser_id in ids[1:]:
            cursor.execute("DELETE FROM subjects WHERE id=?", (loser_id,))
            removed += 1
    conn.commit()
    if removed:
        print(f"✅ Removed {removed} duplicate subject row(s) (same branch/year/semester/name, different code)")


def sync_class_start_time(conn):
    """
    The teaching day now starts at 10:00 (was 09:00) - shifts every time_slot
    forward by 1 hour IN PLACE (same row id/day_of_week/is_break, just new
    start/end labels), never by deleting and recreating rows, so existing
    timetable_entries (which reference a slot by id) keep pointing at the
    same physical period, just correctly relabeled - and any already-decided
    short day (sync_short_days, matched by row id via is_active) is
    unaffected by the relabeling.
    Processed latest-time-first so each shift's target time slot is never
    itself overwritten by a later step in the same pass. Idempotent: skipped
    once no row is still at the old 09:00 start.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM time_slots WHERE start_time='09:00'")
    if cursor.fetchone()[0] == 0:
        return

    for old_start, old_end, new_start, new_end in [
        ("16:00", "17:00", "17:00", "18:00"),
        ("15:00", "16:00", "16:00", "17:00"),
        ("14:00", "15:00", "15:00", "16:00"),
        ("12:00", "13:00", "13:00", "14:00"),
        ("11:00", "12:00", "12:00", "13:00"),
        ("10:00", "11:00", "11:00", "12:00"),
        ("09:00", "10:00", "10:00", "11:00"),
    ]:
        cursor.execute(
            "UPDATE time_slots SET start_time=?, end_time=? WHERE start_time=? AND end_time=?",
            (new_start, new_end, old_start, old_end))
    conn.commit()
    print("✅ Shifted teaching day to start at 10:00 (was 09:00)")


def sync_short_days(conn):
    """
    Two weekdays run a shortened 4-hour day (starting 2 hours late or ending
    2 hours early, picked randomly per day) instead of the normal 6 hours -
    applies institution-wide since time_slots is shared by every group.
    Decided once: if any non-break slot is already inactive, a choice was
    already made, so this is skipped rather than reshuffling on every
    restart. Regenerate a group's timetable to see the shortened days.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM time_slots WHERE is_break=0 AND is_active=0")
    if cursor.fetchone()[0] > 0:
        return

    cursor.execute("SELECT DISTINCT day_of_week, day_name FROM time_slots WHERE is_break=0 ORDER BY day_of_week")
    days = cursor.fetchall()
    if len(days) < 2:
        return

    for day_of_week, day_name in random.sample(days, 2):
        if random.choice([True, False]):
            cursor.execute(
                "UPDATE time_slots SET is_active=0 WHERE day_of_week=? AND start_time IN ('10:00','11:00')",
                (day_of_week,))
            print(f"✅ {day_name} shortened: starts 2 hours late (12:00)")
        else:
            cursor.execute(
                "UPDATE time_slots SET is_active=0 WHERE day_of_week=? AND start_time IN ('16:00','17:00')",
                (day_of_week,))
            print(f"✅ {day_name} shortened: ends 2 hours early (16:00)")
    conn.commit()


# ============================================================
# DATABASE
# ============================================================
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT CHECK(role IN ("admin","teacher","student")) DEFAULT "student",
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        department TEXT NOT NULL,
        designation TEXT,
        specialization TEXT,
        max_hours_per_day INTEGER DEFAULT 6,
        max_hours_per_week INTEGER DEFAULT 24,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT UNIQUE NOT NULL,
        room_name TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        room_type TEXT DEFAULT "lecture",
        building TEXT,
        floor INTEGER,
        has_projector BOOLEAN DEFAULT 0,
        has_whiteboard BOOLEAN DEFAULT 1,
        has_ac BOOLEAN DEFAULT 0,
        has_computers BOOLEAN DEFAULT 0,
        is_lab BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        branch TEXT NOT NULL,
        year INTEGER NOT NULL,
        semester INTEGER DEFAULT 1,
        credits INTEGER DEFAULT 3,
        hours_per_week INTEGER DEFAULT 3,
        is_lab BOOLEAN DEFAULT 0,
        teacher_id INTEGER,
        teacher2_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id),
        FOREIGN KEY (teacher2_id) REFERENCES teachers(id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_code TEXT UNIQUE NOT NULL,
        course_name TEXT NOT NULL,
        description TEXT,
        credits INTEGER DEFAULT 3,
        hours_per_week INTEGER DEFAULT 3,
        theory_hours INTEGER DEFAULT 2,
        lab_hours INTEGER DEFAULT 1,
        is_lab BOOLEAN DEFAULT 0,
        is_elective BOOLEAN DEFAULT 0,
        department TEXT,
        semester INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS student_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_code TEXT UNIQUE NOT NULL,
        group_name TEXT NOT NULL,
        semester INTEGER NOT NULL,
        department TEXT NOT NULL,
        academic_year TEXT,
        student_count INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS course_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        semester INTEGER NOT NULL,
        academic_year TEXT DEFAULT "2024-2025",
        hours_per_week INTEGER DEFAULT 3,
        theory_hours INTEGER DEFAULT 2,
        lab_hours INTEGER DEFAULT 1,
        is_lab BOOLEAN DEFAULT 0,
        priority INTEGER DEFAULT 1,
        is_elective BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses(id),
        FOREIGN KEY (teacher_id) REFERENCES teachers(id),
        FOREIGN KEY (group_id) REFERENCES student_groups(id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS time_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_code TEXT NOT NULL,
        day_of_week INTEGER NOT NULL,
        day_name TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        duration INTEGER DEFAULT 60,
        slot_type TEXT DEFAULT "lecture",
        is_break BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS timetable_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        room_id INTEGER NOT NULL,
        slot_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        semester INTEGER NOT NULL,
        academic_year TEXT DEFAULT "2024-2025",
        status TEXT DEFAULT "scheduled",
        week_number INTEGER DEFAULT 1,
        batch TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id),
        FOREIGN KEY (group_id) REFERENCES student_groups(id),
        FOREIGN KEY (room_id) REFERENCES rooms(id),
        FOREIGN KEY (slot_id) REFERENCES time_slots(id),
        FOREIGN KEY (course_id) REFERENCES courses(id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS saved_timetables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch TEXT NOT NULL,
        year INTEGER NOT NULL,
        section TEXT NOT NULL,
        semester INTEGER NOT NULL,
        timetable_data TEXT NOT NULL,
        generated_by INTEGER,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS conflict_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conflict_type TEXT,
        severity TEXT DEFAULT "warning",
        teacher_id INTEGER,
        group_id INTEGER,
        room_id INTEGER,
        slot_id INTEGER,
        conflict_description TEXT,
        resolved BOOLEAN DEFAULT 0,
        resolved_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS holidays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        holiday_name TEXT NOT NULL,
        holiday_date DATE UNIQUE NOT NULL,
        is_optional BOOLEAN DEFAULT 0,
        description TEXT
    )''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_teachers_dept ON teachers(department)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_subjects_branch_year ON subjects(branch, year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ca_teacher ON course_assignments(teacher_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ca_group ON course_assignments(group_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tt_group ON timetable_entries(group_id, slot_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tt_teacher ON timetable_entries(teacher_id, slot_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_slots_day ON time_slots(day_of_week)')

    # ✅ Run migrations BEFORE inserting sample data
    conn.commit()
    run_migrations(conn)
    sync_rooms(conn)
    dedupe_course_assignments(conn)
    backfill_subject_electives(conn)
    dedupe_subjects_by_name(conn)

    _insert_sample_data(cursor)
    conn.commit()

    # Must run AFTER _insert_sample_data, which is what actually creates the
    # time_slots rows on a brand-new database - both of these only edit rows
    # that already exist, they don't create them. Start-time shift must run
    # before sync_short_days so a fresh install's short-day choice (if any)
    # is made against the correct (10:00-18:00) schedule.
    sync_class_start_time(conn)
    sync_short_days(conn)
    conn.commit()
    conn.close()
    print("✅ Database initialized")


def _insert_sample_data(cursor):
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        return

    print("📝 Inserting sample data...")

    admin_pw   = hashlib.sha256("admin123".encode()).hexdigest()
    teacher_pw = hashlib.sha256("teacher123".encode()).hexdigest()
    student_pw = hashlib.sha256("student123".encode()).hexdigest()

    for u, e, p, fn, r in [
        ("admin",    "admin@sgsits.edu",    admin_pw,   "Administrator",      "admin"),
        ("teacher1", "teacher1@sgsits.edu", teacher_pw, "Prof. Rahul Sharma", "teacher"),
        ("teacher2", "teacher2@sgsits.edu", teacher_pw, "Prof. Neha Verma",   "teacher"),
        ("teacher",  "teacher@sgsits.edu",  teacher_pw, "Demo Teacher",       "teacher"),
        ("student1", "student1@sgsits.edu", student_pw, "John Student",       "student"),
        ("student",  "student@sgsits.edu",  student_pw, "Demo Student",       "student"),
    ]:
        cursor.execute(
            "INSERT OR IGNORE INTO users (username,email,password_hash,full_name,role,is_active) VALUES (?,?,?,?,?,1)",
            (u, e, p, fn, r))

    for n, e, d, dg, sp, md, mw in [
        ("Prof. Rahul Sharma", "rahul@sgsits.edu",   "CSE", "Professor",           "Data Structures",              6, 24),
        ("Prof. Neha Verma",   "neha@sgsits.edu",    "CSE", "Associate Professor", "Discrete Structures",          6, 24),
        ("Prof. Sanjay Gupta", "sanjay@sgsits.edu",  "CSE", "Professor",           "Digital Systems",              6, 24),
        ("Prof. Anjali Rao",   "anjali@sgsits.edu",  "CSE", "Assistant Professor", "Object Oriented Programming",  5, 22),
        ("Prof. Meena Singh",  "meena@sgsits.edu",   "CSE", "Associate Professor", "Database Management Systems",  6, 24),
        ("Prof. Ravi Kumar",   "ravi@sgsits.edu",    "CSE", "Professor",           "Theory of Computation",        5, 20),
        ("Prof. Vikram Joshi", "vikram@sgsits.edu",  "CSE", "Assistant Professor", "Web Technology",               6, 24),
        ("Prof. Kavita Deshmukh", "kavita@sgsits.edu", "CSE", "Assistant Professor", "Systems Programming",       6, 24),
        ("Prof. Sunita Yadav", "sunita@sgsits.edu", "CSE", "Assistant Professor", "Programming Languages",       6, 24),
        ("Prof. Amit Tiwari",  "amit@sgsits.edu",    "EE",  "Professor",           "Circuit Theory",               5, 20),
        ("Prof. Priya Patel",  "priya@sgsits.edu",   "ME",  "Assistant Professor", "Thermodynamics",               5, 20),
    ]:
        cursor.execute(
            "INSERT OR IGNORE INTO teachers (name,email,department,designation,specialization,max_hours_per_day,max_hours_per_week,is_active) VALUES (?,?,?,?,?,?,?,1)",
            (n, e, d, dg, sp, md, mw))

    # Real RGPV B.Tech CSE curriculum (3rd & 5th semester) - sourced from the
    # official scheme so sample data reflects an actual course list instead of
    # placeholder names. Lab-bearing subjects get a separate "L"-suffixed
    # course row (is_lab=1) so the lab batch-scheduling mechanism applies to
    # them independently of their paired theory lecture.
    for code, name, desc, credits, hours, theory, lab, is_lab, dept, sem in [
        # Semester 3 (2nd year)
        ("ES301",  "Energy & Environmental Engineering", "Interdisciplinary", 3, 3, 3, 0, 0, "CSE", 3),
        ("CS302",  "Discrete Structures",                "Theory",            3, 3, 3, 0, 0, "CSE", 3),
        ("CS303",  "Data Structures",                     "Theory",            3, 3, 3, 0, 0, "CSE", 3),
        ("CS303L", "Data Structures Lab",                 "Practical",         1, 2, 0, 2, 1, "CSE", 3),
        ("CS304",  "Digital Systems",                     "Theory",            3, 3, 3, 0, 0, "CSE", 3),
        ("CS304L", "Digital Systems Lab",                 "Practical",         1, 2, 0, 2, 1, "CSE", 3),
        ("CS305",  "Object Oriented Programming Methodology", "Theory",        3, 3, 3, 0, 0, "CSE", 3),
        ("CS305L", "OOP Methodology Lab",                 "Practical",         1, 2, 0, 2, 1, "CSE", 3),
        # Semester 5 (3rd year)
        ("CS501",  "Theory of Computation",               "Theory",            3, 3, 3, 0, 0, "CSE", 5),
        ("CS502",  "Database Management Systems",         "Theory",            3, 3, 3, 0, 0, "CSE", 5),
        ("CS502L", "DBMS Lab",                             "Practical",         1, 2, 0, 2, 1, "CSE", 5),
        ("CS504",  "Internet and Web Technology",          "Theory",            3, 3, 3, 0, 0, "CSE", 5),
        ("CS504L", "Web Technology Lab",                   "Practical",         1, 2, 0, 2, 1, "CSE", 5),
        ("CS505",  "Linux Lab",                             "Practical",         1, 2, 0, 2, 1, "CSE", 5),
        ("CS506",  "Python Lab",                            "Practical",         1, 2, 0, 2, 1, "CSE", 5),
        # Other departments (kept as generic placeholders)
        ("EE201",   "Circuit Theory",      "Circuits",   3, 3, 2, 1, 0, "EE",   2),
        ("ME101",   "Engg Mechanics",      "Mechanics",  3, 3, 2, 1, 0, "ME",   1),
    ]:
        cursor.execute(
            "INSERT OR IGNORE INTO courses (course_code,course_name,description,credits,hours_per_week,theory_hours,lab_hours,is_lab,department,semester) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (code, name, desc, credits, hours, theory, lab, is_lab, dept, sem))

    for code, name, branch, year, sem, credits, hours, is_lab in [
        ("ES301",  "Energy & Environmental Engineering",       "CSE", 2, 3, 3, 3, 0),
        ("CS302",  "Discrete Structures",                      "CSE", 2, 3, 3, 3, 0),
        ("CS303",  "Data Structures",                          "CSE", 2, 3, 3, 3, 0),
        ("CS303L", "Data Structures Lab",                      "CSE", 2, 3, 1, 2, 1),
        ("CS304",  "Digital Systems",                          "CSE", 2, 3, 3, 3, 0),
        ("CS304L", "Digital Systems Lab",                      "CSE", 2, 3, 1, 2, 1),
        ("CS305",  "Object Oriented Programming Methodology",  "CSE", 2, 3, 3, 3, 0),
        ("CS305L", "OOP Methodology Lab",                      "CSE", 2, 3, 1, 2, 1),
        ("CS501",  "Theory of Computation",                    "CSE", 3, 5, 3, 3, 0),
        ("CS502",  "Database Management Systems",              "CSE", 3, 5, 3, 3, 0),
        ("CS502L", "DBMS Lab",                                 "CSE", 3, 5, 1, 2, 1),
        ("CS504",  "Internet and Web Technology",               "CSE", 3, 5, 3, 3, 0),
        ("CS504L", "Web Technology Lab",                        "CSE", 3, 5, 1, 2, 1),
        ("CS505",  "Linux Lab",                                  "CSE", 3, 5, 1, 2, 1),
        ("CS506",  "Python Lab",                                 "CSE", 3, 5, 1, 2, 1),
        ("EE201",  "Circuit Theory",                             "EE",  1, 2, 3, 3, 0),
        ("ME101",  "Engg Mechanics",                             "ME",  1, 1, 3, 3, 0),
    ]:
        cursor.execute(
            "INSERT OR IGNORE INTO subjects (code,name,branch,year,semester,credits,hours_per_week,is_lab) VALUES (?,?,?,?,?,?,?,?)",
            (code, name, branch, year, sem, credits, hours, is_lab))

    for code, name, sem, dept, year, count in [
        ("CSE2A", "CSE Year 2 Sec A", 3, "CSE", "2024-2025", 60),
        ("CSE2B", "CSE Year 2 Sec B", 3, "CSE", "2024-2025", 58),
        ("CSE3A", "CSE Year 3 Sec A", 5, "CSE", "2024-2025", 55),
        ("EE1A",  "EE Year 1 Sec A",  1, "EE",  "2024-2025", 55),
        ("ME1A",  "ME Year 1 Sec A",  1, "ME",  "2024-2025", 58),
    ]:
        cursor.execute(
            "INSERT OR IGNORE INTO student_groups (group_code,group_name,semester,department,academic_year,student_count,is_active) VALUES (?,?,?,?,?,?,1)",
            (code, name, sem, dept, year, count))

    slot_id = 1
    for day_idx, day_name in enumerate(DAYS):
        for code, start, end, stype, is_break in [
            ("S1",    "10:00", "11:00", "lecture", 0),
            ("S2",    "11:00", "12:00", "lecture", 0),
            ("S3",    "12:00", "13:00", "lecture", 0),
            ("LUNCH", "13:00", "14:00", "break",   1),
            ("S4",    "15:00", "16:00", "lecture", 0),
            ("S5",    "16:00", "17:00", "lecture", 0),
            ("S6",    "17:00", "18:00", "lecture", 0),
        ]:
            cursor.execute(
                "INSERT OR IGNORE INTO time_slots (id,slot_code,day_of_week,day_name,start_time,end_time,duration,slot_type,is_break,is_active) VALUES (?,?,?,?,?,?,60,?,?,1)",
                (slot_id, f"{day_name[:3]}{code}", day_idx, day_name, start, end, stype, is_break))
            slot_id += 1

    cursor.execute("SELECT id, email FROM teachers")
    tid_by_email = {r["email"]: r["id"] for r in cursor.fetchall()}
    cursor.execute("SELECT id, course_code FROM courses")
    cid_by_code = {r["course_code"]: r["id"] for r in cursor.fetchall()}
    cursor.execute("SELECT id, group_code FROM student_groups")
    gid_by_code = {r["group_code"]: r["id"] for r in cursor.fetchall()}

    # (course_code, teacher_email, group_code, semester, hours_per_week, is_lab)
    course_assignments_seed = [
        ("ES301",  "amit@sgsits.edu",   "CSE2A", 3, 3, 0),
        ("CS302",  "neha@sgsits.edu",   "CSE2A", 3, 3, 0),
        ("CS303",  "rahul@sgsits.edu",  "CSE2A", 3, 3, 0),
        ("CS303L", "rahul@sgsits.edu",  "CSE2A", 3, 2, 1),
        ("CS304",  "sanjay@sgsits.edu", "CSE2A", 3, 3, 0),
        ("CS304L", "sanjay@sgsits.edu", "CSE2A", 3, 2, 1),
        ("CS305",  "anjali@sgsits.edu", "CSE2A", 3, 3, 0),
        ("CS305L", "anjali@sgsits.edu", "CSE2A", 3, 2, 1),

        ("CS302",  "neha@sgsits.edu",   "CSE2B", 3, 3, 0),
        ("CS303",  "rahul@sgsits.edu",  "CSE2B", 3, 3, 0),
        ("CS303L", "rahul@sgsits.edu",  "CSE2B", 3, 2, 1),

        ("CS501",  "ravi@sgsits.edu",   "CSE3A", 5, 3, 0),
        ("CS502",  "meena@sgsits.edu",  "CSE3A", 5, 3, 0),
        ("CS502L", "meena@sgsits.edu",  "CSE3A", 5, 2, 1),
        ("CS504",  "vikram@sgsits.edu", "CSE3A", 5, 3, 0),
        ("CS504L", "vikram@sgsits.edu", "CSE3A", 5, 2, 1),
        ("CS505",  "kavita@sgsits.edu", "CSE3A", 5, 2, 1),
        ("CS506",  "sunita@sgsits.edu", "CSE3A", 5, 2, 1),

        ("EE201",  "amit@sgsits.edu",   "EE1A", 1, 3, 0),
        ("ME101",  "priya@sgsits.edu",  "ME1A", 1, 3, 0),
    ]
    for course_code, email, group_code, sem, hours, is_lab in course_assignments_seed:
        cid = cid_by_code.get(course_code)
        tid = tid_by_email.get(email)
        gid = gid_by_code.get(group_code)
        if cid and tid and gid:
            cursor.execute(
                "INSERT OR IGNORE INTO course_assignments (course_id,teacher_id,group_id,semester,hours_per_week,is_lab) VALUES (?,?,?,?,?,?)",
                (cid, tid, gid, sem, hours, is_lab))

    for name, date, opt in [
        ("Republic Day",     "2024-01-26", 0),
        ("Independence Day", "2024-08-15", 0),
        ("Gandhi Jayanti",   "2024-10-02", 0),
        ("Christmas",        "2024-12-25", 0),
    ]:
        cursor.execute(
            "INSERT OR IGNORE INTO holidays (holiday_name,holiday_date,is_optional) VALUES (?,?,?)",
            (name, date, opt))

    print("✅ Sample data inserted!")


# ============================================================
# APP
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting SGSITS Timetable API v4.0...")
    init_db()
    yield
    print("👋 Shutting down...")

app = FastAPI(title="SGSITS Timetable API", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer()


# ============================================================
# AUTH HELPERS
# ============================================================
def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def create_token(user_id: int, username: str, role: str) -> str:
    return jwt.encode(
        {"user_id": user_id, "username": username, "role": role,
         "exp": datetime.now() + timedelta(days=7)},
        SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ============================================================
# MODELS
# ============================================================
class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None

# Username-prefix convention: student accounts start with "st", teacher
# accounts with "te" (admin has no required prefix). Checked at both signup
# (so new accounts always comply) and login (so a login only ever succeeds
# when the prefix, the account's real role, and the credentials all agree).
ROLE_USERNAME_PREFIXES = {"student": "st", "teacher": "te"}

def check_username_prefix(username: str, role: str):
    prefix = ROLE_USERNAME_PREFIXES.get(role)
    if prefix and not username.lower().startswith(prefix):
        raise HTTPException(
            status_code=400,
            detail=f'{role.capitalize()} usernames must start with "{prefix}" (e.g. "{prefix}rahul").'
        )

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
    designation: Optional[str] = None
    specialization: Optional[str] = None
    max_hours_per_day: Optional[int] = 6
    max_hours_per_week: Optional[int] = 24

class RoomData(BaseModel):
    room_code: str
    room_name: str
    capacity: int
    room_type: str = "lecture"
    building: Optional[str] = None
    floor: Optional[int] = None
    has_projector: Optional[bool] = False
    has_ac: Optional[bool] = False
    has_computers: Optional[bool] = False
    is_lab: Optional[bool] = False

class SubjectData(BaseModel):
    code: str
    name: str
    branch: str
    year: int
    semester: int = 1
    credits: Optional[int] = 3
    hours_per_week: Optional[int] = 3
    is_lab: Optional[bool] = False
    is_elective: Optional[bool] = False
    teacher_id: Optional[int] = None
    teacher2_id: Optional[int] = None

class CourseData(BaseModel):
    course_code: str
    course_name: str
    description: Optional[str] = None
    credits: int = 3
    hours_per_week: int = 3
    theory_hours: int = 2
    lab_hours: int = 1
    is_lab: bool = False
    department: Optional[str] = None
    semester: Optional[int] = None

class CourseAssignmentData(BaseModel):
    course_id: int
    teacher_id: int
    group_id: int
    semester: int
    hours_per_week: int = 3
    theory_hours: int = 2
    lab_hours: int = 1
    is_lab: bool = False

class TimetableGenerateRequest(BaseModel):
    branch: str
    year: int
    section: str
    semester: int = 1

class ConflictResolveRequest(BaseModel):
    resolution_note: Optional[str] = None


# ============================================================
# MATRIX HELPERS
# ============================================================
def _empty_matrix() -> Dict:
    m = {day: {slot: "—" for slot in TIME_SLOTS} for day in DAYS}
    for day in DAYS:
        m[day][LUNCH_SLOT] = "🍽️ LUNCH BREAK"
    return m

def _build_timetable_response(branch, year, section, semester, entries_list, saved_entries=None):
    matrix = _empty_matrix()
    source = saved_entries if saved_entries is not None else entries_list
    for entry in source:
        if saved_entries is not None:
            day      = entry.get("day")
            slot_key = entry.get("time_slot")
            code     = entry.get("subject_code", "")
            room     = entry.get("room_code")
            batch    = entry.get("batch")
        else:
            day      = entry.get("day_name")
            slot_key = f"{entry.get('start_time')}-{entry.get('end_time')}"
            code     = entry.get("course_code", "")
            room     = entry.get("room_code")
            batch    = entry.get("batch")
        # Only lab entries carry a batch (E1/E2/E3) - use that as the signal
        # to add a "Lab" label so it's obvious at a glance which periods are
        # labs vs regular lectures.
        if batch:
            code = f"{code} 🧪Lab ({batch})"
        cell = f"{code}<br>({entry.get('teacher_name','')})"
        if room:
            cell += f"<br>Room {room}"
        if day and slot_key and day in matrix and slot_key in matrix[day] and slot_key != LUNCH_SLOT:
            matrix[day][slot_key] = cell
    return {"branch": branch, "year": year, "semester": semester, "section": section,
            "days": DAYS, "time_slots": TIME_SLOTS, "timetable": matrix}


# ============================================================
# ROOT / HEALTH
# ============================================================
@app.get("/")
async def root():
    return {"message": "SGSITS Timetable API v4.0", "status": "running", "docs": "/docs"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": str(datetime.now())}


# ============================================================
# AUTH
# ============================================================
@app.post("/api/auth/login")
async def login(request: LoginRequest):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE (username=? OR email=?) AND is_active=1",
            (request.username, request.username))
        user = cursor.fetchone()
        if not user or user["password_hash"] != hash_password(request.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if request.role and request.role != user["role"]:
            raise HTTPException(
                status_code=403,
                detail=f"This account is registered as a {user['role']}. Please use the {user['role']} login page."
            )
        check_username_prefix(user["username"], user["role"])
        token = create_token(user["id"], user["username"], user["role"])
        return {"success": True, "token": token,
                "user": {"id": user["id"], "username": user["username"],
                         "email": user["email"], "full_name": user["full_name"], "role": user["role"]}}
    finally:
        conn.close()

@app.post("/api/auth/signup")
async def signup(request: SignupRequest):
    conn = get_db()
    try:
        cursor = conn.cursor()
        check_username_prefix(request.username, request.role)
        cursor.execute("SELECT id FROM users WHERE username=? OR email=?", (request.username, request.email))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already exists")
        cursor.execute(
            "INSERT INTO users (username,email,password_hash,full_name,role,is_active) VALUES (?,?,?,?,?,1)",
            (request.username, request.email, hash_password(request.password), request.full_name, request.role))
        conn.commit()
        user_id = cursor.lastrowid
        token = create_token(user_id, request.username, request.role)
        return {"success": True, "token": token,
                "user": {"id": user_id, "username": request.username,
                         "email": request.email, "full_name": request.full_name, "role": request.role}}
    finally:
        conn.close()


# ============================================================
# ADMIN — USERS
# ============================================================
@app.get("/api/admin/users")
async def get_all_users(_=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id,username,email,full_name,role,is_active,created_at FROM users ORDER BY created_at DESC")
        return {"users": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.put("/api/admin/users/{user_id}/status")
async def update_user_status(user_id: int, request: dict, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active=? WHERE id=?", (request.get("is_active", 1), user_id))
        conn.commit()
        return {"success": True, "message": "User status updated"}
    finally:
        conn.close()

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE id=?", (user_id,))
        user = cursor.fetchone()
        if user and user["role"] == "admin":
            raise HTTPException(status_code=403, detail="Cannot delete admin user")
        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        return {"success": True, "message": "User deleted"}
    finally:
        conn.close()


# ============================================================
# TEACHERS
# ============================================================
@app.get("/api/admin/teachers")
async def get_teachers_admin(_=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teachers WHERE is_active=1 ORDER BY name")
        return {"teachers": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.post("/api/admin/teachers")
async def add_teacher(teacher: TeacherData, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM teachers WHERE email=?", (teacher.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Teacher with email {teacher.email} already exists")
        cursor.execute(
            "INSERT INTO teachers (name,email,department,designation,specialization,max_hours_per_day,max_hours_per_week,is_active) VALUES (?,?,?,?,?,?,?,1)",
            (teacher.name, teacher.email, teacher.department, teacher.designation,
             teacher.specialization, teacher.max_hours_per_day, teacher.max_hours_per_week))
        conn.commit()
        return {"success": True, "message": f"Teacher {teacher.name} added", "id": cursor.lastrowid}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/admin/teachers/directory")
async def get_teacher_directory(branch: Optional[str] = None, _=Depends(require_admin)):
    """Preview the built-in SGSITS faculty directory before loading it into `teachers`."""
    rows = build_teacher_rows(branch)
    return {
        "count": len(rows),
        "teachers": [
            {"name": r[0], "email": r[1], "department": r[2], "designation": r[3], "specialization": r[4]}
            for r in rows
        ]
    }

@app.post("/api/admin/teachers/load-directory")
async def load_teacher_directory(data: Optional[dict] = None, _=Depends(require_admin)):
    """
    Bulk-inserts the built-in SGSITS faculty directory (teachers_data.py) into
    `teachers`. This is a best-effort list assembled from public web search
    results, not an official scrape - department/designation may be outdated or
    incomplete (see teachers_data.py). Manually adding/editing a teacher via
    AddTeacher still works exactly as before. Existing emails are skipped, so
    it's safe to call repeatedly. Optional body: {"branch": "CSE"}
    """
    data = data or {}
    branch = data.get("branch")
    rows = build_teacher_rows(branch)

    conn = get_db()
    try:
        cursor = conn.cursor()
        added, skipped = 0, 0
        for name, email, department, designation, specialization in rows:
            cursor.execute("SELECT id FROM teachers WHERE email=?", (email,))
            if cursor.fetchone():
                skipped += 1
                continue
            cursor.execute(
                "INSERT INTO teachers (name,email,department,designation,specialization,max_hours_per_day,max_hours_per_week,is_active) VALUES (?,?,?,?,?,6,24,1)",
                (name, email, department, designation, specialization))
            added += 1
        conn.commit()
        return {
            "success": True,
            "message": f"Loaded {added} teacher(s) ({skipped} already existed)",
            "added": added,
            "skipped": skipped,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/admin/teachers/load-test-data")
async def load_test_teacher_data(data: Optional[dict] = None, _=Depends(require_admin)):
    """
    Bulk-inserts purely fictional filler teachers (test_teachers_data.py) for
    testing - NOT real people, kept separate from the real SGSITS directory.
    Every row is tagged "(Test Data)" in its designation and uses a distinct
    @test.sgsits.edu email so it's obvious which rows are fake. Existing emails
    are skipped, so it's safe to call repeatedly. Optional body: {"branch": "CSE"}
    """
    data = data or {}
    branch = data.get("branch")
    rows = build_test_teacher_rows(branch)

    conn = get_db()
    try:
        cursor = conn.cursor()
        added, skipped = 0, 0
        for name, email, department, designation, specialization in rows:
            cursor.execute("SELECT id FROM teachers WHERE email=?", (email,))
            if cursor.fetchone():
                skipped += 1
                continue
            cursor.execute(
                "INSERT INTO teachers (name,email,department,designation,specialization,max_hours_per_day,max_hours_per_week,is_active) VALUES (?,?,?,?,?,6,24,1)",
                (name, email, department, designation, specialization))
            added += 1
        conn.commit()
        return {
            "success": True,
            "message": f"Loaded {added} test teacher(s) ({skipped} already existed)",
            "added": added,
            "skipped": skipped,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/admin/teachers/{teacher_id}")
async def update_teacher(teacher_id: int, teacher: TeacherData, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE teachers SET name=?,email=?,department=?,designation=?,specialization=?,max_hours_per_day=?,max_hours_per_week=? WHERE id=?",
            (teacher.name, teacher.email, teacher.department, teacher.designation,
             teacher.specialization, teacher.max_hours_per_day, teacher.max_hours_per_week, teacher_id))
        conn.commit()
        return {"success": True, "message": "Teacher updated"}
    finally:
        conn.close()

@app.delete("/api/admin/teachers/{teacher_id}")
async def delete_teacher(teacher_id: int, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE teachers SET is_active=0 WHERE id=?", (teacher_id,))
        conn.commit()
        return {"success": True, "message": "Teacher deactivated"}
    finally:
        conn.close()

@app.get("/api/teachers")
async def get_teachers_public(department: Optional[str] = None):
    conn = get_db()
    try:
        cursor = conn.cursor()
        if department:
            cursor.execute("SELECT * FROM teachers WHERE department=? AND is_active=1", (department,))
        else:
            cursor.execute("SELECT * FROM teachers WHERE is_active=1 ORDER BY name")
        return {"teachers": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.get("/api/teachers/{teacher_id}/schedule")
async def get_teacher_schedule_by_id(teacher_id: int, _=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT te.*, ts.day_name, ts.start_time, ts.end_time,
                   c.course_code, c.course_name,
                   sg.group_name, sg.group_code,
                   r.room_code, r.room_name
            FROM timetable_entries te
            JOIN time_slots ts ON te.slot_id=ts.id
            JOIN courses c ON te.course_id=c.id
            JOIN student_groups sg ON te.group_id=sg.id
            JOIN rooms r ON te.room_id=r.id
            WHERE te.teacher_id=? AND te.status="scheduled"
            ORDER BY ts.day_of_week, ts.start_time
        ''', (teacher_id,))
        entries = [dict(r) for r in cursor.fetchall()]
        matrix = _empty_matrix()
        for e in entries:
            day = e["day_name"]
            sk  = f"{e['start_time']}-{e['end_time']}"
            if day in matrix and sk in matrix[day] and sk != LUNCH_SLOT:
                code = f"{e['course_code']} 🧪Lab ({e['batch']})" if e.get("batch") else e["course_code"]
                matrix[day][sk] = f"{code}<br>({e['group_code']})<br>{e['room_code']}"
        return {"teacher_id": teacher_id, "schedule": entries, "matrix": matrix, "total_classes": len(entries)}
    finally:
        conn.close()

@app.get("/api/teacher/schedule")
async def get_my_schedule(current_user=Depends(get_current_user)):
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access this")
    conn = get_db()
    try:
        cursor = conn.cursor()
        username = current_user.get("username")
        cursor.execute("SELECT id FROM teachers WHERE email LIKE ? AND is_active=1", (f"%{username}%",))
        teacher = cursor.fetchone()
        if not teacher:
            return {"schedule": [], "matrix": _empty_matrix(), "total_classes": 0}
        cursor.execute('''
            SELECT te.*, ts.day_name, ts.start_time, ts.end_time,
                   c.course_code, c.course_name, sg.group_name, sg.group_code, r.room_code
            FROM timetable_entries te
            JOIN time_slots ts ON te.slot_id=ts.id
            JOIN courses c ON te.course_id=c.id
            JOIN student_groups sg ON te.group_id=sg.id
            JOIN rooms r ON te.room_id=r.id
            WHERE te.teacher_id=? AND te.status="scheduled"
            ORDER BY ts.day_of_week, ts.start_time
        ''', (teacher["id"],))
        entries = [dict(r) for r in cursor.fetchall()]
        matrix = _empty_matrix()
        for e in entries:
            day = e["day_name"]
            sk  = f"{e['start_time']}-{e['end_time']}"
            if day in matrix and sk in matrix[day] and sk != LUNCH_SLOT:
                code = f"{e['course_code']} 🧪Lab ({e['batch']})" if e.get("batch") else e["course_code"]
                matrix[day][sk] = f"{code}<br>({e['group_code']})<br>{e['room_code']}"
        return {"teacher_name": username, "schedule": entries, "matrix": matrix, "total_classes": len(entries)}
    finally:
        conn.close()


# ============================================================
# ROOMS
# ============================================================
@app.get("/api/rooms")
async def get_rooms(room_type: Optional[str] = None):
    conn = get_db()
    try:
        cursor = conn.cursor()
        if room_type:
            cursor.execute("SELECT * FROM rooms WHERE room_type=? AND is_active=1", (room_type,))
        else:
            cursor.execute("SELECT * FROM rooms WHERE is_active=1")
        return {"rooms": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.post("/api/admin/rooms")
async def add_room(room: RoomData, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rooms (room_code,room_name,capacity,room_type,building,floor,has_projector,has_ac,has_computers,is_lab,is_active) VALUES (?,?,?,?,?,?,?,?,?,?,1)",
            (room.room_code, room.room_name, room.capacity, room.room_type, room.building,
             room.floor, room.has_projector, room.has_ac, room.has_computers, room.is_lab))
        conn.commit()
        return {"success": True, "message": f"Room {room.room_code} added", "id": cursor.lastrowid}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/rooms/available")
async def get_available_rooms(slot_id: int, capacity: int = 0, is_lab: bool = False):
    conn = get_db()
    try:
        cursor = conn.cursor()
        query = '''SELECT r.* FROM rooms r WHERE r.is_active=1 AND r.capacity>=?
                   AND r.id NOT IN (SELECT room_id FROM timetable_entries WHERE slot_id=? AND status="scheduled")'''
        params = [capacity, slot_id]
        if is_lab:
            query += " AND r.is_lab=1"
        cursor.execute(query, params)
        return {"slot_id": slot_id, "available_rooms": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()


# ============================================================
# SUBJECTS
# ============================================================
@app.get("/api/admin/subjects")
async def get_subjects_admin(
    branch: Optional[str] = None,
    year: Optional[int] = None,
    semester: Optional[int] = None,
    _=Depends(require_admin)
):
    conn = get_db()
    try:
        cursor = conn.cursor()
        query = '''
            SELECT s.*, t1.name as teacher1_name, t2.name as teacher2_name
            FROM subjects s
            LEFT JOIN teachers t1 ON s.teacher_id=t1.id
            LEFT JOIN teachers t2 ON s.teacher2_id=t2.id
            WHERE 1=1
        '''
        params = []
        if branch:
            query += " AND s.branch=?"; params.append(branch)
        if year:
            query += " AND s.year=?"; params.append(year)
        if semester:
            query += " AND s.semester=?"; params.append(semester)
        query += " ORDER BY s.name"
        cursor.execute(query, params)
        return {"subjects": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.post("/api/admin/subjects")
async def add_subject(subject: SubjectData, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM subjects WHERE code=?", (subject.code,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Subject code {subject.code} already exists")
        cursor.execute(
            "INSERT INTO subjects (code,name,branch,year,semester,credits,hours_per_week,is_lab,is_elective,teacher_id,teacher2_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (subject.code, subject.name, subject.branch, subject.year, subject.semester,
             subject.credits, subject.hours_per_week, subject.is_lab, subject.is_elective,
             subject.teacher_id, subject.teacher2_id))
        subject_id = cursor.lastrowid

        cursor.execute("SELECT id FROM courses WHERE course_code=?", (subject.code,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO courses (course_code,course_name,credits,hours_per_week,is_lab,is_elective,department,semester) VALUES (?,?,?,?,?,?,?,?)",
                (subject.code, subject.name, subject.credits, subject.hours_per_week,
                 subject.is_lab, subject.is_elective, subject.branch, subject.semester))

        conn.commit()
        return {"success": True, "message": f"Subject {subject.name} added", "id": subject_id}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/admin/subjects/assign")
async def assign_subject(data: dict, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()

        subject_id = data.get("subject_id")
        teacher_id = data.get("teacher_id")
        section    = data.get("section", "A")
        branch     = data.get("branch")
        year       = data.get("year", 1)

        # Validate all required fields up front
        if not subject_id or not teacher_id or not section or not branch:
            raise HTTPException(
                status_code=422,
                detail="Missing required fields: subject_id, teacher_id, section, branch"
            )
        if not isinstance(year, int) or year < 1:
            raise HTTPException(
                status_code=422,
                detail=f"year must be a positive integer, got: {year!r}"
            )

        # Fetch subject and convert to dict IMMEDIATELY before any other cursor use
        cursor.execute("SELECT * FROM subjects WHERE id=?", (subject_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Subject with id={subject_id} not found")
        subject = dict(row)  # ✅ plain dict — safe across all subsequent cursor operations

        # Assign teacher to subject
        cursor.execute("UPDATE subjects SET teacher_id=? WHERE id=?", (teacher_id, subject_id))

        # Create student group if not exists
        group_code = f"{branch}{year}{section}"
        cursor.execute("SELECT id FROM student_groups WHERE group_code=?", (group_code,))
        group_row = cursor.fetchone()
        if not group_row:
            cursor.execute(
                "INSERT INTO student_groups (group_code,group_name,semester,department,academic_year,student_count,is_active) VALUES (?,?,?,?,?,60,1)",
                (group_code, f"{branch} Year {year} Sec {section}",
                 subject["semester"], branch, "2024-2025"))
            group_id = cursor.lastrowid
        else:
            group_id = group_row["id"]

        # Ensure course record exists
        cursor.execute("SELECT id FROM courses WHERE course_code=?", (subject["code"],))
        course_row = cursor.fetchone()
        if not course_row:
            cursor.execute(
                "INSERT INTO courses (course_code,course_name,credits,hours_per_week,is_lab,is_elective,department,semester) VALUES (?,?,?,?,?,?,?,?)",
                (subject["code"], subject["name"], subject["credits"],
                 subject["hours_per_week"], subject["is_lab"], subject.get("is_elective", 0), branch, subject["semester"]))
            course_id = cursor.lastrowid
        else:
            course_id = course_row["id"]

        # A group can only have ONE teacher per course at a time - re-assigning
        # replaces the existing course_assignment's teacher rather than adding
        # a second row, which would otherwise double (or triple) that
        # subject's scheduled hours and make it pile up on the same day.
        cursor.execute(
            "SELECT id, teacher_id FROM course_assignments WHERE course_id=? AND group_id=?",
            (course_id, group_id))
        existing_ca = cursor.fetchone()
        if existing_ca:
            if existing_ca["teacher_id"] != teacher_id:
                cursor.execute("UPDATE course_assignments SET teacher_id=? WHERE id=?", (teacher_id, existing_ca["id"]))
        else:
            cursor.execute(
                "INSERT INTO course_assignments (course_id,teacher_id,group_id,semester,hours_per_week) VALUES (?,?,?,?,?)",
                (course_id, teacher_id, group_id, subject["semester"], subject["hours_per_week"]))

        conn.commit()

        # Warn (don't block) if this group/semester now needs more weekly hours
        # than there are teaching slots - generation will otherwise silently
        # leave some subjects short on hours.
        cursor.execute("SELECT COUNT(*) FROM time_slots WHERE is_break=0 AND is_active=1")
        total_available_slots = cursor.fetchone()[0]

        cursor.execute('''
            SELECT c.is_lab, c.hours_per_week
            FROM course_assignments ca JOIN courses c ON ca.course_id=c.id
            WHERE ca.group_id=? AND ca.semester=?
        ''', (group_id, subject["semester"]))
        course_rows = cursor.fetchall()
        subject_count = len(course_rows)
        total_hours_needed = sum(
            (LAB_SESSIONS_PER_WEEK * LAB_SESSION_SLOTS) if r["is_lab"] else min(r["hours_per_week"], MAX_THEORY_SESSIONS_PER_WEEK)
            for r in course_rows
        )

        warning = None
        if total_hours_needed > total_available_slots:
            warning = (
                f"{branch} Year {year} Sem {subject['semester']} now needs {total_hours_needed} "
                f"hours/week across {subject_count} subject(s), but only {total_available_slots} "
                f"teaching slots exist per week. Some subjects may not fit when you generate the timetable."
            )

        # Separate check: only one lab is scheduled per day, so a group with
        # too many lab courses will run out of distinct days before every
        # lab gets its full LAB_SESSIONS_PER_WEEK sessions.
        lab_course_count = sum(1 for r in course_rows if r["is_lab"])
        total_lab_sessions_needed = lab_course_count * LAB_SESSIONS_PER_WEEK
        lab_warning = None
        if total_lab_sessions_needed > MAX_RECOMMENDED_LAB_SESSIONS_PER_WEEK:
            lab_warning = (
                f"{branch} Year {year} Sem {subject['semester']} now has {lab_course_count} lab course(s), "
                f"needing {total_lab_sessions_needed} lab sessions/week total ({LAB_SESSIONS_PER_WEEK} each). "
                f"Only one lab is scheduled per day, so at most {len(DAYS)} can fit in the week - keeping it "
                f"to {MAX_RECOMMENDED_LAB_SESSIONS_PER_WEEK} or fewer ensures every lab gets its full "
                f"{LAB_SESSIONS_PER_WEEK} sessions."
            )

        return {
            "success": True,
            "message": f"Subject assigned to section {section} successfully",
            "warning": warning,
            "lab_warning": lab_warning,
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/admin/subjects/reset-assignments")
async def reset_branch_assignments(data: dict, _=Depends(require_admin)):
    """
    Undoes every subject-teacher-section assignment for one branch: clears
    teacher_id/teacher2_id on its subjects, deletes its course_assignments,
    and clears any timetable already generated for it (since that timetable
    would otherwise reference assignments that no longer exist). Destructive
    and not reversible - the frontend confirms before calling this.
    """
    branch = data.get("branch")
    if not branch:
        raise HTTPException(status_code=422, detail="branch is required")

    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("UPDATE subjects SET teacher_id=NULL, teacher2_id=NULL WHERE branch=?", (branch,))
        subjects_reset = cursor.rowcount

        cursor.execute("SELECT id FROM student_groups WHERE department=?", (branch,))
        group_ids = [r["id"] for r in cursor.fetchall()]

        assignments_deleted = 0
        timetable_entries_deleted = 0
        if group_ids:
            placeholders = ",".join("?" * len(group_ids))
            cursor.execute(f"DELETE FROM course_assignments WHERE group_id IN ({placeholders})", group_ids)
            assignments_deleted = cursor.rowcount
            cursor.execute(f"DELETE FROM timetable_entries WHERE group_id IN ({placeholders})", group_ids)
            timetable_entries_deleted = cursor.rowcount

        cursor.execute("DELETE FROM saved_timetables WHERE branch=?", (branch,))

        conn.commit()
        return {
            "success": True,
            "message": (
                f"{branch} reset: {subjects_reset} subject(s) unassigned, "
                f"{assignments_deleted} assignment(s) removed, "
                f"{timetable_entries_deleted} timetable slot(s) cleared"
            ),
            "subjects_reset": subjects_reset,
            "assignments_deleted": assignments_deleted,
            "timetable_entries_deleted": timetable_entries_deleted,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/admin/curriculum")
async def get_curriculum_catalog(branch: Optional[str] = None, year: Optional[int] = None, _=Depends(require_admin)):
    """Preview the built-in official SGSITS curriculum before loading it into `subjects`."""
    rows = build_subject_rows(branch, year)
    return {
        "count": len(rows),
        "subjects": [
            {"code": r[0], "name": r[1], "branch": r[2], "year": r[3], "semester": r[4],
             "credits": r[5], "hours_per_week": r[6], "is_lab": r[7], "is_elective": r[8]}
            for r in rows
        ]
    }

@app.post("/api/admin/subjects/load-curriculum")
async def load_curriculum(data: Optional[dict] = None, _=Depends(require_admin)):
    """
    Bulk-inserts the built-in SGSITS curriculum (curriculum_data.py) into `subjects`,
    with no teacher assigned yet. Use AssignSubject afterwards to manually assign a
    teacher and section per subject/section - this endpoint only auto-fills the
    subject catalog, it never touches teacher assignment. Existing subject codes are
    skipped, so it's safe to call repeatedly. Optional body: {"branch": "CSE", "year": 2}
    """
    data = data or {}
    branch = data.get("branch")
    year = data.get("year")
    rows = build_subject_rows(branch, year)

    conn = get_db()
    try:
        cursor = conn.cursor()
        added, skipped = 0, 0
        for code, name, b, y, sem, credits, hours, is_lab, is_elective in rows:
            # Skip if this exact code already exists, OR if a subject with the
            # same name already exists for this branch/year/semester under a
            # different code - e.g. an admin manually added the real "CO3210
            # Constitution Of India" before/after this ran, which must not
            # coexist with our own generic "EE-S3-06 Constitution of India".
            cursor.execute(
                "SELECT id FROM subjects WHERE code=? OR (branch=? AND year=? AND semester=? AND lower(trim(name))=?)",
                (code, b, y, sem, name.strip().lower()))
            if cursor.fetchone():
                skipped += 1
                continue
            cursor.execute(
                "INSERT INTO subjects (code,name,branch,year,semester,credits,hours_per_week,is_lab,is_elective) VALUES (?,?,?,?,?,?,?,?,?)",
                (code, name, b, y, sem, credits, hours, is_lab, is_elective))

            cursor.execute("SELECT id FROM courses WHERE course_code=?", (code,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO courses (course_code,course_name,credits,hours_per_week,is_lab,is_elective,department,semester) VALUES (?,?,?,?,?,?,?,?)",
                    (code, name, credits, hours, is_lab, is_elective, b, sem))
            added += 1
        conn.commit()
        return {
            "success": True,
            "message": f"Loaded {added} subjects ({skipped} already existed)",
            "added": added,
            "skipped": skipped,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/subjects/{branch}/{year}")
async def get_subjects_legacy(branch: str, year: int):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, t1.name as teacher1_name, t2.name as teacher2_name
            FROM subjects s
            LEFT JOIN teachers t1 ON s.teacher_id=t1.id
            LEFT JOIN teachers t2 ON s.teacher2_id=t2.id
            WHERE s.branch=? AND s.year=?
        ''', (branch, year))
        return {"subjects": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()


# ============================================================
# COURSES
# ============================================================
@app.get("/api/courses")
async def get_courses(department: Optional[str] = None, semester: Optional[int] = None):
    conn = get_db()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM courses WHERE 1=1"
        params = []
        if department:
            query += " AND department=?"; params.append(department)
        if semester:
            query += " AND semester=?"; params.append(semester)
        cursor.execute(query, params)
        return {"courses": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.post("/api/admin/courses")
async def add_course(course: CourseData, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO courses (course_code,course_name,description,credits,hours_per_week,theory_hours,lab_hours,is_lab,department,semester) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (course.course_code, course.course_name, course.description, course.credits,
             course.hours_per_week, course.theory_hours, course.lab_hours,
             course.is_lab, course.department, course.semester))
        conn.commit()
        return {"success": True, "message": f"Course {course.course_code} added", "id": cursor.lastrowid}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ============================================================
# STUDENT GROUPS
# ============================================================
@app.get("/api/groups")
async def get_groups(semester: Optional[int] = None, department: Optional[str] = None):
    conn = get_db()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM student_groups WHERE is_active=1"
        params = []
        if semester:
            query += " AND semester=?"; params.append(semester)
        if department:
            query += " AND department=?"; params.append(department)
        cursor.execute(query, params)
        return {"groups": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.post("/api/admin/sections")
async def create_section(data: dict, _=Depends(require_admin)):
    """
    Creates a section (student_group), optionally with a default/home room.
    If that room is already the home room of another active section, this
    still creates the section but returns a non-blocking `warning` naming the
    other section(s) - the admin decides whether that's actually a problem
    (e.g. two sections sharing a lecture hall on different days is fine).
    """
    branch = data.get("branch")
    year = data.get("year")
    section = data.get("section")
    student_count = data.get("student_count", 60)
    room_id = data.get("room_id")

    if not branch or not year or not section:
        raise HTTPException(status_code=422, detail="branch, year, and section are required")
    if not isinstance(year, int) or year < 1:
        raise HTTPException(status_code=422, detail=f"year must be a positive integer, got: {year!r}")

    conn = get_db()
    try:
        cursor = conn.cursor()
        group_code = f"{branch}{year}{section}"
        cursor.execute("SELECT id FROM student_groups WHERE group_code=?", (group_code,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Section {group_code} already exists")

        year_label = {1: "1st Year", 2: "2nd Year", 3: "3rd Year", 4: "4th Year"}.get(year, f"Year {year}")
        semester = year * 2 - 1  # first semester of that year, by default

        cursor.execute(
            "INSERT INTO student_groups (group_code,group_name,semester,department,academic_year,student_count,room_id,is_active) VALUES (?,?,?,?,?,?,?,1)",
            (group_code, f"{branch} {year_label} Section {section}", semester, branch, "2024-2025", student_count, room_id))
        conn.commit()

        warning = None
        if room_id:
            cursor.execute(
                "SELECT group_code FROM student_groups WHERE room_id=? AND is_active=1 AND group_code!=?",
                (room_id, group_code))
            others = [r["group_code"] for r in cursor.fetchall()]
            if others:
                cursor.execute("SELECT room_code FROM rooms WHERE id=?", (room_id,))
                room_row = cursor.fetchone()
                room_code = room_row["room_code"] if room_row else str(room_id)
                warning = f"Room {room_code} is already the home room of: {', '.join(others)}"

        return {
            "success": True,
            "message": f"Section {group_code} created",
            "group_code": group_code,
            "warning": warning,
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/groups/{group_id}/timetable")
async def get_group_timetable(group_id: int, _=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT te.*, ts.day_name, ts.start_time, ts.end_time,
                   c.course_code, c.course_name, t.name as teacher_name, r.room_code
            FROM timetable_entries te
            JOIN time_slots ts ON te.slot_id=ts.id
            JOIN courses c ON te.course_id=c.id
            JOIN teachers t ON te.teacher_id=t.id
            JOIN rooms r ON te.room_id=r.id
            WHERE te.group_id=? AND te.status="scheduled"
            ORDER BY ts.day_of_week, ts.start_time
        ''', (group_id,))
        return {"group_id": group_id, "timetable": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()


# ============================================================
# COURSE ASSIGNMENTS
# ============================================================
@app.get("/api/course-assignments")
async def get_course_assignments(
    teacher_id: Optional[int] = None,
    group_id: Optional[int] = None,
    semester: Optional[int] = None,
    _=Depends(get_current_user)
):
    conn = get_db()
    try:
        cursor = conn.cursor()
        query = '''
            SELECT ca.*, c.course_name, c.course_code,
                   t.name as teacher_name, sg.group_name, sg.group_code
            FROM course_assignments ca
            JOIN courses c ON ca.course_id=c.id
            JOIN teachers t ON ca.teacher_id=t.id
            JOIN student_groups sg ON ca.group_id=sg.id
            WHERE 1=1
        '''
        params = []
        if teacher_id:
            query += " AND ca.teacher_id=?"; params.append(teacher_id)
        if group_id:
            query += " AND ca.group_id=?"; params.append(group_id)
        if semester:
            query += " AND ca.semester=?"; params.append(semester)
        cursor.execute(query, params)
        return {"assignments": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.post("/api/admin/course-assignments")
async def add_course_assignment(data: CourseAssignmentData, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO course_assignments (course_id,teacher_id,group_id,semester,hours_per_week,theory_hours,lab_hours,is_lab) VALUES (?,?,?,?,?,?,?,?)",
            (data.course_id, data.teacher_id, data.group_id, data.semester,
             data.hours_per_week, data.theory_hours, data.lab_hours, data.is_lab))
        conn.commit()
        return {"success": True, "message": "Course assignment created", "id": cursor.lastrowid}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ============================================================
# TIME SLOTS
# ============================================================
@app.get("/api/time-slots")
async def get_time_slots(day: Optional[int] = None):
    conn = get_db()
    try:
        cursor = conn.cursor()
        if day is not None:
            cursor.execute("SELECT * FROM time_slots WHERE day_of_week=? AND is_active=1 ORDER BY start_time", (day,))
        else:
            cursor.execute("SELECT * FROM time_slots WHERE is_active=1 ORDER BY day_of_week, start_time")
        return {"time_slots": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()


# ============================================================
# BRANCHES
# ============================================================
@app.get("/api/branches")
async def get_branches():
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT department FROM student_groups WHERE department IS NOT NULL ORDER BY department")
        from_db = [r[0] for r in cursor.fetchall()]
        names = {"CSE":"Computer Science & Engineering","EE":"Electrical Engineering",
                 "ME":"Mechanical Engineering","ECE":"Electronics & Telecommunication Engineering",
                 "CE":"Civil Engineering","IT":"Information Technology",
                 "EI":"Electronics & Instrumentation Engineering",
                 "IPE":"Industrial & Production Engineering",
                 "BME":"Biomedical Engineering","CHE":"Chemical Engineering"}
        branches = [{"code": b, "name": names.get(b, b)} for b in (from_db or list(names.keys()))]
        return {"branches": branches}
    finally:
        conn.close()


# ============================================================
# TIMETABLE GENERATION
# ============================================================
@app.post("/api/timetable/generate")
async def generate_timetable(request: TimetableGenerateRequest, current_user=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        year_label = {1:"FY",2:"SY",3:"TY",4:"Final"}.get(request.year, f"Y{request.year}")
        group_code = f"{request.branch}{request.year}{request.section}"

        cursor.execute("SELECT id FROM student_groups WHERE group_code=?", (group_code,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO student_groups (group_code,group_name,semester,department,academic_year,student_count,is_active) VALUES (?,?,?,?,?,60,1)",
                (group_code, f"{request.branch} {year_label} Sec {request.section}",
                 request.semester, request.branch, "2024-2025"))
            group_id = cursor.lastrowid
        else:
            group_id = row["id"]

        cursor.execute("DELETE FROM timetable_entries WHERE group_id=? AND semester=?", (group_id, request.semester))

        cursor.execute('''
            SELECT ca.*, c.course_code, c.course_name, c.is_lab as course_is_lab, t.name as teacher_name, t.id as tid
            FROM course_assignments ca
            JOIN courses c ON ca.course_id=c.id
            JOIN teachers t ON ca.teacher_id=t.id
            WHERE ca.group_id=? AND ca.semester=?
            ORDER BY ca.priority DESC
        ''', (group_id, request.semester))
        assignments = cursor.fetchall()

        if not assignments:
            cursor.execute('''
                SELECT ca.*, c.course_code, c.course_name, c.is_lab as course_is_lab, t.name as teacher_name, t.id as tid
                FROM course_assignments ca
                JOIN courses c ON ca.course_id=c.id
                JOIN teachers t ON ca.teacher_id=t.id
                JOIN student_groups sg ON ca.group_id=sg.id
                WHERE sg.department=? AND ca.semester=?
                ORDER BY ca.priority DESC
            ''', (request.branch, request.semester))
            assignments = cursor.fetchall()

        if not assignments:
            return {"success": False,
                    "message": f"No course assignments found for {request.branch} Semester {request.semester}. Add subjects and assign teachers first."}

        # Get all non-break slots ordered by day then time
        cursor.execute("SELECT * FROM time_slots WHERE is_break=0 AND is_active=1 ORDER BY day_of_week, start_time")
        available_slots = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT id, room_code, is_lab FROM rooms WHERE is_active=1 ORDER BY capacity DESC")
        all_rooms = [dict(r) for r in cursor.fetchall()]
        room_ids = [r["id"] for r in all_rooms]
        room_code_by_id = {r["id"]: r["room_code"] for r in all_rooms}

        if not room_ids:
            return {"success": False, "message": "No active rooms found. Add rooms first."}

        # Hard separation: a lab room is only ever used for lab sessions and a
        # non-lab room only ever for theory classes, so a class never gets
        # booked into a lab room and a lab never lands in a lecture room.
        lab_room_ids = [r["id"] for r in all_rooms if r["is_lab"]]
        theory_room_ids = [r["id"] for r in all_rooms if not r["is_lab"]]
        if not lab_room_ids:
            lab_room_ids = room_ids  # no dedicated lab rooms configured - fall back
        if not theory_room_ids:
            theory_room_ids = room_ids  # no dedicated non-lab rooms configured - fall back

        # Track what's occupied
        teacher_busy: Dict[int, set] = {}   # teacher_id -> set of slot_ids
        room_busy:    Dict[int, set] = {}   # room_id    -> set of slot_ids
        group_busy:   set            = set() # set of slot_ids already assigned for this group

        # Pre-load every already-scheduled entry for OTHER groups/sections so a
        # teacher (or room) booked elsewhere at a slot can never be double-booked
        # here. The DELETE above only clears this group's own old entries, so
        # anything left in timetable_entries belongs to a different group and
        # must still be respected (e.g. a teacher already teaching 3rd year CSE
        # at Monday 11am must not also get booked for 2nd year CSE at 11am).
        cursor.execute("SELECT teacher_id, room_id, slot_id FROM timetable_entries")
        for existing_teacher_id, existing_room_id, existing_slot_id in cursor.fetchall():
            teacher_busy.setdefault(existing_teacher_id, set()).add(existing_slot_id)
            room_busy.setdefault(existing_room_id, set()).add(existing_slot_id)

        # Enforce each teacher's own max_hours_per_day / max_hours_per_week
        # (stored on the teacher, never checked before this) - without this a
        # teacher can end up with far more periods in one day, or one week,
        # than they're actually meant to teach. Pre-loaded across ALL groups
        # (like teacher_busy above) so a teacher's load on other sections
        # counts against the same daily/weekly caps.
        cursor.execute("SELECT id, COALESCE(max_hours_per_day,6) AS mhd, COALESCE(max_hours_per_week,24) AS mhw FROM teachers")
        teacher_limits: Dict[int, tuple] = {r["id"]: (r["mhd"], r["mhw"]) for r in cursor.fetchall()}

        teacher_day_hours: Dict[tuple, int] = {}   # (teacher_id, day_of_week) -> hours already scheduled
        teacher_week_hours: Dict[int, int] = {}    # teacher_id -> hours already scheduled this week
        cursor.execute('''
            SELECT te.teacher_id, ts.day_of_week, COUNT(*) AS cnt
            FROM timetable_entries te JOIN time_slots ts ON te.slot_id = ts.id
            GROUP BY te.teacher_id, ts.day_of_week
        ''')
        for r in cursor.fetchall():
            teacher_day_hours[(r["teacher_id"], r["day_of_week"])] = r["cnt"]
            teacher_week_hours[r["teacher_id"]] = teacher_week_hours.get(r["teacher_id"], 0) + r["cnt"]

        def teacher_has_capacity(teacher_id: int, day_of_week: int, hours: int) -> bool:
            max_day, max_week = teacher_limits.get(teacher_id, (6, 24))
            if teacher_day_hours.get((teacher_id, day_of_week), 0) + hours > max_day:
                return False
            if teacher_week_hours.get(teacher_id, 0) + hours > max_week:
                return False
            return True

        def record_teacher_hours(teacher_id: int, day_of_week: int, hours: int) -> None:
            teacher_day_hours[(teacher_id, day_of_week)] = teacher_day_hours.get((teacher_id, day_of_week), 0) + hours
            teacher_week_hours[teacher_id] = teacher_week_hours.get(teacher_id, 0) + hours

        entries_list = []
        assigned_count = 0
        conflicts = []

        # Convert to plain dicts immediately
        assignments = [dict(a) for a in assignments]

        # Calculate total hours needed
        total_hours_needed = sum(a["hours_per_week"] for a in assignments)
        total_slots_available = len(available_slots)  # 5 days × 6 slots = 30 usable slots

        # ── LAB SCHEDULING ──────────────────────────────────────────────
        # Fixed policy (LAB_SESSIONS_PER_WEEK / LAB_SESSION_SLOTS, module-level):
        # every lab course gets 3 sessions/week, each a 2-hour (2 consecutive
        # slot) block, with at most one lab session per day for the group. This
        # overrides hours_per_week for lab assignments - it's a scheduling rule,
        # not a per-subject configurable value.
        # Each class is split into 3 lab batches; a lab room holds one batch
        # at a time, so the 3 weekly sessions rotate E1 -> E2 -> E3 rather
        # than the whole class attending all 3 sessions together.
        LAB_BATCHES = ["E1", "E2", "E3"]

        slots_by_day: Dict[int, list] = {}
        for slot in available_slots:
            slots_by_day.setdefault(slot["day_of_week"], []).append(slot)
        for day in slots_by_day:
            slots_by_day[day].sort(key=lambda s: s["start_time"])

        # NOTE: course_assignments has its own (always-0, never-set) is_lab
        # column, which "SELECT ca.*" would silently shadow if this read
        # a.get("is_lab") - dict(sqlite3.Row) keeps the FIRST column with a
        # given name, not the last, so that always resolved to 0 regardless
        # of the course's real lab status. course_is_lab (explicitly aliased
        # from c.is_lab above) is the one actually correct.
        lab_assignments = [a for a in assignments if a.get("course_is_lab")]
        theory_assignments = [a for a in assignments if not a.get("course_is_lab")]

        unmet_lab_sessions: Dict[str, int] = {}
        # Shared across every lab course for this group: each day only fits 2
        # non-overlapping 2-hour blocks, so if one course greedily fills
        # Mon-Wed first, a later lab course can be starved down to Thu/Fri
        # even though Tue/Thu still have a free window. Preferring the
        # least-loaded day first spreads courses across the week instead.
        day_load: Dict[int, int] = {day: 0 for day in slots_by_day}

        # Shared across the WHOLE group, not per lab course: once any lab
        # session lands on a day, no other lab (same or different subject)
        # can also use that day for this group - one lab per day, period.
        group_lab_days: set = set()

        for assignment in lab_assignments:
            teacher_id = assignment["tid"]
            course_id = assignment["course_id"]
            sessions_placed = 0

            for session_idx in range(LAB_SESSIONS_PER_WEEK):
                batch = LAB_BATCHES[session_idx % len(LAB_BATCHES)]
                placed = False

                # Hard cap: never open a new lab-day for this group beyond
                # MAX_RECOMMENDED_LAB_SESSIONS_PER_WEEK, even if a physical
                # weekday is still free. Without this, 2+ lab courses fill
                # every single weekday with a lab (5 lab-courses/week needed
                # across only 5 days), leaving no lab-free day at all - this
                # guarantees at least one.
                if len(group_lab_days) >= MAX_RECOMMENDED_LAB_SESSIONS_PER_WEEK:
                    break

                # Prefer days not adjacent to an existing lab day so labs
                # spread out (Mon/Wed/Fri) instead of running on consecutive
                # days; adjacent days remain a fallback when nothing else fits.
                for day in sorted(slots_by_day.keys(),
                                  key=lambda d: (any(abs(d - g) == 1 for g in group_lab_days), day_load[d], d)):
                    if day in group_lab_days:
                        continue

                    day_slots = slots_by_day[day]
                    for i in range(len(day_slots) - LAB_SESSION_SLOTS + 1):
                        block = day_slots[i:i + LAB_SESSION_SLOTS]

                        # Only a truly back-to-back block counts as "2 hours"
                        # (a gap here means the lunch break sits between them).
                        if any(block[j]["end_time"] != block[j + 1]["start_time"]
                               for j in range(len(block) - 1)):
                            continue

                        block_slot_ids = [s["id"] for s in block]
                        if any(sid in group_busy for sid in block_slot_ids):
                            continue
                        if any(sid in teacher_busy.get(teacher_id, set()) for sid in block_slot_ids):
                            continue
                        if not teacher_has_capacity(teacher_id, day, LAB_SESSION_SLOTS):
                            continue

                        room_id = next(
                            (rid for rid in lab_room_ids
                             if not any(sid in room_busy.get(rid, set()) for sid in block_slot_ids)),
                            None
                        )
                        if room_id is None:
                            continue

                        for slot in block:
                            cursor.execute('''
                                INSERT INTO timetable_entries
                                    (teacher_id,group_id,room_id,slot_id,course_id,semester,academic_year,status,batch)
                                VALUES (?,?,?,?,?,?,"2024-2025","scheduled",?)
                            ''', (teacher_id, group_id, room_id, slot["id"], course_id, request.semester, batch))

                            teacher_busy.setdefault(teacher_id, set()).add(slot["id"])
                            room_busy.setdefault(room_id, set()).add(slot["id"])
                            group_busy.add(slot["id"])

                            entries_list.append({
                                "day":          slot["day_name"],
                                "time_slot":    f"{slot['start_time']}-{slot['end_time']}",
                                "subject_code": assignment["course_code"],
                                "subject_name": assignment["course_name"],
                                "teacher_name": assignment["teacher_name"],
                                "room_code":    room_code_by_id.get(room_id),
                                "batch":        batch
                            })
                            assigned_count += 1

                        record_teacher_hours(teacher_id, day, LAB_SESSION_SLOTS)
                        group_lab_days.add(day)
                        day_load[day] += 1
                        sessions_placed += 1
                        placed = True
                        break

                    if placed:
                        break

                if not placed:
                    break  # no day/room/teacher can fit another session this week

            if sessions_placed < LAB_SESSIONS_PER_WEEK:
                unmet_lab_sessions[assignment["course_code"]] = LAB_SESSIONS_PER_WEEK - sessions_placed
                conflicts.append({
                    "type": "lab",
                    "description": f"{assignment['course_name']}: only {sessions_placed}/{LAB_SESSIONS_PER_WEEK} lab sessions placed (teacher/room/day conflicts)"
                })

        # Theory scheduling below only handles non-lab assignments - labs are
        # fully scheduled above.
        assignments = theory_assignments

        # Build a schedule slot by slot
        # Strategy: round-robin across assignments, spreading evenly across the week
        # Each subject gets slots spread across different days where possible

        # First pass: track how many slots each assignment still needs, capped
        # at MAX_THEORY_SESSIONS_PER_WEEK regardless of the subject's own
        # hours_per_week (e.g. a subject with hours_per_week=5 still only
        # gets 3 classes/week).
        remaining = {i: min(a["hours_per_week"], MAX_THEORY_SESSIONS_PER_WEEK) for i, a in enumerate(assignments)}
        # Days each assignment has already been placed on for this group - used to
        # avoid scheduling the same subject twice in one day (e.g. Data Structures
        # on both Monday period 1 and Monday period 4). A repeat is only allowed
        # as a last resort, when every other subject for this slot is either done
        # or teacher-busy, so hours_per_week that don't fit into 5 distinct days
        # still get scheduled instead of silently dropped.
        subject_days_used: Dict[int, set] = {i: set() for i in range(len(assignments))}

        # Sort slots to spread across days (interleave days instead of filling one day at a time)
        # Reorder slots: slot 0 of each day, then slot 1 of each day, etc.
        slots_by_position: Dict[int, list] = {}
        for slot in available_slots:
            # group by start_time position within the day
            pos_key = slot["start_time"]
            if pos_key not in slots_by_position:
                slots_by_position[pos_key] = []
            slots_by_position[pos_key].append(slot)

        # Interleaved order: for each time position, go through all days
        interleaved_slots = []
        for pos_key in sorted(slots_by_position.keys()):
            interleaved_slots.extend(slots_by_position[pos_key])

        # Assign slots greedily, cycling through subjects
        slot_index = 0
        max_iterations = total_slots_available * len(assignments) * 2  # safety limit
        iterations = 0

        while slot_index < len(interleaved_slots) and iterations < max_iterations:
            iterations += 1
            slot = interleaved_slots[slot_index]
            slot_id = slot["id"]

            # Skip if group already has something this slot
            if slot_id in group_busy:
                slot_index += 1
                continue

            # Find the next assignment that still needs hours
            # Pick the one with the most remaining hours (greedy fill). A subject
            # is never placed twice on the same day for this group.
            day_of_week = slot["day_of_week"]
            best_idx = None
            best_remaining = 0
            for i, assignment in enumerate(assignments):
                if remaining[i] <= 0:
                    continue
                tid = assignment["tid"]
                # Check teacher not busy this slot
                if tid in teacher_busy and slot_id in teacher_busy[tid]:
                    conflicts.append({
                        "type": "teacher",
                        "description": f"Teacher {assignment['teacher_name']} busy at slot {slot_id}"
                    })
                    continue
                if not teacher_has_capacity(tid, day_of_week, 1):
                    conflicts.append({
                        "type": "teacher_overload",
                        "description": f"Teacher {assignment['teacher_name']} at max hours for this day/week"
                    })
                    continue
                if day_of_week in subject_days_used[i]:
                    continue
                if remaining[i] > best_remaining:
                    best_remaining = remaining[i]
                    best_idx = i

            if best_idx is None:
                # No assignment can go here (all teachers busy or all done)
                slot_index += 1
                continue

            assignment = assignments[best_idx]
            teacher_id = assignment["tid"]
            course_id  = assignment["course_id"]

            # Find a free non-lab room (theory classes never use a lab room)
            room_id = None
            for rid in theory_room_ids:
                if rid not in room_busy:
                    room_busy[rid] = set()
                if slot_id not in room_busy[rid]:
                    room_id = rid
                    break

            if not room_id:
                slot_index += 1
                continue

            # Schedule it
            cursor.execute('''
                INSERT INTO timetable_entries
                    (teacher_id,group_id,room_id,slot_id,course_id,semester,academic_year,status)
                VALUES (?,?,?,?,?,?,"2024-2025","scheduled")
            ''', (teacher_id, group_id, room_id, slot_id, course_id, request.semester))

            if teacher_id not in teacher_busy:
                teacher_busy[teacher_id] = set()
            teacher_busy[teacher_id].add(slot_id)
            room_busy[room_id].add(slot_id)
            group_busy.add(slot_id)
            subject_days_used[best_idx].add(day_of_week)
            record_teacher_hours(teacher_id, day_of_week, 1)

            entries_list.append({
                "day":          slot["day_name"],
                "time_slot":    f"{slot['start_time']}-{slot['end_time']}",
                "subject_code": assignment["course_code"],
                "subject_name": assignment["course_name"],
                "teacher_name": assignment["teacher_name"],
                "room_code":    room_code_by_id.get(room_id)
            })

            remaining[best_idx] -= 1
            assigned_count += 1
            slot_index += 1

            # If all done, stop
            if all(v <= 0 for v in remaining.values()):
                break

        timetable_data = json.dumps({
            "branch": request.branch, "year": request.year,
            "semester": request.semester, "section": request.section,
            "entries": entries_list, "days": DAYS, "time_slots": TIME_SLOTS,
            "generated_at": datetime.now().isoformat()
        })
        cursor.execute('''
            INSERT OR REPLACE INTO saved_timetables
                (branch,year,section,semester,timetable_data,generated_by,is_active)
            VALUES (?,?,?,?,?,?,1)
        ''', (request.branch, request.year, request.section, request.semester,
              timetable_data, current_user.get("user_id", 1)))

        for c in conflicts:
            cursor.execute(
                "INSERT INTO conflict_log (conflict_type,severity,conflict_description) VALUES (?,?,?)",
                (c["type"], "warning", c["description"]))

        conn.commit()

        unmet = {assignments[i]["course_code"]: remaining[i]
                 for i in range(len(assignments)) if remaining[i] > 0}
        if unmet_lab_sessions:
            unmet.update({f"{code} (lab sessions)": n for code, n in unmet_lab_sessions.items()})
        msg = f"Timetable generated: {assigned_count} slots scheduled"
        if unmet:
            msg += f". Could not fit: {unmet} (teacher conflicts or insufficient slots)"

        return {
            "success": True,
            "message": msg,
            "assignments_scheduled": assigned_count,
            "conflicts_detected": len(conflicts),
            "unmet_hours": unmet
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ============================================================
# TIMETABLE VIEW
# ============================================================
async def _get_timetable(branch: str, year: int, section: str, semester: int):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timetable_data FROM saved_timetables
            WHERE branch=? AND year=? AND section=? AND semester=? AND is_active=1
            ORDER BY generated_at DESC LIMIT 1
        ''', (branch, year, section, semester))
        saved = cursor.fetchone()
        if saved:
            data = json.loads(saved["timetable_data"])
            return _build_timetable_response(branch, year, section, semester, [], data.get("entries", []))

        group_code = f"{branch}{year}{section}"
        cursor.execute("SELECT id FROM student_groups WHERE group_code=?", (group_code,))
        group_row = cursor.fetchone()
        if not group_row:
            return _build_timetable_response(branch, year, section, semester, [])

        cursor.execute('''
            SELECT te.*, ts.day_name, ts.start_time, ts.end_time,
                   c.course_code, c.course_name, t.name as teacher_name, r.room_code
            FROM timetable_entries te
            JOIN time_slots ts ON te.slot_id=ts.id
            JOIN courses c ON te.course_id=c.id
            JOIN teachers t ON te.teacher_id=t.id
            JOIN rooms r ON te.room_id=r.id
            WHERE te.group_id=? AND te.semester=? AND te.status="scheduled"
            ORDER BY ts.day_of_week, ts.start_time
        ''', (group_row["id"], semester))
        entries = [dict(r) for r in cursor.fetchall()]
        return _build_timetable_response(branch, year, section, semester, entries)
    finally:
        conn.close()

@app.get("/api/timetable/view")
async def view_timetable_query(
    branch: str, year: int, section: str, semester: int = 1,
    current_user=Depends(get_current_user)
):
    return await _get_timetable(branch, year, section, semester)

@app.get("/api/timetable/view/{branch}/{year}/{section}")
async def view_timetable_path(
    branch: str, year: int, section: str, semester: int = 1,
    current_user=Depends(get_current_user)
):
    return await _get_timetable(branch, year, section, semester)


# ============================================================
# CONFLICTS
# ============================================================
@app.get("/api/conflicts/rooms")
async def scan_room_conflicts(_=Depends(require_admin)):
    """
    Safety-net scan, not part of the normal generation path: generate_timetable
    already prevents a room from ever being double-booked (it pre-loads every
    OTHER group's room+slot usage before assigning a new one), so this should
    always come back empty. It exists purely to surface it clearly if it ever
    doesn't - e.g. a future code change to the generator, or rows edited
    directly in the database outside the app.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT te.room_id, r.room_code, te.slot_id,
                   ts.day_name, ts.start_time, ts.end_time,
                   GROUP_CONCAT(DISTINCT sg.group_code) AS group_codes,
                   GROUP_CONCAT(DISTINCT c.course_code) AS course_codes
            FROM timetable_entries te
            JOIN rooms r ON te.room_id = r.id
            JOIN time_slots ts ON te.slot_id = ts.id
            JOIN student_groups sg ON te.group_id = sg.id
            JOIN courses c ON te.course_id = c.id
            WHERE te.status = "scheduled"
            GROUP BY te.room_id, te.slot_id
            HAVING COUNT(DISTINCT te.group_id) > 1
            ORDER BY ts.day_of_week, ts.start_time
        ''')
        conflicts = [dict(r) for r in cursor.fetchall()]
        for c in conflicts:
            c["group_codes"] = c["group_codes"].split(",") if c["group_codes"] else []
            c["course_codes"] = c["course_codes"].split(",") if c["course_codes"] else []
        return {"conflicts": conflicts, "count": len(conflicts)}
    finally:
        conn.close()

@app.get("/api/conflicts")
async def get_conflicts(resolved: bool = False, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conflict_log WHERE resolved=? ORDER BY created_at DESC", (1 if resolved else 0,))
        conflicts = [dict(r) for r in cursor.fetchall()]
        return {"conflicts": conflicts, "count": len(conflicts)}
    finally:
        conn.close()

@app.post("/api/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: int, request: ConflictResolveRequest, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE conflict_log SET resolved=1, resolved_at=CURRENT_TIMESTAMP WHERE id=?", (conflict_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Conflict not found")
        conn.commit()
        return {"success": True, "message": "Conflict resolved"}
    finally:
        conn.close()


# ============================================================
# RESET
# ============================================================
@app.post("/api/admin/reset-timetables")
async def reset_timetables(_=Depends(require_admin)):
    """
    Wipes every generated timetable entry across every branch/year/section, so
    every room and slot goes back to fully free and can be assigned again from
    scratch. Does not touch teachers, subjects, rooms, course assignments or
    student_groups - only the generated schedule itself (timetable_entries),
    the cached saved_timetables views of it, and conflict_log entries that
    were only ever about that now-cleared schedule.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM timetable_entries WHERE status="scheduled"')
        cleared = cursor.fetchone()[0]
        cursor.execute("DELETE FROM timetable_entries")
        cursor.execute("UPDATE saved_timetables SET is_active=0")
        cursor.execute("DELETE FROM conflict_log")
        conn.commit()
        return {
            "success": True,
            "message": f"Reset complete: {cleared} scheduled class(es) cleared. Every room and time slot is now free.",
            "cleared": cleared,
        }
    finally:
        conn.close()


# ============================================================
# STATS
# ============================================================
@app.get("/api/stats")
async def get_stats(_=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        stats = {}
        for key, table, where in [
            ("teachers",          "teachers",          "WHERE is_active=1"),
            ("groups",            "student_groups",    "WHERE is_active=1"),
            ("rooms",             "rooms",             "WHERE is_active=1"),
            ("courses",           "courses",           ""),
            ("subjects",          "subjects",          ""),
            ("timetable_entries", "timetable_entries", 'WHERE status="scheduled"'),
            ("conflicts",         "conflict_log",      "WHERE resolved=0"),
            ("saved_timetables",  "saved_timetables",  "WHERE is_active=1"),
        ]:
            cursor.execute(f"SELECT COUNT(*) FROM {table} {where}")
            stats[key] = cursor.fetchone()[0]
        return stats
    finally:
        conn.close()


# ============================================================
# HOLIDAYS
# ============================================================
@app.get("/api/holidays")
async def get_holidays():
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM holidays ORDER BY holiday_date")
        return {"holidays": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()

@app.post("/api/admin/holidays")
async def add_holiday(data: dict, _=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO holidays (holiday_name,holiday_date,is_optional,description) VALUES (?,?,?,?)",
            (data.get("name"), data.get("date"), data.get("is_optional", 0), data.get("description")))
        conn.commit()
        return {"success": True, "message": "Holiday added"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🎓 SGSITS Timetable API v4.0")
    print("=" * 60)
    print("📍 Server  : http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("=" * 60)
    print("🔐 Credentials:")
    print("   Admin   : admin   / admin123")
    print("   Teacher : teacher / teacher123")
    print("   Student : student / student123")
    print("=" * 60)
    print("📋 All frontend → backend routes:")
    print("   AddTeacher    → GET/POST /api/admin/teachers")
    print("   AddSubject    → GET /api/admin/teachers")
    print("                 → POST /api/admin/subjects")
    print("   AssignSubject → GET /api/admin/subjects?branch=&year=")
    print("                 → GET /api/admin/teachers")
    print("                 → POST /api/admin/subjects/assign")
    print("   GenerateTT    → POST /api/timetable/generate")
    print("                 → GET  /api/timetable/view?branch=&year=&section=&semester=")
    print("   ViewTimetable → GET  /api/timetable/view?branch=&year=&section=")
    print("   StudentDash   → GET  /api/timetable/view?branch=&year=&section=")
    print("   TeacherSched  → GET  /api/teachers/{id}/schedule")
    print("   AdminUsers    → GET  /api/admin/users")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)