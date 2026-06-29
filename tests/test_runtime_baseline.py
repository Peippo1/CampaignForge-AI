from utils.runtime_baseline import OPTIONAL_DEPENDENCIES, SUPPORTED_PYTHON_VERSIONS, build_runtime_baseline


def test_supported_python_versions_are_explicit():
    assert SUPPORTED_PYTHON_VERSIONS == {(3, 11), (3, 12)}


def test_runtime_baseline_allows_current_repo_versions():
    baseline = build_runtime_baseline(version_info=(3, 11))
    assert baseline.supported is True

    baseline = build_runtime_baseline(version_info=(3, 12))
    assert baseline.supported is True


def test_runtime_baseline_marks_unsupported_version():
    baseline = build_runtime_baseline(version_info=(3, 10))
    assert baseline.supported is False


def test_optional_dependency_inventory_is_documented():
    assert "pymysql" in OPTIONAL_DEPENDENCIES
    assert "gspread" in OPTIONAL_DEPENDENCIES
