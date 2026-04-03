"""Direct Nia API client with local caching and chunk extraction."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from harness.prompts import build_nia_query
from harness.retry import HTTPRequestError, post_json_with_retry
from harness.types import NiaChunk, Task


class NiaClientError(RuntimeError):
    """Raised when Nia context retrieval fails."""


class NiaClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        search_endpoint: str | None,
        index_endpoint: str | None,
        cache_dir: Path,
    ) -> None:
        self.api_key = api_key
        self.search_endpoint = search_endpoint
        self.index_endpoint = index_endpoint
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_context(
        self, task: Task, *, limit: int = 6
    ) -> tuple[list[NiaChunk], str, int | None, dict[str, Any]]:
        if not self.api_key:
            raise NiaClientError("Missing NIA_API_KEY")
        if not self.search_endpoint and not self.index_endpoint:
            raise NiaClientError(
                "Missing Nia endpoints. Set NIA_SEARCH_ENDPOINT and/or NIA_INDEX_ENDPOINT."
            )

        query = build_nia_query(task)
        cache_key = self._cache_key(task, query, limit)
        cache_path = self.cache_dir / f"{cache_key}.json"
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as handle:
                cached = json.load(handle)
            retrieval = cached.get("retrieval")
            if not isinstance(retrieval, dict):
                retrieval = self._derive_retrieval_metadata(
                    raw_responses=cached.get("raw_responses"),
                    chunk_payload=cached.get("chunks"),
                )
            return (
                self._deserialize_chunks(cached["chunks"]),
                cached["query"],
                cached.get("response_time_ms"),
                retrieval,
            )

        started = time.perf_counter()
        payload = {
            "query": query,
            "library": task.library,
            "version": task.version_introduced,
            "category": task.category,
            "top_k": limit,
        }

        raw_responses: list[dict[str, Any]] = []
        chunks: list[NiaChunk] = []
        if self.search_endpoint:
            try:
                search_response = self._post_with_mode_fallback(
                    endpoint=self.search_endpoint,
                    payload=payload,
                    modes=["web", "universal", "query", "deep"],
                )
                raw_responses.append({"endpoint": self.search_endpoint, "response": search_response})
                chunks.extend(self._extract_chunks(search_response))
            except NiaClientError as exc:
                message = str(exc)
                raw_responses.append({"endpoint": self.search_endpoint, "error": message})
                # Allow benchmark execution to continue when search is quota-limited.
                # This keeps runs bounded while clearly preserving retrieval error evidence.
                if "status=429" not in message and "status=network-error" not in message:
                    raise
        if not chunks and self.index_endpoint:
            try:
                index_response = self._post_with_mode_fallback(
                    endpoint=self.index_endpoint,
                    payload=payload,
                    modes=["web", "universal", "query", "deep"],
                )
                raw_responses.append({"endpoint": self.index_endpoint, "response": index_response})
                chunks.extend(self._extract_chunks(index_response))
            except NiaClientError as exc:
                raw_responses.append({"endpoint": self.index_endpoint, "error": str(exc)})
                # If search ran but index schema/mode compatibility is bad, prefer completing
                # the task with empty context rather than failing hard.
                if not self.search_endpoint:
                    raise

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        trimmed_chunks = chunks[:limit]
        retrieval = self._derive_retrieval_metadata(
            raw_responses=raw_responses,
            chunk_payload=[chunk.to_dict() for chunk in trimmed_chunks],
        )
        cache_payload = {
            "query": query,
            "response_time_ms": elapsed_ms,
            "chunks": [chunk.to_dict() for chunk in trimmed_chunks],
            "raw_responses": raw_responses,
            "retrieval": retrieval,
        }
        with cache_path.open("w", encoding="utf-8") as handle:
            json.dump(cache_payload, handle, indent=2)

        return trimmed_chunks, query, elapsed_ms, retrieval

    def _cache_key(self, task: Task, query: str, limit: int) -> str:
        source = f"{task.id}|{task.library}|{task.version_introduced}|{query}|{limit}"
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "x-api-key": self.api_key,
        }
        try:
            response, _response_headers = post_json_with_retry(
                url=url,
                payload=payload,
                headers=headers,
                timeout_seconds=60,
                service_name="nia",
                max_attempts=3,
                base_backoff_seconds=1.0,
                max_backoff_seconds=16.0,
            )
            return response
        except HTTPRequestError as exc:
            raise NiaClientError(str(exc)) from exc

    def _post_with_mode_fallback(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
        modes: list[str],
    ) -> dict[str, Any]:
        last_error: NiaClientError | None = None

        for mode in modes:
            candidate_payload = dict(payload)
            candidate_payload["mode"] = mode
            try:
                return self._post_json(endpoint, candidate_payload)
            except NiaClientError as exc:
                message = str(exc)
                if (
                    "status=422" in message
                    or "status=403" in message
                    or "status=429" in message
                    or "rate_limit_exceeded" in message
                    or "union_tag_invalid" in message
                    or "union_tag_not_found" in message
                ):
                    last_error = exc
                    continue
                raise

        if last_error is not None:
            raise last_error
        return self._post_json(endpoint, payload)

    def _extract_chunks(self, payload: dict[str, Any]) -> list[NiaChunk]:
        for key in (
            "results",
            "chunks",
            "data",
            "documents",
            "hits",
            "documentation",
            "other_content",
            "github_repos",
        ):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return [chunk for chunk in (self._coerce_chunk(item) for item in candidate) if chunk]
        return []

    def _coerce_chunk(self, item: Any) -> NiaChunk | None:
        if isinstance(item, str):
            text = item.strip()
            return NiaChunk(text=text) if text else None
        if not isinstance(item, dict):
            return None

        text = (
            item.get("text")
            or item.get("content")
            or item.get("chunk")
            or item.get("snippet")
            or item.get("body")
            or item.get("summary")
        )
        if not isinstance(text, str) or not text.strip():
            return None

        return NiaChunk(
            text=text.strip(),
            title=_optional_str(item.get("title") or item.get("name")),
            url=_optional_str(item.get("url") or item.get("href")),
            source=_optional_str(item.get("source") or item.get("path")),
            metadata={
                k: v
                for k, v in item.items()
                if k not in {"text", "content", "chunk", "snippet", "body"}
            },
        )

    def _deserialize_chunks(self, payload: list[dict[str, Any]]) -> list[NiaChunk]:
        return [
            NiaChunk(
                text=item["text"],
                title=item.get("title"),
                url=item.get("url"),
                source=item.get("source"),
                metadata=item.get("metadata"),
            )
            for item in payload
        ]

    def _derive_retrieval_metadata(
        self,
        *,
        raw_responses: Any,
        chunk_payload: Any,
    ) -> dict[str, Any]:
        endpoint_attempts: list[dict[str, Any]] = []
        errors: list[str] = []

        if isinstance(raw_responses, list):
            for entry in raw_responses:
                if not isinstance(entry, dict):
                    continue
                endpoint = entry.get("endpoint")
                endpoint_label = endpoint if isinstance(endpoint, str) and endpoint else "unknown"
                error = entry.get("error")
                if isinstance(error, str) and error:
                    endpoint_attempts.append(
                        {"endpoint": endpoint_label, "status": "error", "error": error}
                    )
                    errors.append(f"{endpoint_label}: {error}")
                elif "response" in entry:
                    endpoint_attempts.append({"endpoint": endpoint_label, "status": "ok"})
                else:
                    endpoint_attempts.append({"endpoint": endpoint_label, "status": "unknown"})

        chunk_count = len(chunk_payload) if isinstance(chunk_payload, list) else 0
        if chunk_count > 0:
            status = "ok" if not errors else "partial_error"
        else:
            status = "error" if errors else "empty"

        return {
            "status": status,
            "errors": errors,
            "endpoint_attempts": endpoint_attempts,
            "chunk_count": chunk_count,
        }


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
