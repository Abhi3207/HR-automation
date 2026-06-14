"""
Pipeline metrics and observability utilities.

Provides a lightweight, in-memory metrics collector that records
per-stage timing and status for every pipeline run.

Usage:
    from config.metrics import StageTimer

    with StageTimer("job_posting") as timer:
        result = agent.invoke(state)
    metrics_dict = timer.to_dict()
"""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StageTimer:
    """Context manager that records wall-clock time for a pipeline stage.

    Usage::

        with StageTimer("job_posting") as t:
            result = agent.invoke(state)
        t.mark_success()              # or t.mark_failure("reason")
        metrics = t.to_dict()
    """

    stage_name: str
    start_time: float = field(default=0.0, init=False)
    end_time: float = field(default=0.0, init=False)
    elapsed_seconds: float = field(default=0.0, init=False)
    status: str = field(default="running", init=False)   # running, success, error
    error_detail: Optional[str] = field(default=None, init=False)
    tool_call_count: int = field(default=0, init=False)

    def __enter__(self) -> "StageTimer":
        self.start_time = time.time()
        self.status = "running"
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.end_time = time.time()
        self.elapsed_seconds = round(self.end_time - self.start_time, 3)
        if exc_type is not None:
            self.status = "error"
            self.error_detail = str(exc_val)
        # Don't suppress exceptions
        return False

    def mark_success(self) -> None:
        self.status = "success"

    def mark_failure(self, reason: str) -> None:
        self.status = "error"
        self.error_detail = reason

    def count_tool_calls(self, messages: list) -> int:
        """Count tool calls from the message list produced by an agent run."""
        count = 0
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                count += len(msg.tool_calls)
        self.tool_call_count = count
        return count

    def to_dict(self) -> dict:
        return {
            "stage": self.stage_name,
            "elapsed_seconds": self.elapsed_seconds,
            "status": self.status,
            "error": self.error_detail,
            "tool_calls": self.tool_call_count,
        }
