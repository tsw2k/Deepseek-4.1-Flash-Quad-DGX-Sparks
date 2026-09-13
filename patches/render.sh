#!/usr/bin/env bash
# Render one patch set into the files the launcher bind-mounts over the image's vLLM tree.
#
#   patches/render.sh measured /var/tmp/dsv41-patches          # upstream files fetched at the pin
#   patches/render.sh minimal  /var/tmp/dsv41-patches /var/tmp/dsv41-build/vllm
#
# Patch sets are unified diffs against vLLM 172d9a17. Rendering takes the pinned upstream
# file, applies the diff and checks the result against the set's SHA256SUMS, so a node can
# only ever mount bytes that were reviewed here. A diff that does not apply, or applies to a
# different base, fails before anything reaches a container.
#
#   measured  byte-identical to the tree 0xTank benchmarked (whole-file replacements, which
#             also roll three files back to their dsv41-feat state; see docs/PROVENANCE.md)
#   minimal   only the functional changes, rebased onto 172d9a17; not yet booted anywhere
set -euo pipefail

VLLM_PIN=172d9a17117219952fd3d4cdbb04ecb2a09163f4
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
set_name=${1:?usage: render.sh <measured|minimal> <out-root> [vllm-src-at-pin]}
out_root=${2:?missing output root}
src=${3:-}
[ -d "$here/$set_name" ] || { echo "unknown patch set: $set_name" >&2; exit 2; }
for tool in patch sha256sum curl; do
  command -v "$tool" >/dev/null || { echo "missing $tool (sudo apt-get install -y $tool)" >&2; exit 2; }
done

out="$out_root/$set_name"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

if [ -n "$src" ]; then
  head=$(git -C "$src" rev-parse HEAD)
  [ "$head" = "$VLLM_PIN" ] || { echo "$src is at $head, expected $VLLM_PIN" >&2; exit 3; }
fi

# Pristine upstream files at the pin, checked against UPSTREAM-SHA256SUMS.
while read -r _sum path; do
  mkdir -p "$tmp/$(dirname "$path")"
  if [ -n "$src" ]; then
    cp "$src/$path" "$tmp/$path"
  else
    curl -fsSL --retry 5 "https://raw.githubusercontent.com/vllm-project/vllm/$VLLM_PIN/$path" -o "$tmp/$path"
  fi
done < "$here/UPSTREAM-SHA256SUMS"
(cd "$tmp" && sha256sum --quiet -c "$here/UPSTREAM-SHA256SUMS")

for d in "$here/$set_name"/*.diff; do
  patch --quiet --forward --no-backup-if-mismatch -p1 -d "$tmp" < "$d" \
    || { echo "patch failed: $d" >&2; exit 4; }
done
mkdir -p "$tmp/vllm/models/deepseek_v4/nvidia/ops"
cp "$here/new/compact_o_proj.py" "$tmp/vllm/models/deepseek_v4/nvidia/ops/compact_o_proj.py"
(cd "$tmp" && sha256sum --quiet -c "$here/$set_name/SHA256SUMS")

rm -rf "$out"
mkdir -p "$out"
while read -r _sum path; do
  mkdir -p "$out/$(dirname "$path")"
  cp "$tmp/$path" "$out/$path"
  echo "$path"
done < "$here/$set_name/SHA256SUMS" | sed 's#^vllm/##' > "$tmp/mounts.txt"
cp "$here/$set_name/SHA256SUMS" "$out/SHA256SUMS"
cp "$tmp/mounts.txt" "$out/mounts.txt"
echo "rendered $set_name -> $out ($(wc -l < "$out/mounts.txt") files, hashes verified)"
