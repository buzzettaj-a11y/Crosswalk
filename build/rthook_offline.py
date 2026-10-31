# PyInstaller runtime hook (research R3): runs before the entry script, so the offline guard is in place before anything
# else is imported. The Geosupport folders come from the guard's own discovery (os and sys only). install_for_app is
# idempotent, so __main__ installing it again adds nothing.
from wholecount.guard import install_for_app

install_for_app()
