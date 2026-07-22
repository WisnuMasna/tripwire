# Phase 0 — provision the honeypot VPS

The honeypot must be internet-facing to attract real attacks, and **isolated** —
a fresh, dedicated, disposable box with nothing else on it and no credentials
shared with any other host (spec §4). [`cloud-init.yaml`](cloud-init.yaml) does
all the setup automatically on first boot.

## Steps (DigitalOcean — Linode/Vultr are near-identical)

1. **SSH key first.** If you don't already have one you'll add to the droplet:
   ```bash
   ssh-keygen -t ed25519 -C tripwire-honeypot -f ~/.ssh/tripwire
   ```
   This is a **dedicated** key for the honeypot only — never reuse an existing one.

2. **Create the droplet:**
   - Image: **Ubuntu 24.04 LTS** (or 22.04).
   - Plan: cheapest shared-CPU — **1 GB / 1 vCPU (~$6/mo)** is plenty for Cowrie.
   - Region: anywhere; closer to you = easier to reach on the admin port.
   - **Authentication: SSH key** → add the `~/.ssh/tripwire.pub` from step 1.
     Do *not* use a password.
   - **Advanced → Add Initial Scripts (user data):** paste the entire contents of
     [`cloud-init.yaml`](cloud-init.yaml).
   - Hostname: something plausible like `web-prod-01` (attackers see the droplet
     name in some scans).

3. **Create.** Wait ~2–3 minutes for cloud-init to finish (it reboots sshd onto a
   new port mid-run, so the console may briefly look stalled — that's expected).

4. **Reconnect on the new admin port** (cloud-init moved sshd to 64295):
   ```bash
   ssh -p 64295 -i ~/.ssh/tripwire root@<droplet-ip>
   ```
   If you're locked out, use DigitalOcean's **web console** (Access tab) to get in
   and check `/var/log/cloud-init-output.log`.

5. **Confirm the honeypot is live:**
   ```bash
   docker ps                                   # tripwire-cowrie should be Up
   tail -f /opt/tripwire/honeypot/var/log/cowrie/cowrie.json
   ```
   Within minutes you should see `cowrie.session.connect` events from real
   internet scanners hitting port 22. That's your Phase 0 sign-off.

## Isolation checklist (spec §4 — non-negotiable)

- [x] Dedicated droplet, nothing else on it.
- [x] Dedicated SSH key, not reused anywhere.
- [x] Real sshd moved to 64295; honeypot owns 22/23.
- [x] `ufw` default-deny inbound (admin port + honeypot ports only).
- [ ] **Optional hardening:** lock the admin port to your home IP —
      `ufw delete allow 64295/tcp && ufw allow from <your-ip> to any port 64295`.
- [ ] Rebuild from a clean snapshot weekly (spec §4). Take a baseline snapshot now.

## What's next

Real attacks are now landing in `cowrie.json`. **Phase 2** installs a Wazuh agent
on this box and tunnels it (Tailscale) back to the manager on TheHive-5 — see the
commented block at the bottom of [`cloud-init.yaml`](cloud-init.yaml) and
[`../../wazuh/README.md`](../../wazuh/README.md).
