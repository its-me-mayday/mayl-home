from flask import Blueprint, render_template, request, jsonify
from database import init_db
from services.maildir import count_maildir
from services.processor import get_status
from routes.gmail import count_messages
from config import SYNC_LOG

bp = Blueprint('dashboard', __name__)
PAGE_SIZE = 50

@bp.route('/')
def index():
    conn = init_db()
    category = request.args.get('category', '')
    priority = request.args.get('priority', '')
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'date')
    order = request.args.get('order', 'desc')
    page = max(1, int(request.args.get('page', 1)))

    valid_sorts = ['date', 'sender', 'subject', 'category', 'priority']
    if sort not in valid_sorts:
        sort = 'date'
    if order not in ['asc', 'desc']:
        order = 'desc'

    query = 'SELECT * FROM emails WHERE 1=1'
    count_query = 'SELECT COUNT(*) FROM emails WHERE 1=1'
    params = []

    if category:
        query += ' AND category = ?'
        count_query += ' AND category = ?'
        params.append(category)
    if priority:
        query += ' AND priority = ?'
        count_query += ' AND priority = ?'
        params.append(priority)
    if search:
        query += ' AND (subject LIKE ? OR sender LIKE ? OR summary LIKE ?)'
        count_query += ' AND (subject LIKE ? OR sender LIKE ? OR summary LIKE ?)'
        params.extend([f'%{search}%'] * 3)

    total_filtered = conn.execute(count_query, params).fetchone()[0]
    total_pages = max(1, (total_filtered + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    offset = (page - 1) * PAGE_SIZE

    # date_ts è un timestamp Unix (parsing RFC 2822 fatto dal processor)
    # COALESCE fallback su processed_at per email senza date_ts
    sort_expr = "COALESCE(date_ts, strftime('%s', processed_at))" if sort == 'date' else sort
    query += f' ORDER BY {sort_expr} {order.upper()} LIMIT {PAGE_SIZE} OFFSET {offset}'

    emails = conn.execute(query, params).fetchall()
    total = conn.execute('SELECT COUNT(*) FROM emails').fetchone()[0]
    stats = conn.execute('''
        SELECT category, COUNT(*) as count
        FROM emails GROUP BY category
    ''').fetchall()

    # Build page range (max 10 pages shown)
    delta = 4
    left = max(1, page - delta)
    right = min(total_pages, page + delta)
    page_range = list(range(left, right + 1))

    return render_template('index.html',
        emails=emails,
        category=category,
        priority=priority,
        search=search,
        sort=sort,
        order=order,
        total=total,
        stats=stats,
        page=page,
        total_pages=total_pages,
        total_filtered=total_filtered,
        page_range=page_range,
    )


@bp.route('/stats')
def stats():
    conn = init_db()
    total_archived = conn.execute('SELECT COUNT(*) FROM emails').fetchone()[0]
    total_maildir = count_maildir()
    total_gmail = count_messages()
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
        'total_gmail': total_gmail,
        'unprocessed': unprocessed,
        'processing': get_status(),
        'last_sync': last_sync,
        'categories': [{'name': r['category'], 'count': r['count']} for r in categories]
    })

