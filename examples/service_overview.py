PLUGIN_META = {
    "name": "Service Overview",
    "version": "1.0",
    "description": "Summarizes services observed during a completed scan.",
}


def run(context):
    return {
        "services": sorted({p.service for p in context.result.open_ports}),
        "open_ports": [p.port for p in context.result.open_ports],
    }
