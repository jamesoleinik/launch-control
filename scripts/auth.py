"""Authentication helper for Dataverse SDK and Web API.

Uses interactive browser auth (device code flow with persistent caching).
For service principal auth, set CLIENT_ID and CLIENT_SECRET in .env.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_env():
    """Load .env from the repo root."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()


def get_credential():
    """Return an Azure Identity credential for SDK use.
    
    Returns InteractiveBrowserCredential for interactive auth,
    or ClientSecretCredential if CLIENT_ID/CLIENT_SECRET are set.
    """
    load_env()
    client_id = os.environ.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET")
    tenant_id = os.environ.get("TENANT_ID")

    if client_id and client_secret and tenant_id:
        from azure.identity import ClientSecretCredential
        return ClientSecretCredential(tenant_id, client_id, client_secret)
    else:
        # Try DeviceCodeCredential for interactive auth (works better in terminal)
        from azure.identity import DeviceCodeCredential
        return DeviceCodeCredential(tenant_id=tenant_id)


def get_token():
    """Get a raw access token string for Web API calls."""
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    scope = f"{env_url}/.default"
    credential = get_credential()
    token = credential.get_token(scope)
    return token.token


if __name__ == "__main__":
    load_env()
    print(f"Environment: {os.environ.get('DATAVERSE_URL')}")
    token = get_token()
    print(f"Token acquired: {token[:20]}...")
    print("Auth is working.")
