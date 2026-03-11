# mayl-home

Self-hosted email archiver with local AI classification, running on Proxmox LXC.

Syncs email from Gmail (or any IMAP provider) to a local Maildir, classifies each message using a local LLM (Llama 3.2 3B via Ollama), and exposes a web dashboard for search, filtering, bulk deletion, and manual reclassification. No data leaves your network.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Proxmox LXC — mayl-home (192.168.178.115)              │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  cron (every hour, user: archiver)              │    │
│  │    offlineimap → Maildir                        │    │
│  │    echo "Sync completed: $(date)" >> sync.log   │    │
│  │    sudo systemctl start mayl-processor          │    │
│  └────────────────────┬────────────────────────────┘    │
│                       │ triggers                        │
│  ┌────────────────────▼────────────────────────────┐    │
│  │  mayl-processor.service (systemd)               │    │
│  │    reads Maildir                                │    │
│  │    → Ollama (Llama 3.2 3B, localhost:11434)     │    │
│  │    → classifies: category, priority,            │    │
│  │      summary (IT), action_required              │    │
│  │    → writes to SQLite (archive.db)              │    │
│  │    → exposes status via Unix socket             │    │
│  │      /run/mayl/processor.sock                   │    │
│  └────────────────────┬────────────────────────────┘    │
│                       │ IPC (Unix socket)               │
│  ┌────────────────────▼────────────────────────────┐    │
│  │  mayl-dashboard.service (Flask, port 5000)      │    │
│  │    web UI — search, filter, sort, paginate      │    │
│  │    bulk delete (local + Gmail trash)            │    │
│  │    manual reclassify                            │    │
│  │    real-time HUD (stats, progress, categories)  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
         ▲ IMAP SSL                    ▲ HTTP :5000
         │                            │
    imap.gmail.com              your browser
```

### Services

| Service | Type | Restart | Description |
|---|---|---|---|
| `mayl-processor` | systemd simple | no | Classifies new emails, triggered by cron after sync |
| `mayl-dashboard` | systemd simple | always | Flask web UI, reads SQLite and processor socket |
| offlineimap | cron (hourly) | — | Syncs Gmail → local Maildir |
| ollama | systemd | always | Local LLM inference server |

### IPC — Unix Socket

The processor and dashboard communicate via a Unix domain socket at `/run/mayl/processor.sock`.

The processor runs a lightweight threaded server that responds to `STATUS` queries with JSON:

```json
{
  "running": true,
  "processed": 1247,
  "errors": 3,
  "total": 27088,
  "last_run": "2026-03-11 14:30:00",
  "last_run_processed": 1247,
  "last_run_errors": 3
}
```

The dashboard reads this with a 1-second timeout and falls back to a zero-state if the processor is not running — the dashboard never blocks.

---

## Stack

| Component | Technology |
|---|---|
| Infrastructure | OpenTofu + Telmate/proxmox provider |
| Configuration | Ansible (roles, vault-encrypted secrets) |
| Container | Ubuntu 22.04 LXC on Proxmox |
| Email sync | offlineimap |
| AI inference | Ollama + Llama 3.2 3B |
| Backend | Python 3, Flask |
| Database | SQLite |
| Frontend | Bootstrap 5.3 |

---

## Repository Structure

```
mayl-home/
├── terraform/
│   ├── main.tf               # Provider configuration
│   ├── lxc.tf                # LXC resource
│   ├── variables.tf          # All input variables
│   ├── outputs.tf            # container_ip, container_hostname
│   └── itsmemayday.tfvars    # 🔒 gitignored — your actual values
│
├── ansible/
│   ├── ansible.cfg           # host_key_checking = False
│   ├── inventory.yml         # mayl_home host
│   ├── playbook.yml          # roles with tags
│   ├── group_vars/all.yml    # vault-encrypted credentials
│   └── roles/
│       ├── base/             # apt deps, archiver user, zstd
│       ├── ssh/              # SSH hardening (placeholder)
│       ├── imap/             # offlineimap + cron + sudoers
│       ├── ollama/           # Ollama + llama3.2:3b pull
│       ├── processor/        # mayl-processor systemd service
│       └── dashboard/        # Flask app + mayl-dashboard service
│
├── app/
│   ├── main.py               # Flask app factory
│   ├── config.py             # All configuration (env vars)
│   ├── database.py           # SQLite init and connection
│   ├── processor_service.py  # Standalone processor entrypoint
│   ├── socket_server.py      # Unix socket status server
│   ├── requirements.txt
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── dashboard.py      # GET /, GET /stats
│   │   ├── emails.py         # /process, /delete, /smart-select, PATCH /email/<id>
│   │   └── gmail.py          # IMAP delete + message count
│   ├── services/
│   │   ├── __init__.py
│   │   ├── classifier.py     # Ollama API call
│   │   ├── maildir.py        # Maildir reading + cache
│   │   └── processor.py      # Unix socket client
│   └── templates/
│       └── index.html        # Single-page dashboard
│
├── .env.example
├── .gitignore
├── AUTHORS
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

## Prerequisites

- Proxmox VE with API access
- OpenTofu >= 1.11
- Ansible >= 2.14
- Gmail account with IMAP enabled and an App Password (16 chars, no spaces)
- `ansible-vault` password (choose one, keep it safe)

---

## Deploy

### 1. Provision the LXC

```bash
cd terraform
cp itsmemayday.tfvars.example itsmemayday.tfvars
# Edit itsmemayday.tfvars with your Proxmox credentials and network config
tofu init
tofu apply -var-file=itsmemayday.tfvars
```

### 2. Enable SSH on the container

From the Proxmox console (one-time, before Ansible can connect):

```bash
echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
systemctl enable ssh && systemctl start ssh
```

### 3. Encrypt credentials with Ansible Vault

```bash
cd ansible
ansible-vault encrypt_string 'your_ssh_password' --name 'ansible_password' --ask-vault-pass
ansible-vault encrypt_string 'imap.gmail.com' --name 'imap_host' --ask-vault-pass
ansible-vault encrypt_string 'you@gmail.com' --name 'imap_user' --ask-vault-pass
ansible-vault encrypt_string 'abcdabcdabcdabcd' --name 'imap_password' --ask-vault-pass
# Paste results into group_vars/all.yml
```

> Gmail App Password: generate at myaccount.google.com → Security → App Passwords.
> Store the 16-character code **without spaces**.

### 4. Run Ansible

```bash
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

Dashboard will be live at `http://<container-ip>:5000`.

---

## Partial Redeploy

Each role has a tag — redeploy only what changed:

```bash
# Dashboard only (Flask app + template)
ansible-playbook -i inventory.yml playbook.yml --tags dashboard --ask-vault-pass

# Processor service only
ansible-playbook -i inventory.yml playbook.yml --tags processor --ask-vault-pass

# IMAP config + cron
ansible-playbook -i inventory.yml playbook.yml --tags imap --ask-vault-pass
```

> Redeploying `--tags dashboard` does **not** interrupt a processor run in progress.

---

## Dashboard Features

| Feature | Description |
|---|---|
| Search | Full-text on subject, sender, and AI summary |
| Filter | By category and priority |
| Sort | Click any column — asc/desc toggle, preserved across filters |
| Pagination | 50 emails per page with numbered navigator |
| Reclassify | ✏️ dropdown per row — override AI category/priority, updates in-place |
| Smart select | One-click select all spam or all newsletter |
| Delete (local) | Remove from archive only |
| Delete (Gmail) | Move to Gmail trash (auto-deleted after 30 days) |
| HUD sidebar | Live: archived count, maildir total, Gmail total, unprocessed, per-category |
| Processing HUD | Animated dot, progress bar, processed/total, last run summary |
| Button lock | "Processa nuove email" auto-disabled while processor is running |
| IMAP sync time | Timestamp of last successful offlineimap run |

---

## Email Classification

Each email is classified by Llama 3.2 3B:

| Field | Values |
|---|---|
| `category` | useful, work, personal, newsletter, spam, other |
| `priority` | high, medium, low |
| `summary` | max 30 words in Italian |
| `action_required` | true / false |

Emails already in the database are skipped (`INSERT OR IGNORE` on `message_id`). Manual reclassifications are preserved (`manually_classified = 1`).

---

## Useful Commands

```bash
# Processor status and logs
systemctl status mayl-processor
journalctl -u mayl-processor -f

# Dashboard status and logs
systemctl status mayl-dashboard
journalctl -u mayl-dashboard -f

# Trigger processor manually
systemctl start mayl-processor

# Query socket directly
echo STATUS | socat - UNIX-CONNECT:/run/mayl/processor.sock

# Check cron
crontab -u archiver -l

# Sync log
tail -f /home/archiver/sync.log

# Database stats
sqlite3 /home/archiver/archive.db \
  "SELECT category, COUNT(*) FROM emails GROUP BY category;"
```

---

## Roadmap

- [ ] Email detail page (full body reader)
- [ ] SSH key authentication in Ansible
- [ ] Email notifications for high-priority messages (webhook/SMTP)
- [ ] Gunicorn + nginx (replace Flask dev server)
- [ ] Advanced statistics (charts by category and time period)
- [ ] Microservices architecture (separate API, processor, worker with message queue)

---

## Security Notes

- All credentials stored encrypted with `ansible-vault`
- `itsmemayday.tfvars` is gitignored — never commit it
- The `archiver` user runs all services with minimum required permissions
- Gmail access uses App Password (not your main account password)
- Unix socket is chmod 660 — accessible only by the `archiver` user
- Flask runs in dev mode — not suitable for exposure to untrusted networks

---

## License

MIT — see [LICENSE](LICENSE)

## Authors

See [AUTHORS](AUTHORS)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

