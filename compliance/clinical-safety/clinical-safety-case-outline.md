# Clinical Safety Case Outline — NHS Inventory Intelligence Copilot

> **Standard:** DCB0129 (Clinical Risk Management: its Application in the Manufacture of Health IT Systems)
> **Status:** OUTLINE — requires completion by appointed Clinical Safety Officer (CSO)

## 1. System Identification

| Field | Value |
|---|---|
| System Name | NHS Inventory Intelligence Copilot |
| Version | 1.0.0 |
| Classification | Operational decision-support tool (NON-clinical) |
| Developer | [Organisation name] |
| CSO | [To be appointed] |
| Date | [To be completed] |

## 2. System Description

The NHS Inventory Intelligence Copilot is an **operational** tool that supports NHS supply chain staff in managing medical inventory. It provides:

- Stock level monitoring and alerting
- Demand forecasting based on consumption history
- Reorder and redistribution suggestions (requiring human approval)
- Natural language Q&A about inventory data

**Explicit exclusions:**
- The system does NOT make clinical decisions
- The system does NOT access patient records
- The system does NOT recommend clinical treatments or dosages
- All AI recommendations are advisory only and require human review before action

## 3. Intended Use

**Intended users:** Supply chain managers, ward managers, procurement teams
**Intended environment:** NHS Trust internal network / NHS-approved cloud
**Intended purpose:** Operational inventory management support

## 4. Hazard Identification

### Potential Hazards

| ID | Hazard | Severity | Likelihood | Risk Level | Mitigation |
|---|---|---|---|---|---|
| H-001 | Incorrect stock level displayed → wrong reorder decision → supply shortage | Medium | Low | Medium | Audit log, human approval required, data freshness timestamps |
| H-002 | AI recommendation accepted without review → unnecessary expenditure | Low | Low | Low | Mandatory review step in workflow, UI warning, audit trail |
| H-003 | System unavailable during stock emergency | Medium | Low | Medium | Business continuity plan, failover, manual process documented |
| H-004 | Unauthorised access to procurement data | Medium | Low | Medium | RBAC, JWT auth, audit logging, pen testing |
| H-005 | Incorrect demand forecast → suboptimal stock levels | Low | Medium | Medium | Confidence scores shown, forecasts labelled with model type |

### Out of Scope Hazards

The following hazards are explicitly out of scope as the system does not interact with clinical pathways:
- Patient harm from incorrect medication recommendation
- Clinical treatment errors

## 5. Risk Controls

| Control | Implementation |
|---|---|
| Human-in-the-loop approval | `RecommendationDecision` model; recommendations not actioned until approved |
| Audit trail | All actions logged to `audit_logs` table with user, timestamp, and outcome |
| Confidence scoring | Every AI recommendation includes a confidence score and reason codes |
| Data provenance | Evidence JSON attached to every recommendation showing source data |
| Role-based access | RBAC with 7 roles; principle of least privilege |

## 6. Residual Risk Assessment

After controls: all identified hazards reduce to **acceptable** per ALARP (As Low As Reasonably Practicable).

## 7. Approval

| Role | Name | Signature | Date |
|---|---|---|---|
| Clinical Safety Officer | | | |
| Project Lead | | | |
| Information Governance Lead | | | |

---

*This document must be reviewed at each major version release and before deployment to production.*
