# Contributing to mayl-home

Thank you for your interest in contributing!

## How to contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

## Commit convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Description |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation changes |
| `chore:` | Maintenance, dependencies |
| `refactor:` | Code refactoring |

## Reporting bugs

Open an issue with:
- What you were trying to do
- What happened instead
- Your environment (OS, OpenTofu version, Ansible version, Proxmox version)
- Relevant logs from `journalctl -u mayl-dashboard` or Ansible output

## Development setup

To work on the Flask app locally without Proxmox:

```bash
cd app/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set a local maildir path for testing
export MAILDIR=/path/to/test/maildir
export DB_PATH=/tmp/test-archive.db

python main.py
```

## Areas open for contribution

- SSH key-based authentication in Ansible
- Support for multiple IMAP accounts
- Email detail view page
- Export to CSV/PDF
- Notification system for high-priority emails
- Gunicorn/nginx setup for production
- Docker Compose alternative to LXC

