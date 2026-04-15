# Accessibility Evidence Plan — NHS Inventory Intelligence Copilot

> **Standard:** Public Sector Bodies Accessibility Regulations 2018 / WCAG 2.1 AA
> **Status:** PLAN — implement when frontend is developed

## Scope

This document covers the web front-end of the NHS Inventory Intelligence Copilot.

The current release is an API-only backend. This accessibility plan applies to any frontend implementation.

## WCAG 2.1 AA Requirements

### Priority 1 — Must Have

| Criterion | WCAG | Requirement |
|---|---|---|
| Keyboard navigation | 2.1.1 | All features operable by keyboard |
| Focus visible | 2.4.7 | Keyboard focus indicator visible |
| Colour contrast | 1.4.3 | 4.5:1 ratio for text |
| Text resize | 1.4.4 | No loss of functionality at 200% zoom |
| Screen reader support | 4.1.2 | All UI components have accessible names |
| Error identification | 3.3.1 | Errors described in text |
| Language of page | 3.1.1 | HTML `lang` attribute set |

### Priority 2 — Should Have

| Criterion | WCAG | Requirement |
|---|---|---|
| Skip navigation | 2.4.1 | Skip to main content link |
| Consistent navigation | 3.2.3 | Navigation consistent across pages |
| Labels or instructions | 3.3.2 | Form inputs have labels |
| Captions | 1.2.2 | Captions for any video content |

## Testing Plan

| Test Type | Tool | Frequency |
|---|---|---|
| Automated scan | axe-core / Lighthouse | Each release |
| Manual keyboard test | Developer testing | Each release |
| Screen reader test | NVDA + Chrome, VoiceOver + Safari | Before go-live |
| Colour contrast | Colour Contrast Analyser | Design phase |
| User research with disabled users | Moderated sessions | Before go-live |

## Accessibility Statement

An Accessibility Statement must be published with the deployed service per regulation 8 of the Public Sector Bodies Accessibility Regulations 2018.

Template: [https://www.gov.uk/guidance/accessibility-requirements-for-public-sector-websites-and-apps]

---

*This plan must be reviewed and completed before public-facing deployment.*
