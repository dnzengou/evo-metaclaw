# evo-metaclaw

**Live conversation-driven meta-learning.** Capture signals from agent
conversations, distill session-end skill candidates, emit them to
[evo-skillopt](https://github.com/dnzengou/evo-skillopt) for gated training.

One organ of the triad:

```
conversations ──► evo-metaclaw   (capture + summarize)   ← you are here
                ──► evo-skillopt (train + held-out gate + rollback)
                ──► EvoForge     (install as genome pack, idle-window mutation)
```

## Boundary discipline

evo-metaclaw does **one thing**: turn conversations into clean training
signal. It has no gates, no versioning, no promotion logic — those live
in evo-skillopt. It deploys nothing — that lives in EvoForge. If a
feature idea needs a gate, it belongs downstream, not here.

## Install + 60-second demo

```bash
git clone https://github.com/dnzengou/evo-metaclaw.git
cd evo-metaclaw
pip install -e ".[dev]"
python -m pytest                    # 9 tests, stdlib-only core

# capture a session
evo-metaclaw capture demo1 task_success "answered pricing question" --agent sales-bot
evo-metaclaw capture demo1 task_failure "RuntimeError: timeout on PDF tool" --agent sales-bot
evo-metaclaw capture demo1 user_feedback "too verbose" --score -0.8 --agent sales-bot
evo-metaclaw capture demo1 emerging_need "needs PDF export"

# distill → candidate SKILL.md
evo-metaclaw summarize demo1

# emit → evo-skillopt worker (train + gate happen there)
evo-metaclaw emit demo1 sales-bot --worker http://localhost:9000 --token $WORKER_TOKEN
```

## Signal schema

| kind | meaning |
|------|---------|
| `task_success` | agent completed what the user asked |
| `task_failure` | error, empty reply, or rejected output |
| `user_feedback` | explicit thumbs/correction — highest value |
| `coordination` | multi-agent handoff observation |
| `domain_insight` | reusable fact surfaced mid-session |
| `emerging_need` | need no current agent/skill covers |

Score: `-1.0..1.0`. Append-only SQLite (WAL) — downstream reads, never mutates.

## Library use

```python
from metaclaw import SignalStore
from metaclaw.capture import wrap_agent, record_feedback
from metaclaw.summarize import summarize_session

store = SignalStore("metaclaw.db")
safe_agent = wrap_agent(store, session_id, "my-bot", my_agent_fn)  # auto-capture, errors re-raised
record_feedback(store, session_id, "my-bot", "nailed the format", score=1.0)

skill_draft = summarize_session(store, session_id)  # None if session too thin (<3 signals)
```

`llm_hook=` on `summarize_session` swaps the heuristic drafter for an
LLM; hook failure falls back to heuristic — summarization never crashes
a session end.

## Failure-mode guards

- **Thin-session circuit breaker**: < 3 signals → no draft. Anecdote ≠ pattern.
- **Heuristic fallback**: LLM summarizer down → heuristic draft, session not lost.
- **Fail-loud emit**: unreachable worker raises; skills are never silently dropped.
- **No quality guessing**: capture classifies only errors/empties. Quality
  judgment comes from explicit user feedback, not regex astrology.

## Docs

- [docs/architecture.md](docs/architecture.md) — triad data flow, schema, design rules

## License

MIT
