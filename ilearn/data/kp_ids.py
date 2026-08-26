import hashlib
import re
from pathlib import Path
import json

_LEGACY = {
    "三位数乘两位数": "mult_3digit",
    "长方形面积": "rect_area",
    "角的度量": "angle_measure",
    "平行与垂直": "parallel_perp",
    "小数乘法": "dec_mult",
    "同分母分数加法": "frac_add_same",
    "分数乘法": "frac_mult",
    "简易方程": "simple_eq",
    "分数除法": "frac_div",
    "比和比例": "ratio",
    "圆的面积": "circle_area",
    "百分数应用": "percent",
    "因数与倍数": "factors",
}


def slugify_kp(name: str) -> str:
    if name in _LEGACY:
        return _LEGACY[name]
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:48] or "kp_unknown"


def resolve_kp_id(label: str, alias_map: dict[str, str]) -> str | None:
    if label in alias_map:
        return alias_map[label]
    slug = slugify_kp(label)
    return slug if slug != "kp_unknown" else None


def stable_kp_id(label: str, alias_map: dict[str, str]) -> str | None:
    """Resolve label to knowledge_id; hash-fallback for non-ASCII RCAE node names."""
    resolved = resolve_kp_id(label, alias_map)
    if resolved is not None:
        return resolved
    text = label.strip()
    if not text:
        return None
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"kp_{digest}"


def load_alias_map(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    merged = dict(_LEGACY)
    merged.update(data.get("aliases", {}))
    for v in _LEGACY.values():
        merged[v] = v
    return merged


def extend_alias_from_knowledge(
    knowledge: list[dict], alias_map: dict[str, str]
) -> dict[str, str]:
    """Add knowledge node names so MM-K12 / TAL matchers can resolve RCAE labels."""
    extended = dict(alias_map)
    for entry in knowledge:
        kp_id = str(entry.get("id", "")).strip()
        name = str(entry.get("name", "")).strip()
        if kp_id:
            extended[kp_id] = kp_id
        if name and kp_id:
            extended[name] = kp_id
    return extended
