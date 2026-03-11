import socket
import os
import json
import threading

SOCKET_PATH = '/run/mayl/processor.sock'

_status = {
    'running': False,
    'processed': 0,
    'errors': 0,
    'total': 0,
    'last_run': None,
    'last_run_processed': 0,
    'last_run_errors': 0,
}
_lock = threading.Lock()

def update_status(**kwargs):
    global _status
    with _lock:
        _status.update(kwargs)

def get_status() -> dict:
    with _lock:
        return dict(_status)

def _handle(conn):
    try:
        data = conn.recv(256).decode().strip()
        if data == 'STATUS':
            with _lock:
                conn.sendall(json.dumps(_status).encode())
        conn.close()
    except Exception:
        pass

def start_socket_server():
    os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o660)
    server.listen(5)

    def serve():
        while True:
            try:
                conn, _ = server.accept()
                threading.Thread(target=_handle, args=(conn,), daemon=True).start()
            except Exception:
                break

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return t
