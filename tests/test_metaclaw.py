import json

import pytest

from metaclaw.capture import classify, record_exchange, record_feedback, wrap_agent
from metaclaw.emit import train_payload
from metaclaw.signals import Signal, SignalStore
from metaclaw.summarize import digest, summarize_session


@pytest.fixture()
def store(tmp_path):
    s = SignalStore(str(tmp_path / "t.db"))
    yield s
    s.close()


def seed_session(store, sid="s1", n_fail=1):
    record_exchange(store, sid, "bot", "do x", "done: x", 0.1)
    if n_fail:
        record_exchange(store, sid, "bot", "do y", None, 0.2, error=RuntimeError("boom"))
    record_feedback(store, sid, "bot", "too verbose", score=-0.8)
    store.add(Signal(kind="emerging_need", session_id=sid, detail="needs PDF export"))
    store.add(Signal(kind="domain_insight", session_id=sid, detail="user prefers tables"))


def test_signal_validation(store):
    with pytest.raises(ValueError):
        store.add(Signal(kind="bogus", session_id="s", detail="d"))
    with pytest.raises(ValueError):
        store.add(Signal(kind="task_success", session_id="", detail="d"))
    with pytest.raises(ValueError):
        store.add(Signal(kind="task_success", session_id="s", detail="d", score=2.0))


def test_classify():
    assert classify("all good")[0] == "task_success"
    assert classify("", None)[0] == "task_failure"
    assert classify("Traceback (most recent call last)")[0] == "task_failure"
    kind, score = classify(None, RuntimeError("x"))
    assert kind == "task_failure" and score == -1.0


def test_wrap_agent_reraises(store):
    def boom(_):
        raise RuntimeError("nope")
    w = wrap_agent(store, "s9", "bot", boom)
    with pytest.raises(RuntimeError):
        w("hi")
    kinds = store.counts_by_kind("s9")
    assert kinds == {"task_failure": 1}


def test_thin_session_rejected(store):
    record_exchange(store, "thin", "bot", "q", "a", 0.1)
    assert summarize_session(store, "thin") is None


def test_summarize_heuristic(store):
    seed_session(store)
    out = summarize_session(store, "s1")
    assert out is not None
    assert "name: session-s1" in out
    assert "RuntimeError: boom" in out
    assert "Never: too verbose" in out
    assert "needs PDF export" in out
    assert "user prefers tables" in out


def test_llm_hook_fallback(store):
    seed_session(store)

    def bad_hook(_):
        raise ConnectionError("down")

    out = summarize_session(store, "s1", llm_hook=bad_hook)
    assert out is not None and "session-s1" in out  # heuristic fallback


def test_llm_hook_used(store):
    seed_session(store)
    out = summarize_session(store, "s1", llm_hook=lambda d: f"# custom {d['n_signals']}")
    assert out == "# custom 5"


def test_emit_payload_validation():
    p = train_payload("bot1", "# skill", [{"input": "q", "expect": "a"}])
    assert p["source"] == "evo-metaclaw" and len(p["eval_cases"]) == 1
    json.dumps(p)  # must be serializable
    with pytest.raises(ValueError):
        train_payload("", "x")
    with pytest.raises(ValueError):
        train_payload("b", "   ")


def test_digest_shape(store):
    seed_session(store)
    d = digest(store.for_session("s1"))
    assert d["n_signals"] == 5
    assert d["kinds"]["task_success"] == 1
    assert d["failure_rate"] == 0.2
