import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict

_LOG_LOCK = Lock()


def _env_enabled(name: str, default: str = "true") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _new_user_id() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%dT%H%M%S%fZ"), now.isoformat().replace("+00:00", "Z")


def log_route_result(
    method: str,
    symptom_source: str,
    symptom_value: str,
    response: Dict[str, Any],
) -> Dict[str, Any]:
    user_id, timestamp_utc = _new_user_id()
    response_with_id = dict(response)
    response_with_id["user_id"] = user_id

    if not _env_enabled("LOG_ROUTE_REQUESTS", "true"):
        return response_with_id

    log_path = Path(os.getenv("ROUTE_LOG_PATH", "logs/route_requests.jsonl"))
    entry = {
        "user_id": user_id,
        "timestamp_utc": timestamp_utc,
        "method": method,
        "input": {
            "symptom_source": symptom_source,
            "symptom_value": symptom_value,
        },
        "output": response_with_id,
    }

    try:
        with _LOG_LOCK:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write("\n")
    except OSError as exc:
        print(f"Route request logging failed: {exc}", file=sys.stderr)

    return response_with_id
