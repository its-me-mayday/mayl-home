import socket
import json

SOCKET_PATH = '/run/mayl/processor.sock'

_fallback_status = {
    'running': False,
    'processed': 0,
    'errors': 0,
    'total': 0,
    'last_run': None,
    'last_run_processed': 0,
    'last_run_errors': 0,
}

def get_status() -> dict:
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(1.0)
        client.connect(SOCKET_PATH)
        client.sendall(b'STATUS')
        data = b''
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            data += chunk
        client.close()
        return json.loads(data.decode())
    except Exception:
        return dict(_fallback_status)

def start_processing() -> bool:
    """Non più usato — il processor è un servizio separato."""
    return False
