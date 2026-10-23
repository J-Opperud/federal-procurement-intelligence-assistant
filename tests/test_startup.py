import os
import subprocess
import sys


def test_application_import_fails_without_jwt_secret():
    env = os.environ.copy()
    env.pop("JWT_SECRET_KEY", None)

    code = """
from app.config import Settings
Settings.model_config["env_file"] = None
Settings.model_config["env_file_encoding"] = None

# Recreate the module-level settings with environment-file loading disabled.
import app.config
app.config.settings = Settings(_env_file=None)

# Reload the security module so it uses the replacement settings.
import importlib
import app.utils.security
importlib.reload(app.utils.security)

# Importing main should now fail if it constructs settings at startup.
import app.main
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode != 0
    assert "jwt_secret_key" in result.stderr
