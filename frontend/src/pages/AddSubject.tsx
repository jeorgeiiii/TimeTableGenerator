// frontend/src/pages/AddSubject.tsx
import { useState, useEffect } from "react";
import { BRANCHES } from "@/lib/store";
import { toast } from "sonner";
import api from "../services/api";

const AddSubject = () => {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [branch, setBranch] = useState("");
  const [year, setYear] = useState<number>(1);
  const [semester, setSemester] = useState<number>(1);
  const [credits, setCredits] = useState(3);
  const [hours, setHours] = useState(3);
  const [isLab, setIsLab] = useState(false);
  const [isElective, setIsElective] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingCurriculum, setLoadingCurriculum] = useState(false);

  // Semester options based on year
  const getSemesterOptions = () => {
    if (year === 1) return [1, 2];
    if (year === 2) return [3, 4];
    if (year === 3) return [5, 6];
    if (year === 4) return [7, 8];
    return [1, 2];
  };

  // Reset semester when year changes
  useEffect(() => {
    const semesters = getSemesterOptions();
    setSemester(semesters[0]);
  }, [year]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!code) {
      toast.error("Subject Code is required");
      return;
    }
    if (!name) {
      toast.error("Subject Name is required");
      return;
    }
    if (!branch) {
      toast.error("Branch is required");
      return;
    }

    setLoading(true);

    try {
      const token = localStorage.getItem('token');

      const requestData = {
        code: code.toUpperCase(),
        name: name,
        branch: branch,
        year: year,
        semester: semester,
        credits: credits,
        hours_per_week: hours,
        is_lab: isLab,
        is_elective: isElective,
      };

      console.log("Sending subject data:", JSON.stringify(requestData, null, 2));

      const response = await api.post("/admin/subjects", requestData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log("Response:", response.data);

      if (response.data.success) {
        toast.success(`Subject "${name}" added successfully! Use Assign Subject to give it a teacher.`);
        // Reset form
        setCode("");
        setName("");
        setBranch("");
        setYear(1);
        setSemester(1);
        setCredits(3);
        setHours(3);
        setIsLab(false);
        setIsElective(false);
      } else {
        toast.error(response.data.message || "Failed to add subject");
      }
    } catch (error: any) {
      console.error("Error adding subject:", error);
      if (error.response) {
        console.error("Response data:", error.response.data);
        const errorMsg = error.response.data?.detail || error.response.data?.message || "Server error";
        toast.error(errorMsg);
      } else if (error.request) {
        toast.error("No response from server. Check if backend is running.");
      } else {
        toast.error("Failed to add subject. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLoadCurriculum = async () => {
    setLoadingCurriculum(true);
    try {
      const response = await api.post("/admin/subjects/load-curriculum", {
        branch: branch || undefined,
        year: branch ? year : undefined,
      });
      const { added, skipped } = response.data;
      toast.success(`Loaded ${added} subject(s) from the official curriculum (${skipped} already existed).`);
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || "Failed to load curriculum";
      toast.error(errorMsg);
    } finally {
      setLoadingCurriculum(false);
    }
  };

  return (
    <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
      <h2 className="text-2xl font-bold mb-6">📚 Add New Subject</h2>

      <div className="mb-6 p-4 rounded-lg bg-primary/10 border border-primary/30 flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
        <div>
          <p className="font-medium">⚡ Auto-load official SGSITS subjects</p>
          <p className="text-xs text-muted-foreground">
            Fills in subjects from the built-in curriculum (no teacher assigned yet — use "Assign Subject" after).
            Uses the Branch/Year selected below, or loads every branch if left blank.
          </p>
        </div>
        <button
          type="button"
          onClick={handleLoadCurriculum}
          disabled={loadingCurriculum}
          className="px-4 py-2 rounded-lg font-medium border border-primary/50 hover:bg-primary/20 disabled:opacity-50 whitespace-nowrap"
        >
          {loadingCurriculum ? "Loading..." : "Load Curriculum"}
        </button>
      </div>

      <p className="mb-4 p-3 bg-muted/20 border border-border rounded-lg text-sm text-muted-foreground">
        This only creates the subject record. Assign a teacher and section afterwards on the "Assign Subject" page.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Subject Code *</label>
            <input
              value={code}
              onChange={e => setCode(e.target.value.toUpperCase())}
              placeholder="e.g., EE301, CS201"
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Subject Name *</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g., Power System, Data Structures"
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Branch *</label>
            <select
              value={branch}
              onChange={e => setBranch(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Branch</option>
              {BRANCHES.map((b, idx) => <option key={`branch-${idx}`} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Year *</label>
            <select
              value={year}
              onChange={e => setYear(parseInt(e.target.value))}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="1">1st Year</option>
              <option value="2">2nd Year</option>
              <option value="3">3rd Year</option>
              <option value="4">4th Year</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Semester *</label>
            <select
              value={semester}
              onChange={e => setSemester(parseInt(e.target.value))}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              {getSemesterOptions().map(s => (
                <option key={s} value={s}>Semester {s}</option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground mt-1">
              {year === 1 && "1st Year → Semester 1 or 2"}
              {year === 2 && "2nd Year → Semester 3 or 4"}
              {year === 3 && "3rd Year → Semester 5 or 6"}
              {year === 4 && "4th Year → Semester 7 or 8"}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Credits</label>
            <input
              type="number"
              value={credits}
              onChange={e => setCredits(Number(e.target.value))}
              min="1"
              max="6"
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Hours/Week</label>
            <input
              type="number"
              value={hours}
              onChange={e => setHours(Number(e.target.value))}
              min="1"
              max="8"
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-3 pt-6">
            <input
              type="checkbox"
              checked={isLab}
              onChange={e => setIsLab(e.target.checked)}
              className="w-4 h-4 rounded border-border"
            />
            <label className="text-sm font-medium">Is Lab Course?</label>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={isElective}
              onChange={e => setIsElective(e.target.checked)}
              className="w-4 h-4 rounded border-border"
            />
            <label className="text-sm font-medium">Is Elective?</label>
          </div>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-2.5 rounded-lg text-primary-foreground font-medium disabled:opacity-50"
          style={{ background: "var(--gradient-nebula)" }}
        >
          {loading ? "Adding..." : "+ Add Subject"}
        </button>
      </form>
    </div>
  );
};

export default AddSubject;
