from django.core.management.base import BaseCommand
from api.models import Documentation
import json

class Command(BaseCommand):
    help = 'Validates and cleans documentation entries'

    def handle(self, *args, **options):
        for doc in Documentation.objects.all():
            try:
                json.loads(doc.content)
                self.stdout.write(self.style.SUCCESS(f'Valid doc ID: {doc.id}'))
            except Exception:
                self.stdout.write(self.style.ERROR(f'Deleting invalid doc ID: {doc.id}'))
                doc.delete()