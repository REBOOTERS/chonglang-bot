#!/usr/bin/env bash

set -euo pipefail

source_dir="${1:-res}"
output_dir="${2:-$source_dir}"

if ! command -v dwebp >/dev/null 2>&1; then
  echo "Error: dwebp is required. Install it with: brew install webp" >&2
  exit 1
fi

if [[ ! -d "$source_dir" ]]; then
  echo "Error: source directory does not exist: $source_dir" >&2
  exit 1
fi

converted=0
deleted=0
skipped=0

while IFS= read -r -d '' source_file; do
  relative_path="${source_file#"$source_dir"/}"
  output_file="$output_dir/${relative_path%.webp}.png"

  if [[ -e "$output_file" ]]; then
    printf 'Skipped (exists): %s\n' "$output_file"
    ((skipped += 1))
    continue
  fi

  mkdir -p "$(dirname "$output_file")"
  dwebp "$source_file" -o "$output_file" >/dev/null
  rm "$source_file"
  printf 'Converted: %s -> %s\n' "$source_file" "$output_file"
  ((converted += 1))
  ((deleted += 1))
done < <(find "$source_dir" -type f -iname '*.webp' -print0)

printf 'Complete: %d converted, %d deleted, %d skipped. Output: %s\n' "$converted" "$deleted" "$skipped" "$output_dir"