# Phase 1 — Cowrie honeypot

A Cowrie SSH/Telnet honeypot in Docker. It emulates a real Linux box, lets
attackers "log in", records every credential, command, and file transfer, and
writes structured events to `var/log/cowrie/cowrie.json` — the single file the
rest of the Tripwire pipeline consumes.

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Runs the `cowrie/cowrie` container, maps ports, mounts config + logs |
| `cowrie.cfg` | Overrides: fake hostname, listen ports, SSH banner, JSON logging |
| `userdb.txt` | Which logins "succeed" (we let common botnet creds in on purpose) |
| `setup.sh` | One-time: creates `var/` with the right ownership, seeds `.env` |
| `test-connection.sh` | Acceptance test: drives a session, proves it hit `cowrie.json` |

## Run it (local test)

```bash
cd honeypot
./setup.sh              # creates var/ tree + .env
docker compose up -d    # starts Cowrie on 2222 (SSH) and 2223 (Telnet)
```

Verify capture:

```bash
./test-connection.sh              # automated if `sshpass` is present
# or manually, from another shell:
ssh -p 2222 root@localhost        # password: anything
#   then type:  uname -a; whoami; ls -la /   ; exit
tail -f var/log/cowrie/cowrie.json
```

You should see `cowrie.session.connect`, `cowrie.login.success`,
`cowrie.command.input`, and `cowrie.session.closed` events, one JSON object per
line.

## Deploying to the isolated VPS

The spec's isolation rules are **non-negotiable** — do this in order:

1. **Move the real sshd off port 22 first** (e.g. to `64295`) and confirm you can
   still log in on the new port. Skipping this locks you out once Cowrie takes 22.
2. Set `SSH_LISTEN_PORT=22` and `TELNET_LISTEN_PORT=23` in `honeypot/.env`.
3. Fresh, dedicated droplet — no reused SSH keys, no credentials shared with any
   other host.
4. Firewall: inbound 22/23 to the honeypot; the real sshd port limited to your IP.
   No outbound from the honeypot beyond DNS.
5. Rebuild from a clean snapshot on a schedule (weekly) in case of compromise.

## What's next

**Phase 2** installs a Wazuh agent on this box to tail `var/log/cowrie/cowrie.json`
and ship it to the existing `wazuh-lab` manager, with custom decoders/rules that
turn raw Cowrie events into structured alerts. See [`../wazuh/README.md`](../wazuh/README.md).
