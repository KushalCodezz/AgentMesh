-- init.sql — Initial PostgreSQL schema for AI Office
-- Runs automatically on first postgres container start

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Conversations ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id     UUID NOT NULL,
    request      TEXT NOT NULL,
    status       VARCHAR(32) NOT NULL DEFAULT 'pending',
    metadata     JSONB DEFAULT '{}',
    deliverable  JSONB,
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);

-- ── Tasks ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id  UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    trace_id         UUID NOT NULL,
    capability       VARCHAR(32) NOT NULL,
    title            VARCHAR(255) NOT NULL,
    description      TEXT,
    status           VARCHAR(32) NOT NULL DEFAULT 'pending',
    priority         INTEGER NOT NULL DEFAULT 50,
    budget_tokens    INTEGER NOT NULL DEFAULT 4000,
    depends_on       TEXT[] DEFAULT '{}',
    assigned_agents  TEXT[] DEFAULT '{}',
    result           JSONB,
    confidence       FLOAT DEFAULT 0.0,
    error            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_conversation_id ON tasks(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- ── Agent Registry ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agents (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id          VARCHAR(64) UNIQUE NOT NULL,
    name              VARCHAR(128) NOT NULL,
    description       TEXT,
    capabilities      TEXT[] DEFAULT '{}',
    model_preference  VARCHAR(32) DEFAULT 'claude',
    system_prompt     TEXT,
    is_adaptive       BOOLEAN DEFAULT FALSE,
    is_active         BOOLEAN DEFAULT TRUE,
    reliability_score FLOAT DEFAULT 1.0,
    total_tasks       INTEGER DEFAULT 0,
    success_rate      FLOAT DEFAULT 1.0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Adaptive Proposals ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS adaptive_proposals (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposal_id           VARCHAR(64) UNIQUE NOT NULL,
    triggered_by          VARCHAR(32) NOT NULL,
    spec                  JSONB NOT NULL,
    failure_count         INTEGER NOT NULL,
    avg_confidence        FLOAT NOT NULL,
    sandbox_passed        BOOLEAN DEFAULT FALSE,
    status                VARCHAR(32) NOT NULL DEFAULT 'pending',
    requires_human_approval BOOLEAN DEFAULT TRUE,
    approved_by           VARCHAR(128),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Audit Log ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    trace_id        UUID,
    conversation_id UUID,
    task_id         UUID,
    agent_id        VARCHAR(64),
    event_type      VARCHAR(64) NOT NULL,
    payload         JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_trace_id ON audit_log(trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at DESC);

-- ── Task Metrics (for adaptive layer) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS task_metrics (
    id               BIGSERIAL PRIMARY KEY,
    task_id          UUID NOT NULL,
    conversation_id  UUID NOT NULL,
    capability       VARCHAR(32) NOT NULL,
    agent_id         VARCHAR(64) NOT NULL,
    success          BOOLEAN NOT NULL,
    confidence       FLOAT,
    latency_ms       INTEGER,
    tokens_used      INTEGER,
    error_signature  VARCHAR(128),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_capability ON task_metrics(capability);
CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON task_metrics(created_at DESC);
