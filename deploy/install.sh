#!/usr/bin/env bash
# Install the motorsports-digest systemd timer, filling in the paths/user for
# this machine. No hand-editing of unit files required.
#
#   SERVICE_USER — account to run the digest as  (default: the sudo caller)
#   SERVICE_DIR  — repo checkout dir             (default: this repo's root)
#
# Override either via env, e.g.
#   SERVICE_USER=digest SERVICE_DIR=/opt/digest sudo -E ./deploy/install.sh
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="${SERVICE_DIR:-$(dirname "$DEPLOY_DIR")}"
SERVICE_USER="${SERVICE_USER:-${SUDO_USER:-$(id -un)}}"
UNIT_DIR=/etc/systemd/system

UNITS=(
    motorsports-digest.service motorsports-digest.timer
    key-expiry-notify.service key-expiry-notify.timer
)
for unit in "${UNITS[@]}"; do
    sed -e "s|__DIR__|$SERVICE_DIR|g" -e "s|__USER__|$SERVICE_USER|g" \
        "$DEPLOY_DIR/$unit" | sudo tee "$UNIT_DIR/$unit" >/dev/null
    echo "installed $UNIT_DIR/$unit"
done

sudo systemctl daemon-reload
sudo systemctl enable --now motorsports-digest.timer
sudo systemctl enable --now key-expiry-notify.timer
echo "enabled timers (user=$SERVICE_USER dir=$SERVICE_DIR)"
echo
echo "One-time: record the key + its expiry so reminders can fire —"
echo "  $SERVICE_DIR/.venv/bin/python -m digest.notify_key_expiry \\"
echo "    --config $SERVICE_DIR/config.toml --state $SERVICE_DIR/key-expiry.state \\"
echo "    --init --expires YYYY-MM-DD"
