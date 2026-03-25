# GEMINI.MD: AI Collaboration Guide

This document provides essential context for AI models interacting with the **Customer Booking Agent** project. Adhering to these guidelines will ensure consistency and maintain code quality across the multi-agent system.

## 1. Project Overview & Purpose

* **Primary Goal:** A multi-agent system designed to assist users with travel bookings and customer information retrieval.
* **Architecture:** An orchestrator-delegate model where a "Customers" agent manages user identity and delegates booking tasks to a "Bookings" agent.
* **Business Domain:** Travel & Hospitality / Customer Relationship Management (CRM).

## 2. Core Technologies & Stack

* **Languages:** Python 3.10+ (managed via `uv`).
* **Frameworks:**
    * **Google Agent Development Kit (ADK) 1.x:** Core framework for agent logic.
    * **Vertex AI Agent Engine (Reasoning Engine):** Deployment platform for remote execution.
    * **FastAPI:** Web frontend (`fast-api-fe`) providing an OpenAI-compatible chat interface.
* **Key Libraries:**
    * `google-adk`: Agent building and tool registration.
    * `google-cloud-aiplatform`: Vertex AI SDK for session management and streaming queries.
    * `a2a-sdk`: (Experimental) Agent-to-Agent communication.
* **Infrastucture:**
    * **Google Cloud Identity-Aware Proxy (IAP):** Handles authentication and provides JWT claims (user identity, roles).
    * **Vertex AI Memory Bank:** Provides long-term, cross-session memory for user preferences.

## 3. Architectural Patterns

* **Multi-Agent Orchestration:**
    * `customers/agent.py`: The root orchestrator. It looks up customer details and detects booking intent.
    * `bookings/agent.py`: Specialized agent for processing reservations and booking logic.
* **Project Structure:**
    * `/customers`: Orchestrator agent logic.
    * `/bookings`: Booking agent logic.
    * `/fast-api-fe`: Web UI and API gateway.
    * `/deployment`: Terraform and deployment scripts for Agent Engine and Cloud Run.
* **Communication Flow:**
    * User -> IAP (Auth) -> FastAPI -> Customers Agent (Vertex AI SDK) -> Bookings Agent (Agent Engine API/A2A).

## 4. Coding Conventions & Style Guide

* **Python Style:** PEP 8 compliance, 4-space indentation.
* **Naming:** `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_CASE` for constants.
* **ADK Patterns:**
    * Favor the **Agent-Executor/ServiceManager** pattern for lazy loading.
    * Use `FunctionTool` for simple tasks and `AgentTool` for delegation.
* **Memory Management:**
    * Use `vertexai.Client.agent_engines.memories` for long-term fact extraction.

## 5. Key Files & Entrypoints

* **Main Entrypoints:**
    * `fast-api-fe/main.py`: The web interface entry point.
    * `customers/deploy_agent_engine.py`: Script to deploy the orchestrator.
    * `bookings/deploy_agent_engine.py`: Script to deploy the booking agent.
* **Configuration:**
    * `pyproject.toml`: Root dependency management (using `uv`).
    * `Makefile`: Centralized commands for `install`, `playground`, `deploy`, and `test`.

## 6. Development & Testing Workflow

* **Package Management:** Always use `uv`. Run `make install` to sync the environment.
* **Local Testing:** Use `make playground` to launch the ADK web preview.
* **Evaluation:** Use `make eval` to run ADK evalsets against agent trajectories.
* **Deployment:** Use `make deploy` and `make deploy-customers` to push to Vertex AI.

## 7. Specific Instructions for AI Collaboration

* **Surgical Edits:** When modifying agent logic, preserve existing model parameters and system prompt structures.
* **ADK Reference:** Refer to `google.adk` documentation for tool and agent registration patterns.
* **Testing:** Proactively suggest/run `make test` or `make eval` after architectural changes.
* **Auth Details:** Be aware that user identity is extracted from the `x-goog-iap-jwt-assertion` header in `fast-api-fe` and passed to agents.
