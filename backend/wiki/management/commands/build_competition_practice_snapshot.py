import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from wiki.competition_practice import build_competition_practice_snapshot


class Command(BaseCommand):
    help = "Build a JSON snapshot for competition practice links from local markdown tables."

    def add_arguments(self, parser):
        parser.add_argument("--provincial", type=str, required=True, help="Path to 01 - 省赛与邀请赛.md")
        parser.add_argument("--icpc", type=str, required=True, help="Path to 02 - ICPC.md")
        parser.add_argument("--ccpc", type=str, required=True, help="Path to 03 - CCPC.md")
        parser.add_argument(
            "--output",
            type=str,
            default="backend/data/competition_practice_links_snapshot.json",
            help="Output JSON snapshot path.",
        )

    def handle(self, *args, **options):
        source_paths = {
            "provincial_invitational": options["provincial"],
            "icpc": options["icpc"],
            "ccpc": options["ccpc"],
        }

        for key, raw_path in source_paths.items():
            if not Path(raw_path).exists():
                raise CommandError(f"{key} source file not found: {raw_path}")

        records = build_competition_practice_snapshot(source_paths)
        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Built competition practice snapshot: {output_path} ({len(records)} rows)"))
