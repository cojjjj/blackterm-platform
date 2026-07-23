BLACKTERM v7.3 - Investigation Explorer

Updated behavior:
- Cases-first graph starts with only case roots.
- Double-click a case or entity to expand/collapse its direct relationships.
- New EXPLORE layout uses radial grouping around case roots.
- Breadcrumb context shows the current selected/expanded entity.
- Entity nodes can open an associated linked case when available.
- Existing Network, Cluster, Tree, search, focus, export, and map actions remain available.
- Default relationship threshold remains 85% to reduce noise.

Run:
  python -m pip install -e .
  python -m blackterm_recon gui

Tests:
  PYTHONPATH=. pytest -q tests/test_graph_explorer_v73.py tests/test_graph_layout_v71.py tests/test_graph_layout_v72.py tests/test_relationship_graph_v70.py
