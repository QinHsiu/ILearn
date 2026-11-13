"""Trajectory hash-chain replay verification."""

from __future__ import annotations

from ilearn.audit.trajectory import Trajectory


def replay_trajectory(traj: Trajectory) -> bool:
    """验证轨迹的哈希链连续性。"""
    expected = traj.start_state_hash
    for node in traj.nodes:
        if node.state_hash_before != expected:
            return False
        expected = node.state_hash_after
    return expected == traj.end_state_hash
