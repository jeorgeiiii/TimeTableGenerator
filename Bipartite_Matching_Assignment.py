# Bipartite_Matching_Assignment.py - Simplified Working Version
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# ============ DATA CLASSES ============

@dataclass
class Teacher:
    """Teacher with availability and schedule tracking"""
    id: str
    name: str
    department: str
    max_hours_per_day: int = 6
    unavailable_slots: List[str] = field(default_factory=list)
    schedule: Dict[str, str] = field(default_factory=dict)
    
    def is_available(self, slot_id: str) -> bool:
        return slot_id not in self.schedule and slot_id not in self.unavailable_slots
    
    def assign_slot(self, slot_id: str, course_id: str) -> bool:
        if self.is_available(slot_id):
            self.schedule[slot_id] = course_id
            return True
        return False
    
    def clear_schedule(self):
        self.schedule = {}


@dataclass
class StudentGroup:
    """Student group/section with schedule tracking"""
    id: str
    name: str
    semester: int
    department: str
    student_count: int = 0
    schedule: Dict[str, str] = field(default_factory=dict)
    
    def is_available(self, slot_id: str) -> bool:
        return slot_id not in self.schedule
    
    def assign_slot(self, slot_id: str, course_id: str) -> bool:
        if self.is_available(slot_id):
            self.schedule[slot_id] = course_id
            return True
        return False
    
    def clear_schedule(self):
        self.schedule = {}


@dataclass
class Room:
    """Room/classroom with capacity and schedule"""
    id: str
    name: str
    capacity: int
    room_type: str = "lecture"
    has_projector: bool = False
    schedule: Dict[str, str] = field(default_factory=dict)
    
    def is_available(self, slot_id: str) -> bool:
        return slot_id not in self.schedule
    
    def can_accommodate(self, student_count: int) -> bool:
        return self.capacity >= student_count
    
    def assign_slot(self, slot_id: str, course_id: str) -> bool:
        if self.is_available(slot_id):
            self.schedule[slot_id] = course_id
            return True
        return False
    
    def clear_schedule(self):
        self.schedule = {}


@dataclass
class TimeSlot:
    """Time slot definition"""
    id: str
    day: int
    day_name: str
    start_time: str
    end_time: str
    name: str


@dataclass
class Course:
    """Course with teacher and group assignments"""
    id: str
    name: str
    code: str
    teacher_id: str
    group_id: str
    hours_per_week: int = 3
    is_lab: bool = False
    preferred_room: Optional[str] = None
    priority: int = 1
    assigned_slots: List[str] = field(default_factory=list)


# ============ ENHANCED TIMETABLE SCHEDULER ============

class TimetableScheduler:
    """Enhanced scheduler with collision prevention"""
    
    def __init__(self):
        self.teachers: Dict[str, Teacher] = {}
        self.student_groups: Dict[str, StudentGroup] = {}
        self.rooms: Dict[str, Room] = {}
        self.time_slots: Dict[str, TimeSlot] = {}
        self.courses: List[Course] = []
        self.conflicts: List[Dict] = []
        self.assignments: List[Dict] = []
        
    def add_teacher(self, teacher_id: str, name: str, department: str, max_hours: int = 6) -> Teacher:
        self.teachers[teacher_id] = Teacher(teacher_id, name, department, max_hours)
        return self.teachers[teacher_id]
    
    def add_student_group(self, group_id: str, name: str, semester: int, 
                          department: str, student_count: int = 0) -> StudentGroup:
        self.student_groups[group_id] = StudentGroup(group_id, name, semester, department, student_count)
        return self.student_groups[group_id]
    
    def add_room(self, room_id: str, name: str, capacity: int, 
                 room_type: str = "lecture", has_projector: bool = False) -> Room:
        self.rooms[room_id] = Room(room_id, name, capacity, room_type, has_projector)
        return self.rooms[room_id]
    
    def add_time_slot(self, slot_id: str, day: int, day_name: str, 
                      start_time: str, end_time: str, name: str) -> TimeSlot:
        self.time_slots[slot_id] = TimeSlot(slot_id, day, day_name, start_time, end_time, name)
        return self.time_slots[slot_id]
    
    def add_course(self, course_id: str, name: str, code: str, teacher_id: str,
                   group_id: str, hours_per_week: int = 3, is_lab: bool = False,
                   preferred_room: Optional[str] = None, priority: int = 1) -> Course:
        course = Course(course_id, name, code, teacher_id, group_id, 
                       hours_per_week, is_lab, preferred_room, priority)
        self.courses.append(course)
        return course
    
    def check_teacher_conflict(self, teacher_id: str, slot_id: str) -> bool:
        teacher = self.teachers.get(teacher_id)
        return not teacher.is_available(slot_id) if teacher else False
    
    def check_group_conflict(self, group_id: str, slot_id: str) -> bool:
        group = self.student_groups.get(group_id)
        return not group.is_available(slot_id) if group else False
    
    def check_room_conflict(self, room_id: str, slot_id: str) -> bool:
        room = self.rooms.get(room_id)
        return not room.is_available(slot_id) if room else False
    
    def assign_course_to_slot(self, course: Course, slot_id: str, room_id: str) -> Tuple[bool, List[str]]:
        conflicts = []
        
        if self.check_teacher_conflict(course.teacher_id, slot_id):
            conflicts.append("Teacher conflict")
        if self.check_group_conflict(course.group_id, slot_id):
            conflicts.append("Group conflict")
        if self.check_room_conflict(room_id, slot_id):
            conflicts.append("Room conflict")
        
        if conflicts:
            return False, conflicts
        
        teacher = self.teachers.get(course.teacher_id)
        group = self.student_groups.get(course.group_id)
        room = self.rooms.get(room_id)
        
        if teacher:
            teacher.assign_slot(slot_id, course.id)
        if group:
            group.assign_slot(slot_id, course.id)
        if room:
            room.assign_slot(slot_id, course.id)
        
        course.assigned_slots.append(slot_id)
        self.assignments.append({
            'course_id': course.id,
            'course_name': course.name,
            'teacher_id': course.teacher_id,
            'group_id': course.group_id,
            'room_id': room_id,
            'slot_id': slot_id,
        })
        
        return True, []
    
    def generate_timetable(self, priority_order: str = "lab") -> Dict:
        """Generate timetable using priority-based assignment"""
        
        self.clear_all_schedules()
        self.conflicts = []
        self.assignments = []
        
        # Sort courses
        if priority_order == "lab":
            self.courses.sort(key=lambda c: (not c.is_lab, -c.priority))
        
        assigned_count = 0
        total_hours = sum(c.hours_per_week for c in self.courses)
        failed_courses = []
        
        for course in self.courses:
            hours_assigned = 0
            
            while hours_assigned < course.hours_per_week:
                assigned = False
                
                for slot_id in self.time_slots.keys():
                    for room_id in self.rooms.keys():
                        success, _ = self.assign_course_to_slot(course, slot_id, room_id)
                        if success:
                            assigned = True
                            assigned_count += 1
                            hours_assigned += 1
                            break
                    if assigned:
                        break
                
                if not assigned:
                    failed_courses.append({
                        'course_id': course.id,
                        'course_name': course.name,
                        'hours_assigned': hours_assigned,
                        'hours_needed': course.hours_per_week
                    })
                    break
        
        return {
            'success': len(failed_courses) == 0,
            'assigned_count': assigned_count,
            'total_hours': total_hours,
            'completion_rate': (assigned_count / total_hours * 100) if total_hours > 0 else 0,
            'failed_courses': failed_courses,
            'conflicts': self.conflicts,
            'assignments': self.assignments
        }
    
    def clear_all_schedules(self):
        for teacher in self.teachers.values():
            teacher.clear_schedule()
        for group in self.student_groups.values():
            group.clear_schedule()
        for room in self.rooms.values():
            room.clear_schedule()
        for course in self.courses:
            course.assigned_slots = []
        self.assignments = []
        self.conflicts = []
    
    def get_teacher_schedule(self, teacher_id: str) -> Dict:
        teacher = self.teachers.get(teacher_id)
        if not teacher:
            return {}
        
        schedule = {}
        for slot_id, course_id in teacher.schedule.items():
            slot = self.time_slots.get(slot_id)
            course = next((c for c in self.courses if c.id == course_id), None)
            if slot and course:
                schedule[f"{slot.day_name} {slot.start_time}-{slot.end_time}"] = {
                    'course_id': course.id,
                    'course_name': course.name,
                    'course_code': course.code,
                }
        return schedule


# ============ FACTORY FUNCTION ============

def create_timetable_scheduler() -> TimetableScheduler:
    """Create a fully configured timetable scheduler"""
    scheduler = TimetableScheduler()
    
    # Add default teachers
    default_teachers = [
        ("T001", "Prof. Abhijeet", "CSE", 6),
        ("T002", "Prof. Subhit", "Mathematics", 6),
        ("T003", "Prof. Sharma", "Physics", 5),
    ]
    
    for tid, name, dept, hours in default_teachers:
        scheduler.add_teacher(tid, name, dept, hours)
    
    # Add default student groups
    default_groups = [
        ("G001", "SE Comp A", 3, "CSE", 60),
        ("G002", "SE Comp B", 3, "CSE", 58),
    ]
    
    for gid, name, sem, dept, count in default_groups:
        scheduler.add_student_group(gid, name, sem, dept, count)
    
    # Add default rooms
    default_rooms = [
        ("R101", "Room 101", 60, "lecture", True),
        ("R102", "Room 102", 50, "lecture", False),
        ("LAB1", "Computer Lab 1", 40, "lab", True),
    ]
    
    for rid, name, cap, rtype, proj in default_rooms:
        scheduler.add_room(rid, name, cap, rtype, proj)
    
    # Add time slots (Monday to Friday)
    days = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday")]
    times = [
        ("09:00", "10:00", "S1"), ("10:00", "11:00", "S2"),
        ("11:00", "12:00", "S3"), ("12:00", "13:00", "S4"),
        ("14:00", "15:00", "S5"), ("15:00", "16:00", "S6"),
        ("16:00", "17:00", "S7")
    ]
    
    slot_counter = 1
    for day_idx, day_name in days:
        for start, end, name in times:
            scheduler.add_time_slot(
                f"SLOT{slot_counter}", day_idx, day_name, start, end, 
                f"{day_name[:3]}-{name}"
            )
            slot_counter += 1
    
    # Add default courses
    default_courses = [
        ("C001", "Basic Electrical Engineering", "BEE101", "T001", "G001", 3, False, "R101", 1),
        ("C002", "Mathematics 2", "MATH201", "T002", "G001", 4, False, "R102", 2),
        ("C003", "Engineering Physics", "PHY101", "T003", "G001", 3, False, "R101", 1),
    ]
    
    for cid, name, code, tid, gid, hours, lab, room, priority in default_courses:
        scheduler.add_course(cid, name, code, tid, gid, hours, lab, room, priority)
    
    return scheduler


# ============ RUN EXAMPLE ============

if __name__ == "__main__":
    print("=" * 60)
    print("Creating Timetable Scheduler...")
    print("=" * 60)
    
    scheduler = create_timetable_scheduler()
    
    print(f"✅ Loaded {len(scheduler.teachers)} teachers")
    print(f"✅ Loaded {len(scheduler.student_groups)} student groups")
    print(f"✅ Loaded {len(scheduler.rooms)} rooms")
    print(f"✅ Loaded {len(scheduler.time_slots)} time slots")
    print(f"✅ Loaded {len(scheduler.courses)} courses")
    
    print("\n" + "=" * 60)
    print("Generating Timetable...")
    print("=" * 60)
    
    result = scheduler.generate_timetable(priority_order="lab")
    
    print(f"\n📊 Generation Results:")
    print(f"   Success: {result['success']}")
    print(f"   Assigned: {result['assigned_count']}/{result['total_hours']} hours")
    print(f"   Completion Rate: {result['completion_rate']:.1f}%")
    print(f"   Conflicts Detected: {len(result['conflicts'])}")