#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${1:-"${ROOT_DIR}/build/huggingface-space"}"
TEMPLATE_DIR="${ROOT_DIR}/deploy/huggingface_space"

if [[ -e "${OUT_DIR}" ]]; then
  echo "Refusing to overwrite existing package: ${OUT_DIR}" >&2
  echo "Choose a new output path, for example:" >&2
  echo "  bash deploy/huggingface_space/build_package.sh build/huggingface-space-$(date +%Y%m%d-%H%M%S)" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

rsync -a \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  "${ROOT_DIR}/app" \
  "${ROOT_DIR}/core" \
  "${ROOT_DIR}/SampleDataSets" \
  "${OUT_DIR}/"

cp "${ROOT_DIR}/app_v2.py" "${OUT_DIR}/app_v2.py"
cp "${TEMPLATE_DIR}/Dockerfile" "${OUT_DIR}/Dockerfile"
cp "${TEMPLATE_DIR}/README.md" "${OUT_DIR}/README.md"
cp "${TEMPLATE_DIR}/requirements.txt" "${OUT_DIR}/requirements.txt"
cp "${TEMPLATE_DIR}/wsgi.py" "${OUT_DIR}/wsgi.py"
cp "${TEMPLATE_DIR}/.gitignore" "${OUT_DIR}/.gitignore"
cp "${TEMPLATE_DIR}/.gitattributes" "${OUT_DIR}/.gitattributes"

echo "Created clean Hugging Face Space package:"
echo "  ${OUT_DIR}"
