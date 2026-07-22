#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Tripwire honeypot — Google Cloud startup script (e2-micro, Always Free).
#
# Paste into: Create an instance → Advanced options → Management →
#             Automation → "Startup script".
# GCP runs this as root on every boot; it is written to be idempotent.
#
# GCP filters traffic at the VPC level, NOT on the host, so this script does NOT
# touch iptables. You open ports 22 / 23 / 64295 with a VPC firewall rule — see
# README.gcp.md. (A port must be open in the VPC firewall or traffic never
# arrives.)
#
# ⚠  This moves the real sshd to port 64295 so Cowrie can own 22. That means the
#    console's in-browser "SSH" button (which assumes 22) will stop working —
#    reconnect with:  gcloud compute ssh <name> --zone <zone> -- -p 64295
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

# ── 1. Move real sshd off 22 (classic service AND 24.04 socket-activation). ──
sed -i 's/^#\?Port .*/Port 64295/' /etc/ssh/sshd_config
mkdir -p /etc/systemd/system/ssh.socket.d
printf '[Socket]\nListenStream=\nListenStream=64295\n' > /etc/systemd/system/ssh.socket.d/override.conf
systemctl daemon-reload
systemctl restart ssh.socket 2>/dev/null || true
systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null || true

# ── 2. Install Docker + compose (only if missing). ──────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

# ── 3. Write Cowrie config + compose (heredocs are 'quoted' so ${..} stays
#       literal for docker-compose to expand from .env). ─────────────────────
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

# ── 4. Cowrie's image runs as a named 'cowrie' user (a non-1000 uid), so a host
#       chown to 1000 does NOT grant write access. Make the bind-mounted var/
#       world-writable (it only holds honeypot logs/state) — without this Cowrie
#       can't create its SSH host key and port 22 stays dead. ────────────────
mkdir -p /opt/tripwire/honeypot/var/log/cowrie \
         /opt/tripwire/honeypot/var/lib/cowrie/downloads \
         /opt/tripwire/honeypot/var/lib/cowrie/tty
chmod -R 777 /opt/tripwire/honeypot/var

# ── 5. Launch. ──────────────────────────────────────────────────────────────
cd /opt/tripwire/honeypot && docker compose up -d

# ── Phase 2 (later): Tailscale tunnel to the Wazuh manager on TheHive-5. ─────
# curl -fsSL https://tailscale.com/install.sh | sh
# tailscale up --auth-key=tskey-XXXX --hostname=tripwire-honeypot
