"""Entry point. The offline guard is installed before anything else runs (SPEC 12.1 layer 4)."""
from wholecount.guard import install_for_app

install_for_app()

from wholecount import copy  # noqa: E402
from wholecount.brand import VERSION  # noqa: E402


def main(argv=None):
    import sys

    argv = sys.argv[1:] if argv is None else argv
    if "--self-check" in argv:
        # M14: the only command line option besides --version, handled before any window.
        from wholecount.selfcheck import SelfCheckRefused, main as self_check

        try:
            return self_check(argv)
        except SelfCheckRefused:
            return 2
    if "--version" in argv:
        if sys.stdout is not None:
            print(copy.get("app.version_line", version=VERSION))
        return 0
    from wholecount.ui.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
