import socket


FALLBACK = {
    22: "ssh",
    53: "domain",
    80: "http",
    135: "epmap",
    139: "netbios-ssn",
    443: "https",
    445: "microsoft-ds",
    3389: "ms-wbt-server",
    5432: "postgresql",
    6379: "redis",
    8080: "http-proxy",
    27017: "mongodb",
}


def identify_service(port: int) -> str:
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return FALLBACK.get(port, "unknown")
