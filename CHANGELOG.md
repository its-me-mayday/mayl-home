# Changelog

All notable changes to mayl-home will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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


