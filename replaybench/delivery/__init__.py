"""Delivery channels. A mechanism moves a stored tool result; it is not a new case."""

from replaybench.delivery.m1_durable import M1Durable
from replaybench.delivery.m2_queue import M2Queue
from replaybench.delivery.m3_cache import M3Cache

MECHANISMS = {"M1": M1Durable, "M2": M2Queue, "M3": M3Cache}


def open_mechanism(name: str, db_path):
    key = name.upper()
    if key not in MECHANISMS:
        raise ValueError(f"unknown mechanism {name!r}; expected M1, M2, or M3")
    return MECHANISMS[key](db_path)
