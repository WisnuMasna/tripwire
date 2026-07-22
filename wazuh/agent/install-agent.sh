#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Tripwire — install the Wazuh agent on the HONEYPOT VPS (run as root).
#
#   MANAGER_IP=100.x.y.z sudo -E bash install-agent.sh
#
# MANAGER_IP = the Wazuh manager TAILSCALE IP (from: tailscale ip -4) on
# TheHive-5). Tailscale must already be up on BOTH boxes and able to ping each
# other before you run this (see ../README.md step 1).
#
# Pins the agent to 4.9.2 to match the wazuh-lab manager.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
: "${MANAGER_IP:?Set MANAGER_IP to the manager Tailscale IP, e.g. MANAGER_IP=100.x.y.z}"
COWRIE_LOG="/opt/tripwire/honeypot/var/log/cowrie/cowrie.json"

echo "[1/4] Sanity check: can we reach the manager over Tailscale?"
if ! ping -c1 -W3 "$MANAGER_IP" >/dev/null 2>&1; then
  echo "  ! Cannot ping $MANAGER_IP. Is Tailscale up on both hosts? (tailscale status)"
  echo "    Continuing anyway — enrollment will fail if the manager is unreachable."
fi

echo "[2/4] Adding the Wazuh apt repo..."
apt-get install -y curl gnupg apt-transport-https
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | \
  gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
chmod 644 /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
  > /etc/apt/sources.list.d/wazuh.list
apt-get update

echo "[3/4] Installing wazuh-agent 4.9.2, pointed at manager $MANAGER_IP..."
WAZUH_MANAGER="$MANAGER_IP" WAZUH_AGENT_NAME="tripwire-honeypot" \
  apt-get install -y wazuh-agent=4.9.2-1

echo "[3b/4] Adding the Cowrie JSON log to what the agent ships..."
if ! grep -q "cowrie.json" /var/ossec/etc/ossec.conf; then
  sed -i "s#</ossec_config>#  <localfile>\n    <log_format>json</log_format>\n    <location>${COWRIE_LOG}</location>\n  </localfile>\n</ossec_config>#" /var/ossec/etc/ossec.conf
fi

echo "[4/4] Enabling + starting the agent..."
systemctl daemon-reload
systemctl enable wazuh-agent
systemctl restart wazuh-agent

echo
echo "── DONE ─────────────────────────────────────────────────────────────────"
echo "Agent installed and started. Verify enrollment:"
echo "  sudo tail -f /var/ossec/logs/ossec.log   # look for: Connected to the server"
echo "On the manager (TheHive-5), the agent tripwire-honeypot should appear:"
echo "  docker exec <manager-container> /var/ossec/bin/manage_agents -l"
echo "─────────────────────────────────────────────────────────────────────────"
