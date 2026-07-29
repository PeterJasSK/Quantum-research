"""
Quantum Inspire 2 (QI2) credential setup — analogue of credentialsApi.py (IBM).

Unlike IBM (paste a static API token), QI2 authenticates via an OAuth browser
login. Credentials are written to ~/.quantuminspire/config.json and reused by
the qiskit-quantuminspire / pennylane plugins. There is no token to hardcode.

Prereqs (install once):
    pipx install quantuminspire        # provides the `qi` CLI
    pip  install qiskit-quantuminspire # Qiskit plugin (optional)

Run:
    python quantumCredentialsApi.py            # log in (opens browser)
    python quantumCredentialsApi.py --check     # only verify existing login
"""

import json
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".quantuminspire" / "config.json"


def is_logged_in() -> bool:
    """True if a QI2 config with tokens exists."""
    if not CONFIG_PATH.exists():
        return False
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    # config.json holds an "auths" map keyed by host URL, each with tokens.
    return bool(cfg.get("auths"))


def login() -> None:
    """Trigger the QI2 browser login flow via the `qi` CLI."""
    try:
        subprocess.run(["qi", "login"], check=True)
    except FileNotFoundError:
        sys.exit("`qi` CLI not found. Install it:  pipx install quantuminspire")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"qi login failed (exit {exc.returncode}).")


def main() -> None:
    check_only = "--check" in sys.argv

    if is_logged_in():
        print(f"Already logged in. Credentials at {CONFIG_PATH}")
        return

    if check_only:
        sys.exit("Not logged in. Run:  python quantumCredentialsApi.py")

    print("No QI2 credentials found. Opening browser to log in...")
    login()

    if is_logged_in():
        print(f"Login OK. Credentials saved to {CONFIG_PATH}")
    else:
        sys.exit("Login flow finished but no credentials found. Retry `qi login`.")


if __name__ == "__main__":
    main()
