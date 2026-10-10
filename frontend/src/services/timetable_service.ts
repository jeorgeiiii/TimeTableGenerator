// frontend/src/services/timetable_service.ts
import api from './api';

export interface Teacher {
  id: number;
  name: string;
  email: string;
  department: string;
  subjects: string;
}

export interface Subject {
  id: number;
  code: string;
  name: string;
  branch: string;
  year: number;
  teacher_id: number;
  teacher2_id: number | null;
  teacher1_name?: string;
  teacher2_name?: string;
}

export interface Branch {
  code: string;
  name: string;
}

export interface ApiResponse {
  success: boolean;
  message?: string;
}

export interface TimetableData {
  branch: string;
  year: number;
  semester: number;
  section: string;
  days: string[];
  time_slots: string[];
  timetable: Record<string, Record<string, string>>;
  // Section's fixed classroom for theory, and what the generator scheduled
  // (e.g. "5 subjects + 2 labs") - only on timetables generated after rooms
  // were added.
  home_room?: string | null;
  layout?: {
    label: string;
    lab_rooms?: string[];
  } | null;
}

class TimetableService {
  // ── Teachers (Admin only) ───────────────────────────────────────────────
  async addTeacher(data: {
    name: string;
    email: string;
    department: string;
    subjects: string;
  }): Promise<ApiResponse> {
    const response = await api.post('/admin/teachers', data);
    return response.data;
  }

  async getTeachers(): Promise<Teacher[]> {
    const response = await api.get('/admin/teachers');
    return response.data.teachers || [];
  }

  // ── Subjects (Admin only) ──────────────────────────────────────────────
  async addSubject(data: {
    code: string;
    name: string;
    branch: string;
    year: number;
    teacher_id: number;
    teacher2_id?: number;
  }): Promise<ApiResponse> {
    const response = await api.post('/admin/subjects', data);
    return response.data;
  }

  async getSubjects(branch: string, year: number): Promise<Subject[]> {
    const response = await api.get('/admin/subjects', { params: { branch, year } });
    return response.data.subjects || [];
  }

  // ── Branches ────────────────────────────────────────────────────────────
  async getBranches(): Promise<Branch[]> {
    const response = await api.get('/branches');
    return response.data.branches || [];
  }

  // ── Timetable ───────────────────────────────────────────────────────────
  async generateTimetable(
    branch: string,
    year: number,
    section: string,
    semester: number
  ): Promise<ApiResponse> {
    const response = await api.post('/timetable/generate', { branch, year, section, semester });
    return response.data;
  }

  /**
   * FIX: The backend /api/timetable/view returns the matrix object directly —
   * NOT nested under a `.timetable` key.
   * Shape returned: { branch, year, semester, section, days, time_slots, timetable }
   * We just return response.data directly.
   */
  async viewTimetable(
    branch: string,
    year: number,
    section: string,
    semester: number = 1
  ): Promise<TimetableData> {
    const response = await api.get('/timetable/view', {
      params: { branch, year, section, semester },
    });

    // Backend _build_timetable_response returns the object directly (not wrapped)
    const data = response.data;

    // Defensive: if the server ever wraps it, unwrap gracefully
    const result: TimetableData = data.branch ? data : data.timetable ?? data;

    // Guarantee arrays are never undefined so the UI won't crash
    return {
      branch:     result.branch     ?? branch,
      year:       result.year       ?? year,
      semester:   result.semester   ?? semester,
      section:    result.section    ?? section,
      days:       result.days       ?? [],
      time_slots: result.time_slots ?? [],
      timetable:  result.timetable  ?? {},
      home_room:  result.home_room  ?? null,
      layout:     result.layout     ?? null,
    };
  }
}

export default new TimetableService();