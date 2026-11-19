"""Tests package for Review AI Dashboard API.

The settings also read the developer's ``.env`` files, and a real local
configuration (production mode, a password hash, another token lifetime)
would change what the tests see.  The variables the tests depend on are
pinned here, because pytest imports this package before ``conftest`` and the
application.  Environment variables take precedence over ``.env`` files.
"""

import os

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "AI_PROVIDER": "stub",
        "ADMIN_EMAIL": "admin@example.com",
        "ADMIN_PASSWORD": "dev-only-admin-password",
        "ADMIN_PASSWORD_HASH": "",
        "JWT_EXPIRATION_MINUTES": "30",
    }
)
