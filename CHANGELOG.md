# Changelog

All notable changes to mayl-home will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-03-11

### Added

- **Email deletion** — select and delete emails from the local archive
- **Remote deletion** — permanently delete emails from Gmail via IMAP, bypassing trash
- **Smart selection** — one-click selection of all spam or all newsletter emails via AI-assigned categories
- **Manual selection** — checkbox per row plus select-all in table header
- **Delete confirmation modal** — explicit warning before permanent Gmail deletion, with item count shown
- **Atomic deletion logic** — if Gmail deletion fails entirely, local archive is left untouched; local deletion only proceeds after successful remote deletion
- **Auto-detection of Gmail folder names** — works regardless of Gmail language (Italian: "Tutti i messaggi" / "Cestino", English: "All Mail" / "Trash", etc.)
- **IMAP credentials via environment variables** — `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` injected into systemd service via Ansible vault

### Fixed

- IMAP App Password with spaces now stored correctly (spaces must be removed before vault encryption)
- Gmail folder selection now correctly strips quotes from parsed folder names
- systemd service environment variables now correctly passed to Flask process

### Changed

- `/process` endpoint now returns immediately and runs classification in background thread
- `/delete` endpoint checks Gmail first before modifying local archive when `delete_remote: true`

---

## [1.0.0] - 2026-03-11

### Added

- **Terraform/OpenTofu provisioning** — LXC container on Proxmox with configurable CPU, RAM, disk, and network settings
- **Ansible automation** — full configuration via tagged roles: `base`, `ssh`, `imap`, `ollama`, `dashboard`
- **offlineimap integration** — IMAP sync from Gmail (and any IMAP provider) to local Maildir, running every hour via cron
- **Ollama + Llama 3.2 3B** — local AI model for email classification, no data leaves the network
- **Email classification** — each email is assigned a category (useful, work, personal, newsletter, spam, other), a priority (high, medium, low), an AI-generated summary in Italian, and an action_required flag
- **Flask dashboard** — web interface at `http://<container-ip>:5000` with real-time processing updates every 3 seconds
- **Search and filters** — filter by category, priority, and free-text search on subject, sender, and summary
- **Background processing** — email classification runs in a background thread, dashboard stays responsive
- **SQLite storage** — lightweight database storing all archived emails with classification metadata
- **ansible-vault encryption** — all credentials (SSH, IMAP) encrypted inline with ansible-vault
- **Gitignore rules** — tfvars, secrets, email data, and Python artifacts excluded from version control
- **Provider compatibility** — tested with OpenTofu 1.11.x and Telmate/proxmox 3.0.2-rc07

### Infrastructure

- Ubuntu 22.04 LXC container
- 2 vCPU, 8GB RAM, 20GB disk (configurable via variables)
- Static IP assignment via Terraform variables

### Known Limitations

- Initial IMAP sync may timeout on large mailboxes (>5000 emails) — subsequent cron runs will complete the sync
- Flask runs in development mode — for production use, replace with gunicorn
- SSH uses password authentication — SSH key setup recommended for production


