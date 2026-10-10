// frontend/src/pages/CreditSystem.tsx
// SGSITS Choice Based Credit System: per-branch 8-semester credit scheme,
// a branch-vs-branch comparison, the institute's grading rules, and an
// SGPA/CGPA calculator. Data comes from the backend's credit_system.py.
import { useEffect, useMemo, useState } from "react";
import { Loader2, Plus, Trash2, Calculator } from "lucide-react";
import { toast } from "sonner";
import { BRANCHES } from "@/lib/store";
import api from "../services/api";
import authService from "../services/auth.service";
import CreditManager from "./CreditManager";

interface CreditSubject {
  code: string;
  name: string;
  credits: number;
  hours_per_week: number;
  is_lab: boolean;
  is_elective: boolean;
  category: string;
}

interface CreditSemester {
  semester: number;
  year: number;
  subjects: CreditSubject[];
  total_credits: number;
  theory_credits: number;
  lab_credits: number;
  contact_hours: number;
}

interface CreditScheme {
  branch: string;
  semesters: CreditSemester[];
  total_credits: number;
  credits_by_category: Record<string, number>;
  peak_semester: number;
  peak_credits: number;
}

interface BranchOverview {
  branch: string;
  semester_credits: Record<string, number>;
  total_credits: number;
  peak_semester: number;
}

interface Grading {
  grades: { grade: string; min_marks: number; max_marks: number; grade_point: number; description: string }[];
  divisions: { min_cgpa: number; division: string }[];
  min_cgpa_for_degree: number;
  assessment: { theory: Record<string, number>; practical: Record<string, number> };
  marks_scheme?: {
    theory_total: number;
    end_semester_exam: number;
    internal: number;
    internal_parts: { name: string; marks: number }[];
    pass_theory: number;
    pass_total: number;
  };
  passing_rules?: string[];
  categories: Record<string, string>;
  rules: string[];
}

interface CalcRow { credits: number; grade: string }

const SEMESTERS = [1, 2, 3, 4, 5, 6, 7, 8];
const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"];

const card = "bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border";
const select = "w-full px-4 py-2.5 rounded-lg bg-background/50 border border-border focus:ring-2 focus:ring-primary focus:outline-none";

const CreditSystem = () => {
  const [branch, setBranch] = useState("CSE");
  const [scheme, setScheme] = useState<CreditScheme | null>(null);
  const [overview, setOverview] = useState<BranchOverview[]>([]);
  const [grading, setGrading] = useState<Grading | null>(null);
  const [openSem, setOpenSem] = useState<number>(1);
  const [hoverSem, setHoverSem] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<"live" | "reference">("live");
  const canEdit = authService.getCurrentUser()?.role === "admin";

  useEffect(() => {
    api.get("/credits/overview").then(r => setOverview(r.data.branches)).catch(() => toast.error("Could not load branch credit overview"));
    api.get("/credits/grading").then(r => setGrading(r.data)).catch(() => toast.error("Could not load grading rules"));
  }, []);

  useEffect(() => {
    setLoading(true);
    api.get(`/credits/scheme/${branch}`)
      .then(r => setScheme(r.data))
      .catch(() => toast.error(`Could not load the ${branch} credit scheme`))
      .finally(() => setLoading(false));
  }, [branch]);

  const maxCredits = useMemo(
    () => Math.max(26, ...(scheme?.semesters.map(s => s.total_credits) ?? [0])),
    [scheme]
  );
  // Heat-table scale: one hue, darker = more credits, across all branches.
  const [heatMin, heatMax] = useMemo(() => {
    const vals = overview.flatMap(o => Object.values(o.semester_credits));
    return vals.length ? [Math.min(...vals), Math.max(...vals)] : [0, 1];
  }, [overview]);

  const activeSemester = scheme?.semesters.find(s => s.semester === openSem);

  return (
    <div className="space-y-6">
      {/* Header + branch picker */}
      <div className={card}>
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white">🎓 Credit System (CBCS)</h2>
            <p className="text-sm text-gray-300 mt-1 max-w-2xl">
              SGSITS B.Tech credits per subject and semester across all 4 years. 1 hour of lecture or tutorial
              per week = 1 credit, 2 hours of practical = 1 credit.
            </p>
          </div>
          <div className="w-full md:w-48">
            <label className="block text-sm font-medium mb-1 text-gray-300">Branch</label>
            <select value={branch} onChange={e => setBranch(e.target.value)} className={select}>
              {BRANCHES.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
        </div>
        <div className="inline-flex rounded-lg border border-border bg-background/40 p-1 mt-4">
          {([["live", canEdit ? "Manage credits" : "Current credits"], ["reference", "SGSITS reference scheme"]] as const).map(([id, label]) => (
            <button key={id} onClick={() => setView(id)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${view === id ? "bg-primary text-primary-foreground" : "text-gray-300 hover:text-white"}`}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {view === "live" && <CreditManager branch={branch} canEdit={canEdit} />}

      {view === "reference" && loading && !scheme && (
        <div className={`${card} flex items-center justify-center gap-2 text-gray-300`}>
          <Loader2 className="w-5 h-5 animate-spin" /> Loading credit scheme…
        </div>
      )}

      {view === "reference" && scheme && (
        <>
          {/* Stat tiles */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Total credits (8 sem)", value: scheme.total_credits },
              { label: "Heaviest semester", value: `Sem ${ROMAN[scheme.peak_semester - 1]}`, sub: `${scheme.peak_credits} credits` },
              { label: "Avg per semester", value: (scheme.total_credits / 8).toFixed(1) },
              { label: "Min CGPA for degree", value: grading?.min_cgpa_for_degree?.toFixed(1) ?? "5.0" },
            ].map(t => (
              <div key={t.label} className={card}>
                <p className="text-xs uppercase tracking-wide text-gray-400">{t.label}</p>
                <p className="text-3xl font-bold text-white mt-1">{t.value}</p>
                {t.sub && <p className="text-sm text-gray-400">{t.sub}</p>}
              </div>
            ))}
          </div>

          {/* Per-semester bar chart - click a bar to open that semester */}
          <div className={card}>
            <h3 className="text-lg font-bold text-white">{scheme.branch} credits per semester</h3>
            <p className="text-sm text-gray-400 mb-4">Click a semester to see its subjects.</p>
            <div className="relative h-56 flex items-end gap-2 sm:gap-4 border-b border-border">
              {scheme.semesters.map(s => {
                const pct = (s.total_credits / maxCredits) * 100;
                const active = s.semester === openSem;
                return (
                  <button
                    key={s.semester}
                    onClick={() => setOpenSem(s.semester)}
                    onMouseEnter={() => setHoverSem(s.semester)}
                    onMouseLeave={() => setHoverSem(null)}
                    onFocus={() => setHoverSem(s.semester)}
                    onBlur={() => setHoverSem(null)}
                    className="relative flex-1 h-full flex flex-col justify-end items-center group focus:outline-none"
                    aria-label={`Semester ${s.semester}: ${s.total_credits} credits`}
                  >
                    <span className="text-xs font-semibold text-gray-200 mb-1">{s.total_credits}</span>
                    <span
                      className={`w-full max-w-[56px] rounded-t transition-opacity bg-primary ${active ? "opacity-100" : "opacity-60 group-hover:opacity-90"}`}
                      style={{ height: `${pct}%` }}
                    />
                    {hoverSem === s.semester && (
                      <span className="absolute bottom-full mb-2 z-10 whitespace-nowrap rounded-md border border-border bg-background/95 px-3 py-2 text-left text-xs text-gray-200 shadow-lg">
                        <strong className="block text-white">Semester {ROMAN[s.semester - 1]} · Year {s.year}</strong>
                        {s.total_credits} credits · {s.subjects.length} subjects<br />
                        Theory {s.theory_credits} · Lab/Project {s.lab_credits}<br />
                        {s.contact_hours} contact hrs/week
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
            <div className="flex gap-2 sm:gap-4 mt-2">
              {scheme.semesters.map(s => (
                <span key={s.semester} className={`flex-1 text-center text-xs ${s.semester === openSem ? "text-white font-semibold" : "text-gray-400"}`}>
                  Sem {ROMAN[s.semester - 1]}
                </span>
              ))}
            </div>
          </div>

          {/* Subject table for the selected semester */}
          {activeSemester && (
            <div className={`${card} overflow-x-auto`}>
              <div className="flex flex-wrap items-baseline justify-between gap-2 mb-4">
                <h3 className="text-lg font-bold text-white">
                  Semester {ROMAN[activeSemester.semester - 1]} — {activeSemester.total_credits} credits
                </h3>
                <div className="flex gap-1 flex-wrap">
                  {SEMESTERS.map(n => (
                    <button
                      key={n}
                      onClick={() => setOpenSem(n)}
                      className={`px-2.5 py-1 rounded text-xs border ${n === openSem ? "bg-primary text-primary-foreground border-primary" : "border-border text-gray-300 hover:bg-muted/30"}`}
                    >
                      {ROMAN[n - 1]}
                    </button>
                  ))}
                </div>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-border">
                    <th className="py-2 pr-3 font-medium">Code</th>
                    <th className="py-2 pr-3 font-medium">Subject</th>
                    <th className="py-2 pr-3 font-medium">Category</th>
                    <th className="py-2 pr-3 font-medium text-right">Hrs/week</th>
                    <th className="py-2 font-medium text-right">Credits</th>
                  </tr>
                </thead>
                <tbody>
                  {activeSemester.subjects.map(sub => (
                    <tr key={sub.code} className="border-b border-border/50 text-gray-200">
                      <td className="py-2 pr-3 font-mono text-xs text-gray-400">{sub.code}</td>
                      <td className="py-2 pr-3">
                        {sub.name}
                        {sub.is_lab && <span className="ml-2 text-[10px] uppercase tracking-wide text-gray-400 border border-border rounded px-1">Lab</span>}
                        {sub.is_elective && <span className="ml-2 text-[10px] uppercase tracking-wide text-gray-400 border border-border rounded px-1">Elective</span>}
                      </td>
                      <td className="py-2 pr-3 text-gray-400" title={grading?.categories[sub.category]}>
                        {sub.category}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{sub.hours_per_week}</td>
                      <td className="py-2 text-right tabular-nums font-semibold text-white">
                        {sub.credits === 0 ? <span className="text-gray-400 font-normal">0 (audit)</span> : sub.credits}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="text-white font-semibold">
                    <td className="pt-3" colSpan={3}>Total</td>
                    <td className="pt-3 text-right tabular-nums">{activeSemester.contact_hours}</td>
                    <td className="pt-3 text-right tabular-nums">{activeSemester.total_credits}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}

          {/* Credits by category */}
          {grading && (
            <div className={card}>
              <h3 className="text-lg font-bold text-white mb-3">{scheme.branch} credits by category (4 years)</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {Object.entries(scheme.credits_by_category)
                  .sort((a, b) => b[1] - a[1])
                  .map(([cat, cr]) => (
                    <div key={cat} className="rounded-lg border border-border bg-background/30 p-3">
                      <p className="text-xs text-gray-400">{grading.categories[cat] ?? cat}</p>
                      <p className="text-xl font-bold text-white">{cr}</p>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Branch comparison heat table */}
      {view === "reference" && overview.length > 0 && (
        <div className={`${card} overflow-x-auto`}>
          <h3 className="text-lg font-bold text-white">All branches: credits per semester</h3>
          <p className="text-sm text-gray-400 mb-4">Darker cells mean more credits. Each branch peaks in a different semester.</p>
          <table className="w-full text-sm border-separate" style={{ borderSpacing: 2 }}>
            <thead>
              <tr className="text-gray-400">
                <th className="text-left font-medium px-2 py-1">Branch</th>
                {SEMESTERS.map(n => <th key={n} className="font-medium px-2 py-1">{ROMAN[n - 1]}</th>)}
                <th className="font-medium px-2 py-1 text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {overview.map(o => (
                <tr key={o.branch}>
                  <td className={`px-2 py-1.5 font-semibold ${o.branch === branch ? "text-white" : "text-gray-300"}`}>
                    <button onClick={() => setBranch(o.branch)} className="hover:underline">{o.branch}</button>
                  </td>
                  {SEMESTERS.map(n => {
                    const v = o.semester_credits[String(n)] ?? 0;
                    const t = heatMax > heatMin ? (v - heatMin) / (heatMax - heatMin) : 0;
                    return (
                      <td
                        key={n}
                        className={`px-2 py-1.5 text-center tabular-nums rounded ${t > 0.5 ? "text-primary-foreground font-semibold" : "text-white"}`}
                        style={{ backgroundColor: `hsl(var(--primary) / ${0.12 + t * 0.73})` }}
                        title={`${o.branch} Sem ${ROMAN[n - 1]}: ${v} credits${n === o.peak_semester ? " (peak)" : ""}`}
                      >
                        {v}{n === o.peak_semester && <span className="text-[10px] align-top">▲</span>}
                      </td>
                    );
                  })}
                  <td className="px-2 py-1.5 text-right tabular-nums font-semibold text-white">{o.total_credits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {grading && <GradingAndCalculator grading={grading} scheme={scheme} />}
    </div>
  );
};

const GradingAndCalculator = ({ grading, scheme }: { grading: Grading; scheme: CreditScheme | null }) => {
  const [rows, setRows] = useState<CalcRow[][]>([[{ credits: 4, grade: "A" }]]);
  const [result, setResult] = useState<{ semesters: { sgpa: number; credits_registered: number; credits_earned: number }[]; cgpa: number; division: string; eligible_for_degree: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const gradeOptions = [...grading.grades.map(g => g.grade), "I"];

  const prefillFromScheme = () => {
    if (!scheme) return;
    // One calculator semester per scheme semester, credited subjects only.
    setRows(scheme.semesters.map(s =>
      s.subjects.filter(sub => sub.credits > 0).map(sub => ({ credits: sub.credits, grade: "A" }))
    ));
    setResult(null);
  };

  const update = (si: number, ri: number, patch: Partial<CalcRow>) =>
    setRows(rs => rs.map((sem, i) => i !== si ? sem : sem.map((r, j) => j !== ri ? r : { ...r, ...patch })));

  const calculate = async () => {
    setBusy(true);
    try {
      const r = await api.post("/credits/calculate", { semesters: rows });
      setResult(r.data);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Calculation failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className={`${card} space-y-5`}>
        <div>
          <h3 className="text-lg font-bold text-white mb-3">Grading system (UG)</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-border">
                <th className="py-1.5 font-medium">Grade</th>
                <th className="py-1.5 font-medium">Marks</th>
                <th className="py-1.5 font-medium text-right">Grade point</th>
                <th className="py-1.5 font-medium pl-4">Performance</th>
              </tr>
            </thead>
            <tbody>
              {grading.grades.map(g => (
                <tr key={g.grade} className="border-b border-border/50 text-gray-200">
                  <td className="py-1.5 font-semibold text-white">{g.grade}</td>
                  <td className="py-1.5 tabular-nums">{g.min_marks}–{g.max_marks}</td>
                  <td className="py-1.5 text-right tabular-nums">{g.grade_point}</td>
                  <td className="py-1.5 pl-4 text-gray-400">{g.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h4 className="font-semibold text-white mb-2">Division (on final CGPA)</h4>
          <ul className="text-sm text-gray-300 space-y-1">
            {grading.divisions.map(d => <li key={d.division}>CGPA ≥ {d.min_cgpa.toFixed(1)}: {d.division}</li>)}
          </ul>
        </div>
        {grading.marks_scheme && (
          <div className="rounded-lg border border-primary/40 bg-primary/5 p-4">
            <h4 className="font-semibold text-white mb-3">📝 Marks &amp; passing (theory)</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              <table className="w-full">
                <tbody className="text-gray-300">
                  <tr className="border-b border-border/50">
                    <td className="py-1.5">Theory exam (end-semester)</td>
                    <td className="py-1.5 text-right font-semibold text-white tabular-nums">{grading.marks_scheme.end_semester_exam}</td>
                  </tr>
                  {grading.marks_scheme.internal_parts.map(part => (
                    <tr key={part.name} className="border-b border-border/50">
                      <td className="py-1.5 pl-3">{part.name}</td>
                      <td className="py-1.5 text-right tabular-nums">{part.marks}</td>
                    </tr>
                  ))}
                  <tr className="font-semibold text-white">
                    <td className="pt-1.5">Total</td>
                    <td className="pt-1.5 text-right tabular-nums">{grading.marks_scheme.theory_total}</td>
                  </tr>
                </tbody>
              </table>
              <div className="space-y-2">
                <div className="rounded-md border border-border bg-background/40 p-3">
                  <p className="text-xs text-gray-400">Pass in theory</p>
                  <p className="text-2xl font-bold text-white">{grading.marks_scheme.pass_theory} <span className="text-sm font-normal text-gray-400">marks minimum</span></p>
                </div>
                <div className="rounded-md border border-border bg-background/40 p-3">
                  <p className="text-xs text-gray-400">Pass in total (theory + practical)</p>
                  <p className="text-2xl font-bold text-white">{grading.marks_scheme.pass_total} <span className="text-sm font-normal text-gray-400">marks minimum</span></p>
                </div>
              </div>
            </div>
            {grading.passing_rules && (
              <ul className="mt-3 text-xs text-gray-400 list-disc pl-5 space-y-0.5">
                {grading.passing_rules.map(r => <li key={r}>{r}</li>)}
              </ul>
            )}
          </div>
        )}
        <div>
          <h4 className="font-semibold text-white mb-2">Practical evaluation</h4>
          <p className="text-sm text-gray-300">
            Sessional {grading.assessment.practical.sessional}% + end-semester {grading.assessment.practical.end_semester}%.
          </p>
        </div>
        <div>
          <h4 className="font-semibold text-white mb-2">Rules</h4>
          <ul className="text-sm text-gray-300 list-disc pl-5 space-y-1">
            {grading.rules.map(r => <li key={r}>{r}</li>)}
          </ul>
        </div>
      </div>

      <div className={`${card} space-y-4`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-lg font-bold text-white flex items-center gap-2"><Calculator size={18} /> SGPA / CGPA calculator</h3>
          {scheme && (
            <button onClick={prefillFromScheme} className="text-xs px-3 py-1.5 rounded border border-border text-gray-300 hover:bg-muted/30">
              Fill with {scheme.branch} subjects
            </button>
          )}
        </div>
        <p className="text-xs text-gray-400">SGPA = Σ(credits × grade point) ÷ Σ credits. Audit (0-credit) courses are left out.</p>

        <div className="space-y-4 max-h-[28rem] overflow-y-auto pr-1">
          {rows.map((sem, si) => (
            <div key={si} className="rounded-lg border border-border bg-background/30 p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-white">
                  Semester {si + 1}
                  {result?.semesters[si] && <span className="ml-2 font-normal text-gray-300">SGPA {result.semesters[si].sgpa.toFixed(2)}</span>}
                </span>
                {rows.length > 1 && (
                  <button onClick={() => setRows(rs => rs.filter((_, i) => i !== si))} className="text-gray-400 hover:text-red-400" aria-label="Remove semester">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
              {sem.map((r, ri) => (
                <div key={ri} className="flex items-center gap-2 mb-1.5">
                  <input
                    type="number" min={0} max={12} value={r.credits}
                    onChange={e => update(si, ri, { credits: Number(e.target.value) })}
                    className="w-20 px-2 py-1 rounded bg-background/50 border border-border text-sm"
                    aria-label="Credits"
                  />
                  <span className="text-xs text-gray-400">credits</span>
                  <select value={r.grade} onChange={e => update(si, ri, { grade: e.target.value })} className="px-2 py-1 rounded bg-background/50 border border-border text-sm" aria-label="Grade">
                    {gradeOptions.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                  <button onClick={() => setRows(rs => rs.map((s, i) => i !== si ? s : s.filter((_, j) => j !== ri)))} className="text-gray-400 hover:text-red-400 ml-auto" aria-label="Remove subject">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              <button onClick={() => setRows(rs => rs.map((s, i) => i !== si ? s : [...s, { credits: 3, grade: "A" }]))} className="text-xs text-gray-300 hover:text-white inline-flex items-center gap-1 mt-1">
                <Plus size={12} /> Add subject
              </button>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {rows.length < 8 && (
            <button onClick={() => setRows(rs => [...rs, [{ credits: 4, grade: "A" }]])} className="px-3 py-2 rounded-lg border border-border text-sm text-gray-300 hover:bg-muted/30 inline-flex items-center gap-1">
              <Plus size={14} /> Add semester
            </button>
          )}
          <button onClick={calculate} disabled={busy} className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 disabled:opacity-50 inline-flex items-center gap-2">
            {busy && <Loader2 className="w-4 h-4 animate-spin" />} Calculate
          </button>
        </div>

        {result && (
          <div className="rounded-lg border border-border bg-background/40 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-400">CGPA</p>
            <p className="text-4xl font-bold text-white">{result.cgpa.toFixed(2)}</p>
            <p className="text-sm text-gray-300 mt-1">{result.division}</p>
            {!result.eligible_for_degree && (
              <p className="text-sm text-red-400 mt-1">⚠ Below the minimum CGPA of {grading.min_cgpa_for_degree.toFixed(1)} needed for the degree.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CreditSystem;
