"""The app's data folder (SPEC 5.1, P-GEO-4): %LOCALAPPDATA%\\Wholecount on Windows, WHOLECOUNT_DATA_DIR elsewhere."""
import os
import pathlib
import sys

from wholecount.brand import PRODUCT_NAME


def data_dir(platform=None, env=None):
    platform = sys.platform if platform is None else platform
    env = os.environ if env is None else env
    if platform == "win32":
        base = env.get("LOCALAPPDATA") or str(pathlib.Path.home() / "AppData" / "Local")
        return pathlib.Path(base) / PRODUCT_NAME
    return pathlib.Path(env.get("WHOLECOUNT_DATA_DIR") or str(pathlib.Path.home() / f".{PRODUCT_NAME.lower()}"))


def reference_dir(platform=None, env=None):
    return data_dir(platform, env) / "reference"
