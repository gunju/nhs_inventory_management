export const API_BASE = "http://localhost:8000/api/v1";

export async function postInventoryRecommendation(payload: {
  patient_pseudo_id: string;
  case_summary: string;
  site_id: string;
  user_role: string;
}) {
  const response = await fetch(`${API_BASE}/copilot/inventory-recommendation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function getForecast() {
  const response = await fetch(`${API_BASE}/forecasting/run?site_id=site_01&horizon_days=14`);
  return response.json();
}

export async function getReferralDraft() {
  const response = await fetch(`${API_BASE}/referral/draft?patient_pseudo_id=P001&specialty_requested=respiratory`);
  return response.json();
}

export async function getAuditLogs() {
  const response = await fetch(`${API_BASE}/audit/`);
  return response.json();
}
