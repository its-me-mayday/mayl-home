# 📬 mayl-home

> Self-hosted email archiver with local AI classification, running on Proxmox LXC — fully provisioned with Infrastructure as Code.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-green.svg)
![OpenTofu](https://img.shields.io/badge/OpenTofu-1.11+-purple.svg)
![Ansible](https://img.shields.io/badge/Ansible-2.15+-red.svg)

---

## What is mayl-home?

mayl-home is a fully self-hosted system that:

- **Archives** your Gmail (or any IMAP) emails locally on your Proxmox server
- **Classifies** every email using a local AI model (Ollama + Llama 3.2) — no data leaves your network
- **Shows** everything in a clean web dashboard with filters, search, and real-time processing

Everything is provisioned with IaC: one `tofu apply` and one `ansible-playbook` and you're done.

---

## Stack

| Component | Version | Role |
|---|---|---|
| **OpenTofu** | >= 1.11 | Provisions the LXC container on Proxmox |
| **Ansible** | >= 2.15 | Configures the container and deploys all services |
| **offlineimap** | latest | Fetches emails via IMAP, stores as Maildir |
| **Ollama + Llama 3.2 3B** | latest | Local AI model for email classification |
| **Flask** | >= 3.0 | Web dashboard backend |
| **SQLite** | built-in | Stores emails and AI classification results |
| **Proxmox LXC** | Ubuntu 22.04 | Container runtime |

---

## Repository Structure

```
mayl-home/
├── terraform/
│   ├── main.tf               # Provider configuration
│   ├── variables.tf          # All input variables with descriptions
│   ├── outputs.tf            # Output values (IP, hostname)
│   ├── lxc.tf                # LXC container resource
│   └── *.tfvars              # 🔒 Secret values (gitignored)
├── ansible/
│   ├── ansible.cfg           # Ansible configuration
│   ├── inventory.yml         # Host definitions
│   ├── playbook.yml          # Main playbook with tagged roles
│   ├── group_vars/
│   │   └── all.yml           # Vault-encrypted credentials
│   └── roles/
│       ├── base/             # System dependencies, archiver user
│       ├── ssh/              # SSH hardening
│       ├── imap/             # offlineimap setup and cron
│       ├── ollama/           # Ollama + Llama 3.2 installation
│       └── dashboard/        # Flask app deployment
├── app/
│   ├── main.py               # Flask backend + background processing
│   ├── classifier.py         # Ollama AI classifier
│   ├── requirements.txt      # Python dependencies
│   └── templates/
│       └── index.html        # Web dashboard
├── .gitignore
├── .env.example
├── AUTHORS
├── CHANGELOG.md
└── README.md
```

---

## Prerequisites

### On your local machine

- [OpenTofu](https://opentofu.org/docs/intro/install/) >= 1.11
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/) >= 2.15
- `sshpass` (required for Ansible password authentication)

```bash
# macOS
brew install opentofu ansible sshpass

# Ubuntu/Debian
sudo apt install ansible sshpass
wget -O tofu.deb https://github.com/opentofu/opentofu/releases/latest/download/tofu_linux_amd64.deb
sudo dpkg -i tofu.deb
```

### On Proxmox

- Proxmox VE >= 7.x
- Ubuntu 22.04 LXC template downloaded:
  `Proxmox UI → node → local → CT Templates → Templates → ubuntu-22.04-standard`

---

## Quickstart

### Step 1 — Terraform: Provision the LXC container

Copy the example vars file and fill in your values:

```bash
cp .env.example terraform/myvars.tfvars
```

Edit `terraform/myvars.tfvars`:

```hcl
proxmox_host     = "192.168.1.10"       # your Proxmox IP
proxmox_user     = "root@pam"
proxmox_password = "your-proxmox-password"
container_ip     = "192.168.1.80/24"    # desired container IP
gateway          = "192.168.1.1"
```

Run OpenTofu:

```bash
cd terraform/
tofu init
tofu plan -var-file=myvars.tfvars
tofu apply -var-file=myvars.tfvars
```

Expected output:

```
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
Outputs:
  container_hostname = "mayl-home"
  container_ip       = "192.168.1.80/24"
```

> ⚠️ `*.tfvars` files are gitignored — never commit them.

---

### Step 2 — Proxmox Console: Enable SSH

SSH is installed in the container but **not started by default**. Open the container console:

**Proxmox UI → mayl-home → Console**

```bash
# Allow root SSH login
echo "PermitRootLogin yes" >> /etc/ssh/sshd_config

# Enable and start SSH
systemctl enable ssh
systemctl start ssh

# Set the root password (you will use this in Ansible)
passwd root
```

---

### Step 3 — Gmail: Create an App Password

mayl-home uses an **App Password** to connect to Gmail — required if you have 2-Step Verification enabled (recommended).

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Type `mayl-home` as the app name and click **Create**
3. Copy the 16-character password shown (e.g. `abcd efgh ijkl mnop`)

Enable IMAP on Gmail:

1. Gmail → Settings → **See all settings** → **Forwarding and POP/IMAP**
2. Enable IMAP → **Save Changes**

IMAP credentials to use:

```
imap_host:     imap.gmail.com
imap_user:     your@gmail.com
imap_password: abcdefghijklmnop   (no spaces)
```

For Outlook/Hotmail use `outlook.office365.com` as host.

---

### Step 4 — Ansible: Encrypt credentials

Encrypt all credentials with ansible-vault (use the **same vault password** for all):

```bash
cd ansible/

# SSH password (set in Step 2)
ansible-vault encrypt_string 'your-root-password' --name 'ansible_password' --ask-vault-pass

# IMAP credentials (from Step 3)
ansible-vault encrypt_string 'imap.gmail.com' --name 'imap_host' --ask-vault-pass
ansible-vault encrypt_string 'your@gmail.com' --name 'imap_user' --ask-vault-pass
ansible-vault encrypt_string 'abcdefghijklmnop' --name 'imap_password' --ask-vault-pass
```

Paste all four outputs into `ansible/group_vars/all.yml`:

```yaml
ansible_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          (output from first command)

imap_host: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          (output from second command)

imap_user: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          (output from third command)

imap_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          (output from fourth command)
```

Test connectivity:

```bash
ansible -i inventory.yml all -m ping --ask-vault-pass
# Expected: mayl_home | SUCCESS => { "ping": "pong" }
```

---

### Step 5 — Ansible: Deploy everything

```bash
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

This will install and configure: base dependencies, offlineimap, Ollama + Llama 3.2, and the Flask dashboard.

You can also run individual roles with tags:

```bash
ansible-playbook -i inventory.yml playbook.yml --tags base --ask-vault-pass
ansible-playbook -i inventory.yml playbook.yml --tags imap --ask-vault-pass
ansible-playbook -i inventory.yml playbook.yml --tags ollama --ask-vault-pass
ansible-playbook -i inventory.yml playbook.yml --tags dashboard --ask-vault-pass
```

---

### Step 6 — Access the Dashboard

Open your browser at:

```
http://<container-ip>:5000
```

Click **"Processa nuove email"** to start the AI classification. The dashboard updates in real time every 3 seconds while processing.

---

## How it works

```
Gmail/IMAP
    │
    ▼ (every hour via cron)
offlineimap → Maildir on disk
    │
    ▼ (on demand via dashboard)
Flask /process endpoint
    │
    ▼
Ollama Llama 3.2 3B (local AI)
    │  classifies: category, priority, summary, action_required
    ▼
SQLite database
    │
    ▼
Flask dashboard (http://container-ip:5000)
```

### Email categories

| Category | Description |
|---|---|
| `useful` | Important emails worth keeping |
| `work` | Work-related emails |
| `personal` | Personal correspondence |
| `newsletter` | Newsletters and subscriptions |
| `spam` | Unwanted or promotional emails |
| `other` | Everything else |

---

## Useful Commands

| Command | Description |
|---|---|
| `tofu apply -var-file=myvars.tfvars` | Create/update the LXC container |
| `tofu destroy -var-file=myvars.tfvars` | Destroy the container |
| `ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass` | Full deploy |
| `ansible-playbook -i inventory.yml playbook.yml --tags dashboard --ask-vault-pass` | Redeploy dashboard only |
| `ansible -i inventory.yml all -m ping --ask-vault-pass` | Test connectivity |
| `ssh root@<container-ip>` | SSH into the container |
| `systemctl status mayl-dashboard` | Check dashboard service |
| `journalctl -u mayl-dashboard -f` | Live dashboard logs |
| `su - archiver -c "find emails/ -type f \| wc -l"` | Count archived emails |

---

## Security Notes

- `*.tfvars` — gitignored, never committed
- `ansible/group_vars/all.yml` — uses ansible-vault inline encryption, safe to commit
- IMAP credentials — vault-encrypted, never stored in plain text
- SSH root login — enabled only for LAN access
- All AI processing happens locally — no email data leaves your network

---

## Troubleshooting

**SSH connection refused**
→ Open Proxmox console and run `systemctl start ssh`

**Ansible: Permission denied**
→ Re-run `passwd root` from console and re-encrypt with `ansible-vault encrypt_string`

**Ansible vault error: Odd-length string**
→ The vault block in `all.yml` is malformed — re-run `encrypt_string` and paste the exact output including all hex lines

**Terraform: permissions not sufficient**
→ Use provider `Telmate/proxmox` version `3.0.2-rc07` — older versions have issues with OpenTofu >= 1.11

**Ollama: model requires more memory**
→ Increase container RAM to 8192 MB in `terraform/variables.tf` and run `tofu apply`

**Gmail: IMAP authentication failed**
→ Use the App Password (not your Google password) without spaces, and verify IMAP is enabled in Gmail settings

**Gmail: App Passwords not visible**
→ Enable 2-Step Verification first at [myaccount.google.com/security](https://myaccount.google.com/security)

**Dashboard not reachable**
→ Run `systemctl status mayl-dashboard` and `journalctl -u mayl-dashboard -n 30` on the container

