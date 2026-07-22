# Phase 2 — Wazuh parsing

Ship Cowrie's JSON events from the honeypot to the Wazuh manager on **TheHive-5**,
and turn them into scored, MITRE-tagged alerts.

```
Honeypot (<honeypot-ip>)                 TheHive-5 (Wazuh manager, behind NAT)
  cowrie.json                               wazuh-lab docker stack
     │                                         ▲  1514 (events) / 1515 (enroll)
     ▼                                         │
  wazuh-agent  ── Tailscale tunnel (100.x) ────┘
```

## Files

| File | Runs on | Purpose |
|------|---------|---------|
| `agent/install-agent.sh` | honeypot | Installs wazuh-agent 4.9.2, points it at the manager, ships `cowrie.json` |
| `agent/ossec.conf.snippet` | — | Reference for what the agent config ends up containing |
| `rules/cowrie_rules.xml` | manager | Classifies Cowrie events → alerts (ids 100100–100108) |
| `decoders/cowrie_decoders.xml` | — | Intentionally empty (JSON auto-decodes) |
| `install-rules-on-manager.sh` | TheHive-5 | Loads the rules into the manager container + restarts it |

---

## Step 0 — start the manager

TheHive-5 was in a *Saved* state. Boot it and bring the stack up:

```bash
# on TheHive-5
cd ~/…/wazuh-lab        # wherever the wazuh-lab compose lives
docker compose up -d
docker ps               # wazuh.manager / indexer / dashboard should be Up
```

## Step 1 — Tailscale tunnel (both hosts)

Free account, up to 100 devices. Account creation is yours.

1. Sign up at **tailscale.com** (GitHub/Google login).
2. **On TheHive-5:**
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   tailscale ip -4          # ← note this 100.x.y.z — it's your MANAGER_IP
   ```
3. **On the honeypot** (`ssh -p 64295 ubuntu@<honeypot-ip>`):
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
   Or non-interactively with a reusable **auth key** from the Tailscale admin
   console (Settings → Keys):
   ```bash
   sudo tailscale up --auth-key=tskey-XXXX --hostname=tripwire-honeypot
   ```
4. **Confirm the tunnel** — from the honeypot:
   ```bash
   ping -c3 <MANAGER_IP>     # must succeed before Step 3
   ```

## Step 2 — load the rules on the manager

Copy `rules/cowrie_rules.xml` (and this script) to TheHive-5, then:

```bash
# on TheHive-5, from the wazuh/ directory
sudo bash install-rules-on-manager.sh
```
It auto-detects the manager container, installs the rules, restarts Wazuh, and
prints a `wazuh-logtest` command to verify a sample event matches **rule 100103**.

## Step 3 — install the agent on the honeypot

```bash
# on the honeypot
MANAGER_IP=<manager-tailscale-ip> sudo -E bash install-agent.sh
```
It installs wazuh-agent 4.9.2, points it at the manager over Tailscale, and adds
the `cowrie.json` localfile.

## Step 4 — verify end to end

- **Agent connected** (honeypot):
  ```bash
  sudo tail -f /var/ossec/logs/ossec.log      # want: "Connected to the server"
  ```
- **Agent registered** (manager): the Wazuh dashboard (https on TheHive-5) →
  Agents → `tripwire-honeypot` = Active.
- **Alerts flowing:** generate an event by SSHing into the honeypot as an
  "attacker" (`ssh root@<honeypot-ip>`, run `uname -a`), then on the manager:
  ```bash
  docker exec <manager-container> tail -f /var/ossec/logs/alerts/alerts.json | grep cowrie
  ```
  You should see alerts with `rule.id` 100101–100108 and the decoded `src_ip`,
  `username`, `input`, etc.

That decoded, scored alert stream is exactly what the **Phase 3** triage service
will poll from the Wazuh API, enrich, and hand to Claude.

## Troubleshooting

- **Agent won't connect:** confirm `ping <MANAGER_IP>` works from the honeypot;
  confirm the manager published 1514/1515 (`docker ps` on TheHive-5).
- **Enrollment rejected:** the manager may require a registration password
  (`<use_password>`). Default wazuh-lab does not; if yours does, add it to the
  agent's `<enrollment>` block.
- **No alerts but agent connected:** on the manager, run the `wazuh-logtest`
  sample from `install-rules-on-manager.sh` to confirm the rules loaded.
