import os
from supabase import create_client, Client
from typing import Optional

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "roadsense-images")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_image(file_bytes, destination_path):
    try:
        if supabase is None:
            raise RuntimeError("Supabase client is not configured")

        bucket = supabase.storage.from_(SUPABASE_BUCKET)

        file_obj = BytesIO(file_bytes)
        bucket.upload(
            path=destination_path,
            file=file_obj,
            file_options={
                "content-type": "image/jpeg",
                "cache-control": "3600",
                "upsert": "false"
            }
        )

        return bucket.get_public_url(destination_path)

    except Exception as e:
        raise RuntimeError(f"Supabase upload failed for {destination_path}: {e}")

def delete_image(destination_path: str):
    """Delete a single image from Supabase Storage."""
    if supabase is None:
        print(f"[LOCAL] Cannot delete {destination_path} - Supabase not configured")
        return
    
    supabase.storage.from_(SUPABASE_BUCKET).remove([destination_path])

def list_files(folder: str = "frames"):
    """List files in Supabase bucket."""
    if supabase is None:
        print("[LOCAL] Cannot list files - Supabase not configured")
        return []
    
    return supabase.storage.from_(SUPABASE_BUCKET).list(folder)
    
def delete_old_images(older_than_days=2):
    """List and delete images older than N days from the frames folder."""
    if supabase is None:
        raise ValueError("Supabase credentials are not configured")

    from datetime import datetime, timezone, timedelta

    files = supabase.storage.from_(SUPABASE_BUCKET).list("frames")
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    deleted = []

    for f in files:
        created = f.get("created_at", "")
        name = f.get("name", "")
        if created and name:
            file_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if file_time < cutoff:
                path = f"frames/{name}"
                supabase.storage.from_(SUPABASE_BUCKET).remove([path])
                deleted.append(path)

    return deleted
