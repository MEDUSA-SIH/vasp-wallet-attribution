# packages/common

Shared Python types used across services (Phase 26 – optional workspace).

Currently a stub – it re-exports a few helpers from `app.schemas` so other
monorepo packages can import them without depending on the api package.

```python
from common.types import HealthResponse
```
"""