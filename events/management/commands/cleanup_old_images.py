from django.core.management.base import BaseCommand
from utils.supabase_storage import delete_old_images

class Command(BaseCommand):
    help = "Delete Supabase images older than 2 days"

    def handle(self, *args, **options):
        deleted = delete_old_images(older_than_days=2)
        self.stdout.write(f"Deleted {len(deleted)} old images: {deleted}")
