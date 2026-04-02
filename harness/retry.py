"""Shared HTTP retry utilities for provider and Nia API calls."""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
NON_RETRYABLE_429_MARKERS = {
    "insufficient_quota",
    "billing_hard_limit_reached",
    "exceeded your current quota",
    "credit balance is too low",
}


@dataclass(frozen=True)
class RetryAttempt:
    attempt: int
    retryable: bool
    status_code: int | None
    request_id: str | None
    error: str
    delay_seconds: float | None = None


class HTTPRequestError(RuntimeError):
    """Raised when an HTTP request fails after retry attempts."""

    def __init__(self, message: str, attempts: list[RetryAttempt]) -> None:
        super().__init__(message)
        self.attempts = attempts


LoggerFn = Callable[[str], None]


def post_json_with_retry(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: int,
    service_name: str,
    max_attempts: int = 5,
    base_backoff_seconds: float = 1.0,
    max_backoff_seconds: float = 16.0,
    logger: LoggerFn | None = print,
) -> tuple[dict[str, Any], dict[str, str]]:
    """POST JSON with bounded exponential backoff for retryable failures."""
    attempts: list[RetryAttempt] = []

    for attempt_index in range(1, max_attempts + 1):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return json.loads(body), dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            response_headers = dict(exc.headers.items()) if exc.headers else {}
            request_id = _extract_request_id(response_headers)
            details = exc.read().decode("utf-8", errors="replace")
            retryable = _is_retryable_http_error(status_code=exc.code, details=details)

            if retryable and attempt_index < max_attempts:
                retry_after_seconds = _parse_retry_after_seconds_from_error_body(details)
                delay = _compute_delay(
                    attempt=attempt_index,
                    base_backoff_seconds=base_backoff_seconds,
                    max_backoff_seconds=max_backoff_seconds,
                    retry_after_header=response_headers.get("retry-after"),
                    retry_after_seconds=retry_after_seconds,
                )
                attempts.append(
                    RetryAttempt(
                        attempt=attempt_index,
                        retryable=True,
                        status_code=exc.code,
                        request_id=request_id,
                        error=_compact_error(details),
                        delay_seconds=delay,
                    )
                )
                _log_retry(
                    logger=logger,
                    service_name=service_name,
                    attempt=attempt_index,
                    max_attempts=max_attempts,
                    delay_seconds=delay,
                    status_code=exc.code,
                    request_id=request_id,
                    error_preview=details,
                )
                time.sleep(delay)
                continue

            attempts.append(
                RetryAttempt(
                    attempt=attempt_index,
                    retryable=retryable,
                    status_code=exc.code,
                    request_id=request_id,
                    error=_compact_error(details),
                    delay_seconds=None,
                )
            )
            raise HTTPRequestError(
                _format_terminal_error(
                    service_name=service_name,
                    url=url,
                    status_code=exc.code,
                    request_id=request_id,
                    details=details,
                    attempts=attempts,
                ),
                attempts=attempts,
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            retryable = True
            error_text = str(exc)

            if attempt_index < max_attempts:
                delay = _compute_delay(
                    attempt=attempt_index,
                    base_backoff_seconds=base_backoff_seconds,
                    max_backoff_seconds=max_backoff_seconds,
                    retry_after_header=None,
                    retry_after_seconds=None,
                )
                attempts.append(
                    RetryAttempt(
                        attempt=attempt_index,
                        retryable=retryable,
                        status_code=None,
                        request_id=None,
                        error=_compact_error(error_text),
                        delay_seconds=delay,
                    )
                )
                _log_retry(
                    logger=logger,
                    service_name=service_name,
                    attempt=attempt_index,
                    max_attempts=max_attempts,
                    delay_seconds=delay,
                    status_code=None,
                    request_id=None,
                    error_preview=error_text,
                )
                time.sleep(delay)
                continue

            attempts.append(
                RetryAttempt(
                    attempt=attempt_index,
                    retryable=retryable,
                    status_code=None,
                    request_id=None,
                    error=_compact_error(error_text),
                    delay_seconds=None,
                )
            )
            raise HTTPRequestError(
                _format_terminal_error(
                    service_name=service_name,
                    url=url,
                    status_code=None,
                    request_id=None,
                    details=error_text,
                    attempts=attempts,
                ),
                attempts=attempts,
            ) from exc

    raise HTTPRequestError(
        f"{service_name}: exhausted retry attempts for {url}",
        attempts=attempts,
    )


def _compute_delay(
    *,
    attempt: int,
    base_backoff_seconds: float,
    max_backoff_seconds: float,
    retry_after_header: str | None,
    retry_after_seconds: float | None,
) -> float:
    computed = min(max_backoff_seconds, base_backoff_seconds * (2 ** (attempt - 1)))
    computed = random.uniform(0.0, computed)
    retry_after = _parse_retry_after(retry_after_header)
    if retry_after is not None:
        computed = max(computed, retry_after)
    if retry_after_seconds is not None:
        computed = max(computed, retry_after_seconds)
    return max(0.05, computed)


def _parse_retry_after(raw: str | None) -> float | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _parse_retry_after_seconds_from_error_body(details: str) -> float | None:
    try:
        payload = json.loads(details)
    except json.JSONDecodeError:
        return None

    candidates: list[Any] = []
    if isinstance(payload, dict):
        candidates.append(payload.get("retry_after_seconds"))
        detail = payload.get("detail")
        if isinstance(detail, dict):
            candidates.append(detail.get("retry_after_seconds"))
        elif isinstance(detail, list):
            for item in detail:
                if isinstance(item, dict):
                    candidates.append(item.get("retry_after_seconds"))

    for value in candidates:
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
        if isinstance(value, str):
            try:
                parsed = float(value)
            except ValueError:
                continue
            if parsed >= 0:
                return parsed
    return None


def _log_retry(
    *,
    logger: LoggerFn | None,
    service_name: str,
    attempt: int,
    max_attempts: int,
    delay_seconds: float,
    status_code: int | None,
    request_id: str | None,
    error_preview: str,
) -> None:
    if logger is None:
        return
    status_fragment = f"status={status_code}" if status_code is not None else "status=network-error"
    request_fragment = f" request_id={request_id}" if request_id else ""
    logger(
        (
            f"[retry] service={service_name} attempt={attempt}/{max_attempts} "
            f"{status_fragment} sleep={delay_seconds:.1f}s{request_fragment} "
            f"error={_compact_error(error_preview)}"
        )
    )


def _format_terminal_error(
    *,
    service_name: str,
    url: str,
    status_code: int | None,
    request_id: str | None,
    details: str,
    attempts: list[RetryAttempt],
) -> str:
    status_fragment = f"status={status_code}" if status_code is not None else "status=network-error"
    request_fragment = f" request_id={request_id}" if request_id else ""
    return (
        f"{service_name} request failed: {url} {status_fragment}{request_fragment}; "
        f"attempts={len(attempts)}; last_error={_compact_error(details)}"
    )


def _extract_request_id(headers: dict[str, str]) -> str | None:
    for key in ("request-id", "x-request-id"):
        value = headers.get(key)
        if value:
            return value
    return None


def _compact_error(text: str, limit: int = 280) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _is_retryable_http_error(*, status_code: int, details: str) -> bool:
    if status_code not in RETRYABLE_STATUS_CODES:
        return False

    lowered = details.lower()
    if status_code == 429 and any(marker in lowered for marker in NON_RETRYABLE_429_MARKERS):
        return False
    return True
