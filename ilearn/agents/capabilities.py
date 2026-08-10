"""Per-agent state write capabilities."""

AGENT_CAPABILITIES: dict[str, frozenset[str]] = {
    "assessment": frozenset({"paper"}),
    "practice": frozenset({"grades", "evidence"}),
    "diagnosis": frozenset({"diagnosis", "portrait"}),
    "planning": frozenset({"plan", "plan_history_append"}),
    "curriculum": frozenset({"citations"}),
    "tutor": frozenset({"tutor_turn"}),
}


def assert_writes_allowed(agent_name: str, write_keys: set[str]) -> None:
    """Raise when an agent attempts to write outside its capability set."""
    allowed = AGENT_CAPABILITIES.get(agent_name, frozenset())
    bad = write_keys - allowed
    if bad:
        raise PermissionError(f"{agent_name} cannot write {sorted(bad)}")
