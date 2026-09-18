#!/usr/bin/env bash
# Cloud Agent install step for the HackSpain X-Ray analysis repo.
# Installs pinned Python dependencies and reliably materializes the Git LFS
# datasets. A single `git lfs pull` has been observed to exit 0 while leaving
# the large data/transactions.csv (~472 MB) as a pointer, so pull with retries
# and fail loudly if any dataset is still a pointer instead of real data.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f requirements.txt ]; then
  pip install --break-system-packages -r requirements.txt
else
  pip install --break-system-packages duckdb==1.5.5 plotly==7.1.0 narwhals==2.26.0
fi

LFS_FILES="data/invoices.csv data/transactions.csv"

is_pointer() {
  head -c 42 "$1" 2>/dev/null | grep -q "git-lfs.github.com"
}

for attempt in 1 2 3 4 5; do
  git lfs pull || true
  incomplete=0
  for f in $LFS_FILES; do
    if is_pointer "$f"; then
      incomplete=1
      echo "Git LFS dataset still a pointer: $f (attempt $attempt/5)"
    fi
  done
  if [ "$incomplete" -eq 0 ]; then
    echo "All Git LFS datasets materialized."
    break
  fi
  sleep $((attempt * 3))
done

for f in $LFS_FILES; do
  if is_pointer "$f"; then
    echo "ERROR: Git LFS dataset '$f' was not materialized after retries." >&2
    exit 1
  fi
done
