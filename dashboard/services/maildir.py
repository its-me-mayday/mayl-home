import os
import time
from config import MAILDIR, MAILDIR_CACHE_TTL

_cache = {'count': 0, 'last_updated': 0}

def count_maildir() -> int:
    global _cache
    now = time.time()
    if now - _cache['last_updated'] < MAILDIR_CACHE_TTL:
        return _cache['count']

    total = 0
    for folder_name in os.listdir(MAILDIR):
        folder_path = os.path.join(MAILDIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
        try:
            for sub in ['cur', 'new']:
                sub_path = os.path.join(folder_path, sub)
                if os.path.isdir(sub_path):
                    total += len(os.listdir(sub_path))
        except Exception:
            pass

    _cache = {'count': total, 'last_updated': now}
    return total

def iter_maildir_messages():
    import mailbox
    for folder_name in os.listdir(MAILDIR):
        folder_path = os.path.join(MAILDIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
        try:
            mbox = mailbox.Maildir(folder_path)
            yield from mbox
        except Exception:
            continue
