"""Resilience helpers for Episode 1 metadata scripts.

Dataverse occasionally fails table/column/lookup creation with a transient
SQL-side error (e.g. "A severe error occurred on the current command",
deadlocks, timeouts). Each of those errors is recoverable with a short
backoff and retry. This module provides:

  - is_duplicate(e)   : recognize "already exists"-style errors
  - is_transient(e)   : recognize retryable platform errors
  - short_error(e)    : single-line, truncated error for human-readable logs
  - attempt(label, fn): run fn() with retry+backoff; return one of
                        'created' | 'duplicate' | 'failed'
  - attempt_many(jobs, workers): run many attempt()s in parallel threads

Used by create_datamodel.py, ep1_provenance.py, modeling_skill.py.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, Literal, Sequence, Tuple

_DUPLICATE_MARKERS = (
    "duplicate",
    "already exists",
    "matching key",
    "already being used",
    "cannot be used again",
    "is not unique within an entity",
    "navigationpropertyname",
)

_TRANSIENT_MARKERS = (
    "severe error occurred on the current command",
    "deadlock",
    "timeout expired",
    "operation timed out",
    "the wait operation timed out",
    "transport-level error",
    "connection was forcibly closed",
    "service is currently unavailable",
    "request rate is large",
    "throttle",
    "internal server error",
    "sqlexception",
    "cannot start another",
    "entitycustomization",
    "solution installation or removal failed",
)

# Serialize prints across worker threads so output stays readable.
_print_lock = threading.Lock()


def _log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def is_duplicate(e: BaseException) -> bool:
    msg = str(e).lower()
    return any(m in msg for m in _DUPLICATE_MARKERS)


def is_transient(e: BaseException) -> bool:
    if is_duplicate(e):
        return False
    msg = str(e).lower()
    return any(m in msg for m in _TRANSIENT_MARKERS)


def short_error(e: BaseException, limit: int = 240) -> str:
    """Return a single-line summary of an exception, truncated."""
    first_line = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
    if len(first_line) > limit:
        first_line = first_line[:limit].rstrip() + "..."
    return f"{type(e).__name__}: {first_line}"


def attempt(
    label: str,
    fn: Callable[[], object],
    *,
    max_attempts: int = 4,
    base_delay: float = 2.0,
) -> Literal["created", "duplicate", "failed"]:
    """Run fn() with retry+backoff on transient errors.

    Prints a one-line outcome ("  Created: X" / "  X already exists" /
    "  ERROR X: ...") and returns the outcome category.
    """
    for attempt_num in range(1, max_attempts + 1):
        try:
            fn()
            _log(f"  Created: {label}")
            return "created"
        except Exception as e:  # noqa: BLE001
            if is_duplicate(e):
                _log(f"  {label} already exists, skipping.")
                return "duplicate"
            if is_transient(e) and attempt_num < max_attempts:
                delay = base_delay * (2 ** (attempt_num - 1))
                _log(
                    f"  {label}: transient error (attempt {attempt_num}/{max_attempts}); "
                    f"retrying in {delay:.0f}s -- {short_error(e)}"
                )
                time.sleep(delay)
                continue
            _log(f"  ERROR {label}: {short_error(e)}")
            return "failed"
    return "failed"


def attempt_many(
    jobs: Iterable[Tuple[str, Callable[[], object]]],
    *,
    workers: int = 6,
    max_attempts: int = 4,
    base_delay: float = 2.0,
) -> Sequence[Tuple[str, str]]:
    """Run many attempt()s in parallel threads.

    `jobs` is an iterable of (label, callable) pairs. Returns a list of
    (label, outcome) tuples in completion order. Dataverse SDK calls release
    the GIL during HTTP I/O, so threads parallelize wall-clock time well.
    """
    jobs = list(jobs)
    if not jobs:
        return []
    outcomes: list[Tuple[str, str]] = []
    workers = max(1, min(workers, len(jobs)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_label = {
            pool.submit(
                attempt, label, fn,
                max_attempts=max_attempts, base_delay=base_delay,
            ): label
            for label, fn in jobs
        }
        for fut in as_completed(future_to_label):
            label = future_to_label[fut]
            outcomes.append((label, fut.result()))
    return outcomes

