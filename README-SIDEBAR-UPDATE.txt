BLACKTERM GROUPED SIDEBAR UPDATE

Replace these files in your project:
  blackterm_recon/desktop/dock.py
  blackterm_recon/desktop/main_window.py

What changed:
- Five collapsible sections: Operations, Investigations, Intelligence,
  Visualization, and Platform.
- Active routes automatically reveal their section.
- Existing page labels, indices, callbacks, and self.dock.buttons compatibility
  remain intact.
- Future ungrouped pages automatically appear under Platform.
- Added command-bar aliases: "open threat" and "open intel".

Run:
  python -m blackterm_recon gui
