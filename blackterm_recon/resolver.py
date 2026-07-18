import ipaddress
import socket

from .exceptions import TargetValidationError


def resolve_target(target: str) -> tuple[str, str | None]:
    target = target.strip()
    if not target:
        raise TargetValidationError("target cannot be empty")
    try:
        ip = socket.gethostbyname(target)
    except socket.gaierror as exc:
        raise TargetValidationError(f"could not resolve target: {target}") from exc
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror):
        hostname = None
    return ip, hostname


def enforce_target_policy(target: str, allow_public: bool) -> tuple[str, str | None]:
    ip, hostname = resolve_target(target)
    address = ipaddress.ip_address(ip)
    allowed = address.is_private or address.is_loopback or address.is_link_local
    if not allowed and not allow_public:
        raise TargetValidationError(
            "Public targets are disabled. Scan only systems you own or are authorized to assess."
        )
    return ip, hostname
