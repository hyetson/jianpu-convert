import argparse
import json
from pathlib import Path
import sys

from .pipeline import PROJECT, build, doctor
from .single import convert_single
from .dual import convert_dual


def main() -> int:
    parser = argparse.ArgumentParser(description="Staff PDF → MusicXML → numbered-notation PDF (no LilyPond)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Read-only runtime/dependency check")
    for name in ('single','dual'):
        solo = commands.add_parser(name, help="One instrument PDF/MusicXML -> numbered notation; dual expands local independent voices")
        add_part_arguments(solo, name)
    for name in ("convert", "from-musicxml"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--config", type=Path, default=PROJECT / "configs/silk-road.json")
        cmd.add_argument("--draft", action="store_true", help="Allow a clearly marked review PDF despite reported OMR errors")
        cmd.add_argument("--overwrite", action="store_true", help="Replace only generated output, never example PDFs")
        if name == "convert":
            cmd.add_argument("--audiveris", help="Absolute path to Audiveris.exe")
            cmd.add_argument("--timeout", type=int, default=1200)
        else:
            cmd.add_argument("xml", nargs="+", type=Path, help="One XML/MXL for each configured part")
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            print(json.dumps(doctor(), ensure_ascii=False, indent=2))
        else:
            if args.command in ("single","dual"):
                convert = convert_dual if args.command=='dual' else convert_single
                extra = {'primary_voice':args.primary_voice} if args.command=='dual' else {}
                result = convert(args.input, args.output, profile=args.profile, musicxml=args.musicxml,
                    instrument_name=args.instrument_name, instrument_family=args.instrument_family, part_id=args.part_id,
                    xml_part=args.xml_part, title=args.title, composer=args.composer, node_executable=args.node,
                    audiveris=args.audiveris, draft=args.draft, overwrite=args.overwrite, timeout=args.timeout, **extra)
            else:
                result = build(args.config, xml_inputs=args.xml if args.command == "from-musicxml" else None,
                           audiveris=getattr(args, "audiveris", None), draft=args.draft,
                           overwrite=args.overwrite, timeout=getattr(args, "timeout", 1200))
            summary = {key: result[key] for key in ("run", "workflow", "pdf", "score", "report", "resolvedConfig", "errors", "warnings") if key in result}
            summary["pages"] = result.get("render", {}).get("pages")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def add_part_arguments(solo, name):
    solo.add_argument("input", type=Path)
    solo.add_argument("--output", type=Path, required=True)
    solo.add_argument("--profile", type=Path, default=PROJECT / ('configs/dual-voice.json' if name=='dual' else 'configs/single-voice.json'))
    if name=='dual': solo.add_argument('--primary-voice',help='Source staff:voice ID used as the upper voice when both sound')
    solo.add_argument("--musicxml", type=Path, help="Reviewed XML/MXL for this PDF; skips OMR")
    solo.add_argument("--instrument-name", default="单乐器")
    solo.add_argument("--instrument-family", choices=("wind","bowed","plucked","struck-string","unknown"), default="unknown")
    solo.add_argument("--part-id", default="solo")
    solo.add_argument("--xml-part", help="Explicit source MusicXML part ID")
    solo.add_argument("--title")
    solo.add_argument("--composer")
    solo.add_argument("--node", help="Node executable; no global PATH changes")
    solo.add_argument("--audiveris")
    solo.add_argument("--timeout", type=int, default=1200)
    solo.add_argument("--draft", action="store_true")
    solo.add_argument("--overwrite", action="store_true")


if __name__ == "__main__":
    raise SystemExit(main())
