"""Local and retrieval tool implementations for Layer 2 agent runs."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.agent_types import AgentTask, TestCommand
from harness.agent_workspace import AgentWorkspace, WorkspaceError
from harness.retry import HTTPRequestError, post_json_with_retry


class AgentToolError(RuntimeError):
    """Raised when a tool invocation fails."""


LOCAL_TOOL_NAMES = (
    "list_files",
    "read_file",
    "search_workspace",
    "write_file",
    "run_task_command",
)

NIA_TOOL_NAME = "nia_search_docs"


def build_tool_inventory(*, include_nia: bool, task_has_test_command: bool) -> list[str]:
    inventory = ["list_files", "read_file", "search_workspace", "write_file"]
    if task_has_test_command:
        inventory.append("run_task_command")
    if include_nia:
        inventory.append(NIA_TOOL_NAME)
    return inventory


def build_tool_schemas(*, include_nia: bool, task_has_test_command: bool) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = [
        _tool_schema(
            "list_files",
            "List files under a workspace-relative directory.",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "path": {"type": "string", "default": "."},
                    "max_results": {"type": "integer", "minimum": 1, "default": 500},
                    "max_depth": {"type": "integer", "minimum": 1, "default": 8},
                },
            },
        ),
        _tool_schema(
            "read_file",
            "Read a workspace-relative text file with truncation metadata.",
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "max_bytes": {"type": "integer", "minimum": 1, "default": 20000},
                },
            },
        ),
        _tool_schema(
            "search_workspace",
            "Search workspace text files by substring or regex-style pattern.",
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["pattern"],
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "max_results": {"type": "integer", "minimum": 1, "default": 200},
                },
            },
        ),
        _tool_schema(
            "write_file",
            "Write content to one allowed output file path.",
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["path", "content"],
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        ),
    ]
    if task_has_test_command:
        schemas.append(
            _tool_schema(
                "run_task_command",
                "Run the task's predefined command (no arbitrary arguments).",
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {},
                },
            )
        )
    if include_nia:
        schemas.append(
            _tool_schema(
                NIA_TOOL_NAME,
                "Retrieve documentation chunks from Nia using a structured query.",
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["query", "library", "version"],
                    "properties": {
                        "query": {"type": "string"},
                        "library": {"type": "string"},
                        "version": {"type": "string"},
                        "top_k": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                    },
                },
            )
        )
    return schemas


def _tool_schema(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


class AgentTools:
    """Executes Layer 2 tool calls with strict workspace and path boundaries."""

    def __init__(
        self,
        *,
        workspace: AgentWorkspace,
        task: AgentTask,
        include_nia: bool,
        nia_search_callable: Any | None = None,
    ) -> None:
        self.workspace = workspace
        self.task = task
        self.include_nia = include_nia
        self.nia_search_callable = nia_search_callable
        self.tool_logs: list[dict[str, Any]] = []

    def execute(self, *, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        started = _now_iso()
        began = time.perf_counter()

        error: str | None = None
        result_payload: dict[str, Any] | None = None
        try:
            if name == "list_files":
                result_payload = self.list_files(
                    path=_coerce_str(arguments.get("path"), default="."),
                    max_results=_coerce_positive_int(arguments.get("max_results"), default=500),
                    max_depth=_coerce_positive_int(arguments.get("max_depth"), default=8),
                )
            elif name == "read_file":
                result_payload = self.read_file(
                    path=_require_str(arguments, "path"),
                    max_bytes=_coerce_positive_int(arguments.get("max_bytes"), default=20000),
                )
            elif name == "search_workspace":
                result_payload = self.search_workspace(
                    pattern=_require_str(arguments, "pattern"),
                    path=_coerce_str(arguments.get("path"), default="."),
                    max_results=_coerce_positive_int(arguments.get("max_results"), default=200),
                )
            elif name == "write_file":
                result_payload = self.write_file(
                    path=_require_str(arguments, "path"),
                    content=_require_str(arguments, "content"),
                )
            elif name == "run_task_command":
                result_payload = self.run_task_command(arguments=arguments)
            elif name == NIA_TOOL_NAME:
                result_payload = self.nia_search_docs(arguments=arguments)
            else:
                raise AgentToolError(f"Unknown tool '{name}'")
        except (AgentToolError, WorkspaceError, OSError, ValueError) as exc:
            error = str(exc)

        finished = _now_iso()
        duration_ms = int((time.perf_counter() - began) * 1000)
        status = "ok" if error is None else "error"
        log_row = {
            "tool_name": name,
            "arguments": arguments,
            "result": result_payload,
            "error": error,
            "status": status,
            "started_at": started,
            "finished_at": finished,
            "duration_ms": duration_ms,
        }
        self.tool_logs.append(log_row)

        if error is not None:
            raise AgentToolError(error)
        return result_payload or {}

    def list_files(self, *, path: str = ".", max_results: int = 500, max_depth: int = 8) -> dict[str, Any]:
        resolved = self.workspace.resolve_read_path(path)
        if not resolved.exists():
            raise AgentToolError(f"Path not found: {path}")
        if not resolved.is_dir():
            raise AgentToolError(f"Path is not a directory: {path}")

        files: list[str] = []
        truncated = False
        for child in sorted(resolved.rglob("*")):
            if not child.is_file():
                continue
            relative_to_scope = child.relative_to(resolved)
            file_depth = len(relative_to_scope.parts)
            if file_depth > max_depth:
                continue
            files.append(str(child.relative_to(self.workspace.workspace_root)))
            if len(files) >= max_results:
                truncated = True
                break
        return {
            "path": path,
            "files": files,
            "count": len(files),
            "truncated": truncated,
            "max_results": max_results,
            "max_depth": max_depth,
        }

    def read_file(self, *, path: str, max_bytes: int = 20000) -> dict[str, Any]:
        resolved = self.workspace.resolve_read_path(path)
        if not resolved.exists() or not resolved.is_file():
            raise AgentToolError(f"File not found: {path}")

        raw = resolved.read_bytes()
        truncated = len(raw) > max_bytes
        selected = raw[:max_bytes]
        content = selected.decode("utf-8", errors="replace")
        return {
            "path": path,
            "content": content,
            "truncated": truncated,
            "bytes_total": len(raw),
            "bytes_returned": len(selected),
        }

    def search_workspace(
        self,
        *,
        pattern: str,
        path: str = ".",
        max_results: int = 200,
    ) -> dict[str, Any]:
        resolved = self.workspace.resolve_read_path(path)
        if not resolved.exists():
            raise AgentToolError(f"Path not found: {path}")

        rg_bin = shutil.which("rg")
        matches: list[dict[str, Any]] = []
        truncated = False

        if rg_bin is not None:
            cmd = [
                rg_bin,
                "--line-number",
                "--no-heading",
                "--color",
                "never",
                pattern,
                str(resolved),
            ]
            completed = subprocess.run(
                cmd,
                cwd=self.workspace.workspace_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode not in {0, 1}:
                raise AgentToolError(f"search_workspace failed via rg: {completed.stderr.strip()}")

            for line in completed.stdout.splitlines():
                parts = line.split(":", 2)
                if len(parts) != 3:
                    continue
                file_path, line_no, content = parts
                try:
                    line_number = int(line_no)
                except ValueError:
                    continue
                rel = str(Path(file_path).resolve().relative_to(self.workspace.workspace_root.resolve()))
                matches.append({"path": rel, "line": line_number, "text": content})
                if len(matches) >= max_results:
                    truncated = True
                    break
        else:
            for file_path in sorted(resolved.rglob("*")):
                if not file_path.is_file():
                    continue
                try:
                    rel = str(file_path.relative_to(self.workspace.workspace_root))
                    with file_path.open("r", encoding="utf-8", errors="replace") as handle:
                        for line_number, line in enumerate(handle, start=1):
                            if pattern in line:
                                matches.append(
                                    {"path": rel, "line": line_number, "text": line.rstrip("\n")}
                                )
                                if len(matches) >= max_results:
                                    truncated = True
                                    break
                    if truncated:
                        break
                except OSError:
                    continue

        return {
            "pattern": pattern,
            "path": path,
            "matches": matches,
            "count": len(matches),
            "truncated": truncated,
            "backend": "rg" if rg_bin is not None else "python",
        }

    def write_file(self, *, path: str, content: str) -> dict[str, Any]:
        destination = self.workspace.resolve_write_path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        return {
            "path": path,
            "bytes_written": len(content.encode("utf-8")),
        }

    def run_task_command(self, *, arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments:
            raise AgentToolError("run_task_command does not accept arguments")
        if self.task.test_command is None:
            raise AgentToolError("Task does not define test_command")
        return _run_test_command(self.workspace, self.task.test_command)

    def nia_search_docs(self, *, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.include_nia:
            raise AgentToolError("nia_search_docs is not available in this condition")
        if self.nia_search_callable is None:
            raise AgentToolError("nia_search_docs is unavailable: no retrieval callable configured")

        query = _require_str(arguments, "query")
        library = _require_str(arguments, "library")
        version = _require_str(arguments, "version")
        top_k = _coerce_positive_int(arguments.get("top_k"), default=5)

        payload = self.nia_search_callable(
            query=query,
            library=library,
            version=version,
            top_k=top_k,
        )
        if not isinstance(payload, dict):
            raise AgentToolError("nia_search_docs callable must return an object")
        return payload


class Layer2NiaSearchTool:
    """Thin structured retrieval wrapper for Layer 2 agent tool use."""

    def __init__(
        self,
        *,
        api_key: str | None,
        search_endpoint: str | None,
        index_endpoint: str | None,
    ) -> None:
        self.api_key = api_key
        self.search_endpoint = search_endpoint
        self.index_endpoint = index_endpoint
        self.cache_dir = (
            Path(__file__).resolve().parent.parent / "results" / "cache" / "layer2_nia_tool"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def search_docs(self, *, query: str, library: str, version: str, top_k: int = 5) -> dict[str, Any]:
        if not self.api_key:
            raise AgentToolError("Missing NIA_API_KEY")
        if not self.search_endpoint and not self.index_endpoint:
            raise AgentToolError(
                "Missing Nia endpoint configuration. Set NIA_SEARCH_ENDPOINT and/or NIA_INDEX_ENDPOINT."
            )

        started = time.perf_counter()
        attempted_endpoints: list[str] = []
        request_ids: list[str] = []
        modes_tried: list[str] = []
        endpoint_errors: list[str] = []

        cache_key = self._cache_key(query=query, library=library, version=version, top_k=top_k)
        cached_results = self._load_cache(cache_key)
        if cached_results:
            return {
                "query": query,
                "library": library,
                "version": version,
                "top_k": top_k,
                "results": cached_results[:top_k],
                "provider_metadata": {
                    "attempted_endpoints": attempted_endpoints,
                    "request_ids": request_ids,
                    "modes_tried": modes_tried,
                    "response_time_ms": int((time.perf_counter() - started) * 1000),
                    "cache_mode": "exact",
                    "degraded": False,
                    "endpoint_errors": endpoint_errors,
                },
            }

        payload = {
            "query": query,
            "library": library,
            "version": version,
            "top_k": top_k,
        }
        modes = ["web", "universal", "query", "deep"]

        search_payload: dict[str, Any] | None = None
        index_payload: dict[str, Any] | None = None

        if self.search_endpoint:
            attempted_endpoints.append(self.search_endpoint)
            try:
                search_payload, search_request_id, attempted_modes = self._post_with_mode_fallback(
                    endpoint=self.search_endpoint,
                    payload=payload,
                    modes=modes,
                )
                if search_request_id:
                    request_ids.append(search_request_id)
                modes_tried.extend(attempted_modes)
            except AgentToolError as exc:
                endpoint_errors.append(str(exc))

        search_results = _extract_nia_results(search_payload) if search_payload else []
        if not search_results and not self.search_endpoint and self.index_endpoint:
            attempted_endpoints.append(self.index_endpoint)
            try:
                index_payload, index_request_id, attempted_modes = self._post_with_mode_fallback(
                    endpoint=self.index_endpoint,
                    payload=payload,
                    modes=modes,
                )
                if index_request_id:
                    request_ids.append(index_request_id)
                modes_tried.extend(attempted_modes)
            except AgentToolError as exc:
                endpoint_errors.append(str(exc))

        index_results = _extract_nia_results(index_payload) if index_payload else []
        combined = (search_results + index_results)[:top_k]
        cache_mode = "none"
        if combined:
            self._write_cache(
                key=cache_key,
                query=query,
                library=library,
                version=version,
                top_k=top_k,
                results=combined,
            )
        else:
            scoped_cache_results = self._load_scoped_fallback(library=library, version=version)
            if scoped_cache_results:
                combined = scoped_cache_results[:top_k]
                cache_mode = "library_version_fallback"

        duration_ms = int((time.perf_counter() - started) * 1000)

        return {
            "query": query,
            "library": library,
            "version": version,
            "top_k": top_k,
            "results": combined,
            "provider_metadata": {
                "attempted_endpoints": attempted_endpoints,
                "request_ids": request_ids,
                "modes_tried": modes_tried,
                "response_time_ms": duration_ms,
                "cache_mode": cache_mode,
                "degraded": not bool(combined),
                "endpoint_errors": endpoint_errors,
            },
        }

    def _cache_key(self, *, query: str, library: str, version: str, top_k: int) -> str:
        source = f"{query}|{library}|{version}|{top_k}"
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _load_cache(self, key: str) -> list[dict[str, Any]] | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        results = payload.get("results")
        if not isinstance(results, list):
            return None
        rows: list[dict[str, Any]] = []
        for item in results:
            chunk = _coerce_nia_chunk(item)
            if chunk is not None:
                rows.append(chunk)
        return rows or None

    def _load_scoped_fallback(self, *, library: str, version: str) -> list[dict[str, Any]] | None:
        latest_results: list[dict[str, Any]] | None = None
        latest_mtime: float | None = None
        for path in self.cache_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            if payload.get("library") != library or payload.get("version") != version:
                continue
            results = payload.get("results")
            if not isinstance(results, list):
                continue
            rows: list[dict[str, Any]] = []
            for item in results:
                chunk = _coerce_nia_chunk(item)
                if chunk is not None:
                    rows.append(chunk)
            if not rows:
                continue
            mtime = path.stat().st_mtime
            if latest_mtime is None or mtime > latest_mtime:
                latest_mtime = mtime
                latest_results = rows
        return latest_results

    def _write_cache(
        self,
        *,
        key: str,
        query: str,
        library: str,
        version: str,
        top_k: int,
        results: list[dict[str, Any]],
    ) -> None:
        payload = {
            "generated_at": _now_iso(),
            "query": query,
            "library": library,
            "version": version,
            "top_k": top_k,
            "results": results,
        }
        path = self._cache_path(key)
        try:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            return

    def _post_with_mode_fallback(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
        modes: list[str],
    ) -> tuple[dict[str, Any], str | None, list[str]]:
        attempted_modes: list[str] = []
        last_error: AgentToolError | None = None
        for mode in modes:
            attempted_modes.append(mode)
            candidate_payload = dict(payload)
            candidate_payload["mode"] = mode
            try:
                response, headers = self._post_json(endpoint=endpoint, payload=candidate_payload)
                request_id = _extract_request_id(headers)
                return response, request_id, attempted_modes
            except AgentToolError as exc:
                message = str(exc)
                if _is_retryable_mode_error(message):
                    last_error = exc
                    continue
                raise
        if last_error is not None:
            raise last_error
        response, headers = self._post_json(endpoint=endpoint, payload=payload)
        return response, _extract_request_id(headers), attempted_modes

    def _post_json(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, str]]:
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "x-api-key": self.api_key or "",
        }
        try:
            return post_json_with_retry(
                url=endpoint,
                payload=payload,
                headers=headers,
                timeout_seconds=60,
                service_name="nia",
                max_attempts=1,
                base_backoff_seconds=1.0,
                max_backoff_seconds=8.0,
            )
        except HTTPRequestError as exc:
            raise AgentToolError(str(exc)) from exc


def _extract_nia_results(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []

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
            rows: list[dict[str, Any]] = []
            for item in candidate:
                chunk = _coerce_nia_chunk(item)
                if chunk is not None:
                    rows.append(chunk)
            return rows
    return []


def _coerce_nia_chunk(item: Any) -> dict[str, Any] | None:
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return None
        return {"title": None, "url": None, "source": None, "text": text}
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
    return {
        "title": _optional_str(item.get("title") or item.get("name")),
        "url": _optional_str(item.get("url") or item.get("href")),
        "source": _optional_str(item.get("source") or item.get("path")),
        "text": text.strip(),
        "metadata": {
            str(k): v
            for k, v in item.items()
            if k not in {"text", "content", "chunk", "snippet", "body", "summary"}
        },
    }


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _extract_request_id(headers: dict[str, str]) -> str | None:
    for key in ("request-id", "x-request-id"):
        value = headers.get(key)
        if value:
            return value
    return None


def _is_retryable_mode_error(message: str) -> bool:
    return any(
        marker in message
        for marker in (
            "status=422",
            "status=403",
            "union_tag_invalid",
            "union_tag_not_found",
        )
    )


def _run_test_command(workspace: AgentWorkspace, test_command: TestCommand) -> dict[str, Any]:
    cwd = test_command.cwd or "."
    cwd_path = workspace.resolve_read_path(cwd)
    if not cwd_path.exists() or not cwd_path.is_dir():
        raise AgentToolError(f"test_command cwd does not exist: {cwd}")

    started = time.perf_counter()
    timed_out = False
    try:
        completed = subprocess.run(
            test_command.argv,
            cwd=cwd_path,
            capture_output=True,
            text=True,
            timeout=test_command.timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        error = None
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else None
        stderr = exc.stderr if isinstance(exc.stderr, str) else None
        error = "timeout"
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "exists": True,
        "ran": True,
        "argv": test_command.argv,
        "cwd": cwd,
        "timeout_seconds": test_command.timeout_seconds,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "error": error,
        "duration_ms": duration_ms,
    }


def _require_str(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _coerce_str(value: Any, *, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    return value


def _coerce_positive_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("value must be a positive integer")
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
