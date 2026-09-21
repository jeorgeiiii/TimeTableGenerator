// frontend/src/pages/GenerateTimetable.tsx
import { useState, useEffect, useCallback } from "react";
import { BRANCHES, YEARS, hasMultipleSections } from "@/lib/store";
import { toast } from "sonner";
import * as XLSX from 'xlsx';
import { Download, Calendar, Loader2, RotateCcw } from "lucide-react";
import api from "../services/api";

// Semester mapping based on year
const getSemestersForYear = (year: string) => {
  const yearNum = parseInt(year);
  if (yearNum === 1) return [{ value: 1, label: "Semester 1" }, { value: 2, label: "Semester 2" }];
  if (yearNum === 2) return [{ value: 3, label: "Semester 3" }, { value: 4, label: "Semester 4" }];
  if (yearNum === 3) return [{ value: 5, label: "Semester 5" }, { value: 6, label: "Semester 6" }];
  if (yearNum === 4) return [{ value: 7, label: "Semester 7" }, { value: 8, label: "Semester 8" }];
  return [{ value: 1, label: "Semester 1" }, { value: 2, label: "Semester 2" }];
};

interface TimetableData {
  branch: string;
  year: number;
  section: string;
  semester?: number;
  days: string[];
  time_slots: string[];
  timetable: Record<string, Record<string, string>>;
}

const GenerateTimetable = () => {
  const [branch, setBranch] = useState("CSE");
  const [year, setYear] = useState("1");
  const [semester, setSemester] = useState(1);
  const [section, setSection] = useState("A");
  const [timetable, setTimetable] = useState<TimetableData | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [resetting, setResetting] = useState(false);

  // Get available semesters based on selected year
  const availableSemesters = getSemestersForYear(year);

  // Reset semester when year changes
  useEffect(() => {
    setSemester(availableSemesters[0]?.value || 1);
  }, [availableSemesters]);

  // Only CSE/IT have multiple sections - everyone else is always Section A.
  const showSectionField = hasMultipleSections(branch);
  useEffect(() => {
    if (!hasMultipleSections(branch)) {
      setSection("A");
    }
  }, [branch]);

  const loadTimetable = useCallback(async () => {
    setLoading(true);
    try {
      const yearNumber = parseInt(year);
      const response = await api.get("/timetable/view", {
        params: {
          branch,
          year: yearNumber,
          section,
          semester
        }
      });
     setTimetable(response.data || null);
    } catch (error) {
      console.error("Error loading timetable:", error);
      toast.error("Failed to load timetable");
    } finally {
      setLoading(false);
    }
  }, [branch, year, section, semester]);

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    try {
      const yearNumber = parseInt(year);
      const response = await api.post("/timetable/generate", {
        branch,
        year: yearNumber,
        section,
        semester
      });

      if (response.data.success) {
        toast.success(response.data.message || "Timetable generated successfully");
        await loadTimetable();
      } else {
        toast.error(response.data.message || "Generation failed");
      }
    } catch (error) {
      console.error("Generation error:", error);
      toast.error("Failed to generate timetable");
    } finally {
      setGenerating(false);
    }
  }, [branch, year, section, semester, loadTimetable]);

  const handleReset = useCallback(async () => {
    if (!confirm("This clears EVERY generated timetable (all branches, years and sections) so you can regenerate from scratch. Teachers, subjects and assignments are kept. Continue?")) {
      return;
    }
    setResetting(true);
    try {
      const response = await api.post("/admin/reset-timetables");
      toast.success(response.data.message || "Timetables reset");
      await loadTimetable();
    } catch (error: any) {
      console.error("Reset error:", error);
      toast.error(error?.response?.data?.detail || "Failed to reset timetables");
    } finally {
      setResetting(false);
    }
  }, [loadTimetable]);

  useEffect(() => {
    // Auto-load timetable when component mounts
    loadTimetable();
  }, [loadTimetable]);

  const exportToExcel = () => {
    if (!timetable) return;

    const excelData: string[][] = [];
    const headerRow = ["Time / Day", ...timetable.days];
    excelData.push(headerRow);
    
    for (const timeSlot of timetable.time_slots) {
      const row: string[] = [timeSlot];
      for (const day of timetable.days) {
        let cellValue = timetable.timetable[day][timeSlot];
        if (cellValue && cellValue.includes('<br>')) {
          cellValue = cellValue.replace('<br>', ' - ');
        }
        row.push(cellValue === '—' ? '' : cellValue);
      }
      excelData.push(row);
    }
    
    const ws = XLSX.utils.aoa_to_sheet(excelData);
    ws['!cols'] = [{wch:15}, {wch:20}, {wch:20}, {wch:20}, {wch:20}, {wch:20}, {wch:20}];
    const wb = XLSX.utils.book_new();
    
    let sheetName = `TT_${branch}_Y${year}_Sem${semester}_${section}`;
    if (sheetName.length > 31) {
      sheetName = sheetName.substring(0, 31);
    }
    
    XLSX.utils.book_append_sheet(wb, ws, sheetName);
    
    let fileName = `Timetable_${branch}_Year${year}_Sem${semester}_Section${section}.xlsx`;
    if (fileName.length > 100) {
      fileName = `TT_${branch}_Y${year}_S${semester}_${section}.xlsx`;
    }
    
    XLSX.writeFile(wb, fileName);
    toast.success("Timetable exported to Excel!");
  };

  if (loading) {
    return (
      <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border text-center">
        <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-primary" />
        <p className="text-muted-foreground">Loading timetable...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
        <h2 className="text-2xl font-bold mb-6">⚡ Generate Automatic Timetable</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium mb-1">Branch</label>
            <select 
              value={branch} 
              onChange={e => setBranch(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              {BRANCHES.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Year</label>
            <select 
              value={year} 
              onChange={e => setYear(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="1">1st Year</option>
              <option value="2">2nd Year</option>
              <option value="3">3rd Year</option>
              <option value="4">4th Year</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Semester</label>
            <select 
              value={semester} 
              onChange={e => setSemester(parseInt(e.target.value))}
              className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
            >
              {availableSemesters.map(sem => (
                <option key={sem.value} value={sem.value}>{sem.label}</option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground mt-1">
              {year === "1" && "Year 1 → Semester 1 or 2"}
              {year === "2" && "Year 2 → Semester 3 or 4"}
              {year === "3" && "Year 3 → Semester 5 or 6"}
              {year === "4" && "Year 4 → Semester 7 or 8"}
            </p>
          </div>
          
          {showSectionField && (
            <div>
              <label className="block text-sm font-medium mb-1">Section</label>
              <input
                type="text"
                value={section}
                onChange={e => setSection(e.target.value.toUpperCase())}
                placeholder="A"
                className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
              />
            </div>
          )}

          <div className="flex gap-2 items-end">
            <button 
              onClick={handleGenerate}
              disabled={generating}
              className="flex-1 px-6 py-2.5 rounded-lg text-primary-foreground font-medium flex items-center justify-center gap-2"
              style={{ background: "var(--gradient-nebula)" }}
            >
              {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calendar className="w-4 h-4" />}
              {generating ? "Generating..." : "Generate"}
            </button>
            <button
              onClick={handleReset}
              disabled={resetting || generating}
              className="px-4 py-2.5 rounded-lg bg-red-600 text-white font-medium flex items-center gap-2 hover:bg-red-700 transition disabled:opacity-50"
            >
              {resetting ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
              {resetting ? "Resetting..." : "Reset"}
            </button>
            {timetable && (
              <button 
                onClick={exportToExcel}
                className="px-6 py-2.5 rounded-lg bg-green-600 text-white font-medium flex items-center gap-2 hover:bg-green-700 transition"
              >
                <Download className="w-4 h-4" />
                Excel
              </button>
            )}
          </div>
        </div>
      </div>

      {timetable && timetable.days?.length > 0 && (
        <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border overflow-x-auto">
          <h3 className="text-lg font-bold mb-4">
            {timetable.branch} - Year {timetable.year} - Semester {semester} - Section {timetable.section}
          </h3>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gradient-to-r from-primary to-accent text-white">
                <th className="py-3 px-3 text-left border">Time / Day</th>
                {timetable.days?.map((day: string) => (
                  <th key={day} className="py-3 px-3 text-center border">{day}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {timetable.time_slots?.map((slot: string, idx: number) => (
                <tr key={slot} className="border-b border-border/50 hover:bg-muted/20">
                  <td className="py-3 px-3 font-medium border">{slot}</td>
                  {timetable.days?.map((day: string) => {
                    const cell = timetable.timetable[day][slot];
                    const isLunch = slot === '13:00-14:00';
                    // A 2-hour lab fills two consecutive slots with the same
                    // cell: draw it once, spanning both rows.
                    const isLab = cell?.includes('Lab');
                    const prevCell = idx > 0 ? timetable.timetable[day][timetable.time_slots[idx - 1]] : undefined;
                    const nextCell = timetable.timetable[day][timetable.time_slots[idx + 1]];
                    if (isLab && prevCell === cell) return null;
                    const rowSpan = isLab && nextCell === cell ? 2 : 1;
                    return (
                      <td key={day} rowSpan={rowSpan} className={`py-3 px-3 text-center border ${isLunch ? 'bg-yellow-500/10' : ''}`}>
                        {isLunch ? (
                          <span className="text-yellow-600 font-medium">🍽️ LUNCH BREAK</span>
                        ) : cell !== '—' ? (
                          <div dangerouslySetInnerHTML={{ __html: cell }} />
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                        {!isLunch && cell !== '—' && (
                          <div className="text-xs text-muted-foreground mt-1">
                            &nbsp;
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {timetable && timetable.days?.length === 0 && (
        <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border text-center">
          <p className="text-muted-foreground">No timetable entries found. Click Generate to create one.</p>
        </div>
      )}
    </div>
  );
};

export default GenerateTimetable;