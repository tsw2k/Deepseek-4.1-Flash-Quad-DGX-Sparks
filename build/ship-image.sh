#!/usr/bin/env bash
# Copy the image built on the first node to every other node over rail B, and prove that all
# four run the same image ID.
#
#   bash build/ship-image.sh ./cluster.env        # from the operator host, after build-image.sh
#   SRC_RANK=1 bash build/ship-image.sh ./cluster.env   # image was built on spark-02
#
# The archive goes to /var/tmp/image-archive on the build node (rank SRC_RANK, default 0), which the rsync daemon there
# serves on rail B (module "models" = /var/tmp). Workers pull it over rail B, so the copy
# never touches rail A or the management network.
set -euo pipefail
# shellcheck source=/dev/null
source "${1:?usage: ship-image.sh cluster.env}"
: "${IMAGE:?}" "${NODES:?}" "${RAIL_B_IPS:?}"

src=${SRC_RANK:-0}
src_node=${NODES[$src]}
src_ip=${RAIL_B_IPS[$src]}
file="image-archive/$(echo "$IMAGE" | tr ':/' '__').tar"

want=$(ssh "$src_node" "docker image inspect '$IMAGE' --format '{{.Id}}'")
echo "source $src_node $IMAGE $want"
ssh "$src_node" "mkdir -p /var/tmp/image-archive && docker save '$IMAGE' -o '/var/tmp/$file.partial' && mv '/var/tmp/$file.partial' '/var/tmp/$file' && ls -lh '/var/tmp/$file'"

for i in "${!NODES[@]}"; do
  [ "$i" -eq "$src" ] && continue
  n=${NODES[$i]}
  echo "=== $n"
  ssh "$n" "mkdir -p /var/tmp/image-archive && rsync -a --partial rsync://$src_ip/models/$file /var/tmp/$file && docker load -i /var/tmp/$file >/dev/null"
done

bad=0
for n in "${NODES[@]}"; do
  got=$(ssh "$n" "docker image inspect '$IMAGE' --format '{{.Id}}' 2>/dev/null" || true)
  if [ "$got" = "$want" ]; then echo "$n ok"; else echo "$n MISMATCH ($got)"; bad=1; fi
done
exit $bad
