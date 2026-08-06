import os
import requests
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from typing import Optional

from supabase import create_client, Client
from supabase.client import ClientOptions


SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
SUPABASE_BUCKET = os.environ.get(
    "SUPABASE_BUCKET",
    "roadsense-images"
).strip()

_supabase: Optional[Client] = None


def get_supabase_client() -> Client:
    global _supabase

    if _supabase is not None:
        return _supabase

    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not configured")

    if not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_KEY is not configured")

    try:
        _supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
            options=ClientOptions(
                auto_refresh_token=False,
                persist_session=False,
            ),
        )
        return _supabase
    except Exception as e:
        raise RuntimeError(f"Supabase client initialization failed: {e}") from e


def upload_image(file_bytes, destination_path: str) -> str:
    try:
        if hasattr(file_bytes, "read"):
            file_bytes = file_bytes.read()

        if not isinstance(file_bytes, bytes):
            file_bytes = bytes(file_bytes)

        encoded_path = quote(destination_path, safe="/")

        upload_url = (
    f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/"
    f"{SUPABASE_BUCKET}/{encoded_path}"
)

        response = requests.post(
            upload_url,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "image/jpeg",
                "x-upsert": "true",
            },
            data=file_bytes,
            timeout=60,
        )

        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Supabase returned HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )

        return (
    f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/"
    f"{SUPABASE_BUCKET}/{encoded_path}"
)

    except Exception as e:
        raise RuntimeError(
            f"Supabase upload failed for {destination_path}: {e}"
        ) from e

def delete_image(destination_path: str) -> None:
    supabase = get_supabase_client()
    supabase.storage.from_(SUPABASE_BUCKET).remove([destination_path])


def list_files(folder: str = "frames"):
    supabase = get_supabase_client()
    return supabase.storage.from_(SUPABASE_BUCKET).list(folder)


def delete_old_images(older_than_days: int = 2):
    supabase = get_supabase_client()

    files = supabase.storage.from_(SUPABASE_BUCKET).list("frames")
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    deleted = []

    for file_info in files:
        created = file_info.get("created_at")
        name = file_info.get("name")

        if not created or not name:
            continue

        try:
            file_time = datetime.fromisoformat(
                created.replace("Z", "+00:00")
            )
        except ValueError:
            continue

        if file_time < cutoff:
            path = f"frames/{name}"
            supabase.storage.from_(SUPABASE_BUCKET).remove([path])
            deleted.append(path)

    return deleted
