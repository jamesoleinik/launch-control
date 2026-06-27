"""Authentication helper for Dataverse SDK and Web API.

Uses interactive browser auth (device code flow with persistent caching).
For service principal auth, set CLIENT_ID and CLIENT_SECRET in .env.

Multi-environment support
-------------------------
By default the repo-root ``.env`` (with ``DATAVERSE_URL``) is loaded. To target a
second environment (for example the Season 2 episodes, each of which talks to its
own Dataverse/F&O/Fabric substrate) drop a per-episode ``.env`` next to that
episode and select it by name:

    # episodes/ep-09-dataverse-fno/.env  (gitignored)
    DATAVERSE_URL=https://<your-fno-env>.crm.dynamics.com
    FNO_URL=https://<your-fno-env>.operations.dynamics.com

    # then, from any script:
    #   PowerShell:  $env:LC_ENV = "ep-09-dataverse-fno"
    #   bash:        export LC_ENV=ep-09-dataverse-fno
    # or call load_env("ep-09-dataverse-fno") directly.

The per-episode file is layered on top of the root ``.env`` with override, so it
only needs the keys that differ. Per-episode ``.env`` files are already covered by
``.gitignore`` and must never be committed.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolve_env_file(env_name):
    """Return the Path to a per-episode .env for the given selector, or None.

    ``env_name`` may be an episode slug (``ep-09-dataverse-fno``), a path to a
    directory containing a ``.env``, or a direct path to an env file.
    """
    if not env_name:
        return None
    candidate = Path(env_name)
    options = [
        candidate,                                   # direct path to an env file
        candidate / ".env",                          # a directory holding a .env
        REPO_ROOT / "episodes" / env_name / ".env",  # an episode slug
        REPO_ROOT / f".env.{env_name}",              # root-level .env.<name>
    ]
    for path in options:
        if path.is_file():
            return path
    return None


def load_env(env_name=None):
    """Load environment variables.

    Always loads the repo-root ``.env`` as the base. If ``env_name`` (or the
    ``LC_ENV`` environment variable) selects a per-episode ``.env``, that file is
    layered on top with override so episode-specific keys win.
    """
    root_env = REPO_ROOT / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

    env_name = env_name or os.environ.get("LC_ENV")
    episode_env = _resolve_env_file(env_name)
    if episode_env:
        load_dotenv(episode_env, override=True)


def get_credential(env_name=None):
    """Return an Azure Identity credential for SDK use.

    Returns InteractiveBrowserCredential for interactive auth,
    or ClientSecretCredential if CLIENT_ID/CLIENT_SECRET are set.
    """
    load_env(env_name)
    client_id = os.environ.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET")
    tenant_id = os.environ.get("TENANT_ID")

    if client_id and client_secret and tenant_id:
        from azure.identity import ClientSecretCredential
        return ClientSecretCredential(tenant_id, client_id, client_secret)
    else:
        from azure.identity import AzureCliCredential
        return AzureCliCredential(tenant_id=tenant_id, process_timeout=60)


def get_token(env_name=None):
    """Get a raw access token string for Web API calls."""
    load_env(env_name)
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    scope = f"{env_url}/.default"
    credential = get_credential(env_name)
    token = credential.get_token(scope)
    return token.token


if __name__ == "__main__":
    load_env()
    selected = os.environ.get("LC_ENV")
    if selected:
        print(f"LC_ENV: {selected}")
    print(f"Environment: {os.environ.get('DATAVERSE_URL')}")
    token = get_token()
    print(f"Token acquired: {token[:20]}...")
    print("Auth is working.")
