from flask import Blueprint, request, jsonify
from database import init_db
from services.processor import start_processing, get_status
from routes.gmail import delete_messages
from config import VALID_CATEGORIES, VALID_PRIORITIES

bp = Blueprint('emails', __name__)

@bp.route('/process', methods=['POST'])
def process():
    started = start_processing()
    if not started:
        return jsonify({'error': 'Already running'}), 400
    return jsonify({'started': True})

@bp.route('/status')
def status():
    return jsonify(get_status())

@bp.route('/smart-select', methods=['POST'])
def smart_select():
    data = request.json
    mode = data.get('mode')
    if mode not in ['spam', 'newsletter']:
        return jsonify({'error': 'Unknown mode'}), 400

    conn = init_db()
    rows = conn.execute(
        'SELECT id FROM emails WHERE category = ?', (mode,)
    ).fetchall()
    ids = [row['id'] for row in rows]
    return jsonify({'ids': ids, 'count': len(ids)})

@bp.route('/delete', methods=['POST'])
def delete():
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
        remote_deleted, remote_errors = delete_messages(message_ids)
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
    return jsonify({'local_deleted': len(ids), 'remote_deleted': 0, 'remote_errors': 0})

@bp.route('/email/<int:email_id>', methods=['PATCH'])
def reclassify(email_id):
    data = request.json
    category = data.get('category')
    priority = data.get('priority')

    if category and category not in VALID_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400
    if priority and priority not in VALID_PRIORITIES:
        return jsonify({'error': 'Invalid priority'}), 400

    conn = init_db()
    fields = []
    params = []

    if category:
        fields.append('category = ?')
        params.append(category)
    if priority:
        fields.append('priority = ?')
        params.append(priority)

    if not fields:
        return jsonify({'error': 'Nothing to update'}), 400

    fields.append('manually_classified = 1')
    params.append(email_id)

    conn.execute(
        f'UPDATE emails SET {", ".join(fields)} WHERE id = ?', params
    )
    conn.commit()
    return jsonify({'ok': True, 'id': email_id, 'category': category, 'priority': priority})
