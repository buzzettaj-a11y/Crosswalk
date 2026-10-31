"""Constants the guard is installed with. M01 uses the DPAPI names and M05 the Geosupport ones."""

# Bare DLL names that ctypes may load by name (SPEC 12.1). DPAPI lives in crypt32, and LocalFree in kernel32.
DPAPI_DLL_NAMES = ("crypt32", "kernel32")
DPAPI_SYMBOLS = ("CryptProtectData", "CryptUnprotectData", "LocalFree")
GEOSUPPORT_SYMBOLS = ("NYCgeo", "geo")

GEOSUPPORT_DEFAULT_DIRS = (r"C:\Program Files\Geosupport Desktop Edition", r"C:\Program Files (x86)\Geosupport Desktop Edition")


def discover_geosupport_dirs(environ, exists):
    """Folders of a Geosupport install whose DLLs the guard may load (SPEC 12.1 layer 4). Standard library only, because it runs
    before the guard is installed. GEOFILES points at the install's Fls folder, so its parent is the install. GEOFILES set to an
    empty value means the operator turned Geosupport off for this window, so nothing is found."""
    import ntpath

    if "GEOFILES" in environ and not environ["GEOFILES"].strip():
        return ()
    found = []
    geofiles = environ.get("GEOFILES", "").strip()
    candidates = []
    if geofiles:
        candidates.append(ntpath.dirname(geofiles.rstrip("\\/")))
    candidates.extend(GEOSUPPORT_DEFAULT_DIRS)
    for c in candidates:
        if c and exists(c) and ntpath.normcase(c) not in {ntpath.normcase(f) for f in found}:
            found.append(c)
    return tuple(found)
