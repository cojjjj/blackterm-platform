import argparse
import json
import sys

from . import __version__
from .config import load_config
from .engine import ReconEngine
from .exceptions import BlacktermError
from .logging_setup import configure_logging
from .ports import parse_ports


def parser():
    p = argparse.ArgumentParser(prog="blackterm")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan")
    scan.add_argument("target")
    scan.add_argument("-p", "--ports", default="common")
    scan.add_argument("--banners", action="store_true")
    scan.add_argument("--json", action="store_true")

    sub.add_parser("history")
    sub.add_parser("plugins")
    sub.add_parser("config")
    sub.add_parser("gui")
    return p


def main(argv=None):
    args = parser().parse_args(argv)

    if args.command == "gui":
        from .desktop.app import main as gui_main
        return gui_main()

    try:
        config = load_config()
        if getattr(args, "banners", False):
            config.banners = True
        logger = configure_logging(config.log_level, config.log_path)
        engine = ReconEngine(config, logger)

        if args.command == "scan":
            scan_id, result = engine.scan(args.target, parse_ports(args.ports))
            if args.json:
                print(json.dumps({"scan_id": scan_id, **result.to_dict()}, indent=2))
            else:
                print(f"BLACKTERM // RECON scan #{scan_id}")
                print(f"Target: {result.target} ({result.ip})")
                print(f"Open ports: {len(result.open_ports)}")
                for p in result.open_ports:
                    print(f"{p.port:<7} {p.service:<18} {p.latency_ms} ms")
        elif args.command == "history":
            for row in engine.repository.list_recent():
                print(row)
        elif args.command == "plugins":
            for plugin in engine.plugins.plugins:
                print(f"{plugin.name} v{plugin.version}")
            if not engine.plugins.plugins:
                print("No plugins installed.")
        elif args.command == "config":
            print(json.dumps(config.to_dict(), indent=2))
        return 0
    except (BlacktermError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
