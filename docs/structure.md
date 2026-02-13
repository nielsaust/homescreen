# Project Structure

Current structure is moving toward clearer boundaries:

- `app/controllers/`:
  - action routing and controller-like orchestration (`action_dispatcher.py`)
- `app/ui/widgets/`:
  - reusable UI components (`network_status_widget.py`)
- `core/`:
  - event bus + reducer/state store skeleton
- `tools/`:
  - local/device diagnostics and simulation tooling
- `docs/`:
  - testing, observability, architecture notes
- root legacy modules:
  - existing runtime modules that are being migrated incrementally

## Migration strategy

We keep behavior stable while moving responsibilities out of legacy root files in small commits:

1. extract controller/service responsibilities
2. extract reusable UI widgets
3. migrate screen modules to state-driven rendering
4. move remaining legacy modules into `app/...` when coupling is reduced
