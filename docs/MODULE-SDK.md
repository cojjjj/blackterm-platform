# BLACKTERM Module SDK

A module should provide a manifest and a page factory.

```python
from blackterm_recon.platform_sdk import ModuleManifest

manifest = ModuleManifest(
    key="example",
    name="Example Module",
    version="1.0.0",
    description="Demonstration module.",
    category="ANALYSIS",
    entrypoint="example_module:create_module",
)

def create_module(context):
    # Return a QWidget that uses context.engine, context.logger,
    # and context.navigate without reaching into private platform internals.
    ...
```

## Design rules

- Keep module-specific logic outside the desktop shell.
- Use the shared logger and configuration.
- Store persistent data in a module-owned table or database.
- Never claim a module is active until its engine and tests exist.
- Preserve authorization and scope checks for network operations.
