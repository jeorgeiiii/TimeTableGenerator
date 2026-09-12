// frontend/src/pages/AddTeacher.tsx
import { useState, useEffect, useCallback } from "react";
import { BRANCHES } from "@/lib/store";
import { toast } from "sonner";
import api from "../services/api";

interface Teacher {
  id: string | number;
  name: string;
  department: string;
  email?: string;
  max_hours_per_day?: number;
}

const AddTeacher = () => {
  const [name, setName] = useState("");
  const [department, setDepartment] = useState("");
  const [email, setEmail] = useState("");
  const [maxHours, setMaxHours] = useState(6);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [directoryBranch, setDirectoryBranch] = useState("");
  const [loadingDirectory, setLoadingDirectory] = useState(false);
  const [loadingTestData, setLoadingTestData] = useState(false);

  const loadTeachers = useCallback(async () => {
    try {
      const response = await api.get("/admin/teachers");
      setTeachers(response.data.teachers || []);
    } catch (error) {
      console.error("Error loading teachers:", error);
    }
  }, []);

  useEffect(() => {
    loadTeachers();
  }, [loadTeachers]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !department) { 
      toast.error("Name and Department are required"); 
      return; 
    }
    
    try {
      const response = await api.post("/admin/teachers", { name, email, department });
      if (response.data.success) {
        toast.success("Teacher added successfully!");
        setName("");
        setDepartment("");
        setEmail("");
        loadTeachers();
      } else {
        toast.error(response.data.message || "Failed to add teacher");
      }
    } catch (error) {
      toast.error("Failed to add teacher");
    }
  };

  const handleLoadDirectory = async () => {
    setLoadingDirectory(true);
    try {
      const response = await api.post("/admin/teachers/load-directory", {
        branch: directoryBranch || undefined,
      });
      const { added, skipped } = response.data;
      toast.success(`Loaded ${added} teacher(s) from the SGSITS directory (${skipped} already existed).`);
      loadTeachers();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to load teacher directory");
    } finally {
      setLoadingDirectory(false);
    }
  };

  const handleLoadTestData = async () => {
    setLoadingTestData(true);
    try {
      const response = await api.post("/admin/teachers/load-test-data", {
        branch: directoryBranch || undefined,
      });
      const { added, skipped } = response.data;
      toast.success(`Loaded ${added} fictional test teacher(s) (${skipped} already existed).`);
      loadTeachers();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to load test teachers");
    } finally {
      setLoadingTestData(false);
    }
  };

  return (
    <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
      <h2 className="text-2xl font-bold mb-6">👨‍🏫 Add New Teacher</h2>

      <div className="mb-6 p-4 rounded-lg bg-primary/10 border border-primary/30 flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
        <div>
          <p className="font-medium">⚡ Load SGSITS faculty directory</p>
          <p className="text-xs text-muted-foreground">
            Best-effort list gathered from public search results, not an official scrape - review names after loading.
            Uses the branch below, or loads every branch if left blank.
          </p>
          <select
            value={directoryBranch}
            onChange={e => setDirectoryBranch(e.target.value)}
            className="mt-2 px-3 py-1.5 rounded-lg bg-background/50 border border-border text-sm focus:ring-2 focus:ring-primary focus:outline-none"
          >
            <option value="">All branches</option>
            {BRANCHES.map((b, idx) => <option key={`dir-branch-${idx}`} value={b}>{b}</option>)}
          </select>
        </div>
        <button
          type="button"
          onClick={handleLoadDirectory}
          disabled={loadingDirectory}
          className="px-4 py-2 rounded-lg font-medium border border-primary/50 hover:bg-primary/20 disabled:opacity-50 whitespace-nowrap"
        >
          {loadingDirectory ? "Loading..." : "Load Directory"}
        </button>
      </div>

      <div className="mb-6 p-4 rounded-lg bg-muted/20 border border-border flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
        <div>
          <p className="font-medium">🧪 Load fictional test teachers</p>
          <p className="text-xs text-muted-foreground">
            Made-up names for testing (not real people) - 5 per branch, tagged "(Test Data)" so they're easy to spot/remove later.
            Uses the branch selected above, or loads every branch if left blank.
          </p>
        </div>
        <button
          type="button"
          onClick={handleLoadTestData}
          disabled={loadingTestData}
          className="px-4 py-2 rounded-lg font-medium border border-border hover:bg-muted/30 disabled:opacity-50 whitespace-nowrap"
        >
          {loadingTestData ? "Loading..." : "Load Test Teachers"}
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Teacher Name *</label>
            <input 
              value={name} 
              onChange={e => setName(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Department *</label>
            <select 
              value={department} 
              onChange={e => setDepartment(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select Department</option>
              {BRANCHES.map((b, idx) => <option key={`dept-${idx}`} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input 
              type="email" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Max Hours/Day</label>
            <input 
              type="number" 
              value={maxHours} 
              onChange={e => setMaxHours(Number(e.target.value))} 
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none" 
            />
          </div>
        </div>
        <button type="submit" className="px-6 py-2.5 rounded-lg text-primary-foreground font-medium" style={{ background: "var(--gradient-nebula)" }}>
          + Add Teacher
        </button>
      </form>

      {teachers.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-bold mb-4">📋 Existing Teachers</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Name</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Department</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Max Hours/Day</th>
                </tr>
              </thead>
              <tbody>
                {teachers.map((t, idx) => (
                  <tr key={`teacher-${t.id || idx}`} className="border-b border-border/50 hover:bg-muted/20">
                    <td className="py-3 px-4">{t.name}</td>
                    <td className="py-3 px-4">{t.department}</td>
                    <td className="py-3 px-4">{t.max_hours_per_day || 6}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddTeacher;