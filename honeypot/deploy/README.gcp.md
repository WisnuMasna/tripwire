# Phase 0 — provision the honeypot on Google Cloud (free tier)

Free *forever* (1× e2-micro), simpler firewall than Oracle. Uses
[`startup-script.gcp.sh`](startup-script.gcp.sh).

> **Three "stay free" rules — all required, or you get billed / it isn't free:**
> 1. **Region** must be `us-west1`, `us-central1`, or `us-east1` (only these three).
> 2. **Machine type** must be **e2-micro**.
> 3. **Boot disk** must be **Standard persistent disk** — GCP defaults new VMs to
>    a *Balanced* SSD, which is **not** free. Change it, max 30 GB.

## Steps

1. **Sign up** at console.cloud.google.com and create a project. A billing account
   with a card is required; always-free resources aren't charged. (You also get a
   $300 / 90-day credit, separate from the always-free e2-micro.)

2. **Install the gcloud CLI** (optional but easiest for the firewall + SSH steps):
   https://cloud.google.com/sdk/docs/install

3. **Create the instance** (Compute Engine → VM instances → Create):
   - Name: `tripwire-honeypot`
   - Region: **us-central1** (or us-west1 / us-east1), any zone.
   - Machine type: **e2-micro**.
   - Boot disk → Change → Boot disk type: **Standard persistent disk**, size 30 GB,
     image **Ubuntu 22.04 LTS**.
   - Networking → Network tags: add `tripwire` (used by the firewall rule below).
   - **Advanced options → Management → Automation → Startup script:** paste the
     entire contents of [`startup-script.gcp.sh`](startup-script.gcp.sh).
   - Create.

4. **Open the ports** (VPC firewall). Easiest via gcloud:
   ```bash
   gcloud compute firewall-rules create tripwire-honeypot \
     --allow tcp:22,tcp:23,tcp:64295 \
     --source-ranges 0.0.0.0/0 \
     --target-tags tripwire \
     --description "Cowrie honeypot (22/23) + admin SSH (64295)"
   ```
   Console alternative: VPC network → Firewall → Create firewall rule → Targets
   *Specified target tags* = `tripwire`, Source `0.0.0.0/0`, TCP ports
   `22,23,64295`. (Tighten 64295's source to your own IP if it's static.)

5. **Reconnect on the new admin port** (the startup script moved sshd to 64295, so
   the console's SSH button — which uses 22 — won't work):
   ```bash
   gcloud compute ssh tripwire-honeypot --zone <your-zone> -- -p 64295
   ```
   Plain-ssh alternative (username must match the key you added to the VM):
   ```bash
   ssh -p 64295 -i ~/.ssh/tripwire <user>@<external-ip>
   ```
   Locked out? Startup-script logs are at
   `sudo journalctl -u google-startup-scripts.service` (view via Serial console in
   the GCP UI, which doesn't need SSH).

6. **Confirm captures:**
   ```bash
   sudo docker ps                                          # tripwire-cowrie = Up
   tail -f /opt/tripwire/honeypot/var/log/cowrie/cowrie.json
   ```
   Real `cowrie.session.connect` events from internet scanners appear within
   minutes → Phase 0 sign-off.

## Isolation / cost notes (spec §4)

- [x] Dedicated instance + dedicated SSH key (`ssh-keygen -t ed25519 -f ~/.ssh/tripwire`).
- [x] Real sshd on 64295; Cowrie owns 22/23; VPC default-deny except the rule above.
- [ ] Restrict 64295 source to your IP in the firewall rule (recommended).
- [ ] **Keep egress minimal** — free tier includes 1 GB/mo North-America egress; a
      log-only honeypot stays well under. Don't let a "popped" box become a relay
      (AUP + egress cost).
- [ ] Snapshot the boot disk now as a clean baseline; rebuild weekly.

## Next

Phase 2: Wazuh agent on this box + Tailscale tunnel to the manager on TheHive-5.
See the commented block at the bottom of
[`startup-script.gcp.sh`](startup-script.gcp.sh).
