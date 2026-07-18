import pytest

from blackterm_recon.platform_sdk import ModuleManifest, validate_manifest


def test_valid_manifest():
    manifest = ModuleManifest(
        key="demo",
        name="Demo",
        version="1.0",
        description="Demo module",
        category="TEST",
        entrypoint="demo:create",
    )
    validate_manifest(manifest)


def test_invalid_manifest_key():
    manifest = ModuleManifest(
        key="bad key",
        name="Demo",
        version="1.0",
        description="Demo module",
        category="TEST",
        entrypoint="demo:create",
    )
    with pytest.raises(ValueError):
        validate_manifest(manifest)
