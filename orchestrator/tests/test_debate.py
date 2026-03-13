"""
tests/test_debate.py — Tests for the DebateEngine (mock LLM calls).
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from core.debate import DebateEngine, DebatePhase, DebateState


def make_engine(confidence_threshold=0.75, max_rounds=3):
    engine = DebateEngine.__new__(DebateEngine)
    engine.confidence_threshold = confidence_threshold
    engine.escalation_threshold = 0.60
    engine.max_rounds = max_rounds
    return engine


def make_aggregate_response(confidence: float, requires_human: bool = False):
    """Build a mock Claude response for the aggregator."""
    payload = json.dumps({
        "final_output": {"answer": "synthesized output"},
        "confidence": confidence,
        "reasoning": "best synthesis",
        "requires_human_review": requires_human,
        "unresolved_issues": [],
    })
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=payload)]
    return mock_msg


class TestDebateEngine:
    def test_init_debate_creates_state(self):
        engine = make_engine()
        state = engine.init_debate("task-001")
        assert state.task_id == "task-001"
        assert state.phase == DebatePhase.PROPOSE
        assert state.round == 1

    def test_add_proposal(self):
        engine = make_engine()
        state = engine.init_debate("task-001")
        engine.add_proposal(state, "agent_a", {"answer": "A"}, [], 0.8, 1.0)
        assert len(state.proposals) == 1
        assert state.proposals[0].agent_id == "agent_a"

    def test_add_critique(self):
        engine = make_engine()
        state = engine.init_debate("task-001")
        engine.add_critique(state, "qa_agent", "agent_a", ["Issue 1"], ["Fix 1"], 0.7)
        assert len(state.critiques) == 1
        assert state.critiques[0].critic_agent_id == "qa_agent"

    @patch("core.debate.anthropic.Anthropic")
    def test_aggregate_accepts_high_confidence(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = make_aggregate_response(0.85)
        mock_anthropic_cls.return_value = mock_client

        engine = DebateEngine("fake-key", confidence_threshold=0.75, max_rounds=3)
        state = engine.init_debate("task-001")
        engine.add_proposal(state, "agent_a", {"answer": "A"}, [], 0.85, 1.0)
        state = engine.aggregate(state)

        assert state.phase == DebatePhase.DONE
        assert state.final_result is not None
        assert state.requires_human_review is False

    @patch("core.debate.anthropic.Anthropic")
    def test_aggregate_continues_rounds_on_low_confidence(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = make_aggregate_response(0.62)
        mock_anthropic_cls.return_value = mock_client

        engine = DebateEngine("fake-key", confidence_threshold=0.75, max_rounds=3)
        state = engine.init_debate("task-001")
        engine.add_proposal(state, "agent_a", {"answer": "A"}, [], 0.62, 1.0)
        state = engine.aggregate(state)

        # Should continue — not done yet, round incremented
        assert state.phase == DebatePhase.PROPOSE
        assert state.round == 2

    @patch("core.debate.anthropic.Anthropic")
    def test_escalates_after_max_rounds(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = make_aggregate_response(0.45)
        mock_anthropic_cls.return_value = mock_client

        engine = DebateEngine("fake-key", confidence_threshold=0.75, max_rounds=1)
        state = engine.init_debate("task-001")
        engine.add_proposal(state, "agent_a", {"answer": "A"}, [], 0.45, 1.0)
        state = engine.aggregate(state)

        assert state.phase == DebatePhase.DONE
        assert state.requires_human_review is True

    @patch("core.debate.anthropic.Anthropic")
    def test_no_proposals_requires_human_review(self, mock_anthropic_cls):
        engine = DebateEngine("fake-key")
        state = engine.init_debate("task-001")
        state = engine.aggregate(state)

        assert state.requires_human_review is True
        assert state.phase == DebatePhase.DONE

    def test_get_summary(self):
        engine = make_engine()
        state = engine.init_debate("task-001")
        engine.add_proposal(state, "agent_a", {}, [], 0.8, 1.0)
        engine.add_critique(state, "qa_agent", "agent_a", ["iss"], [], 0.7)
        summary = engine.get_summary(state)
        assert summary["task_id"] == "task-001"
        assert summary["proposals_count"] == 1
        assert summary["critiques_count"] == 1
