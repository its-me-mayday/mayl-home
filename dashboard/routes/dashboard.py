from flask import Blueprint, render_template, request, jsonify
from database import init_db
from services.maildir import count_maildir
from services.processor import get_status
from config import SYNC_LOG

bp = Blueprint('dashboard', __name__)

@bp.route('/')
def index():
    conn = init_db()
    category = request.args.get('category', '')
    priority = request.args.get('priority', '')
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'date')
    order = request.args.get('order', 'desc')

    valid_sorts = ['date', 'sender', 'subject', 'category', 'priority']
    if sort not in valid_sorts:
        sort = 'date'
    if order not in ['asc', 'desc']:
        order = 'desc'

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

    query += f' ORDER BY {sort} {order.upper()} LIMIT 100'
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
        sort=sort,
        order=order,
        total=total,
        stats=stats
    )
@bp.route('/stats')
def stats():
    conn = init_db()
    total_archived = conn.execute('SELECT COUNT(*) FROM emails').fetchone()[0]
    total_maildir = count_maildir()
    unprocessed = max(0, total_maildir - total_archived)

    categories = conn.execute('''
        SELECT category, COUNT(*) as count
        FROM emails GROUP BY category ORDER BY count DESC
    ''').fetchall()

    last_sync = 'N/A'
    try:
      with open(SYNC_LOG, 'r') as f:
        lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('Sync completed:'):
                last_sync = line.replace('Sync completed: ', '')
                break
    except Exception:
        pass

    return jsonify({
        'total_archived': total_archived,
        'total_maildir': total_maildir,
        'unprocessed': unprocessed,
        'processing': get_status(),
        'last_sync': last_sync,
        'categories': [{'name': r['category'], 'count': r['count']} for r in categories]
    })
