from flask import Flask, render_template, request, jsonify
import sqlite3, os, mailbox, threading, imaplib

app = Flask(__name__)
DB_PATH = '/home/archiver/archive.db'
MAILDIR = '/home/archiver/emails'

processing_status = {
    'running': False,
    'processed': 0,
    'errors': 0,
    'total': 0
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY,
        message_id TEXT UNIQUE,
        sender TEXT,
        subject TEXT,
        date TEXT,
        body TEXT,
        category TEXT,
        priority TEXT,
        summary TEXT,
        action_required INTEGER,
        processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    return conn

def delete_from_gmail(message_ids: list) -> tuple:
    deleted = 0
    errors = 0
    try:
        imap_host = os.environ.get('IMAP_HOST', '')
        imap_user = os.environ.get('IMAP_USER', '')
        imap_pass = os.environ.get('IMAP_PASSWORD', '')

        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(imap_user, imap_pass)
        print(f'[Gmail] Login OK')

        # Auto-detect folder names by attribute
        _, folders = mail.list()
        all_mail_folder = None
        trash_folder = None

        for folder in folders:
            decoded = folder.decode('utf-8')
            parts = decoded.rsplit('"', 2)
            folder_name = parts[-2] if len(parts) >= 2 else None
            if not folder_name:
                continue
            # Strip any remaining quotes
            folder_name = folder_name.strip('"').strip()
            if '\\All' in decoded:
                all_mail_folder = folder_name
            if '\\Trash' in decoded:
                trash_folder = folder_name

        print(f'[Gmail] All Mail folder: {all_mail_folder}')
        print(f'[Gmail] Trash folder: {trash_folder}')

        if not all_mail_folder:
            print('[Gmail] Could not find All Mail folder')
            mail.logout()
            return 0, len(message_ids)

        select_status, _ = mail.select(f'"{all_mail_folder}"')
        print(f'[Gmail] Select status: {select_status}')
        if select_status != 'OK':
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
                    if trash_folder:
                        mail.uid('copy', uid, f'"{trash_folder}"')
                    mail.uid('store', uid, '+FLAGS', '\\Deleted')
                mail.expunge()
                deleted += 1
            except Exception as e:
                print(f'[Gmail] Error on {msg_id[:50]}: {e}')
                errors += 1

        try:
            if trash_folder:
                mail.select(f'"{trash_folder}"')
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

def process_emails_background():
    global processing_status
    processing_status = {'running': True, 'processed': 0, 'errors': 0, 'total': 0}
    conn = init_db()

    total = 0
    for folder_name in os.listdir(MAILDIR):
        folder_path = os.path.join(MAILDIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
        try:
            mbox = mailbox.Maildir(folder_path)
            total += sum(1 for _ in mbox)
        except Exception:
            pass
    processing_status['total'] = total

    for folder_name in os.listdir(MAILDIR):
        folder_path = os.path.join(MAILDIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
        try:
            mbox = mailbox.Maildir(folder_path)
        except Exception:
            continue

        for msg in mbox:
            msg_id = msg.get('Message-ID', '')
            if not msg_id:
                continue

            existing = conn.execute(
                'SELECT id FROM emails WHERE message_id = ?', (msg_id,)
            ).fetchone()
            if existing:
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
                from classifier import classify_email
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
                print(f'Error classifying {subject}: {e}')

    processing_status['running'] = False

@app.route('/')
def index():
    conn = init_db()
    category = request.args.get('category', '')
    priority = request.args.get('priority', '')
    search = request.args.get('search', '')

    query = 'SELECT * FROM emails WHERE 1=1'
    params = []

    if category:
        query += ' AND category = ?'
        params.append(category)
    if priority:
        query += ' AND priority = ?'
        params.append(priority)
    if search:
        query += ' AND (subject LIKE ? OR sender LIKE ? OR summary LIKE ?)'
        params.extend([f'%{search}%'] * 3)

    query += ' ORDER BY date DESC LIMIT 100'
    emails = conn.execute(query, params).fetchall()
    total = conn.execute('SELECT COUNT(*) FROM emails').fetchone()[0]
    stats = conn.execute('''
        SELECT category, COUNT(*) as count
        FROM emails GROUP BY category
    ''').fetchall()

    return render_template('index.html',
        emails=emails,
        category=category,
        priority=priority,
        search=search,
        total=total,
        stats=stats
    )

@app.route('/process', methods=['POST'])
def process_emails():
    global processing_status
    if processing_status['running']:
        return jsonify({'error': 'Already running'}), 400
    thread = threading.Thread(target=process_emails_background)
    thread.daemon = True
    thread.start()
    return jsonify({'started': True})

@app.route('/status')
def status():
    return jsonify(processing_status)

@app.route('/smart-select', methods=['POST'])
def smart_select():
    data = request.json
    mode = data.get('mode')

    conn = init_db()
    if mode == 'spam':
        rows = conn.execute(
            'SELECT id FROM emails WHERE category = ?', ('spam',)
        ).fetchall()
    elif mode == 'newsletter':
        rows = conn.execute(
            'SELECT id FROM emails WHERE category = ?', ('newsletter',)
        ).fetchall()
    else:
        return jsonify({'error': 'Unknown mode'}), 400

    ids = [row['id'] for row in rows]
    return jsonify({'ids': ids, 'count': len(ids)})

@app.route('/delete', methods=['POST'])
def delete_emails():
    data = request.json
    ids = data.get('ids', [])
    delete_remote = data.get('delete_remote', False)

    if not ids:
        return jsonify({'error': 'No IDs provided'}), 400

    conn = init_db()
    placeholders = ','.join('?' * len(ids))
    rows = conn.execute(
        f'SELECT message_id FROM emails WHERE id IN ({placeholders})', ids
    ).fetchall()
    message_ids = [row['message_id'] for row in rows if row['message_id']]

    if delete_remote:
        remote_deleted, remote_errors = delete_from_gmail(message_ids)
        if remote_errors > 0 and remote_deleted == 0:
            return jsonify({
                'error': f'Gmail deletion failed ({remote_errors} errors) — local archive untouched',
                'local_deleted': 0,
                'remote_deleted': 0,
                'remote_errors': remote_errors
            }), 500
        conn.execute(f'DELETE FROM emails WHERE id IN ({placeholders})', ids)
        conn.commit()
        return jsonify({
            'local_deleted': len(ids),
            'remote_deleted': remote_deleted,
            'remote_errors': remote_errors
        })

    conn.execute(f'DELETE FROM emails WHERE id IN ({placeholders})', ids)
    conn.commit()
    return jsonify({
        'local_deleted': len(ids),
        'remote_deleted': 0,
        'remote_errors': 0
    })

@app.route('/email/<int:email_id>')
def email_detail(email_id):
    conn = init_db()
    email = conn.execute(
        'SELECT * FROM emails WHERE id = ?', (email_id,)
    ).fetchone()
    return render_template('detail.html', email=email)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
