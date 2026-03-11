#!/usr/bin/env python3
"""
Backfill date_ts per le email già in DB che non ce l'hanno.
Esegui una volta sola:
  python3 /home/archiver/mayl-home/app/backfill_date_ts.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from email.utils import parsedate_to_datetime
from database import init_db

def parse_date_ts(date_str):
    if not date_str:
        return None
    try:
        return int(parsedate_to_datetime(date_str).timestamp())
    except Exception:
        return None

conn = init_db()

# Aggiungi colonna se non esiste
try:
    conn.execute('ALTER TABLE emails ADD COLUMN date_ts INTEGER')
    conn.commit()
    print('Colonna date_ts aggiunta')
except Exception:
    print('Colonna date_ts già esistente')

rows = conn.execute('SELECT id, date FROM emails WHERE date_ts IS NULL').fetchall()
print(f'Email da aggiornare: {len(rows)}')

updated = 0
failed = 0
for row in rows:
    ts = parse_date_ts(row['date'])
    if ts:
        conn.execute('UPDATE emails SET date_ts = ? WHERE id = ?', (ts, row['id']))
        updated += 1
    else:
        failed += 1

conn.commit()
print(f'Aggiornate: {updated}, non parsabili: {failed}')

