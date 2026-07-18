import socket


def grab_banner(ip: str, port: int, timeout: float) -> str | None:
    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            if port in {80, 8000, 8080}:
                sock.sendall(b"HEAD / HTTP/1.0\r\nHost: localhost\r\n\r\n")
            data = sock.recv(256)
            return data.decode("utf-8", errors="replace").strip()[:200] if data else None
    except OSError:
        return None
