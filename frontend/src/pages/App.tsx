import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card } from "../components/Card";
import { getAuditLogs, getForecast, getReferralDraft, postInventoryRecommendation } from "../lib/api";

export function App() {
  const [caseSummary, setCaseSummary] = useState(
    "Patient on virtual ward with COPD exacerbation. Oxygen saturation has declined from 94% to 91% over 48 hours with increased breathlessness.",
  );
  const [inventoryResult, setInventoryResult] = useState<any>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [referral, setReferral] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  useEffect(() => {
    getForecast().then(setForecast).catch(() => undefined);
    getReferralDraft().then(setReferral).catch(() => undefined);
    getAuditLogs().then(setAuditLogs).catch(() => undefined);
  }, []);

  const submitCase = async () => {
    const result = await postInventoryRecommendation({
      patient_pseudo_id: "P001",
      case_summary: caseSummary,
      site_id: "site_01",
      user_role: "virtual_ward_coordinator",
    });
    setInventoryResult(result);
    const refreshed = await getAuditLogs();
    setAuditLogs(refreshed);
  };

  const chartData = forecast?.series?.filter((item: any) => item.sku_id === "OX001") ?? [];

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-4 py-8 md:px-8">
      <header className="rounded-[2rem] bg-ink px-8 py-8 text-white shadow-xl">
        <p className="text-sm uppercase tracking-[0.3em] text-teal-200">Decision support only</p>
        <h1 className="mt-3 text-4xl font-semibold">NHS Care Operations Copilot</h1>
        <p className="mt-4 max-w-3xl text-slate-200">
          Connects patient pathway signals, approved protocol evidence, inventory bundles, demand forecasting, and referral drafting with clinician review required at every step.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <h2 className="text-xl font-semibold text-ink">Patient Case Demo</h2>
          <p className="mt-2 text-sm text-slate-600">Synthetic data only. Recommendations are advisory and require clinician approval.</p>
          <textarea
            className="mt-4 min-h-40 w-full rounded-2xl border border-slate-200 bg-mist p-4 text-sm"
            value={caseSummary}
            onChange={(event) => setCaseSummary(event.target.value)}
          />
          <button className="mt-4 rounded-full bg-signal px-5 py-3 font-medium text-white" onClick={submitCase}>
            Run Inventory Copilot
          </button>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold text-ink">Referral Draft</h2>
          {referral ? (
            <div className="mt-4 space-y-3 text-sm text-slate-700">
              <p>{referral.summary}</p>
              <p className="font-medium text-ink">Suggested route: {referral.suggested_route.type}</p>
              <p>{referral.suggested_route.reasoning}</p>
              <p className="rounded-2xl bg-amber-50 p-3 text-alert">Clinician approval required before any onward action.</p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">Referral draft will appear once the backend is seeded and running.</p>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <h2 className="text-xl font-semibold text-ink">Recommended Inventory</h2>
          {inventoryResult ? (
            <div className="mt-4 space-y-4 text-sm">
              <p className="font-medium text-ink">{inventoryResult.recommended_bundles?.[0]?.bundle_name}</p>
              {inventoryResult.recommended_bundles?.[0]?.items?.map((item: any) => (
                <div key={item.sku_id} className="rounded-2xl bg-mist p-3">
                  <p className="font-medium">{item.item_name} ({item.sku_id})</p>
                  <p>Qty: {item.qty} {item.unit}</p>
                  <p className="mt-1 text-slate-700">{item.rationale}</p>
                  <p className="mt-1 text-xs text-slate-500">Decision factors: {item.decision_factors.join(", ")}</p>
                  <p>Substitutions: {item.substitutions.join(", ") || "None"}</p>
                </div>
              ))}
              <p className="rounded-2xl bg-slate-50 p-3">
                Confidence: {inventoryResult.recommended_bundles?.[0]?.rationale?.confidence ?? "n/a"}
              </p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">Run the demo case to generate a protocol-backed inventory recommendation.</p>
          )}
        </Card>

        <Card>
          <h2 className="text-xl font-semibold text-ink">Evidence and Citations</h2>
          {inventoryResult?.recommended_bundles?.[0]?.rationale?.citations?.length ? (
            <div className="mt-4 space-y-3 text-sm text-slate-700">
              {inventoryResult.recommended_bundles[0].rationale.explainability_notes?.map((note: any) => (
                <div key={note.label} className="rounded-2xl bg-slate-50 p-3">
                  <p className="font-medium text-ink">{note.label}</p>
                  <p>{note.detail}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">{note.source}</p>
                </div>
              ))}
              {inventoryResult.recommended_bundles[0].rationale.citations.map((citation: any) => (
                <div key={citation.chunk_id} className="rounded-2xl border border-slate-200 p-3">
                  <p className="font-medium text-ink">{citation.doc_id}</p>
                  <p>{citation.quote}</p>
                  <p className="mt-2 text-xs text-slate-500">{citation.url_or_path}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">Citations are shown only when approved evidence exists.</p>
          )}
        </Card>

        <Card>
          <h2 className="text-xl font-semibold text-ink">Warnings</h2>
          <div className="mt-4 space-y-3 text-sm">
            {inventoryResult?.recommended_bundles?.[0]?.explainability?.governance_notes?.map((note: string) => (
              <div key={note} className="rounded-2xl bg-slate-50 p-3 text-slate-700">
                <p>{note}</p>
              </div>
            ))}
            {(inventoryResult?.warnings ?? []).map((warning: any, index: number) => (
              <div key={`${warning.type}-${index}`} className="rounded-2xl bg-amber-50 p-3 text-alert">
                <p className="font-medium">{warning.type}</p>
                <p>{warning.detail}</p>
              </div>
            ))}
            {!inventoryResult && <p className="text-slate-500">Stockout and evidence warnings will appear here.</p>}
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <Card>
          <h2 className="text-xl font-semibold text-ink">Forecasting Trends</h2>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="forecastFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#007a6c" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#007a6c" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#d6e1e0" strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="q50" stroke="#007a6c" fill="url(#forecastFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold text-ink">Audit Log</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-700">
            {auditLogs.slice(0, 5).map((log) => (
              <div key={log.id} className="rounded-2xl bg-mist p-3">
                <p className="font-medium text-ink">{log.request_id}</p>
                <p>{log.user_role}</p>
                <p className="text-xs text-slate-500">{log.created_at}</p>
              </div>
            ))}
            {!auditLogs.length && <p className="text-slate-500">Audit events will populate after recommendation runs.</p>}
          </div>
        </Card>
      </div>
    </main>
  );
}
