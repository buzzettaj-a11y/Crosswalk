"""Writes docs/USER_GUIDE.md from wholecount/copy/guide.py and copies the stage images into docs/guide/img/ (M15).

    python tools/make_docs.py            write the guide (and copy images from build/screens when they're there)
    python tools/make_docs.py --check    fail when the committed guide differs from what the generator writes now
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GUIDE = ROOT / "docs" / "USER_GUIDE.md"
IMG = ROOT / "docs" / "guide" / "img"
SCREENS = ROOT / "build" / "screens"
# The populated 1440 frame of each stage, from make screens: M11 for stages 1 to 5, M12 for 6 to 9.
SOURCE_FRAMES = {"sources": "m11-01-sources-populated-1440.png", "schema": "m11-02-schema-populated-1440.png",
                 "prepare": "m11-03-prepare-populated-1440.png", "map": "m11-04-map-populated-1440.png",
                 "programs": "m11-05-programs-populated-1440.png", "run": "m12-06-run-after-1440.png",
                 "review": "m12-07-review-after-1440.png", "summary": "m12-08-summary-after-1440.png",
                 "export": "m12-09-export-after-1440.png"}


def render():
    from wholecount.copy.guide import build_guide, to_markdown

    return to_markdown(build_guide())


def images(text):
    import re

    return re.findall(r"!\[\]\(([^)]+)\)", text)


def copy_images():
    from wholecount.ui.frame.stages import BY_ID

    IMG.mkdir(parents=True, exist_ok=True)
    n = 0
    for sid, frame in SOURCE_FRAMES.items():
        src = SCREENS / frame
        if src.exists():
            shutil.copy(src, IMG / f"{BY_ID[sid].nn}-{sid}.png")
            n += 1
    return n


def check():
    want = render()
    have = GUIDE.read_text(encoding="utf-8") if GUIDE.exists() else ""
    problems = []
    if have != want:
        problems.append("docs/USER_GUIDE.md differs from what tools/make_docs.py writes; run make docs")
    problems += [f"missing image {p}" for p in images(want) if not (ROOT / "docs" / p).exists()]
    return problems


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--check" in argv:
        problems = check()
        for p in problems:
            print(p)
        return 1 if problems else 0
    GUIDE.write_text(render(), encoding="utf-8")
    print(f"docs/USER_GUIDE.md, {copy_images()} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
