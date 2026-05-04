# Hugging Face Spaces Deployment

This folder contains the files used to build a clean QuantDSF Docker Space package.

## Build the package

From the repository root:

```bash
bash deploy/huggingface_space/build_package.sh
```

The package is written to:

```text
build/huggingface-space
```

That folder is intended to become the root of the Hugging Face Space repository.

ZIP example datasets are tracked with Git LFS because Hugging Face rejects
regular Git files larger than 10 MiB.

## Hugging Face settings

Create a new Space with:

- SDK: Docker
- App port: 7860
- Hardware: CPU Basic

The Docker command is already defined in the package Dockerfile:

```bash
gunicorn wsgi:server --bind 0.0.0.0:7860 --workers 1 --threads 4 --timeout 300
```

## Included content

The package intentionally includes only:

- `app/`
- `core/`
- `SampleDataSets/`
- `app_v2.py`
- Docker/WSGI/requirements files
- Hugging Face Space `README.md`

It intentionally excludes manuscript files, virtual environments, browser profiles, debug folders, logs, and old development archives.
