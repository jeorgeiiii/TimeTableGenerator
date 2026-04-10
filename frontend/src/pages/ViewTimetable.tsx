// frontend/src/pages/ViewTimetable.tsx
import { useState, useEffect, useCallback } from "react";
import { BRANCHES, YEARS } from "@/lib/store";
import { toast } from "sonner";
import * as XLSX from 'xlsx';
import { Download, Eye, Loader2 } from "lucide-react";
import timetableService, { TimetableData } from '../services/timetable_service';

const ViewTimetable = () => {
  const [branch, setBranch] = useState("CSE");
  const [year, setYear] = useState("1st Year");
  const [section, setSection] = useState("A");
  const [timetable, setTimetable] = useState<TimetableData | null>(null);
  const [loading, setLoading] = useState(false);

  const loadTimetable = useCallback(async () => {
    setLoading(true);
    try {
      // Convert "1st Year" to 1, "2nd Year" to 2, etc.
      const yearNumber = parseInt(year.replace(/\D/g, ''));
      const data = await timetableService.viewTimetable(branch, yearNumber, section);
      setTimetable(data);
      if (data.branch) {
        toast.success("Timetable loaded!");
      }
    } catch (error) {
      console.error("Error loading timetable:", error);
      toast.error("Failed to load timetable");
    } finally {
      setLoading(false);
    }
  }, [branch, section, year]);

  const exportToExcel = () => {
    if (!timetable) return;

    const excelData: string[][] = [];
    const headerRow: string[] = ["Time / Day", ...timetable.days];
    excelData.push(headerRow);
    
    for (const timeSlot of timetable.time_slots) {
      const row: string[] = [timeSlot];
      for (const day of timetable.days) {
        const dayData = timetable.timetable?.[day];
        let cellValue = dayData?.[timeSlot] || '—';
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
    XLSX.utils.book_append_sheet(wb, ws, `Timetable_${branch}_Year${year}_Section${section}`);
    XLSX.writeFile(wb, `Timetable_${branch}_Year${year}_Section${section}.xlsx`);
    toast.success("Timetable exported to Excel!");
  };

  useEffect(() => {
    loadTimetable();
  }, [loadTimetable]);

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
        <h2 className="text-2xl font-bold mb-6">👁️ View Timetable</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
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
              {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
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
          <div className="flex gap-2 items-end">
            <button 
              onClick={loadTimetable}
              className="flex-1 px-6 py-2.5 rounded-lg text-primary-foreground font-medium flex items-center justify-center gap-2"
              style={{ background: "var(--gradient-nebula)" }}
            >
              <Eye className="w-4 h-4" />
              Load Timetable
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

      {timetable && timetable.days && (
        <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border overflow-x-auto">
          <h3 className="text-lg font-bold mb-4">
            {timetable.branch} - {timetable.year} - Section {timetable.section}
          </h3>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gradient-to-r from-primary to-accent text-white">
                <th className="py-3 px-3 text-left border">Time / Day</th>
                {timetable.days.map((day: string) => (
                  <th key={day} className="py-3 px-3 text-center border">{day}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {timetable.time_slots.map((slot: string) => (
                <tr key={slot} className="border-b border-border/50 hover:bg-muted/20">
                  <td className="py-3 px-3 font-medium border">{slot}</td>
                  {timetable.days.map((day: string) => {
                    const dayData = timetable.timetable?.[day];
                    const cell = dayData?.[slot] || '—';
                    const isLunch = slot === '12:00-13:00';
                    return (
                      <td key={day} className={`py-3 px-3 text-center border ${isLunch ? 'bg-yellow-500/10' : ''}`}>
                        {isLunch ? (
                          <span className="text-yellow-600 font-medium">🍽️ LUNCH BREAK</span>
                        ) : cell !== '—' ? (
                          <div dangerouslySetInnerHTML={{ __html: cell }} />
                        ) : (
                          <span className="text-muted-foreground">—</span>
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
    </div>
  );
};

export default ViewTimetable;