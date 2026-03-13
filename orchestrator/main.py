"""
main.py — FastAPI application entry point.
Exposes REST API + WebSocket for real-time event streaming.
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.orchestrator import Orchestrator

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = structlog.get_logger()

# ─── App lifecycle ─────────────────────────────────────────────────────────────

orchestrator: Optional[Orchestrator] = None
ws_connections: Dict[str, List[WebSocket]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    logger.info("Starting AI Office Orchestrator...")
    orchestrator = Orchestrator()
    logger.info("Orchestrator ready.")
    yield
    logger.info("Shutting down AI Office Orchestrator...")


app = FastAPI(
    title="AI Office Orchestrator",
    description="Multi-agent orchestration platform — research, architecture, code, creative, QA",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request/Response models ───────────────────────────────────────────────────

class StartConversationRequest(BaseModel):
    request: str
    metadata: Optional[Dict[str, Any]] = None


class StartConversationResponse(BaseModel):
    conversation_id: str
    trace_id: str
    status: str


class ApproveProposalRequest(BaseModel):
    action: str  # "approve" | "reject"


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Conversations ──────────────────────────────────────────────────────────────

@app.post("/api/v1/conversations", response_model=StartConversationResponse)
async def start_conversation(body: StartConversationRequest):
    """Submit a user request. Returns immediately; execution runs async."""
    if not body.request.strip():
        raise HTTPException(400, "Request cannot be empty")

    result = await orchestrator.start_conversation(body.request, body.metadata)
    return result


@app.get("/api/v1/conversations")
async def list_conversations():
    """List all conversations with status summary."""
    return await orchestrator.list_conversations()


@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation state including tasks and results."""
    conv = await orchestrator.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, f"Conversation {conversation_id} not found")
    return conv


@app.get("/api/v1/conversations/{conversation_id}/deliverable")
async def get_deliverable(conversation_id: str):
    """Get the packaged deliverable for a completed conversation."""
    conv = await orchestrator.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Not found")
    if conv.get("status") != "completed":
        raise HTTPException(202, "Conversation not yet complete")
    return conv.get("deliverable", {})


# ── Agents ─────────────────────────────────────────────────────────────────────

@app.get("/api/v1/agents")
async def list_agents():
    """List all registered agents with reliability stats."""
    return orchestrator.get_agent_stats()


# ── Adaptive Layer ─────────────────────────────────────────────────────────────

@app.get("/api/v1/adaptive/proposals")
async def list_proposals():
    """List all agent proposals from the adaptive layer."""
    return orchestrator.get_adaptive_proposals()


@app.post("/api/v1/adaptive/proposals/{proposal_id}")
async def action_proposal(proposal_id: str, body: ApproveProposalRequest):
    """Approve or reject an agent proposal (human ops)."""
    if body.action == "approve":
        success = await orchestrator.approve_agent_proposal(proposal_id)
    elif body.action == "reject":
        success = await orchestrator.reject_agent_proposal(proposal_id)
    else:
        raise HTTPException(400, "action must be 'approve' or 'reject'")

    if not success:
        raise HTTPException(404, f"Proposal {proposal_id} not found or action failed")
    return {"status": "ok", "proposal_id": proposal_id, "action": body.action}


# ── WebSocket — real-time event stream ─────────────────────────────────────────

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """
    Stream real-time events for a conversation.
    Polls the conversation's event list and pushes new events as they arrive.
    """
    await websocket.accept()
    ws_connections.setdefault(conversation_id, []).append(websocket)

    last_event_index = 0
    try:
        while True:
            conv = await orchestrator.get_conversation(conversation_id)
            if conv:
                events = conv.get("events", [])
                if len(events) > last_event_index:
                    new_events = events[last_event_index:]
                    for event in new_events:
                        await websocket.send_json(event)
                    last_event_index = len(events)

                if conv.get("status") in ("completed", "failed"):
                    await websocket.send_json({"type": "stream_end", "status": conv["status"]})
                    break

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    finally:
        ws_connections.get(conversation_id, []).remove(websocket)


# ── System stats ───────────────────────────────────────────────────────────────

@app.get("/api/v1/stats")
async def system_stats():
    """System-wide stats for the admin dashboard."""
    conversations = await orchestrator.list_conversations()
    agents = orchestrator.get_agent_stats()
    proposals = orchestrator.get_adaptive_proposals()

    status_counts: Dict[str, int] = {}
    for c in conversations:
        status_counts[c["status"]] = status_counts.get(c["status"], 0) + 1

    return {
        "conversations": {
            "total": len(conversations),
            "by_status": status_counts,
        },
        "agents": {
            "total": len(agents),
            "avg_reliability": (
                sum(a["reliability_score"] for a in agents) / len(agents) if agents else 0
            ),
        },
        "adaptive": {
            "proposals_total": len(proposals),
            "proposals_pending": sum(1 for p in proposals if p["status"] == "pending"),
        },
    }
