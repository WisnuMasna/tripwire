# Phase 0 — provision the honeypot on Oracle Cloud (Always Free)

Free *forever*, generous specs. Uses [`cloud-init.oracle.yaml`](cloud-init.oracle.yaml),
which handles the host firewall Oracle's image locks down by default.

> **The one thing that trips everyone up:** Oracle has **two** firewalls. The
> cloud-init script opens the *host* iptables, but you must ALSO open the ports in
> the cloud-level **VCN Security List** (step 5). If a port isn't open in *both*,
> traffic never arrives.

## Steps

1. **Sign up** at cloud.oracle.com → "Start for free". Needs a card for identity
   verification; Always-Free resources are never charged. Pick a home region near
   you (it's permanent).

2. **Dedicated SSH key** (honeypot-only, never reused):
   ```bash
   ssh-keygen -t ed25519 -C tripwire-honeypot -f ~/.ssh/tripwire
   ```

3. **Create the instance** (Compute → Instances → Create):
   - Image: **Canonical Ubuntu 22.04**.
   - Shape: **VM.Standard.A1.Flex** (Ampere ARM), **1 OCPU / 6 GB** — well inside
     the always-free 4-OCPU/24 GB allowance. Cowrie's image is multi-arch, so ARM
     is fine.
     - *If you get "Out of host capacity"* (common on Ampere): retry a different
       Availability Domain, or fall back to **VM.Standard.E2.1.Micro** (x86, 1 GB,
       also always-free) — the script works unchanged on it.
   - SSH keys: upload `~/.ssh/tripwire.pub`.
   - **Show advanced options → Initialization script:** paste the entire contents
     of [`cloud-init.oracle.yaml`](cloud-init.oracle.yaml).
   - Create.

4. **Note the public IPv4** shown on the instance page.

5. **Open the ports in the VCN Security List** (the cloud firewall):
   - Instance page → Virtual Cloud Network → **Security Lists** → the default list
     → **Add Ingress Rules**. Add three, all *Stateless: No, IP Protocol: TCP,
     Source 0.0.0.0/0*:
     - Dest port **22** — honeypot SSH
     - Dest port **23** — honeypot Telnet
     - Dest port **64295** — your admin SSH (tighten Source to *your* IP/32 if you
       have a static IP)

6. **Reconnect on the new admin port** (login user is `ubuntu`, not root):
   ```bash
   ssh -p 64295 -i ~/.ssh/tripwire ubuntu@<public-ip>
   ```
   Locked out? Oracle console → instance → **Console connection** for recovery, and
   check `/var/log/cloud-init-output.log`.

7. **Confirm captures:**
   ```bash
   sudo docker ps                                          # tripwire-cowrie = Up
   tail -f /opt/tripwire/honeypot/var/log/cowrie/cowrie.json
   ```
   Real `cowrie.session.connect` events from internet scanners should appear within
   minutes. That's your Phase 0 sign-off.

## Isolation / AUP notes (spec §4)

- [x] Dedicated instance + dedicated SSH key.
- [x] Real sshd on 64295; Cowrie owns 22/23; host firewall default-deny.
- [ ] Restrict 64295 ingress to your IP in the Security List (recommended).
- [ ] **Keep egress locked** so a "popped" box can't be a launch point — this is
      what keeps a free-tier provider from flagging you for abuse. A passive,
      log-only honeypot is within AUP; an open relay is not.
- [ ] Snapshot the boot volume now as a clean baseline; rebuild weekly.

## Next

Phase 2: Wazuh agent on this box + Tailscale tunnel to the manager on TheHive-5.
See the commented block in [`cloud-init.oracle.yaml`](cloud-init.oracle.yaml).
