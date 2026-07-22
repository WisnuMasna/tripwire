#!/usr/bin/env bash
# Tripwire honeypot — one-time setup. Creates the bind-mounted var/ tree with
# the ownership Cowrie (uid 1000 inside the image) needs to write logs.
set -euo pipefail
cd "$(dirname "$0")"

echo "[*] Creating var/ directory tree..."
mkdir -p var/log/cowrie var/lib/cowrie/downloads var/lib/cowrie/tty

# Cowrie's image runs as a named 'cowrie' user (a non-1000 uid), so a host-side
# chown to 1000 does NOT grant it write access. Make var/ world-writable instead
# (it only holds honeypot logs/state). Without this Cowrie can't write its SSH
# host key and port 22 stays dead while telnet still works.
if [ "$(uname)" = "Linux" ]; then
  echo "[*] Making var/ writable by the container's cowrie user..."
  if [ "$(id -u)" -ne 0 ]; then SUDO=sudo; else SUDO=""; fi
  $SUDO chmod -R 777 var
else
  echo "[*] Non-Linux host detected — Docker Desktop handles bind-mount perms."
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[*] Wrote .env from .env.example (edit ports before deploying to the VPS)."
fi

echo "[+] Done. Start the honeypot with:  docker compose up -d"
