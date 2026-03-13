#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  AgentMesh — Quick Start Script
#  Run this once on your machine: bash start.sh
# ═══════════════════════════════════════════════════════════

set -e

BOLD="\033[1m"
GREEN="\033[32m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}${CYAN}🏢  AgentMesh — Starting up...${RESET}"
echo ""

# ── 1. Check Docker ──────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo -e "${RED}✗ Docker not found.${RESET}"
  echo "  Install from: https://docs.docker.com/get-docker/"
  exit 1
fi

if ! docker info &>/dev/null; then
  echo -e "${RED}✗ Docker daemon not running. Please start Docker Desktop.${RESET}"
  exit 1
fi

echo -e "${GREEN}✓ Docker is running${RESET}"

# ── 2. Create .env if missing ────────────────────────────────
if [ ! -f .env ]; then
  cp .env.example .env
  echo -e "${YELLOW}⚠  Created .env from .env.example${RESET}"
fi

# ── 3. Check for ANTHROPIC_API_KEY ──────────────────────────
if grep -q "sk-ant-\.\.\." .env || ! grep -q "ANTHROPIC_API_KEY=sk-ant" .env; then
  echo ""
  echo -e "${YELLOW}  ┌──────────────────────────────────────────────────────┐${RESET}"
  echo -e "${YELLOW}  │  ANTHROPIC_API_KEY not set in .env                   │${RESET}"
  echo -e "${YELLOW}  │  Get yours at: https://console.anthropic.com/keys     │${RESET}"
  echo -e "${YELLOW}  └──────────────────────────────────────────────────────┘${RESET}"
  echo ""
  read -rp "  Paste your Anthropic API key (sk-ant-...): " KEY
  if [[ "$KEY" == sk-ant-* ]]; then
    # Replace the placeholder line
    sed -i.bak "s|ANTHROPIC_API_KEY=sk-ant-\.\.\.|ANTHROPIC_API_KEY=$KEY|g" .env
    sed -i.bak "s|ANTHROPIC_API_KEY=sk-ant-...|ANTHROPIC_API_KEY=$KEY|g" .env
    rm -f .env.bak
    echo -e "${GREEN}  ✓ API key saved to .env${RESET}"
  else
    echo -e "${RED}  ✗ Invalid key format — agents will use mock mode${RESET}"
  fi
fi

# ── 4. Pull images & build ───────────────────────────────────
echo ""
echo -e "${BOLD}  Pulling Docker images...${RESET}"
docker compose pull --quiet postgres redis chromadb minio jaeger 2>/dev/null || true

echo -e "${BOLD}  Building orchestrator + frontend...${RESET}"
docker compose build --quiet

# ── 5. Start services ───────────────────────────────────────
echo ""
echo -e "${BOLD}  Starting all services...${RESET}"
docker compose up -d

# ── 6. Wait for health ──────────────────────────────────────
echo ""
echo -e "  Waiting for services to be healthy..."
sleep 4

MAX=30; COUNT=0
until curl -sf http://localhost:8000/health >/dev/null 2>&1 || [ $COUNT -ge $MAX ]; do
  sleep 2; COUNT=$((COUNT+1))
  echo -n "."
done
echo ""

if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
  echo -e "${GREEN}  ✓ Orchestrator is up${RESET}"
else
  echo -e "${YELLOW}  ⚠  Orchestrator still starting — check: docker compose logs orchestrator${RESET}"
fi

# ── 7. Create MinIO bucket ──────────────────────────────────
sleep 2
docker compose exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null || true
docker compose exec -T minio mc mb local/ai-office-artifacts 2>/dev/null || true

# ── 8. Done ─────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}  ✅  AgentMesh is running!${RESET}"
echo ""
echo -e "  ${BOLD}Dashboard${RESET}    →  ${CYAN}http://localhost:3000${RESET}"
echo -e "  ${BOLD}API Docs${RESET}     →  ${CYAN}http://localhost:8000/docs${RESET}"
echo -e "  ${BOLD}MinIO${RESET}        →  ${CYAN}http://localhost:9001${RESET}  (minioadmin / minioadmin)"
echo -e "  ${BOLD}Jaeger${RESET}       →  ${CYAN}http://localhost:16686${RESET}"
echo ""
echo -e "  ${BOLD}Quick test:${RESET}"
echo -e "  ${CYAN}curl -X POST http://localhost:8000/api/v1/conversations \\${RESET}"
echo -e "  ${CYAN}  -H 'Content-Type: application/json' \\${RESET}"
echo -e "  ${CYAN}  -d '{\"request\": \"Research the AI coding assistant market\"}'${RESET}"
echo ""
echo -e "  ${BOLD}Stop:${RESET}  docker compose down"
echo -e "  ${BOLD}Logs:${RESET}  docker compose logs -f orchestrator"
echo ""
