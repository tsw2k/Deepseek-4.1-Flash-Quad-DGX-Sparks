#!/usr/bin/env bash
# Download the checkpoint once, on the first node, without the two Engram shards.
#
#   bash weights/fetch.sh ./cluster.env          # on spark-01
#
# Shards 1-46 (286.1 GiB) are needed in full on every rank. Shards 47-48 (189.1 GiB) hold the
# two Engram tables, of which each TP4 rank reads only its own quarter: those are cut per node
# by engram-slice.py instead, so no node ever stores all 189 GiB.
#
# A download this size fills the page cache, and on GB10 the page cache is the GPU's memory.
# Run it in the maintenance window with nothing serving, and keep a flusher running.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=/dev/null
source "${1:?usage: fetch.sh cluster.env}"
: "${MODEL_DIR:?}" "${MODEL_REVISION:?}"

# pip --user installs land in ~/.local/bin, which a non-interactive ssh session does not have
export PATH="$HOME/.local/bin:$PATH"
command -v hf >/dev/null ||{ echo "hf CLI missing: python3 -m pip install --user -U huggingface_hub" >&2; exit 2; }

need_gib=300
free_gib=$(df --output=avail -BG "$(dirname "$MODEL_DIR")" | tail -1 | tr -dc 0-9)
[ "$free_gib" -ge "$need_gib" ] || { echo "only ${free_gib} GiB free under $(dirname "$MODEL_DIR"); need ${need_gib}" >&2; exit 3; }

mkdir -p "$MODEL_DIR"
# One glob, not two patterns: hf 1.x reads a second value after --exclude as a positional
# filename, warns "Ignoring --exclude since filenames have been explicitly set", and then
# downloads exactly the Engram shard this was meant to skip.
HF_HUB_ENABLE_HF_TRANSFER=0 hf download deepseek-ai/DeepSeek-V4.1-Flash \
  --revision "$MODEL_REVISION" \
  --local-dir "$MODEL_DIR" \
  --exclude 'model-0004[78]-of-00048.safetensors' \
  --max-workers 8

python3 "$here/verify.py" "$MODEL_DIR"
