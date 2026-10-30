"""Entry point. The offline guard is installed before anything else runs (SPEC 12.1 layer 4)."""
from wholecount.guard import install_for_app

install_for_app()

from wholecount import copy  # noqa: E402
from wholecount.brand import VERSION  # noqa: E402


def main():
    # The window arrives in M10.
    print(copy.get("app.version_line", version=VERSION))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
