# DSPT Evidence Notes — NHS Inventory Intelligence Copilot

> **Standard:** NHS Data Security and Protection Toolkit (DSPT)
> **Status:** NOTES — map to your Trust's DSPT submission

## Relevant DSPT Assertions

The following DSPT assertions are most relevant to this system:

### Data Security Standard 1: Personal Confidential Data
- Assertion 1.3: All staff with access to personal data have completed Data Security Awareness training
  - **Evidence:** User provisioning process must include mandatory training verification

### Data Security Standard 3: Training
- System administrators and developers complete annual cyber security training
  - **Evidence:** HR training records

### Data Security Standard 6: Cyber Security
- Assertion 6.1: Network security controls in place
  - **Evidence:** Firewall rules, TLS in transit, VPN/private network access only
- Assertion 6.4: Penetration test completed
  - **Evidence:** Engage third-party pen testing before go-live; track remediation

### Data Security Standard 7: Continuity Planning
- Assertion 7.1: Business continuity plans tested
  - **Evidence:** BCP document, test records, RTO/RPO defined

### Data Security Standard 10: Accountable Suppliers
- If using cloud hosting or third-party AI (OpenAI), Data Processing Agreements required
  - **Evidence:** Signed DPAs with all processors

## Audit Log as DSPT Evidence

The system's `audit_logs` and `data_access_logs` tables provide evidence for:

- Who accessed what data and when (Data Access Log)
- All changes to stock records (Audit Log `action=stock_adjustment`)
- All recommendation approvals (Audit Log `action=recommendation_decision`)
- Authentication events (Audit Log `action=user_login`)

SQL to export evidence:

```sql
-- Data access summary for DSPT submission
SELECT
    DATE(created_at) AS access_date,
    user_id,
    endpoint,
    data_classification,
    COUNT(*) AS access_count
FROM data_access_logs
WHERE created_at >= '2024-01-01'
GROUP BY DATE(created_at), user_id, endpoint, data_classification
ORDER BY access_date DESC;
```

---

*Coordinate with your Trust's IG/DSPT lead to map this system's controls to specific DSPT assertions in your submission.*
