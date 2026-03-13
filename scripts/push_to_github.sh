#!/usr/bin/env bash
# scripts/push_to_github.sh
# Usage: ./scripts/push_to_github.sh <github-username> <repo-name>
set -euo pipefail

GITHUB_USER="${1:-YOUR_USERNAME}"
REPO_NAME="${2:-ai-office}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"  # set via env or gh auth

echo "🏢 Pushing AI Office to GitHub..."
echo "   Repo: https://github.com/$GITHUB_USER/$REPO_NAME"

# Check gh CLI
if command -v gh &>/dev/null; then
    echo "Using GitHub CLI..."
    gh repo create "$REPO_NAME" --public --description "Collaborative AI Office: Multi-agent orchestration platform" || true
    git remote set-url origin "https://github.com/$GITHUB_USER/$REPO_NAME.git" 2>/dev/null || \
    git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
elif [ -n "$GITHUB_TOKEN" ]; then
    echo "Using GITHUB_TOKEN..."
    curl -s -X POST \
      -H "Authorization: token $GITHUB_TOKEN" \
      -H "Content-Type: application/json" \
      https://api.github.com/user/repos \
      -d "{\"name\":\"$REPO_NAME\",\"description\":\"Collaborative AI Office: Multi-agent orchestration platform\",\"private\":false}" \
      | grep -q '"full_name"' && echo "Repo created" || echo "Repo may already exist"
    git remote set-url origin "https://$GITHUB_TOKEN@github.com/$GITHUB_USER/$REPO_NAME.git" 2>/dev/null || \
    git remote add origin "https://$GITHUB_TOKEN@github.com/$GITHUB_USER/$REPO_NAME.git"
else
    echo "❌ Neither 'gh' CLI nor GITHUB_TOKEN found."
    echo "   Install GitHub CLI: https://cli.github.com/"
    echo "   Or: export GITHUB_TOKEN=your_token"
    exit 1
fi

git add -A
git commit -m "feat: initial AI Office platform — full multi-agent orchestration

- Core orchestrator with Task DAG planner (Claude-powered)
- Debate engine: PROPOSE → CRITIQUE → RESPOND → AGGREGATE
- Adaptive layer: auto-detects gaps, proposes new agents
- 5 specialist agents: ProductManager, Architect, Engineer, QA, Creative
- LLM adapters: Claude, DeepSeek, Gemini (normalized interface)
- Storage: ChromaDB vector store + S3 object store + PostgreSQL
- FastAPI backend with REST + WebSocket real-time events
- Next.js admin dashboard with live event streaming
- Full test suite: 29 tests (envelope, debate, adaptive, API)
- Docker Compose (local) + Kubernetes manifests (production)
- GitHub Actions CI/CD pipeline
" 2>/dev/null || git commit --allow-empty -m "chore: sync"

git push -u origin main --force

echo ""
echo "✅ Pushed to: https://github.com/$GITHUB_USER/$REPO_NAME"
echo "   → API docs:   https://github.com/$GITHUB_USER/$REPO_NAME#quick-start"
