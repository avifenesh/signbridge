"""SignBridge Sign Dictionary Pipeline — CLI entry point.

Usage:
    python -m dictionary.cli extract <video> --sign-id <id> --gloss <GLOSS> [--output <path>]
    python -m dictionary.cli build [--signs-dir <dir>] [--output <path>]
    python -m dictionary.cli validate [--dictionary <path>]
    python -m dictionary.cli info [--dictionary <path>]
    python -m dictionary.cli fingerspell <word>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dictionary.config import DICTIONARY_FILE, OUTPUT_DIR


def cmd_extract(args: argparse.Namespace) -> None:
    """Extract landmarks from a video file."""
    from dictionary.extract.mediapipe import extract_video, save_extraction
    from dictionary.extract.normalize import normalize_extraction
    from dictionary.keyframes.select import reindex_keyframes, select_keyframes

    print(f"Extracting: {args.video}")
    print(f"  sign_id: {args.sign_id}")
    print(f"  gloss:   {args.gloss}")

    result = extract_video(args.video, args.sign_id, args.gloss)
    print(f"  Extracted {len(result.frames)} raw frames at {result.fps:.1f} fps")

    result = normalize_extraction(result)
    print(f"  Normalized to unit space")

    keyframes = select_keyframes(result)
    keyframes = reindex_keyframes(keyframes)
    print(f"  Selected {len(keyframes)} keyframes")

    # Save raw extraction
    output = Path(args.output) if args.output else OUTPUT_DIR / "extractions" / f"{args.sign_id}.json"
    save_extraction(result, output)

    # Save keyframes separately
    kf_output = output.parent / f"{args.sign_id}_keyframes.json"
    kf_data = {
        "sign_id": args.sign_id,
        "gloss": args.gloss,
        "keyframe_count": len(keyframes),
        "duration_ms": keyframes[-1].time_ms if keyframes else 0,
        "frames": [
            {
                "time_ms": f.time_ms,
                **({"left_hand": f.left_hand} if f.left_hand else {}),
                **({"right_hand": f.right_hand} if f.right_hand else {}),
                **({"body": f.body} if f.body else {}),
                **({"face": f.face} if f.face else {}),
            }
            for f in keyframes
        ],
    }
    kf_output.parent.mkdir(parents=True, exist_ok=True)
    with open(kf_output, "w") as f:
        json.dump(kf_data, f, indent=2)

    print(f"  Saved extraction: {output}")
    print(f"  Saved keyframes:  {kf_output}")


def cmd_build(args: argparse.Namespace) -> None:
    """Build dictionary.json from extracted sign data."""
    from dictionary.build.builder import build_dictionary

    signs_dir = Path(args.signs_dir) if args.signs_dir else OUTPUT_DIR / "extractions"
    output = Path(args.output) if args.output else DICTIONARY_FILE

    # Load all keyframe files
    sign_entries = []
    if signs_dir.exists():
        for kf_file in sorted(signs_dir.glob("*_keyframes.json")):
            with open(kf_file) as f:
                kf_data = json.load(f)

            sign_id = kf_data["sign_id"]
            gloss = kf_data["gloss"]
            duration_ms = kf_data.get("duration_ms", 0)
            frames = kf_data.get("frames", [])

            entry = {
                "sign_id": sign_id,
                "gloss": gloss,
                "duration_ms": round(duration_ms),
                "category": "sign",
                "frames": [
                    {
                        "time_ms": f["time_ms"],
                        "joints": {
                            **(f.get("right_hand", {})),
                            **(f.get("left_hand", {})),
                            **(f.get("body", {})),
                        },
                        **({"face": f["face"]} if "face" in f else {}),
                    }
                    for f in frames
                ],
            }
            sign_entries.append(entry)
            print(f"  Loaded: {sign_id} ({gloss}) — {len(frames)} keyframes")

    print(f"Loaded {len(sign_entries)} extracted signs")

    result = build_dictionary(
        sign_entries,
        include_fingerspelling=not args.no_fingerspelling,
        include_numbers=not args.no_numbers,
        output_path=output,
    )

    meta = result["_meta"]
    print(f"Built dictionary: {output}")
    print(f"  Signs: {meta['total_signs']}")
    print(f"  Fingerspelling: {meta['total_fingerspelling']}")
    print(f"  Numbers: {meta['total_numbers']}")
    print(f"  Total entries: {meta['total_entries']}")

    # Report file size
    size_bytes = output.stat().st_size
    if size_bytes > 1_000_000:
        print(f"  File size: {size_bytes / 1_000_000:.1f} MB")
    else:
        print(f"  File size: {size_bytes / 1_000:.1f} KB")


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate a dictionary.json file."""
    from dictionary.build.builder import load_dictionary
    from dictionary.validate.quality import validate_dictionary

    path = Path(args.dictionary) if args.dictionary else DICTIONARY_FILE
    print(f"Validating: {path}")

    dictionary = load_dictionary(path)
    report = validate_dictionary(dictionary)
    print(report.summary())

    if report.failing > 0:
        sys.exit(1)


def cmd_info(args: argparse.Namespace) -> None:
    """Show info about a dictionary.json file."""
    from dictionary.build.builder import load_dictionary

    path = Path(args.dictionary) if args.dictionary else DICTIONARY_FILE
    dictionary = load_dictionary(path)

    meta = dictionary.get("_meta", {})
    signs = dictionary.get("signs", {})

    print(f"Dictionary: {path}")
    print(f"  Version: {meta.get('version', 'unknown')}")
    print(f"  Total entries: {meta.get('total_entries', len(signs))}")
    print(f"  Signs: {meta.get('total_signs', '?')}")
    print(f"  Fingerspelling: {meta.get('total_fingerspelling', '?')}")
    print(f"  Numbers: {meta.get('total_numbers', '?')}")
    print()

    # Category breakdown
    categories: dict[str, int] = {}
    for sign in signs.values():
        cat = sign.get("category", "uncategorized")
        categories[cat] = categories.get(cat, 0) + 1
    print("  Categories:")
    for cat, count in sorted(categories.items()):
        print(f"    {cat}: {count}")

    # Size estimate
    size_bytes = path.stat().st_size
    if size_bytes > 1_000_000:
        print(f"\n  File size: {size_bytes / 1_000_000:.1f} MB")
    else:
        print(f"\n  File size: {size_bytes / 1_000:.1f} KB")


def cmd_export(args: argparse.Namespace) -> None:
    """Export dictionary in Android app format (bones + quaternions + float face)."""
    from dictionary.build.builder import load_dictionary
    from dictionary.build.export import export_for_app

    dict_path = Path(args.dictionary) if args.dictionary else DICTIONARY_FILE
    output_dir = Path(args.output) if args.output else Path("app/src/main/assets/dictionary")

    print(f"Loading: {dict_path}")
    dictionary = load_dictionary(dict_path)

    signs = dictionary.get("signs", {})
    print(f"  {len(signs)} entries to convert")

    print(f"Exporting to: {output_dir}")
    app_dict_path, trans_path = export_for_app(dictionary, output_dir)

    dict_size = app_dict_path.stat().st_size
    trans_size = trans_path.stat().st_size
    print(f"  dictionary.json: {dict_size / 1000:.1f} KB")
    print(f"  transitions.json: {trans_size / 1000:.1f} KB")
    print("Done — app-compatible format with bone quaternions + float face values")


def cmd_fingerspell(args: argparse.Namespace) -> None:
    """Preview fingerspelling sequence for a word."""
    from dictionary.build.fingerspelling import build_fingerspelling_sequence

    word = args.word.upper()
    frames = build_fingerspelling_sequence(word)
    print(f"Fingerspelling: {word}")
    print(f"  Frames: {len(frames)}")
    total_ms = frames[-1].time_ms if frames else 0
    print(f"  Duration: {total_ms}ms")
    print()
    for f in frames:
        hand = f.right_hand or {}
        tip = hand.get("index_tip", [0, 0, 0])
        print(f"  {f.time_ms:6.0f}ms  index_tip={tip}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dictionary",
        description="SignBridge Sign Dictionary Pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # extract
    p_extract = sub.add_parser("extract", help="Extract landmarks from video")
    p_extract.add_argument("video", help="Path to video file")
    p_extract.add_argument("--sign-id", required=True, help="Sign identifier (e.g., 'book')")
    p_extract.add_argument("--gloss", required=True, help="ASL gloss (e.g., 'BOOK')")
    p_extract.add_argument("--output", help="Output path for extraction JSON")

    # build
    p_build = sub.add_parser("build", help="Build dictionary.json")
    p_build.add_argument("--signs-dir", help="Directory with extracted keyframe files")
    p_build.add_argument("--output", help="Output path for dictionary.json")
    p_build.add_argument("--no-fingerspelling", action="store_true", help="Exclude fingerspelling")
    p_build.add_argument("--no-numbers", action="store_true", help="Exclude numbers")

    # validate
    p_validate = sub.add_parser("validate", help="Validate dictionary.json")
    p_validate.add_argument("--dictionary", help="Path to dictionary.json")

    # info
    p_info = sub.add_parser("info", help="Show dictionary info")
    p_info.add_argument("--dictionary", help="Path to dictionary.json")

    # export
    p_export = sub.add_parser("export", help="Export dictionary for Android app")
    p_export.add_argument("--dictionary", help="Path to source dictionary.json")
    p_export.add_argument("--output", help="Output directory for app assets")

    # fingerspell
    p_fs = sub.add_parser("fingerspell", help="Preview fingerspelling for a word")
    p_fs.add_argument("word", help="Word to fingerspell")

    args = parser.parse_args()

    commands = {
        "extract": cmd_extract,
        "build": cmd_build,
        "validate": cmd_validate,
        "export": cmd_export,
        "info": cmd_info,
        "fingerspell": cmd_fingerspell,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
