"""pytest configuration for backend tests."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-minimum-32-chars-long-for-testing")
