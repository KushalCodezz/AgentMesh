"""
tests/test_envelope.py — Tests for the core message envelope schema.
"""
import pytest
from datetime import datetime, timezone
from core.envelope import (
    Envelope, MessageType, TaskSpec, TaskStatus,
    CapabilityTag, Priority, AgentResult, ProvenanceRef, Evidence
)


class TestEnvelope:
    def test_default_ids_are_unique(self):
        e1 = Envelope()
        e2 = Envelope()
        assert e1.message_id != e2.message_id
        assert e1.trace_id != e2.trace_id

    def test_reply_inherits_trace_and_conversation(self):
        parent = Envelope(
            from_agent="orchestrator",
            to_agent="agent_a",
            type=MessageType.TASK,
            payload={"task": "do something"},
        )
        reply = parent.reply("agent_a", {"result": "done"})
        assert reply.trace_id == parent.trace_id
        assert reply.conversation_id == parent.conversation_id
        assert reply.from_agent == "agent_a"
        assert reply.to_agent == "orchestrator"
        assert reply.type == MessageType.REPLY

    def test_reply_creates_new_message_id(self):
        parent = Envelope()
        reply = parent.reply("agent_x", {})
        assert reply.message_id != parent.message_id

    def test_payload_is_arbitrary_dict(self):
        e = Envelope(payload={"key": "value", "nested": {"a": 1}})
        assert e.payload["key"] == "value"
        assert e.payload["nested"]["a"] == 1

    def test_refs_default_empty(self):
        e = Envelope()
        assert e.refs == []

    def test_meta_defaults(self):
        e = Envelope()
        assert e.meta.priority == Priority.NORMAL
        assert e.meta.budget_tokens == 4000
        assert e.meta.requires_debate is False


class TestTaskSpec:
    def test_task_defaults(self):
        t = TaskSpec(
            conversation_id="conv-1",
            trace_id="trace-1",
            capability=CapabilityTag.RESEARCH,
            title="Research task",
            description="Do research",
        )
        assert t.status == TaskStatus.PENDING
        assert t.confidence == 0.0
        assert t.depends_on == []

    def test_task_id_auto_generated(self):
        t1 = TaskSpec(conversation_id="c", trace_id="t", capability=CapabilityTag.CODE, title="T", description="D")
        t2 = TaskSpec(conversation_id="c", trace_id="t", capability=CapabilityTag.CODE, title="T", description="D")
        assert t1.task_id != t2.task_id

    def test_capability_tags(self):
        caps = [CapabilityTag.RESEARCH, CapabilityTag.CODE, CapabilityTag.QA,
                CapabilityTag.CREATIVE, CapabilityTag.ARCHITECTURE, CapabilityTag.PLANNING]
        for cap in caps:
            t = TaskSpec(conversation_id="c", trace_id="t", capability=cap, title="T", description="D")
            assert t.capability == cap


class TestAgentResult:
    def test_successful_result(self):
        r = AgentResult(
            task_id="t1",
            agent_id="engineer_agent",
            success=True,
            output={"files": []},
            confidence=0.92,
            tokens_used=1500,
            latency_ms=2300,
        )
        assert r.success is True
        assert r.confidence == 0.92
        assert r.requires_human_review is False

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            AgentResult(task_id="t", agent_id="a", success=True, output={}, confidence=1.5)
        with pytest.raises(Exception):
            AgentResult(task_id="t", agent_id="a", success=True, output={}, confidence=-0.1)

    def test_provenance_refs(self):
        ref = ProvenanceRef(
            ref_type="url",
            ref_id="ref-001",
            description="Market research source",
            source_url="https://example.com/research",
        )
        r = AgentResult(
            task_id="t1",
            agent_id="product_manager_agent",
            success=True,
            output={},
            confidence=0.85,
            refs=[ref],
        )
        assert len(r.refs) == 1
        assert r.refs[0].ref_type == "url"
        assert r.refs[0].source_url == "https://example.com/research"
