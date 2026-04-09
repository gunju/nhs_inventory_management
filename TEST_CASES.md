# NHS Care Operations Copilot Test Cases

This file contains practical demo and QA scenarios for the MVP. All examples use synthetic or pseudonymised inputs only.

## How to run the cases

Use either:

- the frontend at `http://localhost:5173`
- the FastAPI docs at `http://localhost:8000/docs`
- the inventory recommendation endpoint: `POST /api/v1/copilot/inventory-recommendation`

Recommended test flow:

1. Paste a case into the patient case input.
2. Run the inventory copilot.
3. Review:
   - bundle contents
   - item-level rationale
   - citations
   - confidence
   - warnings
   - explainability notes
   - audit log entry

## Expected behaviour principles

- Recommendations are decision support only.
- Clinician approval is always required.
- No evidence means no recommendation.
- Confidence can change without changing the bundle if the same pathway and rule set still apply.
- Inventory variation should now reflect monitoring needs and case signals.

## Test Case 1: Respiratory Deterioration

### Input

```json
{
  "patient_pseudo_id": "P001",
  "case_summary": "Patient on virtual ward with COPD exacerbation. Oxygen saturation has declined from 94% to 91% over 48 hours with increased breathlessness.",
  "site_id": "site_01",
  "user_role": "virtual_ward_coordinator"
}
```

### Expected outcome

- Pathway should be `virtual_ward_respiratory`
- Monitoring needs should include `pulse_oximetry` and `blood_pressure`
- Inventory should include `OX001`
- Inventory may include `BP002`
- Citations should be present
- Confidence should be non-zero
- Explainability notes should be visible
- Stockout warning for pulse oximeter is likely

## Test Case 2: Stable Respiratory Follow-Up

### Input

```json
{
  "patient_pseudo_id": "P002",
  "case_summary": "Patient recovering at home after respiratory admission. Stable symptoms and routine remote observations required.",
  "site_id": "site_01",
  "user_role": "virtual_ward_coordinator"
}
```

### Expected outcome

- Pathway should remain respiratory
- Urgency should be lower than Test Case 1
- Inventory should usually be smaller than the urgent deterioration case
- `OX001` is likely
- Fewer warning/escalation cues than the urgent case

## Test Case 3: Respiratory Case with Infection Cue

### Input

```json
{
  "patient_pseudo_id": "P003",
  "case_summary": "Virtual ward respiratory patient with worsening breathlessness, fever, and declining oxygen saturation over 48 hours.",
  "site_id": "site_01",
  "user_role": "virtual_ward_nurse"
}
```

### Expected outcome

- Respiratory pathway
- Monitoring needs should include `pulse_oximetry`, `blood_pressure`, and `temperature_monitoring`
- Inventory should include `OX001`, `BP002`, and `TH003`
- Explainability should mention deterioration and infection-style cues
- Citations should be present

## Test Case 4: General Virtual Ward Case

### Input

```json
{
  "patient_pseudo_id": "P004",
  "case_summary": "Patient discharged home for general virtual ward follow-up with routine observations and no respiratory red flags.",
  "site_id": "site_01",
  "user_role": "clinical_ops_coordinator"
}
```

### Expected outcome

- Pathway should likely fall back to `virtual_ward_general`
- Bundle should differ from the respiratory deterioration case
- Respiratory-specific evidence may be weaker or absent
- If evidence is insufficient, warnings should reflect that

## Test Case 5: Heart Failure Style Monitoring

### Input

```json
{
  "patient_pseudo_id": "P005",
  "case_summary": "Patient on home monitoring with heart failure symptoms, increasing ankle swelling, and need for daily blood pressure and weight monitoring.",
  "site_id": "site_01",
  "user_role": "clinical_ops_coordinator"
}
```

### Expected outcome

- Monitoring needs should include `weight_monitoring`
- Inventory should include `WS004`
- Explainability should mention heart-failure-style monitoring context
- This is a good demo of bundle variation beyond the respiratory baseline

## Test Case 6: Insufficient Evidence / Refusal Behaviour

### Input

```json
{
  "patient_pseudo_id": "P006",
  "case_summary": "Orthopaedic rehab equipment request for home mobility support unrelated to approved virtual ward respiratory protocols.",
  "site_id": "site_01",
  "user_role": "clinical_ops_coordinator"
}
```

### Expected outcome

- No strong recommendation should be returned
- Warning should indicate insufficient evidence or no matching approved evidence-backed rules
- This is the clearest governance test for “no evidence, no recommendation”

## Test Case 7: Stock Pressure Demonstration

### Input

```json
{
  "patient_pseudo_id": "P007",
  "case_summary": "Another respiratory pathway patient needing home pulse oximetry, blood pressure monitoring, and temperature checks after discharge.",
  "site_id": "site_01",
  "user_role": "supply_chain_lead"
}
```

### Expected outcome

- Respiratory monitoring kit style response
- Warning panel should be useful for stockout-risk storytelling
- Good case for linking patient need with operational risk

## Test Case 8: Referral Draft Companion Case

Use the referral endpoint:

```text
GET /api/v1/referral/draft?patient_pseudo_id=P001&specialty_requested=respiratory
```

### Expected outcome

- Draft summary should populate
- Suggested route should be one of:
  - `A_AND_G`
  - `REFERRAL_ASSESSMENT`
  - `ROUTINE_REFERRAL`
- `required_human_approval` should be `true`
- Protocol citations should be present when evidence exists

## Test Case 9: Forecast Horizon Comparison

Use:

- `GET /api/v1/forecasting/run?site_id=site_01&horizon_days=7`
- `GET /api/v1/forecasting/run?site_id=site_01&horizon_days=14`
- `GET /api/v1/forecasting/run?site_id=site_01&horizon_days=28`

### Expected outcome

- Output schema should include `q10`, `q50`, and `q90`
- Longer horizons should extend the series length
- This should be presented as structured forecasting, not LLM prediction

## Suggested demo sequence

Use this order for a strong live demo:

1. Test Case 1: show standard respiratory deterioration support
2. Test Case 3: show added thermometer and richer explainability
3. Test Case 5: show a different monitoring bundle with weight scale
4. Test Case 6: show refusal behaviour
5. Test Case 9: show forecasting
6. Test Case 8: show referral drafting
7. Audit log: show governance trail

## Good talking points during review

- “The bundle is deterministic and evidence-constrained.”
- “The confidence score reflects evidence strength, not autonomous certainty.”
- “The explainability panel shows patient signals, rules applied, and governance notes.”
- “The system supports clinical operations decisions and always requires human review.”
