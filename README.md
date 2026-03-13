# 🏢 AI Office — Multi-Agent Orchestration Platform

A collaborative AI Office where specialist agents (research, engineering, creative, QA) work together, debate, cross-validate, and self-improve by spawning new agents when capability gaps are detected.

## Architecture

```
USER/UI → API Gateway → Orchestrator (Task Planner + Debate Engine + Adaptive Layer)
                              ↓
         ┌────────────────────┼───────────────────┐
    Message Queue        Shared Memory        Object Store
    (Redis)             (ChromaDB + PG)         (S3)
         └────────────────────┼───────────────────┘
                              ↓
    ┌──────────────────────────────────────────────────┐
    │  Agents                                          │
    │  ProductManagerAgent  ArchitectAgent             │
    │  EngineerAgent        QAAgent                   │
    │  CreativeAgent        AdaptiveAgentCreator       │
    └──────────────────────────────────────────────────┘
```

## Features

- **Task DAG Planner** — Decompose user intent into assignable subtasks
- **Multi-Agent Adapters** — Claude (code), DeepSeek (research), Gemini (creative)
- **Debate Engine** — PROPOSE → CRITIQUE → RESPOND loop with reliability scoring
- **Shared Memory** — ChromaDB vector store + PostgreSQL metadata + S3 object store
- **Adaptive Layer** — Auto-detect capability gaps, spawn new specialized agents
- **Cross-Validation** — Every output verified by at least one other agent
- **Full Audit Trail** — OpenTelemetry tracing, provenance on every artifact
- **Admin Dashboard** — Real-time trace viewer, agent registry, human-ops approval

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/YOUR_ORG/ai-office.git
cd ai-office
cp .env.example .env
# Edit .env with your API keys

# 2. Start local stack
docker-compose up -d

# 3. Open dashboard
open http://localhost:3000

# 4. API docs
open http://localhost:8000/docs
```

## Project Structure

```
ai-office/
├── orchestrator/          # FastAPI backend + all agent logic
│   ├── core/              # Planner, debate engine, adaptive layer
│   ├── agents/            # All specialist agent implementations
│   ├── adapters/          # LLM provider wrappers (Claude/DeepSeek/Gemini)
│   ├── storage/           # Vector DB, object store, metadata DB
│   └── api/               # REST + WebSocket endpoints
├── frontend/              # Next.js admin dashboard
├── infra/                 # Docker + Kubernetes configs
└── scripts/               # Setup & utility scripts
```

## Environment Variables

See `.env.example` for all required configuration.

## Roadmap

- [x] Core orchestrator + message envelope
- [x] All 6 specialist agents
- [x] Debate engine with reliability scoring
- [x] Adaptive agent creator
- [x] ChromaDB + PostgreSQL + Redis storage
- [x] Admin dashboard with real-time updates
- [ ] Production Kubernetes deployment
- [ ] Pinecone/Weaviate production vector DB
- [ ] Full multi-modal (audio/video) pipeline

## License

MIT
