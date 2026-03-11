import os

DB_PATH = os.environ.get('DB_PATH', '/home/archiver/archive.db')
MAILDIR = os.environ.get('MAILDIR', '/home/archiver/emails')
SYNC_LOG = os.environ.get('SYNC_LOG', '/home/archiver/sync.log')

IMAP_HOST = os.environ.get('IMAP_HOST', 'imap.gmail.com')
IMAP_USER = os.environ.get('IMAP_USER', '')
IMAP_PASSWORD = os.environ.get('IMAP_PASSWORD', '')

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2:3b')

VALID_CATEGORIES = ['useful', 'work', 'personal', 'newsletter', 'spam', 'other']
VALID_PRIORITIES = ['high', 'medium', 'low']
MAILDIR_CACHE_TTL = 60  # seconds
