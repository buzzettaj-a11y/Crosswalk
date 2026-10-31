"""Writes build/version_info.txt, the exe's Windows version resource, from wholecount/brand.py (M14 section 0)."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wholecount.brand import PRODUCT_NAME, VERSION  # noqa: E402

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
                    date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{publisher}'),
      StringStruct('FileDescription', '{name}'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', '{name}'),
      StringStruct('OriginalFilename', '{name}.exe'),
      StringStruct('ProductName', '{name}'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def version_tuple(v):
    parts = [int(x) for x in v.split(".")[:4]]
    return tuple(parts + [0] * (4 - len(parts)))


def publisher():
    import json

    data = json.loads((ROOT / "tools" / "signing.json").read_text(encoding="utf-8"))
    local = ROOT / "tools" / "signing.local.json"
    if local.exists():
        data.update(json.loads(local.read_text(encoding="utf-8")))
    return data["publisher"]


def render():
    return TEMPLATE.format(t=version_tuple(VERSION), v=VERSION, name=PRODUCT_NAME, publisher=publisher())


def main():
    out = ROOT / "build" / "version_info.txt"
    out.write_text(render(), encoding="utf-8")
    print(out.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
