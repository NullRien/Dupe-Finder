# Dupe-Finder

A small command line utility that locates duplicate files by comparing their
content hashes. The tool can optionally remove duplicates and includes a helper
command to download a sample image dataset (with seeded duplicates) for quick
experimentation.

## Features

- Recursively scans folders and groups files that share the same MD5 checksum.
- Supports configurable buffer sizes for hashing very large files efficiently.
- Interactive or automatic deletion of duplicate files.
- One-command download of a small public image dataset that already contains a
  few duplicate images for testing the workflow.

## Requirements

Python 3.9 or newer is recommended. All dependencies are provided by the Python
standard library.

## Usage

Scan a folder and review the duplicate report:

```bash
python main.py /path/to/folder
```

Delete duplicates automatically as part of the scan:

```bash
python main.py /path/to/folder --delete
```

Adjust the read buffer size used when hashing files (default is 64 KiB):

```bash
python main.py /path/to/folder --buffer-size 131072
```

## Download a Sample Dataset

To fetch a ready-made dataset of insect images (sourced from the PyTorch
`hymenoptera_data` tutorial) and seed it with a few duplicate files, run:

```bash
python main.py --download-sample-data data
```

The dataset will be extracted into the `data/hymenoptera_data` directory. When a
scan path is not provided, the freshly downloaded dataset is scanned
automatically. Re-run with `--delete` to immediately clean up the duplicates.

If you need to re-download the dataset or you prefer not to create extra
duplicate files while downloading, the following options are available:

- `--force-download` – download the archive again even if it already exists.
- `--skip-duplicate-seeding` – skip the step that creates duplicate test files.

## Planned Improvements

- Additional checksum algorithms (SHA-256, BLAKE3) for environments that forbid
  MD5.
- Optional HTML report output.
