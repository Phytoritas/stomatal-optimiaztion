from __future__ import annotations

from enum import Enum


class Organ(str, Enum):
    FRUIT = "fruit"
    LEAF = "leaf"
    STEM = "stem"
    ROOT = "root"
    SHOOT = "shoot"
