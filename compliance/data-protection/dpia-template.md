# Data Protection Impact Assessment (DPIA) Template
# NHS Inventory Intelligence Copilot

> **Status:** TEMPLATE — complete with IG team before processing personal data
> **Standard:** UK GDPR Article 35 / ICO DPIA guidance

## 1. Describe the Processing

**What personal data is processed?**

| Data Category | Examples | Source | Purpose |
|---|---|---|---|
| User accounts | Name, NHS email, role | HR / manual entry | Authentication, audit |
| Audit logs | User ID, action, timestamp, IP address | System-generated | Compliance, security |
| Data access logs | User ID, endpoint accessed, timestamp | System-generated | DSPT evidence |

**What personal data is explicitly NOT processed:**
- Patient data or patient-identifiable information
- Clinical records
- Health data

**Data flows:**
1. User authentication: email/password → hashed password stored in PostgreSQL
2. User actions: logged to `audit_logs` table with user ID and IP
3. No data is shared with third parties except where explicitly configured (e.g., OpenAI for LLM; review data minimisation)

## 2. Assess Necessity and Proportionality

| Question | Response |
|---|---|
| Lawful basis | Public task (NHS operational function) / legitimate interests |
| Is the processing necessary? | Yes — authentication and audit are essential for DSPT compliance |
| Is there a less privacy-intrusive approach? | Pseudonymisation of user IDs in logs considered |
| How long is data retained? | Define retention policy (suggested: audit logs 7 years, inactive accounts 2 years) |
| Subject rights process | Define SAR handling procedure |

## 3. Identify and Assess Risks

| Risk | Likelihood | Impact | Control |
|---|---|---|---|
| Unauthorised access to user accounts | Low | Medium | Hashed passwords (bcrypt), JWT auth, RBAC |
| Data breach via SQL injection | Very Low | High | Parameterised queries (SQLAlchemy ORM), no raw SQL |
| Excessive data retention | Medium | Low | Define and enforce retention policy |
| Third-party LLM receives query data | Low | Medium | Default LLM provider is `mock` (no external calls); review before enabling OpenAI |

## 4. Sign-off

| Role | Name | Date |
|---|---|---|
| Data Controller Representative | | |
| Data Protection Officer (DPO) | | |
| System Owner | | |

---

*This DPIA must be reviewed annually and whenever processing activities change significantly.*
