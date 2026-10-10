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
import copy
import json
import random
from curriculum_data import build_subject_rows, BRANCHES as CURRICULUM_BRANCHES
import credit_system
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
# every lab course gets 3 sessions/week, each a 2-hour (2 consecutive slot) block.
# A lab course still appears on at most one day once (never twice on a day).
LAB_SESSIONS_PER_WEEK = 3
LAB_SESSION_SLOTS = 2

# No theory subject is scheduled more than this many periods/week, even if its
# hours_per_week says more - a scheduling policy, like the lab one above, not
# a per-subject configurable value.
MAX_THEORY_SESSIONS_PER_WEEK = 3

# Credit weighting: a theory subject worth more credits than the section's
# lowest-credit theory subject gets one extra period/week per extra credit, up
# to this many, on top of the cap above (so a subject 1 credit above gets 4
# periods, 2 or more above gets 5). Extras only use periods the section has
# free - see credit_bonus_sessions.
MAX_CREDIT_BONUS_SESSIONS = 2

# How many weekdays a section's labs normally spread over (generate_timetable),
# which keeps one weekday lab-free. A day holds 2 lab blocks, so this already
# fits 2 lab courses (6 sessions); a section with more labs than fit in these
# days automatically gets all 5 weekdays instead of losing sessions.
MAX_RECOMMENDED_LAB_SESSIONS_PER_WEEK = 4

def credit_bonus_sessions(theory_assignments: list, free_slots: int) -> list:
    """Extra periods/week for each theory assignment, by credits (see
    MAX_CREDIT_BONUS_SESSIONS). free_slots is how many periods the section
    still has after its labs and base theory periods; when that is fewer than
    the extras wanted, they are handed out one per subject per round, highest
    credits first (then the subject's own hours_per_week), so the heaviest
    subjects are served first and nobody gets a 2nd extra before the others
    got their 1st. Non-credit (audit) subjects never count as the lowest, and
    a subject with no weekly hours of its own (seminar, training) stays off
    the timetable whatever its credits."""
    credits = [(a.get("course_credits") or 0) if (a.get("hours_per_week") or 0) > 0 else 0
               for a in theory_assignments]
    extras = [0] * len(theory_assignments)
    credit_bearing = [c for c in credits if c > 0]
    if not credit_bearing:
        return extras
    lowest = min(credit_bearing)
    wanted = [max(0, min(MAX_CREDIT_BONUS_SESSIONS, c - lowest)) for c in credits]
    order = sorted(range(len(credits)),
                   key=lambda i: (-credits[i], -(theory_assignments[i].get("hours_per_week") or 0), i))
    for _ in range(MAX_CREDIT_BONUS_SESSIONS):
        for i in order:
            if free_slots <= 0:
                return extras
            if extras[i] < wanted[i]:
                extras[i] += 1
                free_slots -= 1
    return extras


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
    ("subjects",           "ltp",                 "TEXT"),
    ("subjects",           "credit_source",       "TEXT DEFAULT 'curriculum'"),

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
        # 17 more lecture rooms -> 40 theory rooms in all (plus 33 labs = 73
        # rooms), enough for every branch-year-section to keep its own home
        # classroom. Generic numbering continuing the ATC/LT pattern above -
        # rename to the real room numbers if they differ.
        ("ATC 308", "ATC 308", 60, "lecture", "ATC", 3, 1, 1, 1, 0, 0),
        ("ATC 401", "ATC 401", 60, "lecture", "ATC", 4, 1, 1, 1, 0, 0),
        ("ATC 402", "ATC 402", 60, "lecture", "ATC", 4, 1, 1, 1, 0, 0),
        ("ATC 403", "ATC 403", 60, "lecture", "ATC", 4, 1, 1, 1, 0, 0),
        ("ATC 404", "ATC 404", 60, "lecture", "ATC", 4, 1, 1, 1, 0, 0),
        ("ATC 405", "ATC 405", 60, "lecture", "ATC", 4, 1, 1, 1, 0, 0),
        ("ATC 406", "ATC 406", 60, "lecture", "ATC", 4, 1, 1, 1, 0, 0),
        ("ATC 407", "ATC 407", 60, "lecture", "ATC", 4, 1, 1, 1, 0, 0),
        ("ATC 408", "ATC 408", 60, "lecture", "ATC", 4, 1, 1, 1, 0, 0),
        ("ATC 501", "ATC 501", 60, "lecture", "ATC", 5, 1, 1, 1, 0, 0),
        ("ATC 502", "ATC 502", 60, "lecture", "ATC", 5, 1, 1, 1, 0, 0),
        ("ATC 503", "ATC 503", 60, "lecture", "ATC", 5, 1, 1, 1, 0, 0),
        ("ATC 504", "ATC 504", 60, "lecture", "ATC", 5, 1, 1, 1, 0, 0),
        ("ATC 505", "ATC 505", 60, "lecture", "ATC", 5, 1, 1, 1, 0, 0),
        ("ATC 506", "ATC 506", 60, "lecture", "ATC", 5, 1, 1, 1, 0, 0),
        ("LT 501", "LT 501", 80, "lecture", "LT", 5, 1, 1, 1, 0, 0),
        ("LT 502", "LT 502", 80, "lecture", "LT", 5, 1, 1, 1, 0, 0),
        ("LB01", "Lab 01", 40, "lab", "Lab Block", 1, 1, 0, 0, 1, 1),
        ("LB02", "Lab 02", 40, "lab", "Lab Block", 1, 1, 0, 0, 1, 1),
        ("LB03", "Lab 03", 40, "lab", "Lab Block", 1, 1, 0, 0, 1, 1),
    ]:
        cursor.execute(
            "INSERT OR IGNORE INTO rooms (room_code,room_name,capacity,room_type,building,floor,has_projector,has_whiteboard,has_ac,has_computers,is_lab,is_active) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
            (code, name, cap, rtype, building, floor, proj, board, ac, comp, is_lab))

    # Department labs: with only the 3 common Lab Block rooms, every section
    # in the institute competed for the same 3 rooms and later sections were
    # left with half their lab sessions unplaced. Each department gets its own
    # 3 labs (building = branch code, which generate_timetable uses to prefer a
    # section's own department labs). Generic names - SGSITS's real lab room
    # numbers weren't available; rename/add/deactivate them as needed.
    for branch in CURRICULUM_BRANCHES:
        for n in (1, 2, 3):
            cursor.execute(
                "INSERT OR IGNORE INTO rooms (room_code,room_name,capacity,room_type,building,floor,has_projector,has_whiteboard,has_ac,has_computers,is_lab,is_active) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
                (f"{branch} LAB-{n}", f"{branch} Department Lab {n}", 30, "lab", branch, 1, 1, 1, 0, 1, 1))

    # Retire the old default room set (superseded by ATC/LT/LB above) without
    # deleting the rows outright, so historical timetable_entries referencing
    # them by room_id don't dangle.
    cursor.execute(
        "UPDATE rooms SET is_active=0 WHERE room_code IN ('R101','R102','R201','LAB1','LAB2','LAB3','AUD1')"
    )
    conn.commit()


DEFAULT_SECTIONED_BRANCHES = ("CSE", "IT")  # matches the old hard-coded frontend rule


def sync_class_config(conn):
    """
    Makes sure every branch x year has a class_config row. New rows default
    to the old behaviour (only CSE and IT divided into sections). Any class
    that already has a section other than "A" in student_groups is marked as
    sectioned, so existing data is never hidden. Runs on every startup.
    """
    cursor = conn.cursor()
    for branch in CURRICULUM_BRANCHES:
        for year in (1, 2, 3, 4):
            cursor.execute("INSERT OR IGNORE INTO class_config (branch, year, has_sections) VALUES (?,?,?)",
                           (branch, year, 1 if branch in DEFAULT_SECTIONED_BRANCHES else 0))
            sections = [s for s in class_sections(conn, branch, year) if s["section"] != "A"]
            if sections:
                cursor.execute("UPDATE class_config SET has_sections=1 WHERE branch=? AND year=?", (branch, year))
    conn.commit()


def class_sections(conn, branch: str, year: int):
    """Every section (student_group) of one class, A first."""
    prefix = f"{branch}{year}"
    rows = conn.execute('''
        SELECT sg.id, sg.group_code, sg.student_count, sg.room_id, r.room_code
        FROM student_groups sg LEFT JOIN rooms r ON r.id = sg.room_id
        WHERE sg.department=? AND sg.group_code LIKE ? AND sg.is_active=1
        ORDER BY sg.group_code
    ''', (branch, prefix + "%")).fetchall()
    return [{"id": r["id"], "group_code": r["group_code"], "section": r["group_code"][len(prefix):],
             "student_count": r["student_count"], "home_room": r["room_code"], "room_id": r["room_id"]}
            for r in rows if r["group_code"][len(prefix):].isalpha()]


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


def backfill_subject_credits(conn):
    """
    The SGSITS credit system (credit_system.py) corrected many curriculum
    credit values (e.g. audit courses -> 0, L3-T1 cores -> 4). Subjects
    already loaded from curriculum_data.py keep their old credits, so this
    re-syncs credits on every row whose code AND name still match the
    curriculum - a row an admin renamed/re-purposed under a curriculum code
    is left alone, and so is any row whose credits an admin set by hand
    (credit_source 'manual' / 'preset'). Runs on every startup; a no-op once
    caught up.
    """
    cursor = conn.cursor()
    updated = 0
    for code, name, _b, _y, _sem, credits, _hours, _is_lab, _is_elective in build_subject_rows():
        cursor.execute(
            "UPDATE subjects SET credits=? WHERE code=? AND lower(trim(name))=? AND credits!=? "
            "AND COALESCE(credit_source, 'curriculum')='curriculum'",
            (credits, code, name.strip().lower(), credits))
        updated += cursor.rowcount
        cursor.execute(
            "UPDATE courses SET credits=? WHERE course_code=? AND lower(trim(course_name))=? AND credits!=? "
            "AND course_code IN (SELECT code FROM subjects WHERE COALESCE(credit_source, 'curriculum')='curriculum')",
            (credits, code, name.strip().lower(), credits))
    conn.commit()
    if updated:
        print(f"✅ Backfilled credits on {updated} existing subject(s) to the SGSITS credit system")


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
        ltp TEXT,
        credit_source TEXT DEFAULT 'curriculum',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id),
        FOREIGN KEY (teacher2_id) REFERENCES teachers(id)
    )''')

    # Whether a class (branch + year) is taught as one whole class or divided
    # into sections A, B, C... A class without sections is stored as a single
    # student_group with section "A", so everything downstream (assignments,
    # generation, views) works the same either way.
    cursor.execute('''CREATE TABLE IF NOT EXISTS class_config (
        branch TEXT NOT NULL,
        year INTEGER NOT NULL,
        has_sections INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (branch, year)
    )''')

    # Credit limits (see credit_system.DEFAULT_POLICY) - one row per limit,
    # editable by admins; missing keys fall back to the defaults.
    cursor.execute('''CREATE TABLE IF NOT EXISTS credit_policy (
        key TEXT PRIMARY KEY,
        value INTEGER NOT NULL
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
    sync_class_config(conn)
    dedupe_course_assignments(conn)
    backfill_subject_electives(conn)
    backfill_subject_credits(conn)
    dedupe_subjects_by_name(conn)

    _insert_sample_data(cursor)
    conn.commit()
    ensure_extra_cse_teachers(conn)

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


EXTRA_CSE_TEACHERS = [
    ("Dr. Ashok Malviya",    "ashok.malviya@sgsits.edu",    "Operating Systems"),
    ("Dr. Rekha Solanki",    "rekha.solanki@sgsits.edu",    "Computer Networks"),
    ("Prof. Manish Jain",    "manish.jain@sgsits.edu",      "Software Engineering"),
    ("Prof. Pooja Agrawal",  "pooja.agrawal@sgsits.edu",    "Discrete Mathematics"),
    ("Prof. Nitin Bhatt",    "nitin.bhatt@sgsits.edu",      "Computer Organization"),
    ("Prof. Shweta Mishra",  "shweta.mishra@sgsits.edu",    "Programming Lab"),
    ("Dr. Harish Chandra",   "harish.chandra@sgsits.edu",   "Digital Electronics"),
    ("Prof. Divya Saxena",   "divya.saxena@sgsits.edu",     "Engineering Economics"),
    ("Prof. Gaurav Pandey",  "gaurav.pandey@sgsits.edu",    "Microprocessors"),
    ("Prof. Kirti Vyas",     "kirti.vyas@sgsits.edu",       "Professional Ethics"),
    ("Prof. Sameer Qureshi", "sameer.qureshi@sgsits.edu",   "Electronics Workshop"),
    ("Prof. Lata Chouhan",   "lata.chouhan@sgsits.edu",     "Data Structures Lab"),
]

# 30 more, generated from name pools so every CSE section (1A, 1B, 2A, 2B, 3A,
# 4A ... about 8 teachers each) can have completely separate teachers.
_FIRST = ["Aarti", "Rohit", "Sneha", "Vivek", "Anita", "Suresh", "Neelam", "Tarun", "Ritu", "Mohit",
          "Payal", "Sachin", "Komal", "Deepak", "Monika", "Yogesh", "Rashmi", "Ajay", "Seema", "Alok",
          "Preeti", "Naveen", "Swati", "Rajesh", "Nidhi", "Ankit", "Shilpa", "Pankaj", "Garima", "Varun"]
_LAST = ["Tripathi", "Chaturvedi", "Dubey", "Kulkarni", "Bansal", "Parmar", "Rathore", "Mehta", "Jha", "Shrivastava",
         "Kapoor", "Nair", "Bhargava", "Dwivedi", "Khare", "Patidar", "Soni", "Tomar", "Vaidya", "Awasthi",
         "Chourasia", "Dhakad", "Gour", "Holkar", "Iyer", "Joshi", "Kaushal", "Lodhi", "Mandloi", "Nagar"]
_SPEC = ["Data Structures", "Algorithms", "DBMS", "Operating Systems", "Computer Networks", "Compiler Design",
         "Machine Learning", "Web Technology", "Software Engineering", "Theory of Computation"]
for _i in range(30):
    EXTRA_CSE_TEACHERS.append((
        f"Prof. {_FIRST[_i]} {_LAST[_i]}",
        f"{_FIRST[_i].lower()}.{_LAST[_i].lower()}@sgsits.edu",
        _SPEC[_i % len(_SPEC)]))


def ensure_extra_cse_teachers(conn):
    """Adds spare CSE teachers so a second CSE section can be given its own
    teachers instead of competing with section A for the same ones.
    Idempotent (email is unique)."""
    cursor = conn.cursor()
    for name, email, spec in EXTRA_CSE_TEACHERS:
        cursor.execute(
            "INSERT OR IGNORE INTO teachers (name,email,department,designation,specialization,max_hours_per_day,max_hours_per_week,is_active) VALUES (?,?,?,?,?,6,24,1)",
            (name, email, "CSE", "Assistant Professor", spec))
    conn.commit()


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
    ltp: Optional[str] = None
    # Save even if it breaks a credit limit (the admin confirmed the warning).
    force: Optional[bool] = False

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
            # Parallel batch labs put two entries in one period (E1 in one
            # lab, E2 in another) - show both instead of overwriting.
            if matrix[day][slot_key] != "—":
                matrix[day][slot_key] += "<br>" + cell
            else:
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
        ltp = subject.ltp or None
        if ltp:
            try:
                subject.credits = credit_system.credits_from_ltp(ltp)
                ltp = "-".join(str(x) for x in credit_system.parse_ltp(ltp))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        credits = subject.credits or 0
        raise_if_violations(
            credit_violations(conn, subject.branch, subject_credits=credits, extra=(subject.semester, credits)),
            bool(subject.force))
        cursor.execute(
            "INSERT INTO subjects (code,name,branch,year,semester,credits,hours_per_week,is_lab,is_elective,teacher_id,teacher2_id,ltp,credit_source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'manual')",
            (subject.code, subject.name, subject.branch, subject.year, subject.semester,
             credits, subject.hours_per_week, subject.is_lab, subject.is_elective,
             subject.teacher_id, subject.teacher2_id, ltp))
        subject_id = cursor.lastrowid

        cursor.execute("SELECT id FROM courses WHERE course_code=?", (subject.code,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO courses (course_code,course_name,credits,hours_per_week,is_lab,is_elective,department,semester) VALUES (?,?,?,?,?,?,?,?)",
                (subject.code, subject.name, credits, subject.hours_per_week,
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

        # Separate check: a day holds at most 2 two-hour lab blocks (morning +
        # afternoon), so a section's lab sessions can't exceed 2 x weekdays.
        # Any mix inside that works - 6 subjects + 1 lab, 5 + 2, 4 + 2, 4 + 3.
        lab_course_count = sum(1 for r in course_rows if r["is_lab"])
        theory_count = subject_count - lab_course_count
        total_lab_sessions_needed = lab_course_count * LAB_SESSIONS_PER_WEEK
        max_lab_sessions = 2 * len(DAYS)
        lab_warning = None
        if total_lab_sessions_needed > max_lab_sessions:
            lab_warning = (
                f"{branch} Year {year} Sem {subject['semester']} now has {lab_course_count} lab course(s), "
                f"needing {total_lab_sessions_needed} two-hour lab sessions/week ({LAB_SESSIONS_PER_WEEK} each), "
                f"but a week fits at most {max_lab_sessions} (2 per day). Keep it to "
                f"{max_lab_sessions // LAB_SESSIONS_PER_WEEK} labs or fewer per section."
            )

        return {
            "success": True,
            "message": f"Subject assigned to section {section} successfully",
            "warning": warning,
            "lab_warning": lab_warning,
            "layout": f"{theory_count} subject(s) + {lab_course_count} lab(s), "
                      f"{total_hours_needed}/{total_available_slots} periods per week",
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

# ============================================================
# CREDIT SYSTEM (SGSITS CBCS) - read-only, any logged-in user
# ============================================================
@app.get("/api/credits/overview")
async def get_credit_overview(_=Depends(get_current_user)):
    """Semester-by-semester credit totals for every branch, side by side."""
    return {"branches": credit_system.branch_overview()}

@app.get("/api/credits/scheme/{branch}")
async def get_credit_scheme(branch: str, _=Depends(get_current_user)):
    """Full 8-semester credit scheme (every subject + its credits) for one branch."""
    branch = branch.upper()
    if branch not in CURRICULUM_BRANCHES:
        raise HTTPException(status_code=404, detail=f"Unknown branch '{branch}'")
    return credit_system.credit_scheme(branch)

@app.get("/api/credits/grading")
async def get_grading_rules(_=Depends(get_current_user)):
    return {
        "grades": [{"grade": g, "min_marks": lo, "max_marks": hi, "grade_point": gp, "description": d}
                   for g, lo, hi, gp, d in credit_system.GRADES],
        "divisions": [{"min_cgpa": t, "division": label} for t, label in credit_system.DIVISIONS],
        "min_cgpa_for_degree": credit_system.MIN_CGPA_FOR_DEGREE,
        "assessment": credit_system.ASSESSMENT,
        "marks_scheme": credit_system.MARKS_SCHEME,
        "passing_rules": credit_system.PASSING_RULES,
        "categories": credit_system.CATEGORY_LABELS,
        "rules": credit_system.RULES,
    }

@app.post("/api/credits/calculate")
async def calculate_gpa(data: dict, _=Depends(get_current_user)):
    """
    Body: {"semesters": [[{"credits": 4, "grade": "A"}, ...], ...]}
    Returns each semester's SGPA plus the overall CGPA and division.
    """
    semesters = data.get("semesters") or []
    try:
        per_sem = []
        for entries in semesters:
            value, registered, earned = credit_system.sgpa(entries)
            per_sem.append({"sgpa": value, "credits_registered": registered, "credits_earned": earned})
        overall = credit_system.cgpa(semesters)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "semesters": per_sem,
        "cgpa": overall,
        "division": credit_system.division_for(overall),
        "eligible_for_degree": overall >= credit_system.MIN_CGPA_FOR_DEGREE,
    }


# ------------------------------------------------------------
# Credit management: live credits from the `subjects` table, editable by
# admins, with SGSITS credit limits enforced on every change. Every write
# re-totals the affected branch and refuses (409) anything that would push
# a subject, semester, or the 4-year total past the policy - unless the
# request says force=true (the admin saw the warning and confirmed).
# ------------------------------------------------------------
def get_credit_policy(conn) -> dict:
    policy = dict(credit_system.DEFAULT_POLICY)
    for r in conn.execute("SELECT key, value FROM credit_policy").fetchall():
        if r["key"] in policy:
            policy[r["key"]] = r["value"]
    return policy


def branch_semester_totals(conn, branch: str, overrides: Optional[Dict[int, int]] = None,
                           extra: Optional[tuple] = None) -> Dict[int, int]:
    """{semester: credits} for a branch from the live subjects table.
    overrides: {subject_id: new_credits} applied before totalling.
    extra: (semester, credits) for a subject about to be inserted."""
    overrides = overrides or {}
    totals: Dict[int, int] = {}
    for r in conn.execute("SELECT id, semester, credits FROM subjects WHERE branch=?", (branch,)).fetchall():
        credits = overrides.get(r["id"], r["credits"] or 0)
        totals[r["semester"]] = totals.get(r["semester"], 0) + credits
    if extra:
        totals[extra[0]] = totals.get(extra[0], 0) + extra[1]
    return totals


def credit_violations(conn, branch: str, subject_credits: Optional[int] = None,
                      overrides: Optional[Dict[int, int]] = None, extra: Optional[tuple] = None):
    """Limit violations caused by a proposed change (overrides / extra as in
    branch_semester_totals), judged only on the semesters it touches."""
    policy = get_credit_policy(conn)
    before = branch_semester_totals(conn, branch)
    after = branch_semester_totals(conn, branch, overrides=overrides, extra=extra)
    touched = {extra[0]} if extra else set()
    if overrides:
        marks = ",".join("?" * len(overrides))
        touched |= {r["semester"] for r in conn.execute(
            f"SELECT semester FROM subjects WHERE id IN ({marks})", list(overrides)).fetchall()}
    return credit_system.check_policy(policy, after, subject_credits, semesters=touched,
                                      previous=before)


def raise_if_violations(violations, force: bool):
    if violations and not force:
        raise HTTPException(status_code=409, detail={
            "message": "This change breaks the SGSITS credit limits. Send force=true to save anyway.",
            "violations": violations,
        })


@app.get("/api/credits/policy")
async def get_policy(_=Depends(get_current_user)):
    conn = get_db()
    try:
        return {"policy": get_credit_policy(conn), "defaults": credit_system.DEFAULT_POLICY,
                "labels": credit_system.POLICY_LABELS}
    finally:
        conn.close()


@app.put("/api/admin/credits/policy")
async def update_policy(data: dict, _=Depends(require_admin)):
    """Body: any subset of the policy keys, e.g. {"semester_max_credits": 24}.
    {"reset": true} restores every limit to the SGSITS defaults."""
    conn = get_db()
    try:
        if data.get("reset"):
            conn.execute("DELETE FROM credit_policy")
        else:
            new = get_credit_policy(conn)
            for key, value in data.items():
                if key not in credit_system.DEFAULT_POLICY:
                    raise HTTPException(status_code=400, detail=f"Unknown limit '{key}'")
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    raise HTTPException(status_code=400, detail=f"'{key}' must be a whole number")
                if value < 0:
                    raise HTTPException(status_code=400, detail=f"'{key}' cannot be negative")
                new[key] = value
            if new["semester_min_credits"] > new["semester_max_credits"]:
                raise HTTPException(status_code=400, detail="Min credits per semester cannot exceed the max")
            if new["program_min_credits"] > new["program_max_credits"]:
                raise HTTPException(status_code=400, detail="Min total credits cannot exceed the max")
            for key, value in new.items():
                conn.execute("INSERT INTO credit_policy (key, value) VALUES (?, ?) "
                             "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        conn.commit()
        return {"success": True, "policy": get_credit_policy(conn)}
    finally:
        conn.close()


@app.get("/api/credits/live/{branch}")
async def get_live_credits(branch: str, _=Depends(get_current_user)):
    """Credits as they are in the database right now (what admins edit),
    grouped by semester, with each subject's SGSITS preset and the branch's
    status against the credit limits."""
    branch = branch.upper()
    conn = get_db()
    try:
        policy = get_credit_policy(conn)
        rows = conn.execute(
            "SELECT id, code, name, year, semester, credits, hours_per_week, is_lab, is_elective, ltp, credit_source "
            "FROM subjects WHERE branch=? ORDER BY semester, code", (branch,)).fetchall()
        semesters: Dict[int, dict] = {}
        for r in rows:
            s = semesters.setdefault(r["semester"], {"semester": r["semester"], "year": r["year"], "subjects": [], "total_credits": 0})
            credits = r["credits"] or 0
            s["subjects"].append({
                "id": r["id"], "code": r["code"], "name": r["name"], "credits": credits,
                "hours_per_week": r["hours_per_week"], "is_lab": bool(r["is_lab"]),
                "is_elective": bool(r["is_elective"]), "ltp": r["ltp"],
                "credit_source": r["credit_source"] or "curriculum",
                "category": credit_system.categorize(r["name"], r["year"], bool(r["is_lab"]), bool(r["is_elective"])),
                "curriculum_default": credit_system.curriculum_default(r["code"], r["name"]),
                "sgsits_preset": credit_system.sgsits_preset(r["name"], bool(r["is_lab"]), r["hours_per_week"]),
            })
            s["total_credits"] += credits
        totals = {k: v["total_credits"] for k, v in semesters.items()}
        return {
            "branch": branch,
            "policy": policy,
            "status": credit_system.policy_status(policy, totals),
            "semesters": [semesters[k] for k in sorted(semesters)],
        }
    finally:
        conn.close()


@app.get("/api/credits/suggest")
async def suggest_credits(name: str, is_lab: bool = False, hours_per_week: Optional[int] = None, _=Depends(get_current_user)):
    """SGSITS preset credits for a subject name - used by Add Subject to pre-fill credits."""
    return {"suggestion": credit_system.sgsits_preset(name, is_lab, hours_per_week)}


def _set_subject_credits(conn, subject_id: int, credits: int, ltp: Optional[str], source: str, force: bool):
    row = conn.execute("SELECT id, code, name, branch FROM subjects WHERE id=?", (subject_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Subject not found")
    violations = credit_violations(conn, row["branch"], subject_credits=credits, overrides={subject_id: credits})
    raise_if_violations(violations, force)
    conn.execute("UPDATE subjects SET credits=?, ltp=?, credit_source=? WHERE id=?", (credits, ltp, source, subject_id))
    conn.execute("UPDATE courses SET credits=? WHERE course_code=?", (credits, row["code"]))
    conn.commit()
    return {"success": True, "id": subject_id, "name": row["name"], "credits": credits, "ltp": ltp,
            "credit_source": source, "warnings": violations}


@app.put("/api/admin/subjects/{subject_id}/credits")
async def assign_subject_credits(subject_id: int, data: dict, _=Depends(require_admin)):
    """
    Assign credits to one subject. Body: {"credits": 4} or {"ltp": "3-1-2"}
    (credits then come from the SGSITS rule L + T + P/2), plus optional
    "force": true to save past a credit limit.
    """
    ltp = data.get("ltp") or None
    try:
        if ltp:
            credits = credit_system.credits_from_ltp(ltp)
            ltp = "-".join(str(x) for x in credit_system.parse_ltp(ltp))
        elif data.get("credits") is not None:
            credits = int(data["credits"])
        else:
            raise HTTPException(status_code=400, detail="Send 'credits' or 'ltp'")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    conn = get_db()
    try:
        return _set_subject_credits(conn, subject_id, credits, ltp, "manual", bool(data.get("force")))
    finally:
        conn.close()


@app.delete("/api/admin/subjects/{subject_id}/credits")
async def remove_subject_credits(subject_id: int, _=Depends(require_admin)):
    """Remove a subject's credits (sets them to 0 - it stays in the timetable
    as a non-credit/audit course). Never breaks an upper limit, so no force."""
    conn = get_db()
    try:
        return _set_subject_credits(conn, subject_id, 0, None, "manual", True)
    finally:
        conn.close()


@app.post("/api/admin/subjects/{subject_id}/credits/reset")
async def reset_subject_credits(subject_id: int, data: Optional[dict] = None, _=Depends(require_admin)):
    """Put a subject back on its SGSITS default: the curriculum value if this
    is a built-in curriculum subject, otherwise the SGSITS preset."""
    data = data or {}
    conn = get_db()
    try:
        row = conn.execute("SELECT code, name, is_lab, hours_per_week FROM subjects WHERE id=?", (subject_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Subject not found")
        default = credit_system.curriculum_default(row["code"], row["name"])
        if default is not None:
            return _set_subject_credits(conn, subject_id, default, None, "curriculum", bool(data.get("force")))
        preset = credit_system.sgsits_preset(row["name"], bool(row["is_lab"]), row["hours_per_week"])
        if not preset:
            raise HTTPException(status_code=404, detail="No SGSITS default is known for this subject")
        return _set_subject_credits(conn, subject_id, preset["credits"], preset["ltp"], "preset", bool(data.get("force")))
    finally:
        conn.close()


@app.post("/api/admin/credits/apply-presets")
async def apply_credit_presets(data: dict, _=Depends(require_admin)):
    """
    Pre-assign SGSITS preset credits to a branch's subjects in one go.
    Body: {"branch": "IT", "semester": 5 (optional), "include_manual": false,
           "dry_run": true, "force": false}
    dry_run returns the proposed changes and resulting limit violations
    without saving. Subjects an admin already edited by hand are skipped
    unless include_manual is true.
    """
    branch = (data.get("branch") or "").upper()
    if not branch:
        raise HTTPException(status_code=400, detail="branch is required")
    semester = data.get("semester")
    conn = get_db()
    try:
        query = "SELECT id, code, name, semester, credits, is_lab, hours_per_week, ltp, credit_source FROM subjects WHERE branch=?"
        params: list = [branch]
        if semester:
            query += " AND semester=?"
            params.append(int(semester))
        changes = []
        for r in conn.execute(query, params).fetchall():
            if (r["credit_source"] == "manual") and not data.get("include_manual"):
                continue
            preset = credit_system.sgsits_preset(r["name"], bool(r["is_lab"]), r["hours_per_week"])
            # A change = different credits, or the same credits but no L-T-P
            # recorded yet (curriculum subjects only ever stored credits).
            if preset and (preset["credits"] != (r["credits"] or 0) or not r["ltp"]):
                changes.append({"id": r["id"], "code": r["code"], "name": r["name"], "semester": r["semester"],
                                "from": r["credits"] or 0, "to": preset["credits"], "ltp": preset["ltp"],
                                "ltp_from": r["ltp"], "source": preset["source"]})
        overrides = {c["id"]: c["to"] for c in changes}
        violations = credit_violations(conn, branch, overrides=overrides)
        if data.get("dry_run", True):
            return {"dry_run": True, "changes": changes, "violations": violations}
        raise_if_violations(violations, bool(data.get("force")))
        for c in changes:
            conn.execute("UPDATE subjects SET credits=?, ltp=?, credit_source='preset' WHERE id=?", (c["to"], c["ltp"], c["id"]))
            conn.execute("UPDATE courses SET credits=? WHERE course_code=?", (c["to"], c["code"]))
        conn.commit()
        return {"dry_run": False, "applied": len(changes), "changes": changes, "violations": violations}
    finally:
        conn.close()

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
        if section != "A":
            # A second section means this class is now divided into sections.
            cursor.execute("INSERT INTO class_config (branch, year, has_sections) VALUES (?,?,1) "
                           "ON CONFLICT(branch, year) DO UPDATE SET has_sections=1", (branch, year))
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

# ------------------------------------------------------------
# Classes with / without sections. A class = branch + year. "Without
# sections" = one whole class (stored as the single section "A");
# "with sections" = divided into A, B, C... each with its own subjects'
# teachers, timetable and home classroom.
# ------------------------------------------------------------
def _class_info(conn, branch: str, year: int):
    row = conn.execute("SELECT has_sections FROM class_config WHERE branch=? AND year=?", (branch, year)).fetchone()
    has_sections = bool(row["has_sections"]) if row else branch in DEFAULT_SECTIONED_BRANCHES
    return {"branch": branch, "year": year, "has_sections": has_sections,
            "sections": class_sections(conn, branch, year)}


def _ensure_section(conn, branch: str, year: int, section: str, student_count: int = 60, room_id=None):
    group_code = f"{branch}{year}{section}"
    if conn.execute("SELECT id FROM student_groups WHERE group_code=?", (group_code,)).fetchone():
        return False
    year_label = {1: "1st Year", 2: "2nd Year", 3: "3rd Year", 4: "4th Year"}.get(year, f"Year {year}")
    conn.execute(
        "INSERT INTO student_groups (group_code,group_name,semester,department,academic_year,student_count,room_id,is_active) VALUES (?,?,?,?,?,?,?,1)",
        (group_code, f"{branch} {year_label} Section {section}", year * 2 - 1, branch, "2024-2025", student_count, room_id))
    return True


@app.get("/api/classes")
async def list_classes(branch: Optional[str] = None, year: Optional[int] = None, _=Depends(get_current_user)):
    """Every class (branch x year) with whether it has sections and which ones."""
    conn = get_db()
    try:
        branches = [branch.upper()] if branch else list(CURRICULUM_BRANCHES)
        years = [year] if year else [1, 2, 3, 4]
        return {"classes": [_class_info(conn, b, y) for b in branches for y in years]}
    finally:
        conn.close()


@app.put("/api/admin/classes")
async def configure_class(data: dict, _=Depends(require_admin)):
    """
    Body: {"branch": "EE", "year": 2, "has_sections": true,
           "sections": ["A", "B"] (optional), "student_count": 60 (optional)}
    has_sections=false makes it one whole class - refused (409) while
    sections other than A still exist, so nobody's assignments or timetable
    silently disappear; remove those sections first. has_sections=true
    creates any listed sections that don't exist yet (default A and B).
    """
    branch = (data.get("branch") or "").upper()
    year = data.get("year")
    if branch not in CURRICULUM_BRANCHES or not isinstance(year, int) or not 1 <= year <= 4:
        raise HTTPException(status_code=422, detail="Valid branch and year (1-4) are required")
    has_sections = bool(data.get("has_sections"))
    student_count = int(data.get("student_count") or 60)
    conn = get_db()
    try:
        existing = class_sections(conn, branch, year)
        if not has_sections:
            extra = [s["section"] for s in existing if s["section"] != "A"]
            if extra:
                raise HTTPException(status_code=409, detail=(
                    f"{branch} year {year} still has section(s) {', '.join(extra)}. "
                    f"Remove them before making it a single class."))
            _ensure_section(conn, branch, year, "A", student_count)
        else:
            wanted = [str(s).strip().upper() for s in (data.get("sections") or []) if str(s).strip()]
            if not wanted and len(existing) < 2:
                wanted = ["A", "B"]
            bad = [s for s in wanted if not s.isalpha() or len(s) > 2]
            if bad:
                raise HTTPException(status_code=422, detail=f"Section names must be letters, e.g. A, B, C (got {', '.join(bad)})")
            for s in wanted:
                _ensure_section(conn, branch, year, s, student_count)
        conn.execute("INSERT INTO class_config (branch, year, has_sections) VALUES (?,?,?) "
                     "ON CONFLICT(branch, year) DO UPDATE SET has_sections=excluded.has_sections",
                     (branch, year, int(has_sections)))
        conn.commit()
        return {"success": True, **_class_info(conn, branch, year)}
    finally:
        conn.close()


@app.put("/api/admin/sections/{branch}/{year}/{section}/room")
async def set_section_room(branch: str, year: int, section: str, data: dict, _=Depends(require_admin)):
    """
    Set (or clear, with room_id null) the home classroom of one section - or
    of a whole class, which is section "A". Creates the section if it doesn't
    exist yet. Only lecture rooms are allowed (labs are picked per lab
    session from the department's labs). Warns, without blocking, when the
    room is already another section's home. Takes effect on the next
    generation of that section's timetable.
    """
    branch, section = branch.upper(), section.upper()
    room_id = data.get("room_id")
    conn = get_db()
    try:
        room_code = None
        if room_id is not None:
            room = conn.execute("SELECT room_code, is_lab FROM rooms WHERE id=? AND is_active=1", (room_id,)).fetchone()
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")
            if room["is_lab"]:
                raise HTTPException(status_code=422, detail=f"{room['room_code']} is a lab - pick a lecture room as the classroom")
            room_code = room["room_code"]
        _ensure_section(conn, branch, year, section)
        group_code = f"{branch}{year}{section}"
        conn.execute("UPDATE student_groups SET room_id=? WHERE group_code=?", (room_id, group_code))
        conn.commit()
        warning = None
        if room_id is not None:
            others = [r["group_code"] for r in conn.execute(
                "SELECT group_code FROM student_groups WHERE room_id=? AND is_active=1 AND group_code!=?",
                (room_id, group_code)).fetchall()]
            if others:
                warning = (f"{room_code} is also the classroom of {', '.join(others)} - the generator "
                           f"will move clashing periods to another free room.")
        return {"success": True, "group_code": group_code, "home_room": room_code, "warning": warning}
    finally:
        conn.close()


@app.delete("/api/admin/sections/{group_code}")
async def delete_section(group_code: str, _=Depends(require_admin)):
    """Remove one section with its teacher assignments and generated
    timetables. Not reversible - the frontend confirms first."""
    conn = get_db()
    try:
        row = conn.execute("SELECT id, department FROM student_groups WHERE group_code=?", (group_code,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Section {group_code} not found")
        branch = row["department"]
        rest = group_code[len(branch):]
        year, section = int(rest[0]), rest[1:]
        conn.execute("DELETE FROM timetable_entries WHERE group_id=?", (row["id"],))
        conn.execute("DELETE FROM course_assignments WHERE group_id=?", (row["id"],))
        conn.execute("DELETE FROM saved_timetables WHERE branch=? AND year=? AND section=?", (branch, year, section))
        conn.execute("DELETE FROM student_groups WHERE id=?", (row["id"],))
        conn.commit()
        return {"success": True, "message": f"Section {group_code} removed", **_class_info(conn, branch, year)}
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
def _assign_own_teachers(cursor, group_id: int, department: str, source: list) -> None:
    """Copy `source` course assignments onto `group_id`, giving every course a
    different teacher than the source section's, and a different teacher from
    each other wherever the department has enough teachers."""
    seen_courses = set()
    courses = []
    for a in source:
        if a["course_id"] not in seen_courses:
            seen_courses.add(a["course_id"])
            courses.append(a)

    source_teachers = {a["tid"] for a in courses}
    cursor.execute("SELECT teacher_id, COUNT(*) AS n FROM course_assignments GROUP BY teacher_id")
    load = {r["teacher_id"]: r["n"] for r in cursor.fetchall()}
    cursor.execute("SELECT id FROM teachers WHERE department=? AND is_active=1", (department,))
    dept_teachers = sorted((r["id"] for r in cursor.fetchall()),
                           key=lambda tid: (load.get(tid, 0), tid))
    pool = [t for t in dept_teachers if t not in source_teachers]
    fallback_pool = sorted(source_teachers)  # only if the dept has no spare teachers

    for i, a in enumerate(courses):
        tid = pool.pop(0) if pool else fallback_pool[i % len(fallback_pool)]
        cursor.execute('''
            INSERT INTO course_assignments
                (course_id,teacher_id,group_id,semester,hours_per_week,theory_hours,lab_hours,is_lab,priority)
            VALUES (?,?,?,?,?,?,?,?,?)
        ''', (a["course_id"], tid, group_id, a["semester"], a["hours_per_week"],
              a.get("theory_hours"), a.get("lab_hours"), 1 if a.get("course_is_lab") else 0,
              a.get("priority") or 1))


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
            SELECT ca.*, c.course_code, c.course_name, c.is_lab as course_is_lab, c.credits as course_credits, t.name as teacher_name, t.id as tid
            FROM course_assignments ca
            JOIN courses c ON ca.course_id=c.id
            JOIN teachers t ON ca.teacher_id=t.id
            WHERE ca.group_id=? AND ca.semester=?
            ORDER BY ca.priority DESC
        ''', (group_id, request.semester))
        assignments = cursor.fetchall()

        if not assignments:
            cursor.execute('''
                SELECT ca.*, c.course_code, c.course_name, c.is_lab as course_is_lab, c.credits as course_credits, t.name as teacher_name, t.id as tid
                FROM course_assignments ca
                JOIN courses c ON ca.course_id=c.id
                JOIN teachers t ON ca.teacher_id=t.id
                JOIN student_groups sg ON ca.group_id=sg.id
                WHERE sg.department=? AND ca.semester=?
                ORDER BY ca.priority DESC
            ''', (request.branch, request.semester))
            borrowed = [dict(r) for r in cursor.fetchall()]

            # This section has no assignments of its own, so it would reuse
            # another section's subjects AND teachers - and those teachers are
            # already booked in the other section's slots, so half the classes
            # can't be placed. Give this section the same subjects but its own
            # teachers (least-loaded in the department, none of the source
            # section's), saved as this group's real assignments.
            if borrowed:
                _assign_own_teachers(cursor, group_id, request.branch, borrowed)
                cursor.execute('''
                    SELECT ca.*, c.course_code, c.course_name, c.is_lab as course_is_lab, c.credits as course_credits, t.name as teacher_name, t.id as tid
                    FROM course_assignments ca
                    JOIN courses c ON ca.course_id=c.id
                    JOIN teachers t ON ca.teacher_id=t.id
                    WHERE ca.group_id=? AND ca.semester=?
                    ORDER BY ca.priority DESC
                ''', (group_id, request.semester))
                assignments = cursor.fetchall()

        if not assignments:
            return {"success": False,
                    "message": f"No course assignments found for {request.branch} Semester {request.semester}. Add subjects and assign teachers first."}

        # Get all non-break slots ordered by day then time
        cursor.execute("SELECT * FROM time_slots WHERE is_break=0 AND is_active=1 ORDER BY day_of_week, start_time")
        available_slots = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT id, room_code, is_lab, building FROM rooms WHERE is_active=1 ORDER BY capacity DESC")
        all_rooms = [dict(r) for r in cursor.fetchall()]
        room_ids = [r["id"] for r in all_rooms]
        room_code_by_id = {r["id"]: r["room_code"] for r in all_rooms}

        if not room_ids:
            return {"success": False, "message": "No active rooms found. Add rooms first."}

        # Hard separation: a lab room is only ever used for lab sessions and a
        # non-lab room only ever for theory classes, so a class never gets
        # booked into a lab room and a lab never lands in a lecture room.
        # Labs go to this branch's own department labs first, then the common
        # Lab Block; other departments' labs are only a last resort.
        lab_rooms = [r for r in all_rooms if r["is_lab"]]
        lab_rooms.sort(key=lambda r: (0 if r["building"] == request.branch else 1 if r["building"] == "Lab Block" else 2))
        lab_room_ids = [r["id"] for r in lab_rooms]
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

        # Home classroom: every theory class of this section is taught in one
        # fixed room (student_groups.room_id) instead of whichever room happens
        # to be free first, so students aren't moving rooms every period. Kept
        # across regenerations; a new section gets the lecture room no other
        # section calls home, least booked first. Other rooms are only used for
        # a period where the home room is already taken.
        cursor.execute("SELECT room_id FROM student_groups WHERE id=?", (group_id,))
        home_room_id = cursor.fetchone()["room_id"]
        if home_room_id not in theory_room_ids:
            cursor.execute("SELECT room_id FROM student_groups WHERE room_id IS NOT NULL AND id!=?", (group_id,))
            taken_homes = {r["room_id"] for r in cursor.fetchall()}
            candidates = [rid for rid in theory_room_ids if rid not in taken_homes] or theory_room_ids
            home_room_id = min(candidates, key=lambda rid: (len(room_busy.get(rid, ())), theory_room_ids.index(rid)))
            cursor.execute("UPDATE student_groups SET room_id=? WHERE id=?", (home_room_id, group_id))
        theory_room_ids = [home_room_id] + [rid for rid in theory_room_ids if rid != home_room_id]

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
        lab_count_by_day: Dict[int, int] = {}
        MAX_LABS_PER_DAY = 2  # a day only has a morning and an afternoon 2-hour block

        # Lab units: normally each lab course runs on its own (the whole section
        # is in the lab while batches E1/E2/E3 take turns). When a section's
        # labs can't fit that way - e.g. 5 subjects + 2 labs on a week with
        # shortened days - labs are paired and run in PARALLEL batch rotation:
        # E1 in lab A while E2 is in lab B, then E2/E3, then E3/E1. Every batch
        # still does each lab once a week, in half the section time.
        # "Can't fit" includes the credit bonus: if labs one at a time would
        # leave no room for the extra periods of higher-credit subjects, the
        # labs run in parallel so those periods get their slots.
        # Pairing only for the bonus is dropped again if it costs a lab
        # session (it needs two teachers and two lab rooms free at once):
        # the labs are then re-placed one at a time, as without the bonus.
        theory_periods_needed = sum(min(a["hours_per_week"], MAX_THEORY_SESSIONS_PER_WEEK) for a in theory_assignments)
        bonus_periods_wanted = sum(credit_bonus_sessions(theory_assignments, len(available_slots)))
        sequential_lab_periods = len(lab_assignments) * LAB_SESSIONS_PER_WEEK * LAB_SESSION_SLOTS
        parallel_for_base = theory_periods_needed + sequential_lab_periods > len(available_slots)
        parallel_labs = (len(lab_assignments) >= 2 and
                         theory_periods_needed + bonus_periods_wanted + sequential_lab_periods > len(available_slots))
        paired_units = []
        unpaired = list(lab_assignments)
        while unpaired:
            first = unpaired.pop(0)
            # Two labs can only share a time if different teachers take them.
            partner = next((a for a in unpaired if a["tid"] != first["tid"]), None) if parallel_labs else None
            if partner:
                unpaired.remove(partner)
                paired_units.append([first, partner])
            else:
                paired_units.append([first])
        lab_plans = [paired_units]
        if parallel_labs and not parallel_for_base:
            lab_plans.append([[a] for a in lab_assignments])

        for plan_no, lab_units in enumerate(lab_plans):
            cursor.execute("SAVEPOINT lab_plan")
            before_labs = copy.deepcopy((teacher_busy, room_busy, group_busy, teacher_day_hours, teacher_week_hours,
                                         entries_list, conflicts, assigned_count))
            # How many weekdays may carry a lab for this section, sized to its own
            # lab load so any mix works (6 subjects + 1 lab, 5 + 2, 4 + 2, 4 + 3):
            # normally MAX_RECOMMENDED_LAB_SESSIONS_PER_WEEK days (keeps one
            # lab-free day), but a section whose labs can't fit in that many days
            # at MAX_LABS_PER_DAY gets every weekday instead of losing sessions.
            total_lab_sessions = len(lab_units) * LAB_SESSIONS_PER_WEEK
            lab_day_cap = min(len(slots_by_day),
                              max(MAX_RECOMMENDED_LAB_SESSIONS_PER_WEEK, -(-total_lab_sessions // MAX_LABS_PER_DAY)))

            for unit in lab_units:
                sessions_placed = 0
                unit_lab_days: set = set()  # a lab unit is never repeated on a day
                unit_teachers = [a["tid"] for a in unit]

                for session_idx in range(LAB_SESSIONS_PER_WEEK):
                    # Course i of the unit takes batch (session + i) - so in a pair
                    # the two labs always have different batches at the same time.
                    batches = [LAB_BATCHES[(session_idx + i) % len(LAB_BATCHES)] for i in range(len(unit))]
                    placed = False

                    # Never open a new lab-day beyond lab_day_cap (see above) -
                    # keeps a lab-free day whenever this section's labs allow it.
                    lab_day_cap_reached = len(group_lab_days) >= lab_day_cap

                    # Prefer days not adjacent to an existing lab day so labs
                    # spread out (Mon/Wed/Fri) instead of running on consecutive
                    # days; adjacent days remain a fallback when nothing else fits.
                    for day in sorted(slots_by_day.keys(),
                                      key=lambda d: (any(abs(d - g) == 1 for g in unit_lab_days),
                                                     lab_count_by_day.get(d, 0), day_load[d], d)):
                        if day in unit_lab_days:
                            continue
                        if lab_count_by_day.get(day, 0) >= MAX_LABS_PER_DAY:
                            continue
                        if lab_day_cap_reached and day not in group_lab_days:
                            continue  # keep at least one lab-free day

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
                            if any(sid in teacher_busy.get(t, set()) for t in unit_teachers for sid in block_slot_ids):
                                continue
                            if not all(teacher_has_capacity(t, day, LAB_SESSION_SLOTS) for t in unit_teachers):
                                continue

                            # One free lab room per course in the unit.
                            free_rooms = [rid for rid in lab_room_ids
                                          if not any(sid in room_busy.get(rid, set()) for sid in block_slot_ids)]
                            if len(free_rooms) < len(unit):
                                continue

                            for assignment, batch, room_id in zip(unit, batches, free_rooms):
                                teacher_id = assignment["tid"]
                                for slot in block:
                                    cursor.execute('''
                                        INSERT INTO timetable_entries
                                            (teacher_id,group_id,room_id,slot_id,course_id,semester,academic_year,status,batch)
                                        VALUES (?,?,?,?,?,?,"2024-2025","scheduled",?)
                                    ''', (teacher_id, group_id, room_id, slot["id"], assignment["course_id"], request.semester, batch))

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
                            unit_lab_days.add(day)
                            lab_count_by_day[day] = lab_count_by_day.get(day, 0) + 1
                            day_load[day] += 1
                            sessions_placed += 1
                            placed = True
                            break

                        if placed:
                            break

                    if not placed:
                        break  # no day/room/teacher can fit another session this week

                if sessions_placed < LAB_SESSIONS_PER_WEEK:
                    for assignment in unit:
                        unmet_lab_sessions[assignment["course_code"]] = LAB_SESSIONS_PER_WEEK - sessions_placed
                        conflicts.append({
                            "type": "lab",
                            "description": f"{assignment['course_name']}: only {sessions_placed}/{LAB_SESSIONS_PER_WEEK} lab sessions placed (teacher/room/day conflicts)"
                        })
            if not unmet_lab_sessions or plan_no == len(lab_plans) - 1:
                break
            # Paired labs lost a session - undo them and place the labs singly.
            cursor.execute("ROLLBACK TO lab_plan")
            (teacher_busy, room_busy, group_busy, teacher_day_hours, teacher_week_hours,
             entries_list, conflicts, assigned_count) = before_labs
            unmet_lab_sessions, group_lab_days, lab_count_by_day = {}, set(), {}
            day_load = {day: 0 for day in slots_by_day}

        # Theory scheduling below only handles non-lab assignments - labs are
        # fully scheduled above. Higher-credit subjects go first (within the
        # same priority), so when a week is too full for everything it is the
        # lowest-credit subject that ends up a period short, not the heaviest.
        assignments = sorted(theory_assignments,
                             key=lambda a: (-(a.get("priority") or 0), -(a.get("course_credits") or 0)))

        # Build a schedule slot by slot
        # Strategy: round-robin across assignments, spreading evenly across the week
        # Each subject gets slots spread across different days where possible

        # First pass: track how many slots each assignment still needs, capped
        # at MAX_THEORY_SESSIONS_PER_WEEK regardless of the subject's own
        # hours_per_week (e.g. a subject with hours_per_week=5 still only
        # gets 3 classes/week), plus the credit bonus: higher-credit subjects
        # get 1-2 more periods out of whatever the labs and base periods
        # leave free.
        base_sessions = [min(a["hours_per_week"], MAX_THEORY_SESSIONS_PER_WEEK) for a in assignments]
        free_after_base = len(available_slots) - len(group_busy) - sum(base_sessions)
        bonus_sessions = credit_bonus_sessions(assignments, free_after_base)
        remaining = {i: base_sessions[i] + bonus_sessions[i] for i in range(len(assignments))}
        # Days each assignment has already been placed on for this group - used to
        # avoid scheduling the same subject twice in one day (e.g. Data Structures
        # on both Monday period 1 and Monday period 4). A repeat is only allowed
        # as a last resort, when every other subject for this slot is either done
        # or teacher-busy, so hours_per_week that don't fit into 5 distinct days
        # still get scheduled instead of silently dropped.
        subject_days_used: Dict[int, set] = {i: set() for i in range(len(assignments))}
        subject_slots: Dict[int, list] = {i: [] for i in range(len(assignments))}

        def place_theory(idx: int, slot: dict) -> bool:
            """Book one theory period of assignments[idx] at `slot`, in the
            section's home room if free, else the first free lecture room."""
            nonlocal assigned_count
            slot_id = slot["id"]
            room_id = next((rid for rid in theory_room_ids if slot_id not in room_busy.get(rid, set())), None)
            if room_id is None:
                return False
            assignment = assignments[idx]
            teacher_id = assignment["tid"]
            cursor.execute('''
                INSERT INTO timetable_entries
                    (teacher_id,group_id,room_id,slot_id,course_id,semester,academic_year,status)
                VALUES (?,?,?,?,?,?,"2024-2025","scheduled")
            ''', (teacher_id, group_id, room_id, slot_id, assignment["course_id"], request.semester))
            teacher_busy.setdefault(teacher_id, set()).add(slot_id)
            room_busy.setdefault(room_id, set()).add(slot_id)
            group_busy.add(slot_id)
            subject_days_used[idx].add(slot["day_of_week"])
            subject_slots[idx].append(slot_id)
            record_teacher_hours(teacher_id, slot["day_of_week"], 1)
            entries_list.append({
                "day":          slot["day_name"],
                "time_slot":    f"{slot['start_time']}-{slot['end_time']}",
                "subject_code": assignment["course_code"],
                "subject_name": assignment["course_name"],
                "teacher_name": assignment["teacher_name"],
                "room_code":    room_code_by_id.get(room_id)
            })
            remaining[idx] -= 1
            assigned_count += 1
            return True

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

            place_theory(best_idx, slot)
            slot_index += 1

            # If all done, stop
            if all(v <= 0 for v in remaining.values()):
                break

        # Second pass: the interleaved pass above walks each slot once and
        # never goes back, so a subject can end up a period short even though
        # free slots remain (e.g. 5 subjects + 2 labs). Retry every leftover
        # period over all free slots, least-busy days first: a day the subject
        # doesn't have yet is preferred, and a repeat day - never in the
        # period right next to that subject's other class - is the last resort.
        if any(v > 0 for v in remaining.values()):
            slot_by_id = {s["id"]: s for s in available_slots}
            day_busy_count = lambda d: sum(1 for sid in group_busy if slot_by_id.get(sid, {}).get("day_of_week") == d)
            for idx in range(len(assignments)):
                tid = assignments[idx]["tid"]
                for allow_repeat_day in (False, True):
                    if remaining[idx] <= 0:
                        break
                    for slot in sorted(available_slots, key=lambda s: (day_busy_count(s["day_of_week"]), s["day_of_week"], s["start_time"])):
                        if remaining[idx] <= 0:
                            break
                        d = slot["day_of_week"]
                        if slot["id"] in group_busy or slot["id"] in teacher_busy.get(tid, set()):
                            continue
                        if not teacher_has_capacity(tid, d, 1):
                            continue
                        if d in subject_days_used[idx]:
                            if not allow_repeat_day:
                                continue
                            same_day = [slot_by_id[sid] for sid in subject_slots[idx] if slot_by_id[sid]["day_of_week"] == d]
                            if any(s2["end_time"] == slot["start_time"] or s2["start_time"] == slot["end_time"] for s2 in same_day):
                                continue
                        place_theory(idx, slot)

        home_room_code = room_code_by_id.get(home_room_id)
        n_theory, n_labs = len(theory_assignments), len(lab_assignments)
        # A bonus period that found no slot (teacher busy) is simply dropped -
        # only a shortfall in a subject's base periods counts as unmet.
        bonus_placed = {}
        for i in remaining:
            placed = len(subject_slots[i])
            remaining[i] = max(0, base_sessions[i] - placed)
            if placed > base_sessions[i]:
                bonus_placed[assignments[i]["course_code"]] = placed - base_sessions[i]
        theory_needed = sum(base_sessions) + sum(bonus_placed.values())
        lab_needed = n_labs * LAB_SESSIONS_PER_WEEK
        layout = {
            "label": f"{n_theory} subject{'s' if n_theory != 1 else ''} + {n_labs} lab{'s' if n_labs != 1 else ''}",
            "theory_subjects": n_theory,
            "lab_courses": n_labs,
            "theory_periods": {"placed": theory_needed - sum(max(v, 0) for v in remaining.values()), "needed": theory_needed},
            "lab_sessions": {"placed": lab_needed - sum(unmet_lab_sessions.values()), "needed": lab_needed},
            "credit_bonus_periods": bonus_placed,
            "periods_used": len(group_busy),
            "periods_available": total_slots_available,
            "home_room": home_room_code,
            "lab_rooms": sorted({e["room_code"] for e in entries_list if e.get("batch")}),
        }
        timetable_data = json.dumps({
            "branch": request.branch, "year": request.year,
            "semester": request.semester, "section": request.section,
            "entries": entries_list, "days": DAYS, "time_slots": TIME_SLOTS,
            "home_room": home_room_code, "layout": layout,
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
        msg = (f"Timetable generated ({layout['label']}): {assigned_count} periods scheduled, "
               f"home classroom {home_room_code}")
        if bonus_placed:
            msg += ". Extra periods for higher-credit subjects: " + ", ".join(f"{c} +{n}" for c, n in bonus_placed.items())
        if unmet:
            msg += f". Could not fit: {unmet} (teacher conflicts or insufficient slots)"

        return {
            "success": True,
            "message": msg,
            "assignments_scheduled": assigned_count,
            "conflicts_detected": len(conflicts),
            "unmet_hours": unmet,
            "layout": layout,
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
            resp = _build_timetable_response(branch, year, section, semester, [], data.get("entries", []))
            resp["home_room"] = data.get("home_room")
            resp["layout"] = data.get("layout")
            return resp

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

@app.get("/api/timetable/subjects")
async def timetable_subject_summary(branch: str, year: int, section: str = "A", semester: int = 1,
                                    _=Depends(get_current_user)):
    """
    Every subject of a branch + semester with its credits, and - for one
    section - its assigned teacher and what the generated timetable actually
    gave it (periods/week, rooms). Shown next to the timetable so credits
    and schedule can be checked together. Subjects not assigned to this
    section are included (teacher null) so the full semester is visible.
    """
    branch, section = branch.upper(), section.upper()
    conn = get_db()
    try:
        group = conn.execute("SELECT id FROM student_groups WHERE group_code=?", (f"{branch}{year}{section}",)).fetchone()
        assigned: Dict[str, str] = {}
        if group:
            for r in conn.execute('''
                SELECT c.course_code, t.name AS teacher_name FROM course_assignments ca
                JOIN courses c ON c.id = ca.course_id JOIN teachers t ON t.id = ca.teacher_id
                WHERE ca.group_id=? AND ca.semester=?''', (group["id"], semester)).fetchall():
                assigned[r["course_code"]] = r["teacher_name"]

        periods: Dict[str, int] = {}
        rooms: Dict[str, set] = {}
        saved = conn.execute('''SELECT timetable_data FROM saved_timetables
            WHERE branch=? AND year=? AND section=? AND semester=? AND is_active=1
            ORDER BY generated_at DESC LIMIT 1''', (branch, year, section, semester)).fetchone()
        if saved:
            for e in json.loads(saved["timetable_data"]).get("entries", []):
                code = e.get("subject_code")
                periods[code] = periods.get(code, 0) + 1
                if e.get("room_code"):
                    rooms.setdefault(code, set()).add(e["room_code"])

        subjects = []
        for r in conn.execute('''SELECT code, name, credits, ltp, hours_per_week, is_lab, is_elective, credit_source
            FROM subjects WHERE branch=? AND semester=? ORDER BY is_lab, code''', (branch, semester)).fetchall():
            subjects.append({
                "code": r["code"], "name": r["name"], "credits": r["credits"] or 0, "ltp": r["ltp"],
                "is_lab": bool(r["is_lab"]), "is_elective": bool(r["is_elective"]),
                "custom": (r["credit_source"] or "curriculum") != "curriculum" and
                          credit_system.curriculum_default(r["code"], r["name"]) is None,
                "teacher": assigned.get(r["code"]),
                "periods_per_week": periods.get(r["code"], 0),
                "rooms": sorted(rooms.get(r["code"], ())),
            })
        return {
            "branch": branch, "year": year, "section": section, "semester": semester,
            "subjects": subjects,
            "total_credits": sum(s["credits"] for s in subjects),
            "assigned_credits": sum(s["credits"] for s in subjects if s["teacher"]),
            "scheduled": bool(saved),
        }
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