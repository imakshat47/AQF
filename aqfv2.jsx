import { useState, useEffect } from "react";

const API_BASE = null; // Set to "http://localhost:8000" when running with FastAPI

// ── REAL DATA from your backend (matches exact output of build_form_definition) ──
const DEMO_LOAD = {
  composition_label: "Outpatient high complexity procedures",
  composition_archetype: "openEHR-EHR-COMPOSITION.outpatient_high_complexity_procedures.v1",
  stats: { files: 1, skipped: 0, groups: 4, subgroups: 7, fields: 22, suggestion_fields: 22, null_fields: 4 },
  form: {
    criteria_groups: [
      { group_label: "HCPA", subgroups: [{ label: "General data", fields: [
        { field_key: "fk_issue_date", label: "issue date", full_label: "HCPA → General data → issue date", dv_type: "DV_DATE", suggestion_mode: "date", suggested_values: ["2008-07-01TZ", "2008-06-01TZ"], operators: [{ op: "=", phrase: "is on" }, { op: "<", phrase: "is before" }, { op: ">", phrase: "is after" }, { op: "between", phrase: "is between" }] },
        { field_key: "fk_reason", label: "reason for encounter", full_label: "HCPA → General data → reason for encounter", dv_type: "DV_CODED_TEXT", suggestion_mode: "categorical", suggested_values: ["RADIOTERAPIA", "QUIMIOTERAPIA", "CIRURGIA"], operators: [{ op: "=", phrase: "is" }, { op: "!=", phrase: "is not" }, { op: "contains", phrase: "contains" }] },
        { field_key: "fk_state", label: "State", full_label: "HCPA → General data → State", dv_type: "DV_CODED_TEXT", suggestion_mode: "categorical", suggested_values: ["SÃO PAULO", "MINAS GERAIS", "RIO DE JANEIRO"], operators: [{ op: "=", phrase: "is" }, { op: "!=", phrase: "is not" }, { op: "contains", phrase: "contains" }] },
        { field_key: "fk_age", label: "patient age", full_label: "HCPA → General data → patient age", dv_type: "DV_COUNT", suggestion_mode: "numeric", suggested_values: ["60", "45", "72"], operators: [{ op: "=", phrase: "equals" }, { op: "!=", phrase: "does not equal" }, { op: ">", phrase: "is greater than" }, { op: "<", phrase: "is less than" }, { op: "between", phrase: "is between" }] },
        { field_key: "fk_radio_date", label: "date of beginning of radiotherapy", full_label: "HCPA → radiotherapy → date of beginning of radiotherapy", dv_type: "DV_DATE", suggestion_mode: "date", suggested_values: ["2008-06-01TZ"], operators: [{ op: "=", phrase: "is on" }, { op: "<", phrase: "is before" }, { op: ">", phrase: "is after" }] },
      ]}]},
      { group_label: "Patient discharge", subgroups: [{ label: "(no cluster)", fields: [
        { field_key: "fk_discharge_date", label: "date of discharge", full_label: "Patient discharge → date of discharge", dv_type: "NULL_FLAVOUR", suggestion_mode: "categorical", suggested_values: ["unknown"], operators: [{ op: "is_known", phrase: "is known" }, { op: "is_unknown", phrase: "is unknown" }, { op: "=", phrase: "is" }] },
        { field_key: "fk_discharge_reason", label: "reason for discharge", full_label: "Patient discharge → reason for discharge", dv_type: "DV_CODED_TEXT", suggestion_mode: "categorical", suggested_values: ["Permanência - por características próprias doença", "Alta Curado"], operators: [{ op: "=", phrase: "is" }, { op: "!=", phrase: "is not" }, { op: "contains", phrase: "contains" }] },
      ]}]},
      { group_label: "Problem / Diagnosis", subgroups: [{ label: "(no cluster)", fields: [
        { field_key: "fk_problem", label: "Problem", full_label: "Problem/Diagnosis → Problem", dv_type: "DV_CODED_TEXT", suggestion_mode: "categorical", suggested_values: ["C53.9 Colo do utero NE", "C50.9 Mama NE", "C61 Prostata"], operators: [{ op: "=", phrase: "is" }, { op: "!=", phrase: "is not" }, { op: "contains", phrase: "contains" }] },
        { field_key: "fk_sec_dx", label: "Secondary Diagnosis", full_label: "Problem/Diagnosis → Secondary Diagnosis", dv_type: "DV_CODED_TEXT", suggestion_mode: "categorical", suggested_values: ["CID NAO INFORMADO"], operators: [{ op: "=", phrase: "is" }, { op: "!=", phrase: "is not" }, { op: "contains", phrase: "contains" }] },
        { field_key: "fk_staging", label: "Clinical staging", full_label: "Problem/Diagnosis → Clinical staging", dv_type: "DV_TEXT", suggestion_mode: "categorical", suggested_values: ["1", "2", "3", "4"], operators: [{ op: "=", phrase: "is" }, { op: "!=", phrase: "is not" }, { op: "contains", phrase: "contains" }] },
        { field_key: "fk_topography", label: "topography", full_label: "Problem/Diagnosis → topography", dv_type: "DV_CODED_TEXT", suggestion_mode: "categorical", suggested_values: ["C53.9 Colo do utero NE", "C50.9 Mama NE"], operators: [{ op: "=", phrase: "is" }, { op: "!=", phrase: "is not" }, { op: "contains", phrase: "contains" }] },
      ]}, { label: "TNM / Pathological", fields: [
        { field_key: "fk_lymph", label: "Invaded regional lymphnodes", full_label: "Problem/Diagnosis → Invaded regional lymphnodes", dv_type: "DV_BOOLEAN", suggestion_mode: "boolean", suggested_values: ["true", "false"], operators: [{ op: "=", phrase: "is" }] },
      ]}]},
      { group_label: "Procedure undertaken", subgroups: [{ label: "(no cluster)", fields: [
        { field_key: "fk_procedure", label: "Procedure", full_label: "Procedure undertaken → Procedure", dv_type: "DV_CODED_TEXT", suggestion_mode: "categorical", suggested_values: ["BRAQUITERAPIA DE ALTA TAXA DE DOSE (POR INSERÇÃO)", "QUIMIOTERAPIA ANTINEOPLASICA"], operators: [{ op: "=", phrase: "is" }, { op: "!=", phrase: "is not" }, { op: "contains", phrase: "contains" }] },
        { field_key: "fk_area1", label: "irradiated area 1", full_label: "Procedure undertaken → irradiated area 1", dv_type: "DV_CODED_TEXT", suggestion_mode: "categorical", suggested_values: ["C53.9 Colo do utero NE"], operators: [{ op: "=", phrase: "is" }, { op: "!=", phrase: "is not" }, { op: "contains", phrase: "contains" }] },
        { field_key: "fk_insertions", label: "fields/insertions 1", full_label: "Procedure undertaken → fields/insertions 1", dv_type: "DV_COUNT", suggestion_mode: "numeric", suggested_values: ["4", "6", "1"], operators: [{ op: "=", phrase: "equals" }, { op: ">", phrase: "is greater than" }, { op: "<", phrase: "is less than" }] },
      ]}]},
    ],
    output_fields: [
      { field_key: "fk_issue_date",      label: "HCPA → General data → issue date",               dv_type: "DV_DATE" },
      { field_key: "fk_reason",          label: "HCPA → General data → reason for encounter",     dv_type: "DV_CODED_TEXT" },
      { field_key: "fk_state",           label: "HCPA → General data → State",                    dv_type: "DV_CODED_TEXT" },
      { field_key: "fk_age",             label: "HCPA → General data → patient age",              dv_type: "DV_COUNT" },
      { field_key: "fk_problem",         label: "Problem/Diagnosis → Problem",                    dv_type: "DV_CODED_TEXT" },
      { field_key: "fk_sec_dx",          label: "Problem/Diagnosis → Secondary Diagnosis",        dv_type: "DV_CODED_TEXT" },
      { field_key: "fk_staging",         label: "Problem/Diagnosis → Clinical staging",           dv_type: "DV_TEXT" },
      { field_key: "fk_topography",      label: "Problem/Diagnosis → topography",                 dv_type: "DV_CODED_TEXT" },
      { field_key: "fk_procedure",       label: "Procedure undertaken → Procedure",               dv_type: "DV_CODED_TEXT" },
      { field_key: "fk_discharge_reason",label: "Patient discharge → reason for discharge",       dv_type: "DV_CODED_TEXT" },
      { field_key: "fk_insertions",      label: "Procedure undertaken → fields/insertions 1",     dv_type: "DV_COUNT" },
    ],
  }
};

const DEMO_RESULT = {
  scanned: 1, matched: 1, elapsed_sec: 0.0012, sec_per_doc: 0.0012,
  rows: [{
    "_file": "1_2_1_...json",
    "HCPA → General data → issue date": "2008-07-01TZ",
    "HCPA → General data → reason for encounter": "RADIOTERAPIA",
    "HCPA → General data → State": "SÃO PAULO",
    "HCPA → General data → patient age": "60",
    "Problem/Diagnosis → Problem": "C53.9 Colo do utero NE",
    "Problem/Diagnosis → Secondary Diagnosis": "CID NAO INFORMADO",
    "Problem/Diagnosis → Clinical staging": "2",
    "Problem/Diagnosis → topography": "C53.9 Colo do utero NE",
    "Procedure undertaken → Procedure": "BRAQUITERAPIA DE ALTA TAXA DE DOSE (POR INSERÇÃO)",
    "Patient discharge → reason for discharge": "Permanência - por características próprias doença",
    "Procedure undertaken → fields/insertions 1": "4",
  }],
  funnel: [{ stage: "Scanned files", count: 1, label: "Scanned files" }],
  summary: "Find all records. Show issue date, Problem, reason for encounter.",
};

async function apiLoad(dir) {
  if (!API_BASE) return DEMO_LOAD;
  const r = await fetch(`${API_BASE}/api/load`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ data_dir: dir }) });
  if (!r.ok) throw new Error(`API load error: ${r.status}`);
  return r.json();
}

async function apiQuery(payload) {
  if (!API_BASE) { await new Promise(r => setTimeout(r, 700)); return DEMO_RESULT; }
  const r = await fetch(`${API_BASE}/api/query`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!r.ok) throw new Error(`API query error: ${r.status}`);
  return r.json();
}

// ── COLORS ──────────────────────────────────────────────────────────────────────
const DV_META = {
  DV_CODED_TEXT: { bg: "#ede9fe", text: "#5b21b6", tag: "CODED" },
  DV_TEXT:       { bg: "#e0f2fe", text: "#075985", tag: "TEXT"  },
  DV_DATE:       { bg: "#fef9c3", text: "#713f12", tag: "DATE"  },
  DV_DATE_TIME:  { bg: "#fef9c3", text: "#713f12", tag: "DATE"  },
  DV_COUNT:      { bg: "#dcfce7", text: "#14532d", tag: "COUNT" },
  DV_QUANTITY:   { bg: "#dcfce7", text: "#14532d", tag: "NUM"   },
  DV_BOOLEAN:    { bg: "#f1f5f9", text: "#334155", tag: "BOOL"  },
  NULL_FLAVOUR:  { bg: "#fce7f3", text: "#9d174d", tag: "NULL?" },
};
const dvm = (t) => DV_META[t] || { bg: "#f1f5f9", text: "#475569", tag: t?.slice?.(3,8) || "?" };

const T = {
  teal: "#0d9488", tealBg: "#f0fdfa", tealBorder: "#99f6e4", tealDark: "#0f766e",
  ink: "#0f172a", slate: "#334155", muted: "#64748b", border: "#e2e8f0", bg: "#f8fafc", white: "#ffffff",
  violet: "#7c3aed", violetBg: "#f5f3ff", violetBorder: "#ddd6fe",
  green: "#16a34a", greenBg: "#f0fdf4", greenBorder: "#bbf7d0",
  amber: "#d97706", amberBg: "#fffbeb", amberBorder: "#fde68a",
  red: "#dc2626", redBg: "#fef2f2", redBorder: "#fecaca",
};

// ── MICRO COMPONENTS ──────────────────────────────────────────────────────────────

const DVTag = ({ type }) => {
  const m = dvm(type);
  return <span style={{ fontSize: 9, fontWeight: 800, letterSpacing: "0.07em", padding: "1px 5px", borderRadius: 4, background: m.bg, color: m.text }}>{m.tag}</span>;
};

const Chip = ({ pre, label, onX, hue = "teal" }) => {
  const s = hue === "violet" ? { bg: T.violetBg, text: T.violet, bd: T.violetBorder }
           : hue === "amber"  ? { bg: T.amberBg,  text: T.amber,  bd: T.amberBorder }
                              : { bg: T.tealBg,   text: T.tealDark, bd: T.tealBorder };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 10px", borderRadius: 20, fontSize: 12, fontWeight: 500, background: s.bg, color: s.text, border: `1px solid ${s.bd}` }}>
      {pre && <span style={{ opacity: 0.55, fontSize: 11 }}>{pre}</span>}
      {label}
      {onX && <button onClick={onX} style={{ background: "none", border: "none", cursor: "pointer", padding: 0, color: "inherit", opacity: 0.5, lineHeight: 1, fontSize: 13 }}>×</button>}
    </span>
  );
};

const Panel = ({ title, badge, icon, open, onToggle, accent, children }) => (
  <div style={{ border: `1px solid ${accent ? T.tealBorder : T.border}`, borderRadius: 12, background: T.white, overflow: "hidden" }}>
    <button onClick={onToggle} style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "11px 16px", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span>{icon}</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: T.ink }}>{title}</span>
        {badge && <span style={{ fontSize: 11, fontWeight: 600, background: accent ? T.tealBg : "#f1f5f9", color: accent ? T.tealDark : T.muted, padding: "2px 8px", borderRadius: 20, border: `1px solid ${accent ? T.tealBorder : T.border}` }}>{badge}</span>}
      </div>
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ color: T.muted, transform: open ? "rotate(180deg)" : "none", transition: "transform .18s" }}>
        <path d="M2 5l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </button>
    {open && <div style={{ borderTop: `1px solid ${T.border}`, padding: 16, background: "#fafbfc" }}>{children}</div>}
  </div>
);

// ── CRITERION ROW ──────────────────────────────────────────────────────────────────

function CritRow({ field, value, onChange, onRemove }) {
  const { operator = field.operators[0]?.op, rawValue = "", rangeHi = "" } = value;
  const opObj = field.operators.find(o => o.op === operator) || field.operators[0];
  const isNull = ["is_known", "is_unknown"].includes(operator);
  const isBetween = operator === "between";
  const isCat = (field.suggestion_mode === "categorical" || field.suggestion_mode === "boolean") && field.suggested_values?.length > 0;

  const inp = { fontFamily: "inherit", fontSize: 12, border: `1px solid ${T.border}`, borderRadius: 8, padding: "5px 9px", background: T.white, color: T.ink, outline: "none", boxSizing: "border-box" };
  const upd = (p) => onChange({ operator, rawValue, rangeHi, ...p });

  return (
    <div style={{ background: T.tealBg, border: `1px solid ${T.tealBorder}`, borderRadius: 10, padding: "10px 12px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <DVTag type={field.dv_type} />
          <span style={{ fontSize: 12, fontWeight: 600, color: T.tealDark }}>{field.label}</span>
          <span style={{ fontSize: 11, color: T.muted, background: "#f1f5f9", padding: "0 5px", borderRadius: 4 }}>{field.full_label}</span>
        </div>
        <button onClick={onRemove} style={{ background: "none", border: "none", cursor: "pointer", color: T.muted, padding: 2 }}>✕</button>
      </div>
      <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
        <select value={operator} onChange={e => upd({ operator: e.target.value })} style={{ ...inp, flexShrink: 0 }}>
          {field.operators.map(o => <option key={o.op} value={o.op}>{o.phrase}</option>)}
        </select>
        {!isNull && !isBetween && isCat && (
          <select value={rawValue} onChange={e => upd({ rawValue: e.target.value })} style={{ ...inp, flex: 1 }}>
            <option value="">— select —</option>
            {field.suggested_values.map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        )}
        {!isNull && !isBetween && !isCat && (
          <input type={field.suggestion_mode === "numeric" ? "number" : "text"} placeholder={field.suggested_values?.[0] || "value"} value={rawValue} onChange={e => upd({ rawValue: e.target.value })} style={{ ...inp, flex: 1 }} />
        )}
        {isBetween && <>
          <input type="text" placeholder="from" value={rawValue} onChange={e => upd({ rawValue: e.target.value })} style={{ ...inp, width: 120 }} />
          <span style={{ alignSelf: "center", fontSize: 11, color: T.muted }}>→</span>
          <input type="text" placeholder="to" value={rangeHi} onChange={e => upd({ rangeHi: e.target.value })} style={{ ...inp, width: 120 }} />
        </>}
        {isNull && <span style={{ alignSelf: "center", fontSize: 12, color: T.muted, fontStyle: "italic" }}>No value needed</span>}
      </div>
    </div>
  );
}

// ── RESULT CARD ──────────────────────────────────────────────────────────────────

function RCard({ row, labels, index }) {
  const [exp, setExp] = useState(false);
  const primary = labels.filter(l => row[l] != null);
  const other = Object.keys(row).filter(k => k !== "_file" && !labels.includes(k) && row[k] != null);
  const short = (l) => l.split("→").pop().trim();

  return (
    <div style={{ background: T.white, border: `1px solid ${T.border}`, borderRadius: 12, padding: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontSize: 10, fontFamily: "monospace", color: "#94a3b8" }}>{row._file || `record #${index + 1}`}</span>
        <span style={{ fontSize: 10, fontWeight: 700, background: T.greenBg, color: T.green, padding: "1px 8px", borderRadius: 20, border: `1px solid ${T.greenBorder}` }}>MATCHED</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 14px" }}>
        {primary.map(lbl => (
          <div key={lbl}>
            <div style={{ fontSize: 9, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>{short(lbl)}</div>
            <div style={{ fontSize: 13, fontWeight: 500, color: T.slate, wordBreak: "break-word", marginTop: 2 }}>
              {String(row[lbl]).length > 55 ? String(row[lbl]).slice(0, 52) + "…" : String(row[lbl])}
            </div>
          </div>
        ))}
      </div>
      {other.length > 0 && (
        <button onClick={() => setExp(v => !v)} style={{ marginTop: 10, width: "100%", background: "none", border: `1px solid ${T.border}`, borderRadius: 7, padding: "4px 0", fontSize: 11, color: T.muted, cursor: "pointer", fontFamily: "inherit" }}>
          {exp ? "▲ hide" : `▼ ${other.length} more field${other.length !== 1 ? "s" : ""}`}
        </button>
      )}
      {exp && (
        <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 14px", borderTop: `1px solid ${T.border}`, paddingTop: 8 }}>
          {other.map(k => (
            <div key={k}>
              <div style={{ fontSize: 9, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>{short(k)}</div>
              <div style={{ fontSize: 12, color: T.muted, marginTop: 2 }}>{String(row[k])}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── MAIN ─────────────────────────────────────────────────────────────────────────

export default function AQFv2() {
  const [dataDir, setDataDir] = useState("data");
  const [loading, setLoading] = useState(true);
  const [loadErr, setLoadErr] = useState(null);
  const [formDef, setFormDef] = useState(null);
  const [meta, setMeta] = useState(null);

  const [pFilters, setPFilters] = useState(true);
  const [pOutput, setPOutput] = useState(false);
  const [pMore, setPMore] = useState(false);
  const [pFunnel, setPFunnel] = useState(false);
  const [pExplain, setPExplain] = useState(false);
  const [groupOpen, setGroupOpen] = useState({});

  const [crit, setCrit] = useState({});
  const [outKeys, setOutKeys] = useState(new Set());
  const [sort, setSort] = useState({ field_key: "", direction: "desc" });
  const [adv, setAdv] = useState({ occurrence_semantics: "ALL", include_unknown: false, slice_size: 1000, result_limit: 100 });

  const [result, setResult] = useState(null);
  const [querying, setQuerying] = useState(false);
  const [qErr, setQErr] = useState(null);
  const [view, setView] = useState("cards");
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    apiLoad(dataDir)
      .then(d => {
        setFormDef(d.form);
        setMeta({ label: d.composition_label, arch: d.composition_archetype, stats: d.stats });
        setOutKeys(new Set(d.form.output_fields.slice(0, 5).map(f => f.field_key)));
        setGroupOpen({ [d.form.criteria_groups[0]?.group_label]: true });
        setLoadErr(null);
      })
      .catch(e => setLoadErr(e.message))
      .finally(() => setLoading(false));
  }, [dataDir]);

  const allFields = formDef ? formDef.criteria_groups.flatMap(cg => cg.subgroups.flatMap(sg => sg.fields)) : [];
  const byKey = Object.fromEntries(allFields.map(f => [f.field_key, f]));
  const activeCnt = Object.keys(crit).length;
  const outFields = formDef?.output_fields || [];
  const activeOutLabels = outFields.filter(f => outKeys.has(f.field_key)).map(f => f.label);

  const addCrit = (f) => {
    if (crit[f.field_key]) return;
    setCrit(p => ({ ...p, [f.field_key]: { operator: f.operators[0]?.op || "=", rawValue: "", rangeHi: "" } }));
  };
  const rmCrit = (fk) => setCrit(p => { const n = { ...p }; delete n[fk]; return n; });
  const updCrit = (fk, v) => setCrit(p => ({ ...p, [fk]: v }));
  const toggleOut = (fk) => setOutKeys(p => { const n = new Set(p); n.has(fk) ? n.delete(fk) : n.add(fk); return n; });

  const summary = () => {
    const parts = Object.entries(crit).map(([fk, v]) => {
      const f = byKey[fk]; if (!f) return null;
      const op = f.operators.find(o => o.op === v.operator);
      if (["is_known","is_unknown"].includes(v.operator)) return `${f.label} ${op?.phrase}`;
      if (!v.rawValue) return null;
      return v.operator === "between" ? `${f.label} ${v.rawValue}–${v.rangeHi}` : `${f.label} ${op?.phrase} "${v.rawValue}"`;
    }).filter(Boolean);
    return parts.length ? parts.join(" · ") : "All records — no filters applied";
  };

  const runQuery = async () => {
    setQuerying(true); setQErr(null);
    try {
      const critList = Object.entries(crit).map(([fk, v]) => ({
        field_key: fk, operator: v.operator,
        value: ["is_known","is_unknown"].includes(v.operator) ? null : v.operator === "between" ? [v.rawValue, v.rangeHi] : v.rawValue || null
      })).filter(c => c.value !== null || ["is_known","is_unknown"].includes(c.operator));

      const payload = {
        data_dir: dataDir,
        criteria: critList,
        output_fields: outFields.filter(f => outKeys.has(f.field_key)).map(f => ({ field_key: f.field_key, name: f.label, dv_type: f.dv_type })),
        sort: sort.field_key ? sort : null,
        advanced: adv,
      };
      const res = await apiQuery(payload);
      setResult(res);
      setPFilters(false);
    } catch (e) { setQErr(e.message); }
    finally { setQuerying(false); }
  };

  const reset = () => {
    setCrit({}); setResult(null); setQErr(null); setPFunnel(false); setPExplain(false);
    if (formDef) setOutKeys(new Set(formDef.output_fields.slice(0, 5).map(f => f.field_key)));
  };

  const inp = (extra = {}) => ({ fontFamily: "inherit", fontSize: 12, border: `1px solid ${T.border}`, borderRadius: 8, padding: "5px 9px", background: T.white, color: T.ink, outline: "none", ...extra });

  if (loading) return (
    <div style={{ minHeight: "100vh", background: T.bg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ textAlign: "center" }}>
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        <div style={{ width: 36, height: 36, border: `3px solid ${T.tealBorder}`, borderTopColor: T.teal, borderRadius: "50%", animation: "spin .7s linear infinite", margin: "0 auto 12px" }} />
        <p style={{ color: T.muted, fontSize: 13, margin: 0 }}>Building schema from dataset…</p>
      </div>
    </div>
  );

  if (loadErr) return (
    <div style={{ minHeight: "100vh", background: T.bg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ background: T.white, border: `1px solid ${T.redBorder}`, borderRadius: 12, padding: 24, textAlign: "center", maxWidth: 380 }}>
        <p style={{ fontSize: 14, fontWeight: 600, color: T.red, margin: "0 0 8px" }}>Dataset error</p>
        <p style={{ fontSize: 12, color: T.muted, margin: 0 }}>{loadErr}</p>
      </div>
    </div>
  );

  return (
    <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", minHeight: "100vh", background: T.bg }}>
      <style>{`* { box-sizing: border-box; } button { transition: all .15s; }`}</style>

      {/* HEADER */}
      <div style={{ background: T.white, borderBottom: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: 880, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", height: 54, padding: "0 20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, background: T.tealBg, border: `1px solid ${T.tealBorder}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ fontSize: 11, fontWeight: 800, color: T.tealDark }}>AQ</span>
            </div>
            <div>
              <span style={{ fontSize: 14, fontWeight: 700, color: T.ink }}>AQF</span>
              <span style={{ fontSize: 11, color: T.muted, marginLeft: 6 }}>Adaptive Query Forms v2</span>
            </div>
            {meta && <>
              <div style={{ width: 1, height: 24, background: T.border, margin: "0 6px" }} />
              <span style={{ fontSize: 11, color: T.muted }}>{meta.label}</span>
              {meta.stats && <span style={{ fontSize: 11, color: T.muted }}>· <b style={{ color: T.ink }}>{meta.stats.files}</b> files · <b style={{ color: T.ink }}>{meta.stats.fields}</b> fields</span>}
            </>}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <input value={dataDir} onChange={e => setDataDir(e.target.value)} style={{ ...inp({ width: 170, fontSize: 11, fontFamily: "monospace" }) }} placeholder="data dir" />
            <button onClick={reset} style={{ ...inp({ padding: "5px 12px", cursor: "pointer" }) }}>Reset</button>
          </div>
        </div>
      </div>

      {/* STICKY SUMMARY */}
      <div style={{ background: T.tealDark, padding: "8px 20px", position: "sticky", top: 0, zIndex: 100 }}>
        <div style={{ maxWidth: 880, margin: "0 auto", display: "flex", alignItems: "center", gap: 10 }}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="#99f6e4"><path d="M6 1l1.4 3.6H12L8.7 7.1 10 11 6 8.4 2 11l1.3-3.9L0 4.6h4.6L6 1z"/></svg>
          <span style={{ fontSize: 12, color: "#e0f7f4", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{summary()}</span>
          {activeCnt > 0 && <span style={{ fontSize: 11, background: "rgba(255,255,255,.15)", color: "#ccfbf1", padding: "2px 10px", borderRadius: 20, flexShrink: 0 }}>{activeCnt} filter{activeCnt !== 1 ? "s" : ""}</span>}
        </div>
      </div>

      {/* WORKSPACE */}
      <div style={{ maxWidth: 880, margin: "0 auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 10 }}>

        {/* CHIPS STRIP */}
        {(activeCnt > 0 || outKeys.size > 0) && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5, alignItems: "center", padding: "8px 12px", background: T.white, borderRadius: 10, border: `1px solid ${T.border}` }}>
            <span style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: ".05em", marginRight: 2 }}>Active</span>
            {Object.entries(crit).map(([fk, v]) => {
              const f = byKey[fk]; if (!f) return null;
              const op = f.operators.find(o => o.op === v.operator);
              const val = ["is_known","is_unknown"].includes(v.operator) ? "" : v.operator === "between" ? ` ${v.rawValue}–${v.rangeHi}` : v.rawValue ? ` "${v.rawValue}"` : "";
              return <Chip key={fk} pre={f.label} label={`${op?.phrase}${val}`} hue="teal" onX={() => rmCrit(fk)} />;
            })}
            {outFields.filter(f => outKeys.has(f.field_key)).slice(0, 3).map(f => (
              <Chip key={f.field_key} pre="show" label={f.label.split("→").pop().trim()} hue="violet" onX={() => toggleOut(f.field_key)} />
            ))}
            {outKeys.size > 3 && <span style={{ fontSize: 11, color: T.muted }}>+{outKeys.size - 3} output fields</span>}
          </div>
        )}

        {/* ── FILTERS (generated AQF form) ── */}
        <Panel title="Filters" badge={`${activeCnt} active`} icon="⚙️" open={pFilters} onToggle={() => setPFilters(v => !v)} accent>

          {/* Active criteria editors */}
          {activeCnt > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 14 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: ".06em" }}>Active criteria</div>
              {Object.entries(crit).map(([fk, v]) => {
                const f = byKey[fk]; if (!f) return null;
                return <CritRow key={fk} field={f} value={v} onChange={val => updCrit(fk, val)} onRemove={() => rmCrit(fk)} />;
              })}
            </div>
          )}

          {/* Field search */}
          <div style={{ position: "relative", marginBottom: 10 }}>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search fields…"
              style={{ ...inp({ width: "100%", padding: "7px 12px 7px 30px" }) }} />
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: T.muted }}>
              <circle cx="5.5" cy="5.5" r="4" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M9 9l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>

          {/* Generated groups */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {formDef?.criteria_groups.map(cg => {
              const visible = cg.subgroups.flatMap(sg => sg.fields).filter(f =>
                !search || f.label.toLowerCase().includes(search.toLowerCase()) || (f.full_label||"").toLowerCase().includes(search.toLowerCase())
              );
              if (search && visible.length === 0) return null;
              const isOpen = !!groupOpen[cg.group_label];

              return (
                <div key={cg.group_label} style={{ border: `1px solid ${T.border}`, borderRadius: 10, background: T.white, overflow: "hidden" }}>
                  <button onClick={() => setGroupOpen(p => ({ ...p, [cg.group_label]: !p[cg.group_label] }))}
                    style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 14px", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: T.ink }}>{cg.group_label}</span>
                      <span style={{ fontSize: 10, color: T.muted, background: "#f1f5f9", padding: "1px 7px", borderRadius: 10 }}>{visible.length}</span>
                    </div>
                    <svg width="11" height="11" viewBox="0 0 11 11" fill="none" style={{ color: T.muted, transform: isOpen ? "rotate(180deg)" : "none", transition: "transform .15s" }}>
                      <path d="M1.5 3.5l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>

                  {isOpen && (
                    <div style={{ borderTop: `1px solid ${T.border}` }}>
                      {cg.subgroups.map(sg => {
                        const sflds = sg.fields.filter(f => !search || f.label.toLowerCase().includes(search.toLowerCase()) || (f.full_label||"").toLowerCase().includes(search.toLowerCase()));
                        if (!sflds.length) return null;
                        return (
                          <div key={sg.label}>
                            {sg.label !== "(no cluster)" && (
                              <div style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: ".06em", padding: "5px 14px 2px" }}>{sg.label}</div>
                            )}
                            {sflds.map(field => {
                              const active = !!crit[field.field_key];
                              return (
                                <div key={field.field_key}
                                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 14px", background: active ? T.tealBg : "transparent", borderLeft: `3px solid ${active ? T.teal : "transparent"}` }}>
                                  <div style={{ display: "flex", alignItems: "center", gap: 7, overflow: "hidden" }}>
                                    <DVTag type={field.dv_type} />
                                    <span style={{ fontSize: 12, color: active ? T.tealDark : T.slate, fontWeight: active ? 600 : 400, whiteSpace: "nowrap" }}>{field.label}</span>
                                    {field.suggested_values?.[0] && !active && <span style={{ fontSize: 10, color: "#94a3b8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>e.g. {field.suggested_values[0]}</span>}
                                  </div>
                                  <button onClick={() => active ? rmCrit(field.field_key) : addCrit(field)}
                                    style={{ flexShrink: 0, fontFamily: "inherit", fontSize: 11, padding: "3px 10px", borderRadius: 20, cursor: "pointer", border: `1px solid ${active ? T.tealBorder : T.border}`, background: active ? T.teal : T.white, color: active ? T.white : T.muted, fontWeight: 500, marginLeft: 8 }}>
                                    {active ? "Active ✓" : "+ Filter"}
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Panel>

        {/* ── RESULTS TO SHOW ── */}
        <Panel title="Results to show" badge={`${outKeys.size} fields`} icon="👁" open={pOutput} onToggle={() => setPOutput(v => !v)}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
            {outFields.map(f => {
              const on = outKeys.has(f.field_key);
              const name = f.label.split("→").pop().trim();
              return (
                <button key={f.field_key} onClick={() => toggleOut(f.field_key)}
                  style={{ fontFamily: "inherit", fontSize: 12, padding: "5px 12px", borderRadius: 20, cursor: "pointer", border: `1px solid ${on ? T.violet : T.border}`, background: on ? T.violet : T.white, color: on ? T.white : T.muted, display: "flex", alignItems: "center", gap: 5 }}>
                  <DVTag type={f.dv_type} />
                  {name}
                </button>
              );
            })}
          </div>
          <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 10, display: "flex", gap: 7, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: T.muted, flexShrink: 0 }}>Sort by</span>
            <select value={sort.field_key} onChange={e => setSort(p => ({ ...p, field_key: e.target.value }))} style={inp({ flex: 1 })}>
              <option value="">— none —</option>
              {outFields.filter(f => outKeys.has(f.field_key)).map(f => <option key={f.field_key} value={f.field_key}>{f.label.split("→").pop().trim()}</option>)}
            </select>
            {["asc","desc"].map(d => (
              <button key={d} onClick={() => setSort(p => ({ ...p, direction: d }))}
                style={{ fontFamily: "inherit", fontSize: 12, padding: "5px 12px", borderRadius: 8, cursor: "pointer", border: `1px solid ${sort.direction === d ? T.teal : T.border}`, background: sort.direction === d ? T.teal : T.white, color: sort.direction === d ? T.white : T.muted }}>
                {d === "asc" ? "↑ Asc" : "↓ Desc"}
              </button>
            ))}
          </div>
        </Panel>

        {/* ── MORE OPTIONS ── */}
        <Panel title="More options" icon="⚙" open={pMore} onToggle={() => setPMore(v => !v)}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <div style={{ fontSize: 11, color: T.muted, marginBottom: 5 }}>Occurrence semantics</div>
              <div style={{ display: "flex", gap: 6 }}>
                {["ALL","ANY"].map(opt => (
                  <button key={opt} onClick={() => setAdv(p => ({ ...p, occurrence_semantics: opt }))}
                    style={{ flex: 1, fontFamily: "inherit", fontSize: 12, padding: "6px", borderRadius: 8, cursor: "pointer", border: `1px solid ${adv.occurrence_semantics === opt ? T.teal : T.border}`, background: adv.occurrence_semantics === opt ? T.teal : T.white, color: adv.occurrence_semantics === opt ? T.white : T.muted }}>
                    {opt}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: T.muted, marginBottom: 5 }}>Include unknown values</div>
              <button onClick={() => setAdv(p => ({ ...p, include_unknown: !p.include_unknown }))}
                style={{ width: "100%", fontFamily: "inherit", fontSize: 12, padding: "6px", borderRadius: 8, cursor: "pointer", border: `1px solid ${adv.include_unknown ? T.teal : T.border}`, background: adv.include_unknown ? T.teal : T.white, color: adv.include_unknown ? T.white : T.muted }}>
                {adv.include_unknown ? "Yes — include" : "No — exclude"}
              </button>
            </div>
            <div>
              <div style={{ fontSize: 11, color: T.muted, marginBottom: 5 }}>Slice size (files to scan)</div>
              <input type="number" value={adv.slice_size} onChange={e => setAdv(p => ({ ...p, slice_size: +e.target.value }))} style={inp({ width: "100%" })} />
            </div>
            <div>
              <div style={{ fontSize: 11, color: T.muted, marginBottom: 5 }}>Result limit</div>
              <input type="number" value={adv.result_limit} onChange={e => setAdv(p => ({ ...p, result_limit: +e.target.value }))} style={inp({ width: "100%" })} />
            </div>
          </div>
        </Panel>

        {/* ── SEARCH ACTIONS ── */}
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={runQuery} disabled={querying}
            style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "inherit", fontSize: 14, fontWeight: 700, padding: "11px 24px", borderRadius: 10, background: querying ? T.muted : T.teal, color: T.white, border: "none", cursor: querying ? "default" : "pointer", letterSpacing: ".01em" }}>
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="6.5" cy="6.5" r="5" stroke="currentColor" strokeWidth="1.8"/><path d="M11 11l3 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
            {querying ? "Executing…" : "Execute query"}
          </button>
          <button onClick={reset} style={{ fontFamily: "inherit", fontSize: 13, color: T.muted, background: "none", border: "none", cursor: "pointer", padding: "11px 10px" }}>Reset all</button>
          {result && (
            <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
              {[["cards","⊞ Cards"],["table","⊟ Table"]].map(([m, lbl]) => (
                <button key={m} onClick={() => setView(m)}
                  style={{ fontFamily: "inherit", fontSize: 12, padding: "7px 14px", borderRadius: 8, cursor: "pointer", border: `1px solid ${view === m ? T.ink : T.border}`, background: view === m ? T.ink : T.white, color: view === m ? T.white : T.muted }}>
                  {lbl}
                </button>
              ))}
            </div>
          )}
        </div>

        {qErr && <div style={{ background: "#fef2f2", border: `1px solid ${T.redBorder}`, borderRadius: 10, padding: "9px 13px", fontSize: 12, color: T.red }}>{qErr}</div>}

        {/* ── RESULTS ── */}
        {result && (
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: result.matched > 0 ? T.green : T.red }}>{result.matched > 0 ? "✓" : "✗"}</span>
                <span style={{ fontSize: 14, fontWeight: 700, color: T.ink }}>{result.matched.toLocaleString()} matched</span>
                <span style={{ fontSize: 12, color: T.muted }}>of {result.scanned.toLocaleString()} scanned · {result.elapsed_sec}s</span>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                {[["funnel","↓ Funnel",pFunnel,setPFunnel],["explain","✦ Explain",pExplain,setPExplain]].map(([k,lbl,open,set]) => (
                  <button key={k} onClick={() => set(v => !v)}
                    style={{ fontFamily: "inherit", fontSize: 12, padding: "5px 12px", borderRadius: 8, cursor: "pointer", border: `1px solid ${open ? T.ink : T.border}`, background: open ? T.ink : T.white, color: open ? T.white : T.muted }}>
                    {lbl}
                  </button>
                ))}
              </div>
            </div>

            {pFunnel && result.funnel.length > 0 && (
              <div style={{ background: T.white, border: `1px solid ${T.border}`, borderRadius: 12, padding: 14, marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 10 }}>Query filter funnel</div>
                {result.funnel.map((s, i) => {
                  const max = result.funnel[0]?.count || 1;
                  const pct = Math.round((s.count / max) * 100);
                  return (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 11, color: T.muted, marginBottom: 3 }}>{s.label || s.stage}</div>
                        <div style={{ height: 7, background: "#f1f5f9", borderRadius: 4, overflow: "hidden" }}>
                          <div style={{ width: `${pct}%`, height: "100%", background: `hsl(${175 - i*25},65%,45%)`, borderRadius: 4 }} />
                        </div>
                      </div>
                      <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "monospace", color: T.ink, minWidth: 36, textAlign: "right" }}>{s.count}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {pExplain && (
              <div style={{ background: T.white, border: `1px solid ${T.border}`, borderRadius: 12, padding: 14, marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: T.muted, textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 8 }}>Explainability</div>
                <div style={{ fontSize: 12, color: T.muted, fontStyle: "italic", marginBottom: 10 }}>{result.summary}</div>
                {activeCnt === 0 && <div style={{ background: T.amberBg, border: `1px solid ${T.amberBorder}`, borderRadius: 8, padding: "8px 12px", fontSize: 12, color: T.amber }}>No filters active — all records matched.</div>}
                {Object.entries(crit).map(([fk, v]) => {
                  const f = byKey[fk]; if (!f) return null;
                  const op = f.operators.find(o => o.op === v.operator);
                  return (
                    <div key={fk} style={{ display: "flex", alignItems: "center", gap: 7, padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                      <DVTag type={f.dv_type} />
                      <span style={{ fontSize: 12, color: T.ink, flex: 1 }}>{f.full_label}</span>
                      <span style={{ fontSize: 11, color: T.tealDark, background: T.tealBg, padding: "2px 8px", borderRadius: 6 }}>{op?.phrase} {v.rawValue}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {result.matched === 0 && (
              <div style={{ background: "#fef2f2", border: `1px solid ${T.redBorder}`, borderRadius: 12, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: T.red, marginBottom: 4 }}>No records matched</div>
                <div style={{ fontSize: 12, color: "#ef4444" }}>Try relaxing filters or switching occurrence semantics to ANY.</div>
              </div>
            )}

            {view === "cards" && result.rows.length > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {result.rows.map((row, i) => <RCard key={i} row={row} labels={activeOutLabels} index={i} />)}
              </div>
            )}

            {view === "table" && result.rows.length > 0 && (
              <div style={{ background: T.white, border: `1px solid ${T.border}`, borderRadius: 12, overflow: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: "#f8fafc", borderBottom: `1px solid ${T.border}` }}>
                      {activeOutLabels.map(l => <th key={l} style={{ textAlign: "left", padding: "9px 13px", color: T.muted, fontWeight: 600, fontSize: 10, textTransform: "uppercase", letterSpacing: ".05em", whiteSpace: "nowrap" }}>{l.split("→").pop().trim()}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr key={i} style={{ borderBottom: `1px solid #f1f5f9`, background: i % 2 === 0 ? T.white : "#fafbfc" }}>
                        {activeOutLabels.map(l => <td key={l} style={{ padding: "7px 13px", color: T.slate, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row[l] != null ? String(row[l]) : <span style={{ color: "#94a3b8" }}>—</span>}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* EMPTY STATE */}
        {!result && !querying && (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: T.tealBg, border: `1px solid ${T.tealBorder}`, margin: "0 auto 12px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="9" cy="9" r="6.5" stroke={T.teal} strokeWidth="1.8"/><path d="M14.5 14.5l4 4" stroke={T.teal} strokeWidth="1.8" strokeLinecap="round"/></svg>
            </div>
            <p style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 600, color: T.ink }}>Form auto-generated from schema</p>
            <p style={{ margin: 0, fontSize: 12, color: T.muted }}>{allFields.length} fields across {formDef?.criteria_groups.length} composition groups</p>
            <p style={{ margin: "8px 0 0", fontSize: 12, color: "#94a3b8" }}>Add filters above → Execute query</p>
          </div>
        )}

      </div>
    </div>
  );
}
