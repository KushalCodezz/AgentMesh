#!/usr/bin/env bash
# scripts/setup.sh — One-shot local dev setup for AI Office
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${CYAN}[setup]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
fail() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

echo ""
echo "  🏢  AI Office — Local Dev Setup"
echo "  ──────────────────────────────────────"
echo ""

# ── Check prerequisites ────────────────────────────────────────────────────

log "Checking prerequisites..."
command -v docker   >/dev/null 2>&1 || fail "Docker not found. Install Docker Desktop first."
command -v docker compose version >/dev/null 2>&1 || fail "docker compose not found. Update Docker."
ok "Docker: $(docker --version | head -1)"

# ── Copy env ───────────────────────────────────────────────────────────────

if [ ! -f ".env" ]; then
    log "Creating .env from .env.example..."
    cp .env.example .env
    warn "Edit .env and add your API keys before starting!"
else
    ok ".env already exists — skipping"
fi

# ── Pull images ────────────────────────────────────────────────────────────

log "Pulling base Docker images..."
docker compose pull postgres redis chromadb minio jaeger 2>/dev/null || warn "Some images may need pulling on first start"

# ── Start infra only ───────────────────────────────────────────────────────

log "Starting infrastructure services..."
docker compose up -d postgres redis chromadb minio

log "Waiting for PostgreSQL to be healthy..."
for i in {1..30}; do
    docker compose exec -T postgres pg_isready -U ai_office >/dev/null 2>&1 && break
    echo -n "." && sleep 2
done
echo ""
ok "PostgreSQL ready"

log "Waiting for Redis..."
for i in {1..15}; do
    docker compose exec -T redis redis-cli ping >/dev/null 2>&1 && break
    echo -n "." && sleep 1
done
echo ""
ok "Redis ready"

# ── Create MinIO bucket ────────────────────────────────────────────────────

log "Creating MinIO bucket..."
sleep 3  # Wait for MinIO to finish starting
docker compose exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null || true
docker compose exec -T minio mc mb local/ai-office-artifacts 2>/dev/null || warn "Bucket may already exist"
ok "MinIO bucket ready"

# ── Summary ────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo ""
echo "  Services running:"
echo "    PostgreSQL  → localhost:5432"
echo "    Redis       → localhost:6379"
echo "    ChromaDB    → localhost:8001"
echo "    MinIO       → localhost:9000  (console: 9001)"
echo ""
echo "  Next steps:"
echo "    1. Edit .env — add ANTHROPIC_API_KEY and other keys"
echo "    2. Run: docker compose up"
echo "    3. API:       http://localhost:8000/docs"
echo "    4. Dashboard: http://localhost:3000"
echo "    5. Jaeger:    http://localhost:16686"
echo "    6. MinIO:     http://localhost:9001"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
