"""A write spy: records every file opened for writing, every os.replace and every Path.write_* call."""
import builtins
import io
import os
import pathlib


class WriteSpy:
    def __init__(self, monkeypatch):
        self.mp = monkeypatch
        self.writes = []                  # (path, bytes or None)
        self.reads = []                   # paths opened or read for reading

    def __enter__(self):
        spy = self
        real_open = builtins.open

        def _record_open(file, mode="r", *a, **k):
            f = real_open(file, mode, *a, **k)
            if not any(c in mode for c in "wax+"):
                spy.reads.append(str(file))
            if any(c in mode for c in "wax+"):
                spy.writes.append((str(file), None))
                real_write = f.write

                def write(data):
                    spy.writes.append((str(file), data if isinstance(data, bytes) else str(data).encode("utf-8")))
                    return real_write(data)
                try:
                    f.write = write
                except AttributeError:
                    pass
            return f

        def _replace(src, dst, *a, **k):
            spy.writes.append((str(dst), None))
            return os_replace(src, dst, *a, **k)

        os_replace = os.replace
        self.mp.setattr(builtins, "open", _record_open)
        self.mp.setattr(io, "open", _record_open)
        self.mp.setattr(os, "replace", _replace)
        for name in ("read_text", "read_bytes"):
            real_r = getattr(pathlib.Path, name)

            def make_r(real_r):
                def method(p, *a, **k):
                    spy.reads.append(str(p))
                    return real_r(p, *a, **k)
                return method
            self.mp.setattr(pathlib.Path, name, make_r(real_r))
        for name in ("write_text", "write_bytes"):
            real = getattr(pathlib.Path, name)

            def make(real, name):
                def method(p, data, *a, **k):
                    spy.writes.append((str(p), data if isinstance(data, bytes) else str(data).encode("utf-8")))
                    return real(p, data, *a, **k)
                return method
            self.mp.setattr(pathlib.Path, name, make(real, name))
        return self

    def __exit__(self, *exc):
        return False

    def paths(self):
        return sorted({p for p, _ in self.writes})

    def data(self):
        return b"".join(d for _, d in self.writes if d)
