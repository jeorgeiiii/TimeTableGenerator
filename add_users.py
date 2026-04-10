# add_users.py - Run this to add teacher and student users
import sqlite3
import hashlib

DB_PATH = "sgsits_timetable.db"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def add_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Teacher users
    teachers = [
        ("teacher1", "teacher1@sgsits.edu", "teacher123", "Prof. Rahul Sharma", "teacher"),
        ("teacher2", "teacher2@sgsits.edu", "teacher123", "Prof. Neha Verma", "teacher"),
        ("teacher3", "teacher3@sgsits.edu", "teacher123", "Prof. Amit Tiwari", "teacher"),
    ]
    
    # Student users
    students = [
        ("student1", "student1@sgsits.edu", "student123", "John Doe", "student"),
        ("student2", "student2@sgsits.edu", "student123", "Jane Smith", "student"),
        ("student3", "student3@sgsits.edu", "student123", "Mike Johnson", "student"),
    ]
    
    for username, email, password, full_name, role in teachers + students:
        try:
            hashed = hash_password(password)
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, hashed, full_name, role))
            print(f"✅ Added user: {username} ({role})")
        except Exception as e:
            print(f"Error adding {username}: {e}")
    
    conn.commit()
    conn.close()
    print("\n✅ All users added successfully!")

if __name__ == "__main__":
    add_users()