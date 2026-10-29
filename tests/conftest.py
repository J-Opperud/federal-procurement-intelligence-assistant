"""Shared test configuration."""

import os


os.environ.setdefault("SAM_API_KEY", "mock-sam-api-key-for-tests")
os.environ.setdefault("JWT_SECRET_KEY", "Test-only-sectet-key_with_atleast-32-characters")

