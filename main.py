"""Command line utility for finding and removing duplicate files."""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

DEFAULT_BUFFER_SIZE = 64 * 1024
DATASET_URL = "https://download.pytorch.org/tutorial/hymenoptera_data.zip"
DATASET_ARCHIVE_NAME = "hymenoptera_data.zip"
DATASET_ROOT_NAME = "hymenoptera_data"
IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpg", ".jpeg", ".png", ".tiff"}


@dataclass(frozen=True)
class DuplicateGroup:
    """Container describing duplicate files that share the same checksum."""

    checksum: str
    size: int
    files: tuple[Path, ...]

    @property
    def files_to_remove(self) -> tuple[Path, ...]:
        """Return all but the first file which is used as the canonical copy."""

        return self.files[1:]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan a folder for duplicate files, optionally delete them, and "
            "download a ready-made image dataset for testing."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Path to the folder that should be scanned for duplicate files.",
    )
    parser.add_argument(
        "-b",
        "--buffer-size",
        type=int,
        default=DEFAULT_BUFFER_SIZE,
        help=(
            "Number of bytes to read per chunk when hashing files. "
            "Higher values may improve throughput for large files."
        ),
    )
    parser.add_argument(
        "-d",
        "--delete",
        action="store_true",
        help="Remove duplicate files automatically without asking for confirmation.",
    )
    parser.add_argument(
        "--download-sample-data",
        type=Path,
        metavar="DESTINATION",
        help=(
            "Download a small public image dataset that already contains "
            "artificial duplicates for testing. The dataset will be stored in "
            "DESTINATION and scanned if no PATH is supplied."
        ),
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Download the sample dataset even if it already exists locally.",
    )
    parser.add_argument(
        "--skip-duplicate-seeding",
        action="store_true",
        help=(
            "Do not create additional duplicate files when downloading the sample "
            "dataset."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.buffer_size <= 0:
        print("Error: buffer size must be a positive integer.", file=sys.stderr)
        return 1

    scan_path = args.path

    if args.download_sample_data:
        dataset_path = download_sample_dataset(
            args.download_sample_data,
            create_duplicates=not args.skip_duplicate_seeding,
            force=args.force_download,
        )
        print(f"Sample dataset available at: {dataset_path}")
        if scan_path is None:
            scan_path = dataset_path

    if scan_path is None:
        scan_input = input("Enter the path of the folder to check: ").strip()
        if not scan_input:
            print("Error: a folder path is required to perform the scan.")
            return 1
        scan_path = Path(scan_input)

    scan_path = scan_path.expanduser().resolve()

    if not scan_path.exists():
        print(f"Error: the path '{scan_path}' does not exist.")
        return 1
    if not scan_path.is_dir():
        print(f"Error: the path '{scan_path}' is not a directory.")
        return 1

    print(f"Scanning '{scan_path}' for duplicate files...")
    duplicate_groups = find_duplicates(scan_path, args.buffer_size)

    if not duplicate_groups:
        print("No duplicate files were found.")
        return 0

    print_duplicate_report(duplicate_groups)

    if args.delete:
        removed, reclaimed = delete_duplicates(duplicate_groups)
        print(
            f"Removed {removed} duplicate file(s) and reclaimed {format_size(reclaimed)} of disk space."
        )
        return 0

    if ask_yes_no("Delete the duplicates listed above? [y/N]: "):
        removed, reclaimed = delete_duplicates(duplicate_groups)
        print(
            f"Removed {removed} duplicate file(s) and reclaimed {format_size(reclaimed)} of disk space."
        )
    else:
        print("Duplicates were left untouched.")

    return 0


def find_duplicates(directory: Path, buffer_size: int) -> list[DuplicateGroup]:
    """Return groups of files that have identical content."""

    candidates: dict[int, list[Path]] = defaultdict(list)

    for file_path in iter_regular_files(directory):
        try:
            size = file_path.stat().st_size
        except OSError as exc:  # pragma: no cover - filesystem dependent
            print(f"Warning: failed to stat '{file_path}': {exc}", file=sys.stderr)
            continue
        candidates[size].append(file_path)

    duplicate_groups: list[DuplicateGroup] = []

    for size, files in candidates.items():
        if len(files) < 2:
            continue

        by_checksum: dict[str, list[Path]] = defaultdict(list)
        for file_path in files:
            try:
                checksum = hash_file(file_path, buffer_size)
            except OSError as exc:  # pragma: no cover - filesystem dependent
                print(f"Warning: failed to hash '{file_path}': {exc}", file=sys.stderr)
                continue
            by_checksum[checksum].append(file_path)

        for checksum, matching_files in by_checksum.items():
            if len(matching_files) > 1:
                ordered_files = tuple(sorted(matching_files))
                duplicate_groups.append(DuplicateGroup(checksum, size, ordered_files))

    duplicate_groups.sort(key=lambda group: (group.size, group.checksum))
    return duplicate_groups


def iter_regular_files(directory: Path) -> Iterator[Path]:
    """Yield all regular files within *directory* (recursively)."""

    for path in directory.rglob("*"):
        if path.is_file():
            yield path


def hash_file(file_path: Path, buffer_size: int) -> str:
    """Calculate and return the MD5 checksum of *file_path*."""

    digest = hashlib.md5()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(buffer_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def print_duplicate_report(duplicate_groups: Iterable[DuplicateGroup]) -> None:
    """Pretty-print the discovered duplicate groups."""

    print()
    print("Duplicate files detected:")

    for index, group in enumerate(duplicate_groups, start=1):
        print(
            f"\nGroup {index}: {len(group.files)} file(s), size {format_size(group.size)}, checksum {group.checksum}"
        )
        for file_path in group.files:
            print(f"  - {file_path}")


def delete_duplicates(groups: Iterable[DuplicateGroup]) -> tuple[int, int]:
    """Delete duplicate files, keeping one canonical copy from each group."""

    removed_files = 0
    reclaimed_bytes = 0

    for group in groups:
        for duplicate_path in group.files_to_remove:
            try:
                size = duplicate_path.stat().st_size
            except OSError:  # pragma: no cover - filesystem dependent
                size = 0
            try:
                duplicate_path.unlink()
            except OSError as exc:  # pragma: no cover - filesystem dependent
                print(f"Warning: could not delete '{duplicate_path}': {exc}", file=sys.stderr)
                continue

            removed_files += 1
            reclaimed_bytes += size

    return removed_files, reclaimed_bytes


def download_sample_dataset(
    destination: Path, *, create_duplicates: bool, force: bool
) -> Path:
    """Download and extract a small image dataset for experimenting."""

    destination = destination.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    dataset_root = destination / DATASET_ROOT_NAME

    should_download = force or not dataset_root.exists()

    if should_download:
        archive_path = destination / DATASET_ARCHIVE_NAME
        if archive_path.exists():
            archive_path.unlink()

        print(f"Downloading sample dataset from {DATASET_URL}...")
        with urllib.request.urlopen(DATASET_URL) as response, open(archive_path, "wb") as file:
            shutil.copyfileobj(response, file)

        print(f"Extracting archive to '{destination}'...")
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(destination)

        archive_path.unlink()
    else:
        print(f"Dataset already present at '{dataset_root}'. Use --force-download to refresh it.")

    created_duplicates: list[Path] = []
    if create_duplicates:
        created_duplicates = seed_duplicate_images(dataset_root)

    if created_duplicates:
        print(f"Seeded {len(created_duplicates)} artificial duplicate image(s) for testing.")

    return dataset_root


def seed_duplicate_images(dataset_root: Path, duplicates_per_directory: int = 2) -> list[Path]:
    """Create a handful of duplicate image files within *dataset_root*."""

    if not dataset_root.exists():
        print(
            "Warning: dataset root does not exist, cannot seed duplicate images.",
            file=sys.stderr,
        )
        return []

    created: list[Path] = []

    for directory in sorted(path for path in dataset_root.rglob("*") if path.is_dir()):
        image_files = [file for file in sorted(directory.iterdir()) if _looks_like_image(file)]
        if not image_files:
            continue

        for index, source in enumerate(image_files[:duplicates_per_directory]):
            duplicate_path = directory / f"{source.stem}_duplicate_{index}{source.suffix}"
            if duplicate_path.exists():
                continue
            shutil.copy2(source, duplicate_path)
            created.append(duplicate_path)

    return created


def _looks_like_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def ask_yes_no(prompt: str) -> bool:
    """Prompt the user with a yes/no question and return ``True`` for yes."""
    while True:
        try:
            response = input(prompt)
        except EOFError:  # pragma: no cover - interactive behaviour
            return False

        response = response.strip().lower()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no", ""}:
            return False

        print("Please respond with 'y' or 'n'.")


def format_size(num_bytes: int) -> str:
    """Return a human friendly representation of ``num_bytes``."""

    step_unit = 1024.0
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < step_unit or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= step_unit
    return f"{size:.1f} PB"


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
