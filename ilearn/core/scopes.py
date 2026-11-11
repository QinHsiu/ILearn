"""Agent API scopes — config-file RBAC for offline and keyed deployments."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _PROJECT_ROOT / "data" / "agent_scopes.yaml"
_CACHE: dict[str, dict[str, dict[str, Any]]] = {}


def _parse_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError("agent_scopes root must be a mapping")
        return data
    except ImportError:
        return _parse_simple_scopes_yaml(text)


def _parse_simple_scopes_yaml(text: str) -> dict[str, Any]:
    """Parse the project-default agent_scopes.yaml shape without PyYAML."""
    agents: dict[str, dict[str, Any]] = {}
    enforcement = "hard"
    current: str | None = None
    in_agents = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("enforcement:"):
            enforcement = line.split(":", 1)[1].strip()
            continue
        if line.strip() == "agents:":
            in_agents = True
            continue
        if not in_agents:
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 2 and stripped.endswith(":") and not stripped.startswith("-"):
            current = stripped[:-1]
            agents[current] = {"scopes": [], "api_key_env": None}
            continue
        if current is None:
            continue
        if stripped.startswith("scopes:"):
            rest = stripped.split(":", 1)[1].strip()
            if rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1].strip()
                # Support quoted tokens: ["curriculum:retrieve", ...]
                parts: list[str] = []
                buf = ""
                in_quote = False
                for ch in inner:
                    if ch in {'"', "'"}:
                        in_quote = not in_quote
                        continue
                    if ch == "," and not in_quote:
                        if buf.strip():
                            parts.append(buf.strip())
                        buf = ""
                        continue
                    buf += ch
                if buf.strip():
                    parts.append(buf.strip())
                agents[current]["scopes"] = parts
            continue
        if stripped.startswith("api_key_env:"):
            agents[current]["api_key_env"] = stripped.split(":", 1)[1].strip() or None
    return {"enforcement": enforcement, "agents": agents}


def _normalize_scope_list(scopes: Any) -> list[str]:
    if scopes is None:
        return []
    if isinstance(scopes, str):
        return [scopes]
    out: list[str] = []
    for item in scopes:
        if isinstance(item, dict):
            # PyYAML may parse [curriculum:retrieve] as [{curriculum: retrieve}]
            for key, value in item.items():
                out.append(f"{key}:{value}")
        else:
            out.append(str(item))
    return out


def scopes_path() -> Path:
    override = os.getenv("ILEARN_AGENT_SCOPES_PATH")
    if override:
        return Path(override)
    return _DEFAULT_PATH


def load_agent_scopes() -> dict[str, dict[str, Any]]:
    path = scopes_path()
    cache_key = str(path.resolve()) if path.exists() else str(path)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    if not path.is_file():
        normalized = {
            "curriculum": {"scopes": ["curriculum:retrieve"], "api_key_env": None},
            "practice": {"scopes": ["practice:grade"], "api_key_env": None},
        }
        _CACHE[cache_key] = normalized
        return normalized
    payload = _parse_yaml(path.read_text(encoding="utf-8"))
    agents = payload.get("agents") or {}
    if not isinstance(agents, dict):
        raise ValueError("agent_scopes.agents must be a mapping")
    normalized: dict[str, dict[str, Any]] = {}
    for name, cfg in agents.items():
        if not isinstance(cfg, dict):
            continue
        normalized[str(name)] = {
            "scopes": _normalize_scope_list(cfg.get("scopes")),
            "api_key_env": cfg.get("api_key_env"),
        }
    _CACHE[cache_key] = normalized
    return normalized


def reset_scopes_cache() -> None:
    _CACHE.clear()


def assert_agent_scope(
    agent: str,
    scope: str,
    *,
    api_key: str | None = None,
) -> None:
    """Enforce scope membership; optionally match per-agent API key when configured."""
    agents = load_agent_scopes()
    cfg = agents.get(agent)
    if cfg is None:
        raise PermissionError(f"unknown agent for scope check: {agent}")
    allowed = set(cfg.get("scopes") or [])
    if scope not in allowed:
        raise PermissionError(
            f"{agent} lacks scope {scope!r}; allowed={sorted(allowed)}"
        )
    env_name = cfg.get("api_key_env")
    if not env_name:
        return
    expected = os.getenv(str(env_name))
    if not expected:
        # Offline / unset: membership-only enforcement.
        return
    if api_key != expected:
        raise PermissionError(
            f"{agent} scope {scope!r} requires matching API key from {env_name}"
        )
