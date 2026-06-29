from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import sys


SUPPORTED_PYTHON_VERSIONS = {(3, 11), (3, 12)}

REQUIRED_DEPENDENCIES = (
    "fastapi",
    "pydantic",
    "pandas",
    "streamlit",
)

OPTIONAL_DEPENDENCIES = {
    "pymysql": "CRM-backed dashboard data access",
    "opentelemetry": "FastAPI tracing export",
    "gspread": "Google Sheets sync",
}


@dataclass(frozen=True)
class RuntimeBaseline:
    python_version: tuple[int, int]
    supported: bool
    missing_required: tuple[str, ...]
    missing_optional: tuple[str, ...]


def _is_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def build_runtime_baseline(
    version_info: tuple[int, int] | None = None,
) -> RuntimeBaseline:
    current = version_info or (sys.version_info.major, sys.version_info.minor)
    missing_required = tuple(name for name in REQUIRED_DEPENDENCIES if not _is_installed(name))
    missing_optional = tuple(name for name in OPTIONAL_DEPENDENCIES if not _is_installed(name))
    return RuntimeBaseline(
        python_version=current,
        supported=current in SUPPORTED_PYTHON_VERSIONS,
        missing_required=missing_required,
        missing_optional=missing_optional,
    )


def validate_runtime() -> None:
    baseline = build_runtime_baseline()
    if not baseline.supported:
        supported = ", ".join(f"{major}.{minor}" for major, minor in sorted(SUPPORTED_PYTHON_VERSIONS))
        raise RuntimeError(
            f"Unsupported Python runtime {baseline.python_version[0]}.{baseline.python_version[1]}. "
            f"Supported versions: {supported}."
        )
    if baseline.missing_required:
        raise RuntimeError(
            "Missing required dependencies: " + ", ".join(sorted(baseline.missing_required))
        )


if __name__ == "__main__":
    validate_runtime()
