#!/usr/bin/env python3
import sys
import os
import mailbox
import sqlite3
import time

# Aggiungi app/ al path
sys.path.insert(0, os.path.dirname(__file__))

from socket_server import start_socket_server, update_status
from services.classifier import classify_email
from services.maildir import count_maildir, iter_maildir_messages
from database import init_db
from config import DB_PATH

def main():
    print('[Processor] Starting')
    start_socket_server()

    conn = init_db()
    total = count_maildir()
    update_status(running=True, processed=0, errors=0, total=total, last_run=None)
    print(f'[Processor] Total in maildir: {total}')

    processed = 0
    errors = 0
    start_time = time.time()

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
            processed += 1
            update_status(processed=processed)
        except Exception as e:
            errors += 1
            update_status(errors=errors)
            print(f'[Processor] Error: {subject[:60]}: {e}')

    elapsed = round(time.time() - start_time, 1)
    update_status(
        running=False,
        processed=processed,
        errors=errors,
        last_run=time.strftime('%Y-%m-%d %H:%M:%S'),
        last_run_processed=processed,
        last_run_errors=errors,
    )
    print(f'[Processor] Done: {processed} classified, {errors} errors in {elapsed}s')

    # Tieni il socket vivo 60s dopo il termine così la dashboard può leggere lo stato
    print('[Processor] Keeping socket alive for 60s...')
    time.sleep(60)

if __name__ == '__main__':
    main()
