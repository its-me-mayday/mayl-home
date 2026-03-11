import threading
from database import init_db
from services.classifier import classify_email
from services.maildir import count_maildir, iter_maildir_messages

processing_status = {
    'running': False,
    'processed': 0,
    'errors': 0,
    'total': 0
}

def get_status() -> dict:
    return processing_status

def _extract_body(msg) -> str:
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except Exception:
            pass
    return body

def _run():
    global processing_status
    processing_status = {'running': True, 'processed': 0, 'errors': 0, 'total': count_maildir()}
    conn = init_db()

    for msg in iter_maildir_messages():
        msg_id = msg.get('Message-ID', '')
        if not msg_id:
            continue

        if conn.execute(
            'SELECT id FROM emails WHERE message_id = ?', (msg_id,)
        ).fetchone():
            continue

        subject = msg.get('subject', '(no subject)')
        sender = msg.get('from', '')
        date = msg.get('date', '')
        body = _extract_body(msg)

        try:
            result = classify_email(subject, sender, body)
            conn.execute('''
                INSERT OR IGNORE INTO emails
                (message_id, sender, subject, date, body,
                 category, priority, summary, action_required)
                VALUES (?,?,?,?,?,?,?,?,?)
            ''', (
                msg_id, sender, subject, date, body[:5000],
                result.get('category', 'other'),
                result.get('priority', 'low'),
                result.get('summary', ''),
                1 if result.get('action_required') else 0
            ))
            conn.commit()
            processing_status['processed'] += 1
        except Exception as e:
            processing_status['errors'] += 1
            print(f'[Processor] Error classifying "{subject}": {e}')

    processing_status['running'] = False

def start_processing() -> bool:
    if processing_status['running']:
        return False
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return True
