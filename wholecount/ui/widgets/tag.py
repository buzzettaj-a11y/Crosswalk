"""Tags (style guide Tags/README.md): needs, confirmed, wrong, neutral, plus the solid amber PRACTICE tag."""
from wholecount.ui.widgets.style import label, set_prop


def tag(text, kind="neutral"):
    w = label(text, role="tag")
    set_prop(w, "tag", kind)
    return w
