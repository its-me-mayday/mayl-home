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
        print(f'[Gmail] Login OK')

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
                    errors += 1
                    continue
                for uid in data[0].split():
                    if trash:
                        mail.uid('copy', uid, f'"{trash}"')
                    mail.uid('store', uid, '+FLAGS', '\\Deleted')
                mail.expunge()
                deleted += 1
            except Exception as e:
                print(f'[Gmail] Error on {msg_id[:50]}: {e}')
                errors += 1

        try:
            if trash:
                mail.select(f'"{trash}"')
                mail.store('1:*', '+FLAGS', '\\Deleted')
                mail.expunge()
                print('[Gmail] Trash emptied')
        except Exception as e:
            print(f'[Gmail] Trash error: {e}')

        mail.logout()
        print(f'[Gmail] Done: {deleted} deleted, {errors} errors')

    except Exception as e:
        print(f'[Gmail] Fatal error: {e}')
        return 0, len(message_ids)

    return deleted, errors
