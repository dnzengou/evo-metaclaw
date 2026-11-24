# evo-metaclaw architecture

## Position in the triad

```
┌──────────────────┐   signals    ┌──────────────────┐  gated skills ┌──────────────────┐
│  agent runtime   │─────────────►│  evo-metaclaw    │──────────────►│  evo-skillopt    │
│  (any framework) │  wrap_agent  │  capture · store │  /train POST  │  rollout·reflect │
└──────────────────┘              │  summarize       │               │  gate·rollback   │
                                  └──────────────────┘               └────────┬─────────┘
                                        ▲  emerging_need                      │ promoted
                                        │  signals feed                       ▼
                                  ┌─────┴──────────────────────────────────────────────┐
                                  │  EvoForge — champion install, genome packs,        │
                                  │  idle-window deep mutation, lineage viewer         │
                                  └────────────────────────────────────────────────────┘
```

Design lineage: MetaClaw (live conversation-driven meta-learning) ×
EvoSkillOpt (GRPO, Q-gate, circuit breaker) — see EvoForge
`docs/metalearning_layer.md`, which this repo operationalizes as the
missing signal-capture middle layer.

## Components

| module | job | refuses to |
|--------|-----|-----------|
| `signals.py` | schema + append-only SQLite WAL store | update/delete rows |
| `capture.py` | record exchanges, classify error/empty, wrap callables | judge quality heuristically |
| `summarize.py` | distill session → candidate SKILL.md | gate, version, promote |
| `emit.py` | build + POST evo-skillopt `/train` payloads | retry silently, drop on failure |

## Data rules

1. Signals are facts; summaries are hypotheses; gates are downstream.
2. Every draft is marked "must pass held-out gate before use".
3. Sessions under 3 signals are rejected (circuit breaker vs. noise).
4. User feedback is the only quality signal; everything else is mechanics.

## Store

Single SQLite file, WAL mode, one mutex-guarded connection — same
stdlib pattern as evo-skillopt's job queue. Two indexes
(session_id, ts). No server, no daemon, no dependencies.

## Roadmap

- [ ] Reverse-proxy capture mode (httpx) for runtimes that can't wrap callables
- [ ] Cross-session clustering: same failure in N sessions → stronger candidate
- [ ] Scheduler hooks (sleep/idle/calendar) per metalearning_layer.md §5
- [ ] EvoForge genome-pack export (skill → pack format adapter)
- [ ] Memory-layer signals (episodic/semantic/preference split)
