"""
Records the wall-clock moment ``app.main`` starts importing, before any other
first-party import runs. Must be imported first (see the ``noqa`` comment on
``app/main.py``'s import of it) so ``app.utils.lifespan`` can measure the full
import-to-ready duration, not just the time from lifespan startup.
"""
from time import perf_counter

IMPORT_STARTED_AT = perf_counter()
