# evo-metaclaw

**The lock on self-evolving AI agents.**
Evolution proposes. The claw decides what is allowed to stay.

Governance + learning in one layer of the EvoForge triad:

- **The claw (governance)** — every proposed child skill is scored on
  four axes and stamped or rejected *before it ever runs*. Code, not
  prose: `metaclaw.gate()`.
- **Live meta-learning (signal organ)** — conversation capture turns
  production interactions into skill candidates, distilled at session
  end and emitted to evo-skillopt for gated training.

```
parent ──mutate──▶ child ──▶ ┌─ claw gate ────────┐
                             │  B  budget ok?     │
                             │  Ci depth ≤ 2?     │
                             │  E  fitness ≥ .8×? │
                             │  Bl clauses intact?│
                             └───────┬───────────┘
                       pass ◀────────┴────────▶ reject + logged axes
```

## The four axes

| Axis | Name | Rule | Why |
|---|---|---|---|
| **B** | Budget | Cost and hours must not jump | Prevents "improvement" that is secretly a resource grab |
| **Ci** | Circuit | Self-edit recursion depth ≤ 2 | Caps self-modification depth (matches EvoForge `max_depth=2`) |
| **E** | Evolution | Child fitness ≥ 0.8 × parent | Blocks regressions dressed as exploration |
| **Bl** | Blacklist | Airgap, kill-switch, ownership, rate-limit… clauses cannot be deleted | The constitutional layer — not trade-offs, preconditions |

**Fail one axis, the child dies.** Rejections carry their failing axes,
so attempted escapes are themselves auditable data.

Distinct from evo-skillopt's held-out Q-gate: that gate answers *"is
the child better?"* — the claw answers *"is the child allowed to
exist?"*.

```python
from metaclaw import Mutation, gate

v = gate(Mutation(parent_md=open("skill_v1.md").read(),
                  child_md=open("skill_v2.md").read(),
                  parent_fitness=0.80, child_fitness=0.848, depth=3))
print(v)   # REJECTED (Ci, Bl) — the +6% fitness is irrelevant
```

CLI equivalent: `evo-metaclaw claw parent.md child.md --parent-fitness 0.8 --child-fitness 0.85`

## Signal pipeline (the learning half)

```
conversations ──► evo-metaclaw   (claw + capture + summarize)   ← you are here
                ──► evo-skillopt (train + held-out gate + rollback)
                ──► EvoForge     (install as genome pack, idle-window mutation)
```

| kind | meaning |
|------|---------|
| `task_success` / `task_failure` | exchange outcomes (errors, empty replies) |
| `user_feedback` | explicit thumbs/correction — highest value |
| `coordination` | multi-agent handoff observation |
| `domain_insight` | reusable fact surfaced mid-session |
| `emerging_need` | need no current agent/skill covers |

Append-only SQLite (WAL). Distilled drafts are marked **"must pass
held-out gate before use"** — hypotheses, not promotions.

```bash
pip install -e ".[dev]" && python -m pytest     # 16 tests, stdlib-only

evo-metaclaw capture demo1 task_failure "RuntimeError: timeout" --agent sales-bot
evo-metaclaw capture demo1 user_feedback "too verbose" --score -0.8
evo-metaclaw capture demo1 emerging_need "needs PDF export"
evo-metaclaw summarize demo1                     # → candidate SKILL.md
evo-metaclaw emit demo1 sales-bot --worker http://localhost:9000 --token $WORKER_TOKEN
```

## Boundary discipline

The claw governs *constraints*; it does not train, version, or promote
skills — that stays in evo-skillopt. It deploys nothing — that stays in
EvoForge. Sessions under 3 signals produce no draft (anecdote ≠
pattern). User feedback is the only quality signal; capture classifies
mechanics only.

## Position in the stack

| Layer | Project | Job |
|---|---|---|
| 1 | [EvoForge](https://github.com/dnzengou/evoforge-repo) | Scored Champions on real tasks; dispatch by cost/latency/success |
| 2 | [evo-skillopt](https://github.com/dnzengou/evo-skillopt) | Skill training with held-out gates and rollback |
| 3 | **evo-metaclaw** | Four-axis claw on every mutation; live signal capture |

## Honest limits

- The claw's Bl axis is textual: a clause deleted *and* meaningfully
  preserved in other words passes. Treat it as a tripwire, not a proof.
- "Makes the edit illegal" holds where the gate is wired into the
  mutation path. In a given deployment, verify the wiring before
  trusting the claim.

## Docs

- [docs/architecture.md](docs/architecture.md) — triad data flow, gate semantics, design rules

## License

MIT
