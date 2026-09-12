// frontend/src/pages/AssignSubject.tsx
import { useState, useEffect, useCallback } from "react";
import { store, BRANCHES, YEARS, hasMultipleSections } from "@/lib/store";
import { toast } from "sonner";
import api from "../services/api";

interface SubjectResponse {
  id: string | number;
  code: string;
  name: string;
  branch: string;
  year: number;
  is_lab?: boolean | number;
  is_elective?: boolean | number;
}

interface TeacherResponse {
  id: string | number;
  name: string;
  department: string;
  email: string;
  specialization?: string;
}

// Maps year label ("1st Year", "2nd Year", ...) to integer (1, 2, ...)
const yearLabelToInt = (yearLabel: string): number => {
  const idx = YEARS.indexOf(yearLabel);
  return idx >= 0 ? idx + 1 : 1;
};

// Semester options based on year (year 1 -> sem 1/2, year 2 -> sem 3/4, ...)
const getSemesterOptions = (yearLabel: string): number[] => {
  const y = yearLabelToInt(yearLabel);
  return [y * 2 - 1, y * 2];
};

const AssignSubject = () => {
  const [branch, setBranch] = useState("");
  const [year, setYear] = useState("1st Year");
  const [semester, setSemester] = useState<number>(1);
  const [subjectId, setSubjectId] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [section, setSection] = useState("");
  const [subjects, setSubjects] = useState<SubjectResponse[]>([]);
  const [teachers, setTeachers] = useState<TeacherResponse[]>([]);

  // Reset semester to the first one for this year whenever year changes.
  useEffect(() => {
    setSemester(getSemesterOptions(year)[0]);
  }, [year]);

  const loadSubjects = useCallback(async () => {
    try {
      const response = await api.get("/admin/subjects", {
        params: {
          branch,
          year: yearLabelToInt(year),
          semester,
        },
      });
      setSubjects(response.data.subjects || []);
    } catch (error) {
      console.error("Error loading subjects:", error);
    }
  }, [branch, year, semester]);

  const loadTeachers = useCallback(async () => {
    try {
      const response = await api.get("/admin/teachers");
      setTeachers(response.data.teachers || []);
    } catch (error) {
      console.error("Error loading teachers:", error);
    }
  }, []);

  useEffect(() => {
    loadSubjects();
    loadTeachers();
  }, [branch, year, semester, loadSubjects, loadTeachers]);

  // Only offer teachers from the selected branch's department - a teacher
  // stays picked if still valid, otherwise reset so a stale cross-branch
  // selection can't slip through.
  const filteredTeachers = branch ? teachers.filter(t => t.department === branch) : teachers;
  useEffect(() => {
    if (teacherId && !filteredTeachers.some(t => String(t.id) === teacherId)) {
      setTeacherId("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [branch, teachers]);

  // Only CSE/IT have multiple sections - everyone else is always Section A.
  // Computed fresh at use, not just via effect, so a stale "" from a previous
  // reset can never slip through the required-fields check below.
  const showSectionField = !branch || hasMultipleSections(branch);
  useEffect(() => {
    if (branch && !hasMultipleSections(branch)) {
      setSection("A");
    }
  }, [branch]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const effectiveSection = branch && !hasMultipleSections(branch) ? "A" : section;
    if (!branch || !subjectId || !teacherId || !effectiveSection) {
      toast.error("All fields are required");
      return;
    }

    try {
      const response = await api.post("/admin/subjects/assign", {
        subject_id: parseInt(subjectId),
        teacher_id: parseInt(teacherId),
        section: effectiveSection,
        branch,
        year: yearLabelToInt(year),
      });
      const data = response.data;
      if (data.success) {
        toast.success("Subject assigned successfully!");
        if (data.warning) {
          toast.warning(data.warning);
        }
        if (data.lab_warning) {
          toast.warning(data.lab_warning);
        }
        setSubjectId("");
        setTeacherId("");
        setSection(hasMultipleSections(branch) ? "" : "A");
      } else {
        toast.error(data.message || "Assignment failed");
      }
    } catch (error) {
      toast.error("Failed to assign subject");
    }
  };

  const handleResetBranch = async () => {
    if (!branch) {
      toast.error("Select a branch first");
      return;
    }
    if (!window.confirm(
      `Reset ${branch}? This unassigns every subject's teacher and clears any generated timetable for ${branch}. This cannot be undone.`
    )) {
      return;
    }
    try {
      const response = await api.post("/admin/subjects/reset-assignments", { branch });
      const data = response.data;
      toast.success(data.message || `${branch} assignments reset`);
      loadSubjects();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to reset assignments");
    }
  };

  return (
    <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h2 className="text-2xl font-bold">🔗 Assign Subject to Teacher & Section</h2>
        <button
          type="button"
          onClick={handleResetBranch}
          disabled={!branch}
          title={branch ? `Unassign every subject for ${branch}` : "Select a branch first"}
          className="px-4 py-2 rounded-lg font-medium border border-destructive/50 text-destructive hover:bg-destructive/10 disabled:opacity-50 whitespace-nowrap"
        >
          🔄 Reset {branch || "Branch"} Assignments
        </button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Branch *</label>
            <select
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Branch</option>
              {BRANCHES.map((b, idx) => (
                <option key={`branch-${idx}`} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Year *</label>
            <select
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              {YEARS.map((y, idx) => (
                <option key={`year-${idx}`} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Semester *</label>
            <select
              value={semester}
              onChange={(e) => setSemester(parseInt(e.target.value))}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              {getSemesterOptions(year).map((s) => (
                <option key={`sem-${s}`} value={s}>
                  Semester {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Subject *</label>
            <select
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Subject</option>
              {subjects.map((s, idx) => (
                <option key={`subject-${s.id || idx}`} value={s.id}>
                  {s.is_lab ? "🧪 " : ""}{s.name} ({s.code}){s.is_lab ? " - Lab" : ""}{s.is_elective ? " - Elective" : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Teacher *</label>
            <select
              value={teacherId}
              onChange={(e) => setTeacherId(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">{branch ? `Select Teacher (${branch})` : "Select Teacher"}</option>
              {filteredTeachers.map((t, idx) => (
                <option key={`teacher-${t.id || idx}`} value={t.id}>
                  {t.name} ({t.department}{t.specialization ? ` - ${t.specialization}` : ""})
                </option>
              ))}
            </select>
          </div>
        </div>
        {showSectionField && (
          <div>
            <label className="block text-sm font-medium mb-1">Section *</label>
            <input
              value={section}
              onChange={(e) => setSection(e.target.value)}
              placeholder="e.g., A, B, C"
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>
        )}
        <button
          type="submit"
          className="px-6 py-2.5 rounded-lg text-primary-foreground font-medium"
          style={{ background: "var(--gradient-nebula)" }}
        >
          🔗 Assign Subject
        </button>
      </form>
    </div>
  );
};

export default AssignSubject;