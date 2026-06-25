#!/usr/bin/env python
"""
pgcleanup.py - A script for cleaning up datasets in Galaxy efficiently, by
    bypassing the Galaxy model and operating directly on the database.
    PostgreSQL 9.1 or greater is required.
"""

from pgcleanup_lib import main


if __name__ == "__main__":
    main()
