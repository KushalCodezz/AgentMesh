"""
tests/test_adaptive.py — Tests for the AdaptiveLayer capability gap detection.
"""
import pytest
from unittest.mock import MagicMock, patch
from core.adaptive import AdaptiveLayer, TaskOutcome


def make_layer(**kwargs):
    layer = AdaptiveLayer.__new__(AdaptiveLayer)
    layer.window_size = kwargs.get("window_size", 200)
    layer.failure_threshold = kwargs.get("failure_threshold", 8)
    layer.confidence_threshold = kwargs.get("confidence_threshold", 0.6)
    layer.auto_register = kwargs.get("auto_register", False)
    layer._outcomes = []
    layer._proposals = []
    layer._registered_agents = {}
    return layer


def make_outcome(capability="code", success=False, confidence=0.4, error=None):
    return TaskOutcome(
        task_id="t1",
        capability=capability,
        agent_id="engineer_agent",
        success=success,
        confidence=confidence,
        latency_ms=1200,
        error_signature=error,
    )


class TestAdaptiveLayer:
    def test_record_outcome_appends(self):
        layer = make_layer()
        layer.record_outcome(make_outcome())
        assert len(layer._outcomes) == 1

    def test_window_trims_at_max(self):
        layer = make_layer(window_size=5)
        for _ in range(10):
            layer.record_outcome(make_outcome())
        assert len(layer._outcomes) == 5

    def test_no_gap_below_threshold(self):
        layer = make_layer(failure_threshold=8)
        # Only 3 failures — below threshold
        for _ in range(3):
            layer.record_outcome(make_outcome(success=False, confidence=0.3))
        gaps = layer.analyze_gaps()
        assert gaps == []

    def test_gap_detected_above_threshold(self):
        layer = make_layer(failure_threshold=3)
        for _ in range(5):
            layer.record_outcome(make_outcome(success=False, confidence=0.3, capability="code"))
        gaps = layer.analyze_gaps()
        assert len(gaps) == 1
        assert gaps[0]["capability"] == "code"
        assert gaps[0]["failure_count"] == 5

    def test_no_gap_when_confidence_high(self):
        layer = make_layer(failure_threshold=3, confidence_threshold=0.6)
        # Failures but confidence is above threshold (e.g. intermittent)
        for _ in range(5):
            layer.record_outcome(make_outcome(success=False, confidence=0.8, capability="code"))
        gaps = layer.analyze_gaps()
        # avg_confidence = 0.8 >= 0.6, so no gap
        assert gaps == []

    def test_approve_rejects_unknown_id(self):
        layer = make_layer()
        result = layer.approve_proposal("nonexistent-id")
        assert result is False

    def test_reject_proposal(self):
        layer = make_layer()
        from core.adaptive import AgentProposal
        p = AgentProposal(
            proposal_id="p1",
            spec={"agent_id": "test_agent", "name": "Test", "system_prompt": "..."},
            triggered_by="code",
            failure_count=10,
            avg_confidence=0.4,
        )
        layer._proposals.append(p)
        result = layer.reject_proposal("p1")
        assert result is True
        assert p.status == "rejected"

    def test_get_proposals_returns_list(self):
        layer = make_layer()
        proposals = layer.get_proposals()
        assert isinstance(proposals, list)

    def test_multiple_capabilities_tracked_independently(self):
        layer = make_layer(failure_threshold=3)
        for _ in range(5):
            layer.record_outcome(make_outcome(capability="code", success=False, confidence=0.3))
        for _ in range(2):
            layer.record_outcome(make_outcome(capability="research", success=False, confidence=0.3))

        gaps = layer.analyze_gaps()
        gap_caps = [g["capability"] for g in gaps]
        assert "code" in gap_caps
        assert "research" not in gap_caps  # only 2 failures, below threshold
