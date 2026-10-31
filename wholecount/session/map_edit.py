"""Match your columns, through the session layer (SPEC 3.2, 6.2): date settings and the two-digit year rule."""
from wholecount.engine.dateorder import DateFieldSetting, DateOrder, TwoDigitRule  # noqa: F401


def with_order(setting, order):
    return DateFieldSetting(DateOrder(order) if order else None, setting.pivot if setting else None)


def with_pivot(setting, pivot):
    return DateFieldSetting(setting.order if setting else None, TwoDigitRule(int(pivot)) if pivot is not None else None)
