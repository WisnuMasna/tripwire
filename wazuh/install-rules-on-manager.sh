#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Tripwire — install the Cowrie rules into the Wazuh MANAGER (run on TheHive-5).
#
#   sudo bash install-rules-on-manager.sh
#
# The manager runs in Docker (wazuh-lab). This copies the rules into the
# container's /var/ossec/etc/rules/ and restarts the Wazuh service so they load.
# Override the container name if `docker ps` shows a different one:
#   WAZUH_MANAGER_CONTAINER=wazuh-lab-wazuh.manager-1 sudo -E bash install-rules-on-manager.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

RULES_SRC="rules/cowrie_rules.xml"
CONTAINER="${WAZUH_MANAGER_CONTAINER:-}"

if [ -z "$CONTAINER" ]; then
  # Auto-detect the manager container by image name.
  CONTAINER="$(docker ps --filter "ancestor=wazuh/wazuh-manager" --format '{{.Names}}' | head -n1)"
  if [ -z "$CONTAINER" ]; then
    CONTAINER="$(docker ps --format '{{.Names}}' | grep -i 'wazuh.*manager' | head -n1)"
  fi
fi
[ -n "$CONTAINER" ] || { echo "! Could not find the Wazuh manager container. Set WAZUH_MANAGER_CONTAINER."; exit 1; }
echo "[*] Manager container: $CONTAINER"

echo "[*] Copying rules in..."
docker cp "$RULES_SRC" "$CONTAINER:/var/ossec/etc/rules/cowrie_rules.xml"
docker exec "$CONTAINER" chown wazuh:wazuh /var/ossec/etc/rules/cowrie_rules.xml
docker exec "$CONTAINER" chmod 660 /var/ossec/etc/rules/cowrie_rules.xml

echo "[*] Restarting the manager to load the rules..."
docker exec "$CONTAINER" /var/ossec/bin/wazuh-control restart

echo
echo "[+] Done. Test the rules against a sample Cowrie event with:"
echo "    docker exec -i $CONTAINER /var/ossec/bin/wazuh-logtest <<'EOF'"
echo '    {"eventid":"cowrie.login.success","username":"root","password":"123456","src_ip":"1.2.3.4","session":"a1b2","message":"login attempt [root/123456] succeeded"}'
echo "    EOF"
echo "  You should see it match rule id 100103 (authentication_success)."
