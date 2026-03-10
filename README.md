# mayl-home — Email Archiver with AI Classification

A self-hosted email archiver running on Proxmox LXC, with AI-powered classification via Ollama and a web dashboard built with Flask.

## Stack

| Component | Role |
|---|---|
| **OpenTofu** | Provisions the LXC container on Proxmox |
| **Ansible** | Configures the container (SSH, dependencies, services) |
| **offlineimap** | Fetches emails via IMAP and stores them as Maildir |
| **Ollama + Llama 3.2** | Classifies emails locally with AI |
| **Flask** | Web dashboard to browse and filter archived emails |
| **SQLite** | Stores emails and AI classification results |

## Repository Structure

```
mayl-home/
├── terraform/
│   ├── main.tf               # Terraform provider block
│   ├── variables.tf          # All input variables
│   ├── outputs.tf            # Output values (IP, hostname)
│   ├── lxc.tf                # LXC container resource
│   └── itsmemayday.tfvars    # 🔒 Secret values (gitignored)
├── ansible/
│   ├── ansible.cfg           # Ansible configuration
│   ├── inventory.yml         # Host definitions
│   ├── playbook.yml          # Main playbook
│   └── group_vars/
│       └── all.yml           # Vault-encrypted credentials
├── app/
│   ├── main.py               # Flask backend
│   ├── classifier.py         # Ollama AI classifier
│   ├── requirements.txt      # Python dependencies
│   └── templates/
│       └── index.html        # Web dashboard
├── .gitignore
├── .env.example
└── README.md
```

## Prerequisites

### On your local machine

- [OpenTofu](https://opentofu.org/docs/intro/install/) >= 1.6.0
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/) >= 2.15
- `sshpass` (required for Ansible password auth)

```bash
# macOS
brew install opentofu ansible sshpass

# Ubuntu/Debian
sudo apt install ansible sshpass
```

### On Proxmox

- Proxmox VE >= 7.x
- Ubuntu 22.04 LXC template downloaded:
  `local → CT Templates → Templates → ubuntu-22.04-standard`

---

## Step 1 — Terraform: Provision the LXC container

### Configure credentials

Copy the example file and fill in your values:

```bash
cp .env.example terraform/itsmemayday.tfvars
```

Edit `terraform/itsmemayday.tfvars`:

```hcl
proxmox_host     = "192.168.178.50"
proxmox_user     = "root@pam"
proxmox_password = "your-proxmox-password"
container_ip     = "192.168.178.80/24"
gateway          = "192.168.178.1"
```

> ⚠️ `itsmemayday.tfvars` is gitignored — never commit it.

### Run Terraform

```bash
cd terraform/
tofu init
tofu plan -var-file=itsmemayday.tfvars
tofu apply -var-file=itsmemayday.tfvars
```

Expected output:

```
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
Outputs:
  container_hostname = "mayl-home"
  container_ip       = "192.168.178.80/24"
```

---

## Step 2 — Proxmox Console: Enable SSH

After the container is created, SSH is installed but **not started by default**.
Open the container console from Proxmox web UI:

**Proxmox UI → mayl-home → Console**

Then run these commands inside the container:

```bash
# Allow root login via SSH
echo "PermitRootLogin yes" >> /etc/ssh/sshd_config

# Enable and start SSH
systemctl enable ssh
systemctl start ssh

# Set root password
passwd root
```

> ⚠️ This step is required before running Ansible.
> The password you set here will be used in the next step.

---

## Step 2b — Gmail: Create an App Password

mayl-home connects to Gmail via IMAP using an **App Password** — a dedicated 16-character password that works even with 2-Factor Authentication enabled. You must use this instead of your regular Google password.

### Requirements

- A Google account with **2-Step Verification enabled**
- If not enabled yet: [myaccount.google.com/security](https://myaccount.google.com/security) → 2-Step Verification → Turn on

### Create the App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. You may be asked to re-enter your Google password
3. In the **"App name"** field type `mayl-home`
4. Click **Create**
5. Google shows a 16-character password like `abcd efgh ijkl mnop` — **copy it immediately**, it won't be shown again

### Enable IMAP on Gmail

1. Open Gmail → Settings (gear icon) → **See all settings**
2. Go to the **Forwarding and POP/IMAP** tab
3. Under **IMAP access** → select **Enable IMAP**
4. Click **Save Changes**

### Your IMAP credentials

```
imap_host:     imap.gmail.com
imap_user:     your@gmail.com
imap_password: abcdefghijklmnop  (app password without spaces)
```

### Encrypt and store the credentials

```bash
cd ansible/
ansible-vault encrypt_string 'imap.gmail.com' --name 'imap_host' --ask-vault-pass
ansible-vault encrypt_string 'your@gmail.com' --name 'imap_user' --ask-vault-pass
ansible-vault encrypt_string 'abcdefghijklmnop' --name 'imap_password' --ask-vault-pass
```

Paste all three outputs into `ansible/group_vars/all.yml`:

```yaml
ansible_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          (existing value)

imap_host: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          (output from first command)

imap_user: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          (output from second command)

imap_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          (output from third command)
```

Verify the credentials are readable:

```bash
ansible -i inventory.yml all -m debug -a "msg={{ imap_host }}" --ask-vault-pass
# Expected: "msg": "imap.gmail.com"
```

> ⚠️ Never commit plain text credentials. All secrets must be vault-encrypted before being added to `group_vars/all.yml`.

---

## Step 3 — Ansible: Configure the container

### Encrypt the SSH password

```bash
cd ansible/
ansible-vault encrypt_string 'your-root-password' --name 'ansible_password' --ask-vault-pass
```

Copy the full output and paste it into `ansible/group_vars/all.yml`:

```yaml
ansible_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          62353133353931303538326533383166...
          (full output from the command above)
```

> 💡 Remember your vault password — you will need it every time you run Ansible.

### Test the connection

```bash
ansible -i inventory.yml all -m ping --ask-vault-pass
```

Expected output:

```
mayl_home | SUCCESS => {
    "ping": "pong"
}
```

### Run the playbook

```bash
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

---

## Step 4 — Access the Dashboard

Once the playbook completes, open the web dashboard at:

```
http://192.168.178.80:5000
```

Click **"Processa nuove email"** to trigger the AI classification.

---

## Useful Commands

| Command | Description |
|---|---|
| `tofu apply -var-file=itsmemayday.tfvars` | Create/update the LXC container |
| `tofu destroy -var-file=itsmemayday.tfvars` | Destroy the container |
| `ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass` | Deploy/update the full stack |
| `ansible-vault edit ansible/group_vars/all.yml` | Edit encrypted credentials |
| `ansible -i inventory.yml all -m ping --ask-vault-pass` | Test Ansible connectivity |

---

## Security Notes

- `itsmemayday.tfvars` — gitignored, contains Proxmox credentials
- `ansible/group_vars/all.yml` — vault-encrypted, safe to commit
- Email credentials (IMAP) — stored in vault, never in plain text
- SSH root login is enabled only within the local network (`192.168.178.x`)

---

## Troubleshooting

**SSH connection refused**
→ Open Proxmox console and run `systemctl start ssh`

**Ansible vault error: Odd-length string**
→ The vault block in `all.yml` is malformed. Re-run `encrypt_string` and paste the exact output.

**Terraform: permissions not sufficient**
→ Use provider version `Telmate/proxmox 3.0.2-rc07` — older versions have issues with OpenTofu 1.11.x

**Ansible: Permission denied**
→ Make sure you ran `passwd root` from the Proxmox console and updated the vault with the new password

**Gmail: IMAP authentication failed**
→ Make sure you are using the App Password (not your Google password) and that IMAP is enabled in Gmail settings

**Gmail: App Passwords option not visible**
→ 2-Step Verification must be active on your Google account before App Passwords appear

