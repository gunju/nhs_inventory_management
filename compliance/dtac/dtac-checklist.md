# DTAC Assessment Checklist — NHS Inventory Intelligence Copilot

> **Status:** IN PROGRESS — complete before NHS deployment
> Reference: [Digital Technology Assessment Criteria (DTAC)](https://transform.england.nhs.uk/key-tools-and-info/digital-technology-assessment-criteria-dtac/)

## 1. Clinical Safety (DCB0129 / DCB0160)

| Criterion | Status | Evidence |
|---|---|---|
| Clinical Risk Management System documented | TODO | See `clinical-safety/clinical-safety-case-outline.md` |
| Hazard log maintained | TODO | Initiate via clinical safety officer |
| System classified as non-clinical decision support tool | DONE | Documented in API description and UI copy |
| Clinical Safety Officer (CSO) appointed | TODO | Assign CSO, record in hazard log |
| Clinical safety case report produced | TODO | Required before deployment |

## 2. Data Protection (GDPR / UK GDPR)

| Criterion | Status | Evidence |
|---|---|---|
| Data Protection Impact Assessment (DPIA) completed | TODO | See `data-protection/dpia-template.md` |
| Data Controller identified | TODO | NHS Trust as controller |
| Lawful basis for processing documented | TODO | Legitimate interests / public task |
| Data minimisation applied | DONE | No patient-identifiable data stored |
| Data Retention Policy defined | TODO | Define and document |
| Subject Access Request process documented | TODO | |
| Data Processor agreements in place | TODO | Cloud provider DPAs required |

## 3. Technical Security

| Criterion | Status | Evidence |
|---|---|---|
| Penetration testing completed | TODO | Commission before go-live |
| OWASP Top 10 addressed | PARTIAL | JWT auth, parameterised queries, input validation via Pydantic |
| Authentication: MFA capable | TODO | SSO/MFA integration placeholder |
| Role-based access control implemented | DONE | `app/api/middleware/auth.py` |
| Audit logging implemented | DONE | `app/models/audit.py`, all actions logged |
| Data encrypted in transit (TLS) | TODO | Configure reverse proxy / load balancer |
| Data encrypted at rest | TODO | PostgreSQL encryption or disk-level |
| Secrets management | TODO | Replace `.env` with secrets manager (Vault / AWS Secrets Manager) |
| Dependency vulnerability scanning | TODO | Integrate `safety` / Dependabot |

## 4. Interoperability

| Criterion | Status | Evidence |
|---|---|---|
| HL7 FHIR compatibility considered | TODO | See `interoperability/interoperability-statement.md` |
| NHS login integration scoped | TODO | |
| SNOMED CT / dm+d coding supported | PARTIAL | Product SKU/GTIN fields; dm+d mapping TODO |
| Open API published | DONE | `/docs` and `/openapi.json` endpoints |

## 5. Usability and Accessibility

| Criterion | Status | Evidence |
|---|---|---|
| WCAG 2.1 AA compliance plan | TODO | See `accessibility/accessibility-evidence-plan.md` |
| User research conducted | TODO | |
| Accessibility audit completed | TODO | |

## 6. Business Continuity

| Criterion | Status | Evidence |
|---|---|---|
| Business Continuity Plan documented | TODO | |
| Disaster Recovery plan documented | TODO | |
| RTO / RPO defined | TODO | |
| Backup and restore tested | TODO | |

---

*This checklist must be reviewed and signed off by a named responsible person before deployment.*
