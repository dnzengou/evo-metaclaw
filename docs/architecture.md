# evo-metaclaw architecture

## Position in the triad

```
┌──────────────────┐   signals    ┌──────────────────┐  gated skills ┌──────────────────┐
│  agent runtime   │─────────────►│  evo-metaclaw    │──────────────►│  evo-skillopt    │
│  (any framework) │  wrap_agent  │  claw · capture  │  /train POST  │  rollout·reflect │
└──────────────────┘              │  summarize       │               │  gate·rollback   │
        │                         └────────┬─────────┘               └────────┬─────────┘
        │  proposed child skill            │ reject + axes                    │ promoted
        └─────────────────────────────────►│ (claw: may it exist?)            ▼
                                  ┌────────┴───────────────────────────────────────────┐
                                  │  EvoForge — champion install, genome packs,        │
                                  │  idle-window deep mutation, lineage viewer         │
                                  └────────────────────────────────────────────────────┘
```

Two gates, two questions. The claw (here): *is the child allowed to
exist?* — constitutional, runs before training. The evo-skillopt
Q-gate: *is the child better?* — empirical, runs on held-out cases. A
mutation must pass claw first, then Q-gate.

Design lineage: EvoMetaClaw (four-axis governance spec) × MetaClaw
(live conversation-driven meta-learning) × EvolvedSkillOpt (GRPO,
Q-gate, circuit breaker) — see EvoForge `docs/metalearning_layer.md`.

## Components

| module | job | refuses to |
|--------|-----|-----------|
| `claw.py` | four-axis gate (B/Ci/E/Bl) on proposed mutations | train, version, promote skills |
| `signals.py` | schema + append-only SQLite WAL store | update/delete rows |
| `capture.py` | record exchanges, classify error/empty, wrap callables | judge quality heuristically |
| `summarize.py` | distill session → candidate SKILL.md | gate, version, promote |
| `emit.py` | build + POST evo-skillopt `/train` payloads | retry silently, drop on failure |

## Claw semantics

- **B (Budget)**: `cost_delta` and `hours_delta` must not exceed
  tolerance (default 0 — no jump at all).
- **Ci (Circuit)**: `depth ≤ max_depth` (default 2, matching EvoForge's
  platform-mode bound).
- **E (Evolution)**: `child_fitness ≥ 0.8 × parent_fitness`.
- **Bl (Blacklist)**: every clause pattern present in the parent must
  still match in the child. Default patterns: airgap, kill-switch,
  budget cap, ownership, human oversight, rate limit, max_depth,
  approval gate. Clauses only bind when present in the parent — a
  minimal parent constrains nothing; adding constraints is always legal.
- Bl is **textual**: a clause reworded away semantically but preserved
  in spirit is a known limit (see README "Honest limits").

## Data rules

1. Signals are facts; summaries are hypotheses; gates are downstream.
2. Every draft is marked "must pass held-out gate before use".
3. Sessions under 3 signals are rejected (circuit breaker vs. noise).
4. User feedback is the only quality signal; everything else is mechanics.
5. Rejections are data: failing axes are logged, never silently dropped.

## Store

Single SQLite file, WAL mode, one mutex-guarded connection — same
stdlib pattern as evo-skillopt's job queue. No server, no daemon, no
dependencies.

## Roadmap

- [x] Four-axis claw gate (v0.2.0 — merged from the EvoMetaClaw spec)
- [ ] Rejection ledger: log claw verdicts to SignalStore for audit queries
- [ ] Reverse-proxy capture mode (httpx) for runtimes that can't wrap callables
- [ ] Cross-session clustering: same failure in N sessions → stronger candidate
- [ ] Scheduler hooks (sleep/idle/calendar) per metalearning_layer.md §5
- [ ] EvoForge genome-pack export (skill → pack format adapter)
- [ ] Semantic Bl axis (embedding-based clause equivalence vs. regex)
