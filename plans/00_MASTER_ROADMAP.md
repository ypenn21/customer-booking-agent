# 00_MASTER_ROADMAP: Customer Booking Agent

This document tracks the high-level Strategic Campaigns (Epics) for the Customer Booking Agent project.

## Strategic Campaigns (Epics)

| ID | Campaign Name | Status | Description |
|---|---|---|---|
| EPIC-1 | Secure Authentication & Identity | **Active** | Establish Identity-Aware Proxy (IAP), Microsoft Auth integration, and Identity Platform Blocking Functions. |
| EPIC-2 | Token Management & External Service Integration | Planned | Secure storage of Microsoft API tokens in Secret Manager and retrieval by backend agents. |
| EPIC-3 | Frontend Chat Experience | Planned | FastAPI integration to extract IAP JWTs, manage sessions, and route authenticated requests. |
| EPIC-4 | Orchestration & Multi-Agent Communication | Planned | Customers Orchestrator Agent logic to detect intent and securely delegate to the Bookings Agent. |

> **Note:** For detailed user stories and task interdependencies, refer to `PHASE_1_EPICS_STORIES.md`.