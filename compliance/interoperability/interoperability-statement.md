# Interoperability Statement — NHS Inventory Intelligence Copilot

> **Status:** DRAFT — review with integration team before deployment

## Current Integration Capabilities

### Inbound Data Adapters

The system provides a pluggable adapter architecture (`app/integrations/base.py`):

| Adapter | Format | Status |
|---|---|---|
| `CSVConsumptionAdapter` | CSV file upload | Implemented |
| `MockEPRAdapter` | Mock EPR system | Implemented (dev/test) |
| Custom adapters | Extend `BaseAdapter` ABC | Framework ready |

### API

- **OpenAPI 3.0** specification available at `/openapi.json`
- **RESTful JSON API** — all endpoints return structured JSON
- **JWT authentication** — standard Bearer token scheme

## Future Integration Roadmap

### HL7 FHIR

Planned FHIR resources to align with:

| Resource | Purpose | Status |
|---|---|---|
| `SupplyDelivery` | Goods receipt, stock receipt | Planned |
| `SupplyRequest` | Purchase orders | Planned |
| `Medication` | Medication inventory | Planned |
| `Organization` | Trust/Hospital hierarchy | Planned |
| `Location` | Ward/department locations | Planned |

Target: FHIR R4 compliance for inventory resources.

### NHS Login / NHS Identity

- SSO integration with NHS Identity for user authentication (planned)
- Current: local JWT auth with email/password

### EPMA / EPR Integration

Integration with Electronic Prescribing and Medicines Administration (EPMA) systems:
- Consumption data ingest from EPMA via FHIR `MedicationAdministration` events (planned)
- Currently: CSV upload or mock EPR adapter

### dm+d (Dictionary of Medicines and Devices)

- Product catalogue alignment with NHS dm+d codes (planned)
- `Product.udi` field reserved for UDI/device registration codes
- `Product.gtin` field supports GS1 GTIN barcodes

### NHS Spine / PDS

- No integration required (system does not process patient data)

## Data Standards

| Standard | Usage |
|---|---|
| ISO 8601 | All dates and timestamps |
| UUID v4 | All entity identifiers |
| GS1 GTIN | Product barcode identifiers |
| NHS ODS codes | Trust and hospital identification |

---

*Contact the integration team to discuss EPR/FHIR connector requirements.*
