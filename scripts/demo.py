import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibecheck.errors import ConfigurationError, VibecheckError
from vibecheck.pipeline import analyze_images_to_dict


def main() -> int:
    """Run the local CLI demo for the image-to-vibe pipeline."""
    parser = argparse.ArgumentParser(description="Run the vibecheck image analysis pipeline.")
    parser.add_argument(
        "--img",
        action="append",
        dest="images",
        required=True,
        help="Path to an image. Repeat the flag for multiple images.",
    )
    parser.add_argument(
        "--mode",
        choices=("room", "outfit"),
        default=None,
        help="Optional analysis mode hint.",
    )
    parser.add_argument(
        "--recommend",
        action="store_true",
        help="Also run vibe-to-product recommendations (requires the rec module).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of product recommendations to return (default: 10).",
    )
    args = parser.parse_args()

    try:
        result = analyze_images_to_dict(
            args.images,
            mode=args.mode,
            with_recommendations=args.recommend,
            recommend_top_k=args.top_k,
        )
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except VibecheckError as exc:
        print(f"Pipeline error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
