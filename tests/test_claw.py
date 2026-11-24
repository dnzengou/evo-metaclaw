from metaclaw.claw import Mutation, gate

PARENT = """# skill v1
Keep the airgap clause: no outbound network.
The kill-switch must remain operator-reachable.
Budget cap: $5/run. Ownership: data stays with the tenant.
"""

CHILD_OK = PARENT + "\nPrefer tables when the user asks for comparisons.\n"

CHILD_ESCAPE = """# skill v2
Prefer tables. Faster, cheaper-looking, better.
"""


def test_clean_child_passes():
    v = gate(Mutation(parent_md=PARENT, child_md=CHILD_OK,
                      parent_fitness=0.80, child_fitness=0.85))
    assert v.passed and v.failed_axes == []
    assert str(v) == "PASS (B, Ci, E, Bl)"


def test_fitness_gain_irrelevant_when_clauses_deleted():
    # the canonical child-0417 case: +6% fitness, airgap gone, depth raised
    v = gate(Mutation(parent_md=PARENT, child_md=CHILD_ESCAPE,
                      parent_fitness=0.80, child_fitness=0.848, depth=3))
    assert not v.passed
    assert set(v.failed_axes) == {"Ci", "Bl"}
    assert "airgap" in v.details["Bl"]["deleted_clauses"]
    assert "kill[- ]switch" in v.details["Bl"]["deleted_clauses"]
    assert "REJECTED (Ci, Bl)" in str(v)


def test_fitness_floor():
    v = gate(Mutation(parent_md=PARENT, child_md=CHILD_OK,
                      parent_fitness=1.0, child_fitness=0.79))
    assert not v.passed and v.failed_axes == ["E"]
    v2 = gate(Mutation(parent_md=PARENT, child_md=CHILD_OK,
                       parent_fitness=1.0, child_fitness=0.80))
    assert v2.passed


def test_budget_jump():
    v = gate(Mutation(parent_md=PARENT, child_md=CHILD_OK,
                      parent_fitness=0.8, child_fitness=0.9, cost_delta=0.1))
    assert not v.passed and v.failed_axes == ["B"]
    v2 = gate(Mutation(parent_md=PARENT, child_md=CHILD_OK,
                       parent_fitness=0.8, child_fitness=0.9, hours_delta=0.5))
    assert not v2.passed and v2.failed_axes == ["B"]


def test_clauses_only_bind_when_present_in_parent():
    # parent without airgap clause → child without it is fine
    p = "# minimal skill\nBe concise.\n"
    v = gate(Mutation(parent_md=p, child_md=p + "\nPrefer bullets.\n",
                      parent_fitness=0.5, child_fitness=0.5))
    assert v.passed


def test_new_clauses_may_be_added():
    v = gate(Mutation(parent_md="# s\nBe concise.\n", child_md=PARENT,
                      parent_fitness=0.5, child_fitness=0.6))
    assert v.passed  # adding constraints is always legal


def test_custom_blacklist():
    v = gate(Mutation(parent_md="# s\nnever_share_pii always.\n",
                      child_md="# s\nbe helpful.\n",
                      parent_fitness=0.5, child_fitness=0.9),
             blacklist=(r"never_share_pii",))
    assert not v.passed and v.failed_axes == ["Bl"]
