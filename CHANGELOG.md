# Changelog

All notable changes to mayl-home will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-03-11

### Added

- **mayl-processor systemd service** — email classification extracted into a dedicated systemd service (`mayl-processor.service`), completely independent from the Flask dashboard
- **Unix socket IPC** — processor exposes its status via a Unix domain socket at `/run/mayl/processor.sock`; the dashboard reads state from the socket via a non-blocking client with 1s timeout and automatic fallback
- **socket_server.py** — lightweight threaded socket server embedded in the processor, responds to `STATUS` queries with JSON; stays alive 60 seconds after processing ends so the dashboard can read the final result
- **Automatic processor trigger** — cron job triggers `mayl-processor` via `sudo systemctl start` immediately after each IMAP sync; hourly cron as fallback
- **sudoers rule** — `archiver` user granted passwordless `systemctl start mayl-processor` via `/etc/sudoers.d/mayl-processor`
- **Ansible processor role** — new role `roles/processor/` handles service file deployment, systemd reload, and `/run/mayl` directory creation
- **Processing lock on dashboard** — "Processa nuove email" button reads live processor state from socket on every HUD refresh; automatically disabled when processor is running, re-enabled when idle
- **last_run stats in HUD** — sidebar shows timestamp, classified count, and errors from the last completed processor run
- **Processor survives dashboard redeploy** — redeploying `--tags dashboard` no longer interrupts an in-progress classification run

### Changed

- `services/processor.py` is now a thin Unix socket client instead of a background thread manager
- `routes/emails.py` `/process` endpoint checks socket status before launching and starts the systemd service via `subprocess.Popen`
- `processor_service.py` is the standalone entrypoint for the processor systemd service
- First IMAP sync on deploy now also triggers the processor on completion
- HUD polling consolidated — single `updateHUD()` loop every 5s handles both stats and button lock state

### Architecture

```
offlineimap (cron every hour)
  └── on complete → sudo systemctl start mayl-processor

mayl-processor.service (systemd)
  ├── reads Maildir
  ├── calls Ollama (Llama 3.2 3B) → classifies emails
  ├── writes results to SQLite
  └── exposes live status via Unix socket
      /run/mayl/processor.sock

mayl-dashboard.service (Flask, always-on)
  ├── serves web UI on :5000
  ├── reads SQLite for email list and stats
  └── reads Unix socket for processor status → HUD + button lock
```

---

## [1.2.0] - 2026-03-11

### Added

- **Sidebar HUD** — fixed left sidebar with real-time system statistics, updates every 5 seconds
- **Processing indicator** — animated pulsing dot, live progress bar and processed/total counter
- **Archive stats** — total archived emails, total in maildir, unprocessed count
- **Gmail message count** — sidebar shows total email count from Gmail All Mail folder via IMAP, cached 5 minutes
- **Per-category counters** — clickable category list in sidebar, filters the table on click
- **Last IMAP sync timestamp** — cron writes `Sync completed: YYYY-MM-DD HH:MM:SS` to sync.log; HUD displays it cleanly
- **Maildir cache** — file count cached 60 seconds, computed via `os.listdir` instead of `mailbox.Maildir`

### Changed

- `/stats` endpoint responds in milliseconds (was several seconds on large mailboxes)
- Layout switched from single column to sidebar + main content

---

## [1.1.0] - 2026-03-11

### Added

- **Email deletion** — select and delete emails from the local archive
- **Gmail trash** — selected emails moved to Gmail trash via IMAP (auto-deleted by Gmail after 30 days)
- **Smart selection** — one-click select all spam or all newsletter emails
- **Manual selection** — per-row checkbox plus select-all header checkbox
- **Delete confirmation modal** — explicit warning before Gmail trash operation
- **Atomic deletion** — if Gmail operation fails entirely, local archive is left untouched
- **Auto-detection of Gmail folder names** — parses IMAP LIST response to find All Mail and Trash regardless of Gmail language
- **Reclassify emails** — ✏️ dropdown on each row to manually override AI category and priority; badge updates in-place without page reload; row marked `manually_classified = 1` in DB
- **Sortable columns** — click any column header to sort asc/desc; active column highlighted; sort state preserved across filter changes
- **Pagination** — 50 emails per page, numbered navigator with ellipsis for large ranges
- **IMAP credentials in systemd** — `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` injected as environment variables via Ansible vault

### Fixed

- Gmail folder selection failing due to extra quotes in parsed folder name
- App Password spaces causing IMAP auth failure (must be stored without spaces)

### Changed

- `/delete` endpoint checks Gmail first; local archive only modified after successful remote operation

---

## [1.0.0] - 2026-03-11

### Added

- **OpenTofu provisioning** — LXC container on Proxmox (2 vCPU, 8GB RAM, 20GB disk) via `main.tf`, `lxc.tf`, `variables.tf`, `outputs.tf`
- **Ansible automation** — full configuration via tagged roles: `base`, `ssh`, `imap`, `ollama`, `dashboard`
- **offlineimap** — IMAP sync from Gmail to local Maildir, cron every hour
- **Ollama + Llama 3.2 3B** — local AI model, no data leaves the network
- **Email classification** — category (useful/work/personal/newsletter/spam/other), priority (high/medium/low), Italian summary, action_required flag
- **Flask dashboard** — web UI at `http://<container-ip>:5000`, search and category/priority filters
- **SQLite** — lightweight local database for archived emails and classification metadata
- **ansible-vault** — all credentials encrypted inline with `encrypt_string`

### Infrastructure

- Proxmox node: `192.168.178.50` — container: `192.168.178.115`
- Provider: `Telmate/proxmox 3.0.2-rc07` (required for OpenTofu >= 1.11)
- Ubuntu 22.04 LXC, static IP, `archiver` unprivileged user

### Known Limitations

- Initial IMAP sync may timeout on large mailboxes; subsequent cron runs complete it
- Flask dev server — replace with gunicorn for production
- SSH password auth — key-based recommended for production

