from pathlib import Path
import argparse

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--img", type=str, default=None, help="Optional: path to an image")
    args = p.parse_args()

    print("vibecheck demo ✅")
    if args.img:
        path = Path(args.img)
        print(f"img: {path} | exists: {path.exists()}")
    print("Setup is working. Next step: implement feature extraction in src/vibecheck/features/")

if __name__ == "__main__":
    main()