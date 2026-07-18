def build_summary(result) -> list[str]:
    lines = [
        f"Observed {len(result.open_ports)} open TCP port(s) on {result.ip}.",
    ]
    services = {p.service for p in result.open_ports}
    if "microsoft-ds" in services or "netbios-ssn" in services:
        lines.append("Windows file-sharing services appear reachable.")
    if "http" in services or "https" in services or "http-proxy" in services:
        lines.append("A web-facing service was observed.")
    if "ssh" in services:
        lines.append("Remote shell access through SSH appears reachable.")
    if not result.open_ports:
        lines.append("No open ports were observed in the selected range.")
    lines.append(
        "Exposure does not imply vulnerability. Validate findings on systems you are authorized to assess."
    )
    return lines
