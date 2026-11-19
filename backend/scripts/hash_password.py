#!/usr/bin/env python3
"""Print an ``ADMIN_PASSWORD_HASH`` value for a password typed at the prompt.

Usage
-----
    python scripts/hash_password.py

The password is read without echo and never written anywhere; set the
printed value as the ``ADMIN_PASSWORD_HASH`` runtime variable in Northflank
and drop ``ADMIN_PASSWORD``.
"""

import getpass
import sys
from pathlib import Path

# Ensure the backend directory is on Python path so app modules import cleanly
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.passwords import hash_password


def main() -> None:
    """Ask for the password twice and print the hash."""
    password = getpass.getpass("Admin password: ")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match")
    if not password:
        sys.exit("The password must not be empty")
    # Printed bare: a variable field in the Northflank UI would keep quotes literally.
    print(hash_password(password))


if __name__ == "__main__":
    main()
