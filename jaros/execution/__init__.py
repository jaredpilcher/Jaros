"""The deterministic Execution Plane (EXT-001).

This package validates and acts on inert ``Decision`` data. It must never import
the Reasoning Plane (``jaros.llm`` or ``reasoning_boundary``); the separation is
enforced structurally by ``scripts/check_planes.py``.
"""

from __future__ import annotations
