from __future__ import annotations
import os

# Bypass hostname guard so tests can run outside the production server host.
os.environ.setdefault("TRMNL_SKIP_HOST_CHECK", "1")
