"""Constants the guard is installed with. M01 uses the DPAPI names and M05 the Geosupport ones."""

# Bare DLL names that ctypes may load by name (SPEC 12.1). DPAPI lives in crypt32, and LocalFree in kernel32.
DPAPI_DLL_NAMES = ("crypt32", "kernel32")
DPAPI_SYMBOLS = ("CryptProtectData", "CryptUnprotectData", "LocalFree")
GEOSUPPORT_SYMBOLS = ("NYCgeo", "geo")
