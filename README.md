<div align="center">

# 🏢 AI Office

### Multi-Agent Orchestration Platform

**Research · Architecture · Engineering · QA · Creative — all in one autonomous loop**

[![Tests](https://img.shields.io/badge/tests-29_passing-10b981?style=flat-square)](./orchestrator/tests)
[![Python](https://img.shields.io/badge/python-3.12-3b82f6?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white)](./docker-compose.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-f59e0b?style=flat-square)](./LICENSE)

[**Quick Start**](#-quick-start) · [**Architecture**](#-architecture) · [**Agents**](#-agents) · [**API**](#-api-reference) · [**Dashboard**](#-dashboard) · [**Deployment**](#-deployment)

</div>

---

## What Is This?

AI Office is a **production-ready multi-agent orchestration platform** that coordinates specialist AI agents — researcher, architect, engineer, QA, and creative — to produce complete, verifiable deliverables from a single natural language request.

> *"Research the AI tutoring market in India, design an MVP architecture, build a sample auth service with tests, and create a promo video brief."*
>
> **→ AI Office dispatches agents in parallel, debates high-impact outputs, cross-validates everything, and returns a packaged deliverable with provenance on every claim.**

### Key Capabilities

| | Feature | Detail |
|---|---|---|
| 🧠 | **Task DAG Planner** | Claude converts user intent into a dependency graph of subtasks |
| ⚔️ | **Debate Engine** | PROPOSE → CRITIQUE → RESPOND → AGGREGATE with confidence scoring |
| 🔄 | **Adaptive Layer** | Detects recurring capability gaps, proposes and deploys new agents |
| 🔍 | **Shared Memory** | ChromaDB vector store — every agent reads and writes evidence |
| 📦 | **Provenance** | Every artifact has a chain of refs back to source URLs |
| 🛡️ | **Cross-Validation** | Every primary output verified by at least one other agent |
| 📡 | **Real-Time Events** | WebSocket stream — watch agents work live in the dashboard |
| 🖥️ | **Admin Dashboard** | Next.js 14 — trace viewer, agent registry, human-ops approvals |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER / UI                                │
└───────────────────────────────┬─────────────────────────────────┘
                                │  POST /api/v1/conversations
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  API GATEWAY  (FastAPI + WebSocket)             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR CORE                           │
│                                                                 │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │  Task Planner │  │  Debate Engine │  │  Adaptive Layer  │  │
│  │  (DAG builder)│  │  PROPOSE→AGG   │  │  Gap detect      │  │
│  └───────────────┘  └────────────────┘  └──────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──┐  ┌──────────▼─┐  ┌──────────▼─┐
    │  Product   │  │  Architect │  │  Engineer  │
    │  Manager   │  │   Agent    │  │   Agent    │
    │  (Claude)  │  │  (Claude)  │  │  (Claude)  │
    └────────────┘  └────────────┘  └────────────┘
              │                │                │
    ┌─────────▼──┐  ┌──────────▼─┐             │
    │    QA      │  │  Creative  │             │
    │   Agent    │  │   Agent    │             │
    │  (Claude)  │  │  (Gemini)  │             │
    └────────────┘  └────────────┘             │
              │                │                │
    ──────────┴────────────────┴────────────────┴──
                        SHARED STORAGE
    ┌────────────┐    ┌────────────┐    ┌──────────┐
    │  ChromaDB  │    │  S3/MinIO  │    │ Postgres │
    │ (vectors)  │    │(artifacts) │    │(metadata)│
    └────────────┘    └────────────┘    └──────────┘
```

---

## Full Request Lifecycle

```
User submits request
        │
        ▼
┌───────────────────────────────────────────────┐
│  STEP 1 · PLAN                                │
│                                               │
│  TaskPlanner (Claude Opus) converts           │
│  natural language → TaskSpec DAG:             │
│                                               │
│  t1: research ──────────────────────┐         │
│  t2: architecture  (depends: t1) ───┤         │
│  t3: code          (depends: t2) ───┤         │
│  t4: qa            (depends: t3) ───┘         │
│  t5: creative ──────────────────────┐         │
│                (runs parallel to t1)│         │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│  STEP 2 · DISPATCH                            │
│                                               │
│  Parallel: t1 (research) + t5 (creative)      │
│     ↓ results + refs stored                   │
│  Sequential: t2 → t3 → t4                     │
│     each task receives prior refs as context  │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│  STEP 3 · DEBATE  (high-impact tasks only)    │
│                                               │
│  Round 1:                                     │
│    PROPOSE  Agent submits output + evidence   │
│    CRITIQUE QA + peer agents review           │
│    RESPOND  Agent can revise                  │
│                                               │
│  Aggregate:                                   │
│    score = confidence × reliability_score     │
│    ≥ 0.75  ──► ACCEPT ✓                      │
│    ≥ 0.60  ──► NEXT ROUND (max 3)            │
│    < 0.60  ──► HUMAN REVIEW 🔴               │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│  STEP 4 · ADAPTIVE ANALYSIS                   │
│                                               │
│  Analyze rolling window (last 200 tasks):     │
│    failures > 8 AND avg_confidence < 0.60?    │
│    YES → design new AgentSpec via Claude      │
│         → run sandbox tests                   │
│         → low-impact:   auto-register         │
│         → high-impact:  human_ops_review=true │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│  STEP 5 · DELIVER                             │
│                                               │
│  {                                            │
│    summary,                                   │
│    task_results,       per-agent outputs      │
│    all_refs,           provenance chain       │
│    avg_confidence,                            │
│    requires_human_review: ["t3"],             │
│    assembled_at                               │
│  }                                            │
└───────────────────────────────────────────────┘
```

---

## Debate Engine Protocol

```
PROPOSE PHASE
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   AgentA     │   │   AgentB     │   │   AgentC     │
│ proposal {}  │   │ proposal {}  │   │ proposal {}  │
│ confidence   │   │ confidence   │   │ confidence   │
│    0.82      │   │    0.75      │   │    0.68      │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       └─────────────┬────┘──────────────┘
                     │
                     ▼
CRITIQUE PHASE
┌─────────────────────────────────────────────────┐
│  QAAgent reviews all proposals                  │
│  EngineerAgent critiques architecture choices   │
│  → issues[], suggested_fixes[], confidence      │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
AGGREGATE  (Claude Sonnet as mediator)
┌─────────────────────────────────────────────────┐
│  weighted_score = confidence × reliability      │
│                                                 │
│  score ≥ 0.75  ─────────────────► DONE ✓       │
│  0.60 ≤ score < 0.75 ──► round++ → PROPOSE     │
│  score < 0.60 at max rounds ──────► HUMAN 🔴   │
└─────────────────────────────────────────────────┘
```

---

## Agents

| Agent | Capability | Model | Outputs |
|---|---|---|---|
| **ProductManagerAgent** | `research` `planning` | Claude Opus | PRD, market analysis, competitor matrix, feature backlog |
| **ArchitectAgent** | `architecture` | Claude Opus | ASCII diagram, API contracts, data model, cost estimates |
| **EngineerAgent** | `code` | Claude Opus | Source files, tests, Dockerfile, syntax-validated |
| **QAAgent** | `qa` | Claude Sonnet | Check report with pass/fail/warn per item |
| **CreativeAgent** | `creative` | Claude Sonnet / Gemini | Image prompts, video storyboard, marketing copy |
| **AdaptiveAgentCreator** | `adaptive` | Claude Sonnet | Agent spec, sandbox tests, deployment proposal |

### Message Envelope Schema

Every inter-agent message uses the canonical `Envelope`:

```json
{
  "message_id":       "uuid",
  "trace_id":         "uuid",
  "conversation_id":  "uuid",
  "from_agent":       "orchestrator",
  "to_agent":         "engineer_agent",
  "type":             "task",
  "payload": { "...task-specific content..." },
  "refs": [
    {
      "ref_type":    "vector",
      "ref_id":      "abc123",
      "description": "Research output",
      "source_url":  "https://example.com/report"
    }
  ],
  "meta": {
    "priority":        80,
    "budget_tokens":   4000,
    "requires_debate": true
  }
}
```

---

## Quick Start

### Prerequisites

- Docker Desktop ≥ 4.x
- `ANTHROPIC_API_KEY` (required — powers all agents)
- `DEEPSEEK_API_KEY` and `GEMINI_API_KEY` (optional, Claude used as fallback)

### 1. Clone and Configure

```bash
git clone https://github.com/YOUR_USERNAME/ai-office.git
cd ai-office
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx   # required
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx         # optional
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxx          # optional
```

### 2. Start Everything

```bash
docker compose up
```

Services started:

| Service | URL | Purpose |
|---|---|---|
| **Orchestrator** | `localhost:8000` | FastAPI backend + WebSocket |
| **Dashboard** | `localhost:3000` | Next.js admin UI |
| **API Docs** | `localhost:8000/docs` | Swagger UI |
| **MinIO** | `localhost:9001` | Artifact browser |
| **Jaeger** | `localhost:16686` | Distributed traces |

### 3. Run the Demo

```bash
python scripts/demo.py
```

### 4. Submit via API

```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Research the AI coding assistant market, design a SaaS architecture, and build a sample auth microservice with tests"
  }'
```

---

## Dashboard

The Next.js dashboard gives full real-time visibility:

- **Conversations** — submit requests, watch Task DAG populate, stream live events, view deliverable
- **Agent Registry** — live reliability scores, success rates, latency per agent
- **Adaptive Layer** — review capability gap proposals, approve or reject new agent deployments

---

## API Reference

### Conversations

```
POST   /api/v1/conversations              Submit a new request
GET    /api/v1/conversations              List all
GET    /api/v1/conversations/{id}         Get full state
GET    /api/v1/conversations/{id}/deliverable  Get packaged result
WS     /ws/{id}                           Stream live events
```

### Agents

```
GET    /api/v1/agents                     List with reliability stats
```

### Adaptive Layer

```
GET    /api/v1/adaptive/proposals         List proposals
POST   /api/v1/adaptive/proposals/{id}    Approve or reject
```

**Approve:**
```bash
curl -X POST http://localhost:8000/api/v1/adaptive/proposals/abc-123 \
  -d '{"action": "approve"}'
```

### Stats

```
GET    /api/v1/stats                      System-wide stats
GET    /health                            Health check
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Powers all agents |
| `DEEPSEEK_API_KEY` | — | Research agent (optional) |
| `GEMINI_API_KEY` | — | Creative agent (optional) |
| `CONFIDENCE_THRESHOLD` | `0.75` | Debate accept threshold |
| `ESCALATION_THRESHOLD` | `0.60` | Below this → human review |
| `MAX_DEBATE_ROUNDS` | `3` | Max rounds per debate |
| `TASK_BUDGET_TOKENS` | `4000` | Token budget per task |
| `ADAPTIVE_FAILURE_THRESHOLD` | `8` | Failures before gap proposal |
| `ADAPTIVE_AUTO_REGISTER` | `false` | Auto-register low-impact agents |

---

## Tests

```bash
cd orchestrator

# All tests
pytest tests/ -v

# Specific suites
pytest tests/test_envelope.py   # Message schema
pytest tests/test_debate.py     # Debate engine
pytest tests/test_adaptive.py   # Gap detection
pytest tests/test_api.py        # API endpoints

# With coverage
pytest tests/ --cov=. --cov-report=html
```

**Status: 29/29 passing ✅**

---

## Deployment

### Kubernetes (Production)

```bash
kubectl create namespace ai-office

kubectl create secret generic ai-office-secrets \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=POSTGRES_PASSWORD=changeme \
  -n ai-office

kubectl apply -f infra/k8s/deployment.yaml -n ai-office
```

Includes: 2-replica deployments, HPA (2–10 pods), Ingress with TLS, ConfigMap.

### CI/CD (GitHub Actions)

```
push to main
    ├── test-backend   (pytest with postgres + redis)
    ├── test-frontend  (next build)
    └── docker         (build + push to GHCR)
```

---

## Project Structure

```
ai-office/
├── orchestrator/
│   ├── core/
│   │   ├── envelope.py        Canonical message schema
│   │   ├── planner.py         Task DAG planner
│   │   ├── debate.py          Debate engine
│   │   ├── adaptive.py        Gap detection + agent proposals
│   │   └── orchestrator.py    Central pipeline
│   ├── agents/
│   │   ├── base.py            Abstract base + reliability
│   │   ├── product_manager.py Research + PRD
│   │   ├── architect.py       System design
│   │   ├── engineer.py        Code generation
│   │   ├── qa.py              QA + validation
│   │   └── creative.py        Multimedia + copy
│   ├── adapters/
│   │   └── llm_adapters.py    Claude / DeepSeek / Gemini / OpenAI
│   ├── storage/
│   │   ├── vector_store.py    ChromaDB wrapper
│   │   └── object_store.py    S3/MinIO wrapper
│   ├── tests/                 29 tests
│   ├── main.py                FastAPI app + WebSocket
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── app/               Next.js app router
│       ├── components/        Dashboard components
│       └── lib/api.ts         API client + WebSocket
├── infra/
│   ├── docker/init.sql        PostgreSQL schema
│   └── k8s/deployment.yaml    Kubernetes manifests
├── scripts/
│   ├── setup.sh               One-shot local setup
│   └── demo.py                End-to-end demo
├── .github/workflows/ci.yml   GitHub Actions
├── docker-compose.yml
└── .env.example
```

---

## Roadmap

- [x] Core orchestrator + Task DAG planner
- [x] 5 specialist agents (ProductManager, Architect, Engineer, QA, Creative)
- [x] Debate engine with reliability scoring
- [x] Adaptive agent creator with sandbox testing
- [x] ChromaDB + PostgreSQL + S3/MinIO storage
- [x] Next.js dashboard with real-time WebSocket
- [x] Docker Compose + Kubernetes + GitHub Actions
- [ ] Pinecone / Weaviate production vector DB
- [ ] Full Gemini multimodal pipeline (actual image/video generation)
- [ ] DeepSeek research adapter with live web search
- [ ] Multi-tenant isolation (per-user agent pools)
- [ ] Slack / webhook notifications on completion

---

## License

MIT

---

<div align="center">

Built with Claude, FastAPI, Next.js, ChromaDB, and Docker

</div>
