#!/usr/bin/env bash
# Fan the checkpoint out from the first node to the other three over rail B, then verify it
# on every receiving node against the manifest.
#
#   bash weights/sync.sh ./cluster.env           # from the operator host, after fetch.sh
#
# The Engram shards and engram-local.json are excluded: they are different on every rank
# and are cut in place by engram-slice.py.
set -euo pipefail
# shellcheck source=/dev/null
source "${1:?usage: sync.sh cluster.env}"
: "${MODEL_DIR:?}" "${NODES:?}" "${RAIL_B_IPS:?}" "${REPO_DIR:?}"

case "$MODEL_DIR" in /var/tmp/*) ;; *) echo "MODEL_DIR must live under /var/tmp (rsyncd module root)" >&2; exit 2;; esac
rel=${MODEL_DIR#/var/tmp/}
src_ip=${RAIL_B_IPS[0]}

for i in "${!NODES[@]}"; do
  [ "$i" -eq 0 ] && continue
  n=${NODES[$i]}
  echo "=== ${n}: rsync://$src_ip/models/$rel/"
  # --partial: an interrupted multi-hundred-GiB copy resumes instead of restarting.
  ssh "$n" "mkdir -p '$MODEL_DIR' && rsync -a --partial --info=progress2 \
      --exclude 'model-00047-of-00048.safetensors' --exclude 'model-00048-of-00048.safetensors' \
      --exclude 'engram-local.json' --exclude '.cache/' \
      rsync://$src_ip/models/$rel/ '$MODEL_DIR/'" 2>&1 | tr '\r' '\n' | tail -2
done

for i in "${!NODES[@]}"; do
  [ "$i" -eq 0 ] && continue
  n=${NODES[$i]}
  echo "=== ${n}: verify"
  ssh "$n" "python3 '$REPO_DIR/weights/verify.py' '$MODEL_DIR'"
done
