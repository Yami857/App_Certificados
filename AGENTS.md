# AGENTS.md

> Greenfield repo: no code, build, test, or lint config yet. Do not assume a stack.

## State
- Only contents are `Insumos/Maestro_Estudiantes.xlsx` and `Insumos/Registro_Evaluaciones.xlsx` (source data, Spanish filenames preserved).
- No `README`, manifest, lockfile, or CI. No executable source of truth exists yet.
- Not currently a git repo (`git version 2.56.0.windows.1` available, but uninitialized).

## Working rules
- Treat `Insumos/` as read-only input. Never edit `*.xlsx` in place; write derived outputs elsewhere.
- Toolchain is minimal here: `node`/`npm` not installed; `python`/`python3` resolve only to a Microsoft Store stub (running it opens the Store, no interpreter). Verify with `<tool> --version` before proposing commands; do not invent scripts or deps.
- When a stack is chosen, update this file with the exact verified commands (setup, dev, single-test, lint/typecheck) and entrypoints — keep it to what an agent would otherwise guess wrong.
- Idioma y comunicación: Responder y comunicarse siempre en español. Proporcionar explicaciones claras, sencillas y accesibles para principiantes.
