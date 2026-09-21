// frontend/src/pages/StudentDashboard.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { BRANCHES, YEARS, hasMultipleSections } from '@/lib/store';
import { toast } from "sonner";
import * as XLSX from 'xlsx';
import { Download, Eye, Loader2, Menu, RefreshCw } from "lucide-react";
import StarBackground from '../components/StarBackground';
import authService from '../services/auth.service';
import timetableService, { TimetableData } from '../services/timetable_service';

// Helper: convert "1st Year" / "2nd Year" etc. to an integer
const yearStringToNumber = (y: string): number => {
  const n = parseInt(y.replace(/\D/g, ''), 10);
  return isNaN(n) ? 1 : n;
};

// Semester options for a given year (Year 1 -> Sem 1/2, Year 2 -> Sem 3/4, ...)
const getSemesterOptions = (y: number): number[] => [y * 2 - 1, y * 2];

// Check whether the timetable matrix has any real class (not just "—" or lunch)
const hasTimetableData = (tt: TimetableData | null): boolean => {
  if (!tt || !tt.timetable || !tt.days || !tt.time_slots) return false;
  return tt.days.some(day =>
    tt.time_slots.some(slot => {
      const cell = tt.timetable[day]?.[slot] ?? '';
      return cell && cell !== '—' && !cell.includes('LUNCH');
    })
  );
};

const StudentDashboard: React.FC = () => {
  const [branch,   setBranch]   = useState("CSE");
  const [year,     setYear]     = useState("1st Year");
  const [semester, setSemester] = useState<number>(1);
  const [section,  setSection]  = useState("A");
  const [timetable, setTimetable] = useState<TimetableData | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const user = authService.getCurrentUser();

  // Only CSE/IT have multiple sections - everyone else is always Section A.
  const showSectionField = hasMultipleSections(branch);
  useEffect(() => {
    if (!hasMultipleSections(branch)) {
      setSection("A");
    }
  }, [branch]);

  // Reset semester to the first one for this year whenever year changes.
  useEffect(() => {
    setSemester(getSemesterOptions(yearStringToNumber(year))[0]);
  }, [year]);

  const loadTimetable = useCallback(async () => {
    setLoading(true);
    try {
      const yearNumber = yearStringToNumber(year);
      const data = await timetableService.viewTimetable(branch, yearNumber, section, semester);
      setTimetable(data);

      if (hasTimetableData(data)) {
        toast.success("Timetable loaded successfully!");
      } else {
        toast.info("No timetable found for this selection. Ask your admin to generate one.");
      }
    } catch (error: any) {
      console.error("Error loading timetable:", error);
      toast.error(error?.response?.data?.detail ?? "Failed to load timetable. Please try again.");
      setTimetable(null);
    } finally {
      setLoading(false);
      setHasLoaded(true);
    }
  }, [branch, section, year, semester]);

  // Auto-load on mount with the default selection
  useEffect(() => {
    loadTimetable();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentionally only on mount; user clicks "Load" to refresh

  const exportToExcel = () => {
    if (!timetable || !hasTimetableData(timetable)) {
      toast.error("No timetable data to export.");
      return;
    }

    const excelData: string[][] = [];
    excelData.push(["Time / Day", ...timetable.days]);

    for (const timeSlot of timetable.time_slots) {
      const row: string[] = [timeSlot];
      for (const day of timetable.days) {
        let cellValue = timetable.timetable[day]?.[timeSlot] ?? '—';
        cellValue = cellValue.replace(/<br\s*\/?>/gi, ' – ');
        row.push(cellValue === '—' ? '' : cellValue);
      }
      excelData.push(row);
    }

    const ws = XLSX.utils.aoa_to_sheet(excelData);
    ws['!cols'] = [
      { wch: 15 },
      ...timetable.days.map(() => ({ wch: 22 })),
    ];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(
      wb, ws,
      `TT_${branch}_Y${yearStringToNumber(year)}_${section}`
    );
    XLSX.writeFile(
      wb,
      `Timetable_${branch}_Year${yearStringToNumber(year)}_Section${section}.xlsx`
    );
    toast.success("Timetable exported to Excel!");
  };

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen relative">
      <StarBackground />

      <div className="relative z-10">
        {/* Header */}
        <header className="sticky top-0 z-30 border-b border-border bg-background/40 backdrop-blur-xl px-6 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(o => !o)}
              className="lg:hidden text-foreground"
              aria-label="Toggle sidebar"
            >
              <Menu size={24} />
            </button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                🎓 <span>Student Dashboard</span>
              </h1>
              <p className="text-sm text-muted-foreground">
                Welcome, {user?.full_name || user?.username}!
              </p>
            </div>
          </div>
        </header>

        <main className="p-6">
          <div className="space-y-6">

            {/* Controls */}
            <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border">
              <h2 className="text-2xl font-bold mb-6">👁️ View Your Timetable</h2>

              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
                {/* Branch */}
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

                {/* Year */}
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

                {/* Semester */}
                <div>
                  <label className="block text-sm font-medium mb-1">Semester</label>
                  <select
                    value={semester}
                    onChange={e => setSemester(parseInt(e.target.value))}
                    className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
                  >
                    {getSemesterOptions(yearStringToNumber(year)).map(s => (
                      <option key={s} value={s}>Semester {s}</option>
                    ))}
                  </select>
                </div>

                {/* Section - only CSE/IT run multiple sections */}
                {showSectionField && (
                  <div>
                    <label className="block text-sm font-medium mb-1">Section</label>
                    <input
                      type="text"
                      value={section}
                      onChange={e => setSection(e.target.value.toUpperCase())}
                      placeholder="A"
                      maxLength={2}
                      className="w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none"
                    />
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex gap-2 items-end">
                  <button
                    onClick={loadTimetable}
                    disabled={loading}
                    className="flex-1 px-6 py-2.5 rounded-lg text-primary-foreground font-medium flex items-center justify-center gap-2 disabled:opacity-60"
                    style={{ background: "var(--gradient-nebula)" }}
                  >
                    {loading
                      ? <><Loader2 className="w-4 h-4 animate-spin" /> Loading…</>
                      : <><Eye className="w-4 h-4" /> Load Timetable</>
                    }
                  </button>

                  {hasTimetableData(timetable) && (
                    <button
                      onClick={exportToExcel}
                      className="px-4 py-2.5 rounded-lg bg-green-600 text-white font-medium flex items-center gap-2 hover:bg-green-700 transition"
                      title="Export to Excel"
                    >
                      <Download className="w-4 h-4" />
                      Excel
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Timetable grid */}
            {loading && (
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border text-center">
                <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-primary" />
                <p className="text-muted-foreground">Loading timetable…</p>
              </div>
            )}

            {!loading && hasTimetableData(timetable) && timetable && (
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-8 border border-border overflow-x-auto">
                <h3 className="text-lg font-bold mb-4">
                  {timetable.branch} — Year {timetable.year} — Section {timetable.section}
                  {timetable.semester ? ` (Semester ${timetable.semester})` : ''}
                </h3>

                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-gradient-to-r from-primary to-accent text-white">
                      <th className="py-3 px-3 text-left border whitespace-nowrap">Time / Day</th>
                      {timetable.days.map((day: string) => (
                        <th key={day} className="py-3 px-3 text-center border whitespace-nowrap">
                          {day}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {timetable.time_slots.map((slot: string, idx: number) => (
                      <tr key={slot} className="border-b border-border/50 hover:bg-muted/20">
                        <td className="py-3 px-3 font-medium border whitespace-nowrap">{slot}</td>
                        {timetable.days.map((day: string) => {
                          const cell = timetable.timetable?.[day]?.[slot] ?? '—';
                          const isLunch = cell.includes('LUNCH');
                          const isEmpty = cell === '—';
                          // A 2-hour lab fills two consecutive slots with the same
                          // cell: draw it once, spanning both rows.
                          const isLab = cell.includes('Lab');
                          const prevCell = idx > 0 ? timetable.timetable?.[day]?.[timetable.time_slots[idx - 1]] : undefined;
                          const nextCell = timetable.timetable?.[day]?.[timetable.time_slots[idx + 1]];
                          if (isLab && prevCell === cell) return null;
                          const rowSpan = isLab && nextCell === cell ? 2 : 1;
                          return (
                            <td
                              key={day}
                              rowSpan={rowSpan}
                              className={`py-3 px-3 text-center border ${
                                isLunch
                                  ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 font-medium'
                                  : isEmpty
                                  ? 'text-muted-foreground/40'
                                  : 'text-foreground'
                              }`}
                              dangerouslySetInnerHTML={{ __html: cell }}
                            />
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Empty state — only show after at least one load attempt */}
            {!loading && hasLoaded && !hasTimetableData(timetable) && (
              <div className="bg-card/60 backdrop-blur-md rounded-xl p-10 border border-border text-center space-y-3">
                <p className="text-4xl">📭</p>
                <p className="text-lg font-semibold">No timetable found</p>
                <p className="text-muted-foreground text-sm max-w-md mx-auto">
                  No timetable has been generated yet for{' '}
                  <strong>{branch} — {year} — Section {section}</strong>.
                  Please ask your administrator to generate one, then click{' '}
                  <strong>Load Timetable</strong> again.
                </p>
                <button
                  onClick={loadTimetable}
                  className="mt-2 inline-flex items-center gap-2 px-5 py-2 rounded-lg border border-border hover:bg-muted/30 transition text-sm"
                >
                  <RefreshCw className="w-4 h-4" /> Retry
                </button>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default StudentDashboard;
