import logging
import json
import contextvars
from typing import Any

# Context variables for structured logging
ctx_experiment_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("experiment_id", default=None)
ctx_generation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("generation_id", default=None)
ctx_execution_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("execution_id", default=None)
ctx_task_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("task_id", default=None)


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        exp_id = ctx_experiment_id.get()
        gen_id = ctx_generation_id.get()
        exec_id = ctx_execution_id.get()
        t_id = ctx_task_id.get()

        if exp_id:
            log_obj["experiment_id"] = exp_id
        if gen_id:
            log_obj["generation_id"] = gen_id
        if exec_id:
            log_obj["execution_id"] = exec_id
        if t_id:
            log_obj["task_id"] = t_id

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def get_logger(name: str = "forge") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = StructuredJsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
