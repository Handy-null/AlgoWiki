from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from wiki.competition_practice import load_competition_practice_snapshot, upsert_competition_practice_snapshot


class Command(BaseCommand):
    help = "Import competition practice links from a JSON snapshot into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--snapshot",
            type=str,
            default="backend/data/competition_practice_links_snapshot.json",
            help="Path to the JSON snapshot file.",
        )
        parser.add_argument(
            "--replace-missing",
            action="store_true",
            help="Delete existing rows that are not present in the snapshot.",
        )

    def handle(self, *args, **options):
        snapshot_path = Path(options["snapshot"])
        if not snapshot_path.exists():
            raise CommandError(f"Snapshot file not found: {snapshot_path}")

        records = load_competition_practice_snapshot(snapshot_path)
        summary = upsert_competition_practice_snapshot(
            records,
            replace_missing=options["replace_missing"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Competition practice links imported: "
                f"created {summary['created']}, updated {summary['updated']}, "
                f"removed {summary['removed']}, total {summary['total']}."
            )
        )
