# Canonical performance environment

Stage 0 measurements use the following named environment until a replacement is
recorded in this file. Results from other machines must identify themselves and
must not silently replace this baseline.

## Local Windows development baseline

- Recorded: 2026-07-19 (Australia/Sydney)
- OS: Microsoft Windows 10 Home 10.0.19045, 64-bit
- CPU: AMD Ryzen 5 3600, 6 cores / 12 logical processors
- Memory: 16,725,160 KiB visible (approximately 15.95 GiB)
- Python: 3.12.12, repository virtual environment
- Node.js: 22.20.0
- npm: 10.9.3
- Repository branch: `main`
- Measurement base commit: `18d3bdd4ef05962d15d46d1362ff88581a468292`

Use a warm dependency cache. Backend tests run from `backend/`; frontend checks
run from `frontend/`. Network-backed, database integration, Tender evaluation,
and provider smoke tests are separate lanes and are never included in the
offline default lane.

## CI comparison environment

The default CI workflow uses GitHub-hosted Ubuntu with Python 3.12 and Node 22.
CI is the Linux process-lifecycle comparison environment. Performance figures
from the hosted runner are supporting evidence, not replacements for the local
baseline, because runner hardware is not fixed.
