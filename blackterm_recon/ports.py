from .exceptions import PortSpecificationError


COMMON_PORTS = [
    20, 21, 22, 23, 25, 53, 80, 110, 111, 123, 135, 139, 143, 161,
    389, 443, 445, 465, 514, 587, 631, 636, 873, 902, 993, 995,
    1080, 1194, 1433, 1521, 1723, 1883, 2049, 2375, 2376, 3000,
    3306, 3389, 4444, 5000, 5432, 5601, 5672, 5900, 5985, 5986,
    6379, 6443, 8000, 8080, 8443, 8888, 9000, 9090, 9200, 27017,
]


def _valid(port: int) -> int:
    if not 1 <= port <= 65535:
        raise PortSpecificationError(f"port out of range: {port}")
    return port


def parse_ports(spec: str) -> list[int]:
    value = spec.strip().lower()
    if value == "common":
        return list(COMMON_PORTS)
    if value == "all":
        return list(range(1, 65536))
    if not value:
        raise PortSpecificationError("port specification cannot be empty")

    result = set()
    try:
        for token in value.split(","):
            token = token.strip()
            if "-" in token:
                a, b = token.split("-", 1)
                start, end = _valid(int(a)), _valid(int(b))
                if start > end:
                    raise PortSpecificationError(f"invalid range: {token}")
                result.update(range(start, end + 1))
            else:
                result.add(_valid(int(token)))
    except ValueError as exc:
        raise PortSpecificationError(f"invalid port specification: {spec}") from exc
    return sorted(result)
