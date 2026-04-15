"""Maia single-file bundle archive helpers."""

from __future__ import annotations

from pathlib import Path
import tempfile
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from maia.backup_manifest import load_backup_manifest, write_backup_manifest

__all__ = [
    "BUNDLE_EXTENSION",
    "BUNDLE_MANIFEST_FILENAME",
    "BUNDLE_REGISTRY_FILENAME",
    "inspect_bundle_archive",
    "is_bundle_archive_path",
    "load_bundle_archive",
    "write_bundle_archive",
]

BUNDLE_EXTENSION = ".maia"
BUNDLE_MANIFEST_FILENAME = "manifest.json"
BUNDLE_REGISTRY_FILENAME = "registry.json"


def is_bundle_archive_path(path: Path | str) -> bool:
    """Return whether the given path should be treated as a Maia bundle archive."""

    return Path(path).suffix == BUNDLE_EXTENSION


def write_bundle_archive(
    path: Path | str,
    storage,
    registry,
    *,
    label: str | None = None,
    description: str | None = None,
    source_registry_path: Path | str | None = None,
    team_metadata=None,
) -> Path:
    """Write a Maia bundle archive containing manifest + registry snapshot."""

    bundle_path = Path(path)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="maia-export-") as tmpdir:
        tmpdir_path = Path(tmpdir)
        registry_path = tmpdir_path / BUNDLE_REGISTRY_FILENAME
        storage.save(registry_path, registry, portable=True)
        manifest_path = write_backup_manifest(
            registry_path,
            agent_count=len(registry.list()),
            label=label or bundle_path.stem,
            description=description,
            source_registry_path=source_registry_path,
            team_metadata=team_metadata,
        )

        with ZipFile(bundle_path, mode="w", compression=ZIP_DEFLATED) as archive:
            archive.write(registry_path, arcname=BUNDLE_REGISTRY_FILENAME)
            archive.write(manifest_path, arcname=BUNDLE_MANIFEST_FILENAME)

    return bundle_path


def inspect_bundle_archive(path: Path | str, storage):
    """Inspect a Maia bundle archive and return manifest + registry details."""

    bundle_path = Path(path)
    try:
        with ZipFile(bundle_path, mode="r") as archive:
            archive_names = archive.namelist()
            if archive_names.count(BUNDLE_MANIFEST_FILENAME) != 1:
                raise ValueError(
                    f"Invalid Maia bundle archive {bundle_path}: must contain exactly one {BUNDLE_MANIFEST_FILENAME!r}"
                )
            if archive_names.count(BUNDLE_REGISTRY_FILENAME) != 1:
                raise ValueError(
                    f"Invalid Maia bundle archive {bundle_path}: must contain exactly one {BUNDLE_REGISTRY_FILENAME!r}"
                )
            if set(archive_names) != {BUNDLE_MANIFEST_FILENAME, BUNDLE_REGISTRY_FILENAME}:
                raise ValueError(
                    f"Invalid Maia bundle archive {bundle_path}: "
                    "v1 bundles may only contain 'manifest.json' and 'registry.json'"
                )

            with tempfile.TemporaryDirectory(prefix="maia-import-") as tmpdir:
                tmpdir_path = Path(tmpdir)
                archive.extract(BUNDLE_MANIFEST_FILENAME, path=tmpdir_path)
                manifest_path = tmpdir_path / BUNDLE_MANIFEST_FILENAME
                manifest = load_backup_manifest(manifest_path)
                if manifest.registry_file != BUNDLE_REGISTRY_FILENAME:
                    raise ValueError(
                        f"Invalid Maia bundle archive {bundle_path}: "
                        f"manifest registry_file must be {BUNDLE_REGISTRY_FILENAME!r}"
                    )
                if manifest.registry_file not in archive_names:
                    raise ValueError(
                        f"Invalid Maia bundle archive {bundle_path}: "
                        f"missing {manifest.registry_file!r} referenced by manifest"
                    )

                archive.extract(manifest.registry_file, path=tmpdir_path)
                registry_path = tmpdir_path / manifest.registry_file
                registry = storage.load(registry_path)
                return manifest, registry, bundle_path, Path(manifest.registry_file)
    except BadZipFile as exc:
        raise ValueError(f"Invalid Maia bundle archive {bundle_path}: not a readable zip archive") from exc


def load_bundle_archive(path: Path | str, storage):
    """Load a Maia bundle archive and return (registry, source_path, registry_path)."""

    manifest, registry, bundle_path, registry_path = inspect_bundle_archive(path, storage)
    del manifest
    return registry, bundle_path, registry_path
