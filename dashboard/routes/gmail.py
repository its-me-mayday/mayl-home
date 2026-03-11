import imaplib
from config import IMAP_HOST, IMAP_USER, IMAP_PASSWORD

def _get_folders(mail):
    _, folders = mail.list()
    all_mail = None
    trash = None
    for folder in folders:
        decoded = folder.decode('utf-8')
        parts = decoded.rsplit('"', 2)
        name = parts[-2].strip('"').strip() if len(parts) >= 2 else None
        if not name:
            continue
        if '\\All' in decoded:
            all_mail = name
        if '\\Trash' in decoded:
            trash = name
    return all_mail, trash

def delete_messages(message_ids: list) -> tuple:
    deleted = 0
    errors = 0
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        print('[Gmail] Login OK')

        all_mail, trash = _get_folders(mail)
        print(f'[Gmail] All Mail: {all_mail} | Trash: {trash}')

        if not all_mail:
            print('[Gmail] Could not find All Mail folder')
            mail.logout()
            return 0, len(message_ids)

        status, _ = mail.select(f'"{all_mail}"')
        if status != 'OK':
            print(f'[Gmail] Failed to select {all_mail}')
            mail.logout()
            return 0, len(message_ids)

        for msg_id in message_ids:
            try:
                clean_id = msg_id.strip().replace('"', '\\"')
                _, data = mail.uid('search', None, f'HEADER Message-ID "{clean_id}"')
                if not data[0]:
                    print(f'[Gmail] UID not found: {clean_id[:60]}')
                    errors += 1
                    continue
                for uid in data[0].split():
                    if trash:
                        mail.uid('copy', uid, f'"{trash}"')
                    mail.uid('store', uid, '+FLAGS', '\\Deleted')
                mail.expunge()
                print(f'[Gmail] Moved to trash: {clean_id[:60]}')
                deleted += 1
            except Exception as e:
                print(f'[Gmail] Error on {msg_id[:50]}: {e}')
                errors += 1

        mail.logout()
        print(f'[Gmail] Done: {deleted} moved to trash, {errors} errors')

    except Exception as e:
        print(f'[Gmail] Fatal error: {e}')
        return 0, len(message_ids)

    return deleted, errors

_gmail_cache = {'count': 0, 'last_updated': 0}

def count_messages() -> int:
    global _gmail_cache
    import time
    now = time.time()
    if now - _gmail_cache['last_updated'] < 300:  # cache 5 minuti
        return _gmail_cache['count']
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        all_mail, _ = _get_folders(mail)
        if all_mail:
            status, data = mail.select(f'"{all_mail}"', readonly=True)
            if status == 'OK':
                count = int(data[0])
                _gmail_cache = {'count': count, 'last_updated': now}
                print(f'[Gmail] Total messages: {count}')
        mail.logout()
    except Exception as e:
        print(f'[Gmail] Count error: {e}')
    return _gmail_cache['count']
