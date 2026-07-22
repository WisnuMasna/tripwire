#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Tripwire honeypot — MANUAL bootstrap. Run this ON the Oracle VM, as root,
# when you created a bare instance (no cloud-init). Equivalent to
# cloud-init.oracle.yaml.
#
#   1. SSH in on port 22:   ssh -i ~/.ssh/tripwire ubuntu@<public-ip>
#   2. Create this file:    nano bootstrap-manual.sh   (paste, Ctrl+O, Ctrl+X)
#   3. Run it:              sudo bash bootstrap-manual.sh
#
# ⚠  KEEP your current SSH session OPEN after it runs. It moves admin SSH to
#    64295; open a SECOND terminal and confirm `ssh -p 64295 ubuntu@<ip>` works
#    BEFORE closing this one, so you can't lock yourself out.
#
# ORDER MATTERS: the firewall (and iptables-persistent) is set up BEFORE Docker,
# so installing iptables-persistent can't wipe Docker's forwarding rules — the
# bug that otherwise leaves published ports unreachable until `docker restart`.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "[1/6] Opening host firewall for 22 / 23 / 64295 (Oracle image default-DROPs INPUT)..."
apt-get update -y
apt-get install -y iptables-persistent
iptables -I INPUT -p tcp --dport 64295 -j ACCEPT
iptables -I INPUT -p tcp --dport 22 -j ACCEPT
iptables -I INPUT -p tcp --dport 23 -j ACCEPT
netfilter-persistent save

echo "[2/6] Installing Docker (after the firewall, so its forwarding rules survive)..."
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

echo "[3/6] Writing Cowrie config..."
mkdir -p /opt/tripwire/honeypot
cat > /opt/tripwire/honeypot/.env <<'EOF'
SSH_LISTEN_PORT=22
TELNET_LISTEN_PORT=23
EOF
cat > /opt/tripwire/honeypot/docker-compose.yml <<'EOF'
name: tripwire-honeypot
services:
  cowrie:
    image: cowrie/cowrie:latest
    container_name: tripwire-cowrie
    restart: unless-stopped
    ports:
      - "${SSH_LISTEN_PORT:-2222}:2222"
      - "${TELNET_LISTEN_PORT:-2223}:2223"
    volumes:
      - ./cowrie.cfg:/cowrie/cowrie-git/etc/cowrie.cfg:ro
      - ./userdb.txt:/cowrie/cowrie-git/etc/userdb.txt:ro
      - ./var:/cowrie/cowrie-git/var
    networks: [honeypot-net]
networks:
  honeypot-net:
    driver: bridge
EOF
cat > /opt/tripwire/honeypot/cowrie.cfg <<'EOF'
[honeypot]
hostname = svr01
log_path = var/log/cowrie
download_path = var/lib/cowrie/downloads
ttylog = true
ttylog_path = var/lib/cowrie/tty
auth_class = UserDB
[ssh]
enabled = true
listen_endpoints = tcp:2222:interface=0.0.0.0
version = SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5
[telnet]
enabled = true
listen_endpoints = tcp:2223:interface=0.0.0.0
[output_jsonlog]
enabled = true
logfile = var/log/cowrie/cowrie.json
epoch_timestamp = true
EOF
cat > /opt/tripwire/honeypot/userdb.txt <<'EOF'
root:x:*
admin:x:*
ubuntu:x:*
user:x:*
test:x:*
oracle:x:*
pi:x:*
EOF

echo "[4/6] Moving real sshd off 22 -> 64295 (so Cowrie can own 22)..."
sed -i 's/^#\?Port .*/Port 64295/' /etc/ssh/sshd_config
mkdir -p /etc/systemd/system/ssh.socket.d
printf '[Socket]\nListenStream=\nListenStream=64295\n' > /etc/systemd/system/ssh.socket.d/override.conf
systemctl daemon-reload
systemctl restart ssh.socket 2>/dev/null || true
systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null || true

echo "[5/6] Prepping log dir. Cowrie's image runs as a named 'cowrie' user (a"
echo "      non-1000 uid), so a host-side chown to 1000 does NOT work — make the"
echo "      bind-mounted var/ world-writable instead (it only holds honeypot"
echo "      logs/state). Without this, Cowrie can't create its SSH host key and"
echo "      port 22 stays dead while telnet (which needs no key) still works."
mkdir -p /opt/tripwire/honeypot/var/log/cowrie \
         /opt/tripwire/honeypot/var/lib/cowrie/downloads \
         /opt/tripwire/honeypot/var/lib/cowrie/tty
chmod -R 777 /opt/tripwire/honeypot/var

echo "[6/6] Launching Cowrie..."
cd /opt/tripwire/honeypot && docker compose up -d

echo
echo "── DONE ─────────────────────────────────────────────────────────────────"
echo "Cowrie is now on ports 22 (SSH) and 23 (Telnet). Admin SSH moved to 64295."
echo
echo "NEXT (do NOT close this session yet):"
echo "  1. In the Oracle console, add VCN Security List ingress rules for"
echo "     TCP 23 and TCP 64295 (22 is already allowed by the VCN wizard)."
echo "  2. In a NEW terminal, confirm:  ssh -p 64295 ubuntu@<public-ip>"
echo "  3. Watch captures:  tail -f /opt/tripwire/honeypot/var/log/cowrie/cowrie.json"
echo "  4. Sanity-check SSH is listening (no PermissionError):"
echo "       sudo docker logs tripwire-cowrie --tail=15   # want: Ready to accept SSH connections"
echo "─────────────────────────────────────────────────────────────────────────"
