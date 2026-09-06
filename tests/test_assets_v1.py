import pytest

from backend.assets import AssetValidationError, MAX_ASSET_BYTES, validate_asset


def test_brand_asset_rules_accept_document_and_image_types():
    validate_asset(content_type="application/pdf", size_bytes=MAX_ASSET_BYTES)
    validate_asset(content_type="image/png", size_bytes=1)


def test_brand_asset_rules_reject_unsafe_type_and_oversize_file():
    with pytest.raises(AssetValidationError, match="Unsupported"):
        validate_asset(content_type="text/html", size_bytes=100)
    with pytest.raises(AssetValidationError, match="10 MB"):
        validate_asset(content_type="image/jpeg", size_bytes=MAX_ASSET_BYTES + 1)
