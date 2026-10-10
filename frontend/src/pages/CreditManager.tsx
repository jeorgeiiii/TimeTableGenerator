// frontend/src/pages/CreditManager.tsx
// Live credits from the database, with SGSITS credit limits. Admins can assign
// credits (directly or via L-T-P), remove them, reset to the SGSITS default,
// bulk-apply SGSITS presets, and change the limits. Students see it read-only.
import { useCallback, useEffect, useState } from "react";
import { Loader2, RotateCcw, Save, Sparkles, XCircle, CheckCircle2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import api from "../services/api";

interface Preset { credits: number; ltp: string; source: string }

interface LiveSubject {
  id: number;
  code: string;
  name: string;
  credits: number;
  hours_per_week: number;
  is_lab: boolean;
  is_elective: boolean;
  ltp: string | null;
  credit_source: "curriculum" | "manual" | "preset";
  category: string;
  curriculum_default: number | null;
  sgsits_preset: Preset | null;
}

interface LiveSemester { semester: number; year: number; subjects: LiveSubject[]; total_credits: number }

type Status = "ok" | "under" | "over";

interface LiveData {
  branch: string;
  policy: Record<string, number>;
  status: { semesters: Record<string, { total: number; status: Status }>; total: number; total_status: Status };
  semesters: LiveSemester[];
}

interface PresetPreview {
  changes: { id: number; code: string; name: string; semester: number; from: number; to: number; ltp: string; ltp_from: string | null; source: string }[];
  violations: string[];
}

const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"];
const card = "bg-card/60 backdrop-blur-md rounded-xl p-6 border border-border";
const input = "px-2 py-1 rounded bg-background/50 border border-border text-sm focus:ring-2 focus:ring-primary focus:outline-none";
const btn = "inline-flex items-center gap-1 px-2.5 py-1 rounded border border-border text-xs text-gray-300 hover:bg-muted/30 disabled:opacity-40";

const STATUS: Record<Status, { label: string; cls: string; Icon: typeof CheckCircle2 }> = {
  ok: { label: "Within limits", cls: "text-emerald-400", Icon: CheckCircle2 },
  under: { label: "Below minimum", cls: "text-amber-300", Icon: AlertTriangle },
  over: { label: "Over limit", cls: "text-red-400", Icon: XCircle },
};

const SOURCE_LABEL: Record<string, string> = { curriculum: "Curriculum", manual: "Edited", preset: "SGSITS preset" };

// Ask the admin to confirm a save that breaks a credit limit, then retry with force.
async function withLimitConfirm<T>(send: (force: boolean) => Promise<T>): Promise<T | null> {
  try {
    return await send(false);
  } catch (e: any) {
    const detail = e?.response?.data?.detail;
    if (e?.response?.status === 409 && detail?.violations) {
      const ok = window.confirm(`This breaks the SGSITS credit limits:\n\n• ${detail.violations.join("\n• ")}\n\nSave anyway?`);
      return ok ? await send(true) : null;
    }
    throw e;
  }
}

// Typing a full L-T-P like "3-1-2" also fills Credits (L + T + P/2) right away.
const ltpPatch = (ltp: string): { ltp: string; credits?: string } => {
  const m = ltp.trim().match(/^(\d+)\s*-\s*(\d+)\s*-\s*(\d+)$/);
  return m ? { ltp, credits: String(Number(m[1]) + Number(m[2]) + Math.floor(Number(m[3]) / 2)) } : { ltp };
};

const errMsg = (e: any) => {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : d?.message || "Request failed";
};

const CreditManager = ({ branch, canEdit }: { branch: string; canEdit: boolean }) => {
  const [data, setData] = useState<LiveData | null>(null);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [openSem, setOpenSem] = useState(1);
  const [drafts, setDrafts] = useState<Record<number, { credits: string; ltp: string }>>({});
  const [busyId, setBusyId] = useState<number | null>(null);
  const [policyDraft, setPolicyDraft] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<PresetPreview | null>(null);
  const [presetBusy, setPresetBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get(`/credits/live/${branch}`);
      setData(r.data);
      setDrafts({});
      setPolicyDraft(Object.fromEntries(Object.entries(r.data.policy).map(([k, v]) => [k, String(v)])));
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setLoading(false);
    }
  }, [branch]);

  useEffect(() => { load(); setPreview(null); }, [load]);
  useEffect(() => {
    api.get("/credits/policy").then(r => setLabels(r.data.labels)).catch(() => {});
  }, []);

  const draftOf = (s: LiveSubject) => drafts[s.id] ?? { credits: String(s.credits), ltp: s.ltp ?? "" };
  const setDraft = (s: LiveSubject, patch: Partial<{ credits: string; ltp: string }>) =>
    setDrafts(d => ({ ...d, [s.id]: { ...draftOf(s), ...patch } }));

  const run = async (id: number, fn: () => Promise<unknown>, okMsg: string) => {
    setBusyId(id);
    try {
      const res = await fn();
      if (res !== null) { toast.success(okMsg); await load(); }
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyId(null);
    }
  };

  const saveSubject = (s: LiveSubject) => {
    const d = draftOf(s);
    const ltpChanged = d.ltp.trim() !== (s.ltp ?? "");
    const body: Record<string, unknown> = ltpChanged && d.ltp.trim() ? { ltp: d.ltp.trim() } : { credits: Number(d.credits) };
    run(s.id, () => withLimitConfirm(force => api.put(`/admin/subjects/${s.id}/credits`, { ...body, force })), `${s.name}: credits saved`);
  };
  const removeCredits = (s: LiveSubject) =>
    run(s.id, () => api.delete(`/admin/subjects/${s.id}/credits`), `${s.name}: credits removed (0 / non-credit)`);
  const resetCredits = (s: LiveSubject) =>
    run(s.id, () => withLimitConfirm(force => api.post(`/admin/subjects/${s.id}/credits/reset`, { force })), `${s.name}: reset to SGSITS default`);
  const usePreset = (s: LiveSubject) =>
    s.sgsits_preset && setDraft(s, { credits: String(s.sgsits_preset.credits), ltp: s.sgsits_preset.ltp });

  const savePolicy = async (reset = false) => {
    try {
      const body = reset ? { reset: true } : Object.fromEntries(Object.entries(policyDraft).map(([k, v]) => [k, Number(v)]));
      await api.put("/admin/credits/policy", body);
      toast.success(reset ? "Limits restored to SGSITS defaults" : "Credit limits saved");
      await load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const previewPresets = async () => {
    setPresetBusy(true);
    try {
      const r = await api.post("/admin/credits/apply-presets", { branch, dry_run: true });
      setPreview(r.data);
      if (!r.data.changes.length) toast.info("Every subject already matches its SGSITS preset");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setPresetBusy(false);
    }
  };
  const applyPresets = async () => {
    if (!preview) return;
    if (preview.violations.length && !window.confirm(`Applying these presets breaks the credit limits:\n\n• ${preview.violations.join("\n• ")}\n\nApply anyway?`)) return;
    setPresetBusy(true);
    try {
      const r = await api.post("/admin/credits/apply-presets", { branch, dry_run: false, force: preview.violations.length > 0 });
      toast.success(`Applied SGSITS presets to ${r.data.applied} subject(s)`);
      setPreview(null);
      await load();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setPresetBusy(false);
    }
  };

  if (loading && !data) {
    return <div className={`${card} flex items-center justify-center gap-2 text-gray-300`}><Loader2 className="w-5 h-5 animate-spin" /> Loading live credits…</div>;
  }
  if (!data) return null;

  if (!data.semesters.length) {
    return (
      <div className={`${card} text-gray-300`}>
        No {branch} subjects are in the database yet. Load the SGSITS curriculum from <strong>Add Subject → Load Curriculum</strong>,
        or switch to the <strong>SGSITS reference</strong> view.
      </div>
    );
  }

  const p = data.policy;
  const semester = data.semesters.find(s => s.semester === openSem) ?? data.semesters[0];
  const semStatus = data.status.semesters[String(semester.semester)];
  const totalSt = STATUS[data.status.total_status];

  return (
    <div className="space-y-6">
      {canEdit && (
        <details className={`${card} group`}>
          <summary className="cursor-pointer text-white font-semibold select-none">📘 How to assign credits (easy guide)</summary>
          <div className="mt-4 grid gap-4 md:grid-cols-2 text-sm text-gray-300">
            <div>
              <p className="font-semibold text-white mb-1">What a credit is</p>
              <p>Credits come from weekly hours, written as <span className="font-mono">L-T-P</span> (Lecture - Tutorial - Practical):</p>
              <ul className="list-disc pl-5 mt-1 space-y-0.5">
                <li>1 lecture hour = 1 credit, 1 tutorial hour = 1 credit</li>
                <li>2 practical (lab) hours = 1 credit</li>
                <li>Example: <span className="font-mono">3-1-0</span> = 3 + 1 = <strong>4 credits</strong>; a 2-hour lab <span className="font-mono">0-0-2</span> = <strong>1 credit</strong></li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-white mb-1">Fastest way (whole branch)</p>
              <ol className="list-decimal pl-5 space-y-0.5">
                <li>Pick the branch at the top.</li>
                <li>Click <strong>Pre-assign SGSITS credits</strong>.</li>
                <li>Check the preview, then click <strong>Apply</strong>. Subjects you edited yourself are not touched.</li>
              </ol>
            </div>
            <div>
              <p className="font-semibold text-white mb-1">One subject</p>
              <ol className="list-decimal pl-5 space-y-0.5">
                <li>Click a semester box (Sem I … VIII) below.</li>
                <li>Type the hours in <strong>L-T-P</strong> (e.g. <span className="font-mono">3-1-0</span>) — credits fill in by themselves — or type the <strong>Credits</strong> number directly, or click <strong>use</strong> to take the SGSITS value.</li>
                <li>Click <strong>Save</strong> on that row.</li>
              </ol>
            </div>
            <div>
              <p className="font-semibold text-white mb-1">Other buttons</p>
              <ul className="list-disc pl-5 space-y-0.5">
                <li><strong>Remove</strong> — makes it a 0-credit (audit) course; it stays in the timetable.</li>
                <li><strong>Reset</strong> — back to the SGSITS default value.</li>
                <li>A red/“over limit” semester means too many credits; the limits are at the bottom of this page. You’ll be asked before saving past a limit.</li>
                <li>New subjects from <strong>Add Subject</strong> appear here automatically, with SGSITS credits pre-filled.</li>
              </ul>
            </div>
          </div>
        </details>
      )}

      {/* 4-year total vs limits */}
      <div className={card}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-400">{branch} total credits in the database (4 years)</p>
            <p className="text-3xl font-bold text-white">{data.status.total}
              <span className="text-base font-normal text-gray-400"> / {p.program_min_credits}–{p.program_max_credits}</span>
            </p>
            <p className={`text-sm flex items-center gap-1 ${totalSt.cls}`}><totalSt.Icon size={14} /> {totalSt.label}</p>
          </div>
          {canEdit && (
            <button onClick={previewPresets} disabled={presetBusy} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 disabled:opacity-50">
              {presetBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles size={16} />} Pre-assign SGSITS credits
            </button>
          )}
        </div>
        <LimitBar value={data.status.total} min={p.program_min_credits} max={p.program_max_credits} />

        {/* per-semester status strip */}
        <div className="grid grid-cols-4 sm:grid-cols-8 gap-2 mt-5">
          {Array.from({ length: 8 }, (_, i) => i + 1).map(n => {
            const st = data.status.semesters[String(n)];
            const S = STATUS[st.status];
            return (
              <button key={n} onClick={() => setOpenSem(n)}
                className={`rounded-lg border p-2 text-left transition ${n === semester.semester ? "border-primary bg-primary/10" : "border-border hover:bg-muted/20"}`}>
                <span className="block text-[11px] text-gray-400">Sem {ROMAN[n - 1]}</span>
                <span className="block text-lg font-bold text-white tabular-nums">{st.total}</span>
                <span className={`flex items-center gap-1 text-[11px] ${S.cls}`}><S.Icon size={11} />{st.status === "ok" ? "OK" : S.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* preset preview */}
      {preview && preview.changes.length > 0 && (
        <div className={`${card} border-primary/60`}>
          <h3 className="text-lg font-bold text-white">Preview: SGSITS preset credits for {branch}</h3>
          <p className="text-sm text-gray-400 mb-3">
            {preview.changes.length} subject(s) would get SGSITS credits and L-T-P hours. Subjects you edited by hand are left alone. Nothing is saved until you apply.
          </p>
          <div className="max-h-72 overflow-y-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-gray-400 border-b border-border">
                <th className="py-1.5 font-medium">Sem</th><th className="py-1.5 font-medium">Subject</th>
                <th className="py-1.5 font-medium text-right">Now</th><th className="py-1.5 font-medium text-right">Preset</th>
                <th className="py-1.5 font-medium pl-4">Source</th>
              </tr></thead>
              <tbody>
                {preview.changes.map(c => (
                  <tr key={c.id} className="border-b border-border/50 text-gray-200">
                    <td className="py-1.5">{ROMAN[c.semester - 1]}</td>
                    <td className="py-1.5">{c.name}</td>
                    <td className="py-1.5 text-right tabular-nums">{c.from}{c.ltp_from ? ` (${c.ltp_from})` : ""}</td>
                    <td className="py-1.5 text-right tabular-nums font-semibold text-white">{c.to} ({c.ltp})</td>
                    <td className="py-1.5 pl-4 text-xs text-gray-400">{c.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {preview.violations.length > 0 && (
            <ul className="mt-3 text-sm text-red-400 space-y-1">
              {preview.violations.map(v => <li key={v} className="flex items-center gap-1"><XCircle size={14} /> {v}</li>)}
            </ul>
          )}
          <div className="flex gap-2 mt-4">
            <button onClick={applyPresets} disabled={presetBusy} className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 disabled:opacity-50">
              Apply {preview.changes.length} change(s)
            </button>
            <button onClick={() => setPreview(null)} className="px-4 py-2 rounded-lg border border-border text-sm text-gray-300 hover:bg-muted/30">Cancel</button>
          </div>
        </div>
      )}

      {/* semester editor */}
      <div className={`${card} overflow-x-auto`}>
        <div className="flex flex-wrap items-end justify-between gap-3 mb-2">
          <div>
            <h3 className="text-lg font-bold text-white">Semester {ROMAN[semester.semester - 1]} — {semester.total_credits} credits</h3>
            <p className={`text-sm flex items-center gap-1 ${STATUS[semStatus.status].cls}`}>
              {(() => { const I = STATUS[semStatus.status].Icon; return <I size={14} />; })()}
              {STATUS[semStatus.status].label} (allowed {p.semester_min_credits}–{p.semester_max_credits})
            </p>
          </div>
        </div>
        <LimitBar value={semester.total_credits} min={p.semester_min_credits} max={p.semester_max_credits} />

        <table className="w-full text-sm mt-4 min-w-[760px]">
          <thead>
            <tr className="text-left text-gray-400 border-b border-border">
              <th className="py-2 pr-3 font-medium">Subject</th>
              <th className="py-2 pr-3 font-medium text-right">Hrs</th>
              <th className="py-2 pr-3 font-medium">L-T-P</th>
              <th className="py-2 pr-3 font-medium text-right">Credits</th>
              <th className="py-2 pr-3 font-medium">SGSITS preset</th>
              <th className="py-2 pr-3 font-medium">Source</th>
              {canEdit && <th className="py-2 font-medium text-right">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {semester.subjects.map(s => {
              const d = draftOf(s);
              const dirty = d.credits !== String(s.credits) || d.ltp.trim() !== (s.ltp ?? "");
              const busy = busyId === s.id;
              return (
                <tr key={s.id} className="border-b border-border/50 text-gray-200 align-middle">
                  <td className="py-2 pr-3">
                    <span className="block">{s.name}</span>
                    <span className="font-mono text-[11px] text-gray-500">{s.code}{s.is_lab ? " · lab" : ""}{s.is_elective ? " · elective" : ""}</span>
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">{s.hours_per_week}</td>
                  <td className="py-2 pr-3">
                    {canEdit
                      ? <input value={d.ltp} placeholder="e.g. 3-1-0" onChange={e => setDraft(s, ltpPatch(e.target.value))} className={`${input} w-24`} aria-label={`L-T-P for ${s.name}`} />
                      : <span className="text-gray-400">{s.ltp ?? "—"}</span>}
                  </td>
                  <td className="py-2 pr-3 text-right">
                    {canEdit
                      ? <input type="number" min={0} max={p.subject_max_credits} value={d.credits}
                          onChange={e => setDraft(s, { credits: e.target.value, ltp: "" })}
                          className={`${input} w-16 text-right`} aria-label={`Credits for ${s.name}`} />
                      : <span className="font-semibold text-white tabular-nums">{s.credits}</span>}
                  </td>
                  <td className="py-2 pr-3 text-xs text-gray-400">
                    {s.sgsits_preset ? (
                      <span title={s.sgsits_preset.source}>
                        {s.sgsits_preset.credits} cr ({s.sgsits_preset.ltp})
                        {canEdit && (s.sgsits_preset.credits !== Number(d.credits) || s.sgsits_preset.ltp !== d.ltp.trim()) && (
                          <button onClick={() => usePreset(s)} className="ml-1 underline hover:text-white">use</button>
                        )}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="py-2 pr-3 text-xs">
                    <span className={`px-1.5 py-0.5 rounded border border-border ${s.credit_source === "manual" ? "text-white" : "text-gray-400"}`}>
                      {SOURCE_LABEL[s.credit_source] ?? s.credit_source}
                    </span>
                  </td>
                  {canEdit && (
                    <td className="py-2 text-right whitespace-nowrap space-x-1">
                      <button onClick={() => saveSubject(s)} disabled={!dirty || busy} className={btn} title="Save credits">
                        {busy ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} Save
                      </button>
                      <button onClick={() => removeCredits(s)} disabled={busy || s.credits === 0} className={btn} title="Remove credits (make it a 0-credit course)">
                        <XCircle size={12} /> Remove
                      </button>
                      <button onClick={() => resetCredits(s)} disabled={busy} className={btn} title="Reset to the SGSITS default">
                        <RotateCcw size={12} /> Reset
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
        {canEdit && (
          <p className="text-xs text-gray-400 mt-3">
            Type credits directly, or an L-T-P like <span className="font-mono">3-1-2</span> to compute them (L + T + P/2).
            Remove sets a subject to 0 credits (non-credit/audit) without deleting it from the timetable.
          </p>
        )}
      </div>

      {/* limits */}
      <div className={card}>
        <h3 className="text-lg font-bold text-white mb-1">Credit limits</h3>
        <p className="text-sm text-gray-400 mb-4">
          Defaults come from SGSITS's NEP Scheme 2025 (161 + 2 credits, 14–24 per semester) and SGSITS's 19–26 credit semesters.
          Saves that would go over a maximum are blocked unless confirmed. Minimums only warn.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {Object.keys(p).map(k => (
            <label key={k} className="block">
              <span className="block text-xs text-gray-400 mb-1">{labels[k] ?? k}</span>
              {canEdit
                ? <input type="number" min={0} value={policyDraft[k] ?? ""} onChange={e => setPolicyDraft(d => ({ ...d, [k]: e.target.value }))} className={`${input} w-full`} />
                : <span className="text-xl font-bold text-white">{p[k]}</span>}
            </label>
          ))}
        </div>
        {canEdit && (
          <div className="flex gap-2 mt-4">
            <button onClick={() => savePolicy()} className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90">Save limits</button>
            <button onClick={() => savePolicy(true)} className="px-4 py-2 rounded-lg border border-border text-sm text-gray-300 hover:bg-muted/30">Restore SGSITS defaults</button>
          </div>
        )}
      </div>
    </div>
  );
};

// Horizontal meter: filled to `value`, with the allowed min-max band marked.
const LimitBar = ({ value, min, max }: { value: number; min: number; max: number }) => {
  const scale = Math.max(max * 1.15, value, 1);
  const pct = (x: number) => `${Math.min(100, (x / scale) * 100)}%`;
  const over = value > max;
  return (
    <div className="relative h-3 mt-3 rounded-full bg-background/60 border border-border overflow-hidden" role="meter"
      aria-valuenow={value} aria-valuemin={0} aria-valuemax={max} aria-label={`${value} of ${max} credits`}>
      <div className="absolute inset-y-0 bg-white/10" style={{ left: pct(min), width: `calc(${pct(max)} - ${pct(min)})` }} />
      <div className={`absolute inset-y-0 left-0 rounded-full ${over ? "bg-red-500" : "bg-primary"}`} style={{ width: pct(value) }} />
      <div className="absolute inset-y-0 w-0.5 bg-white/70" style={{ left: pct(max) }} />
    </div>
  );
};

export default CreditManager;
