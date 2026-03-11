from flask import Flask, render_template, request, jsonify
import sqlite3, os, mailbox, threading
from classifier import classify_email

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
