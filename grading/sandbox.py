"""Skeleton E2B sandbox grader."""

from __future__ import annotations

from grading.types import SandboxResult


class SandboxGrader:
    def grade(
        self,
        *,
        executable: bool,
        code: str,
        library: str,
        version: str,
    ) -> SandboxResult:
        if not executable:
            return SandboxResult(
                executed=False,
                exit_code=None,
                stdout=None,
                stderr=None,
                error_type=None,
                status="skipped",
            )

        # This is intentionally a scaffold. The E2B execution path will install the
        # target library version in an isolated sandbox and execute the generated code.
        return SandboxResult(
            executed=False,
            exit_code=None,
            stdout=None,
            stderr=None,
            error_type="NotImplemented",
            status="pending",
        )
