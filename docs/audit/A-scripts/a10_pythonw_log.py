"""Emulate pythonw (fds 1 and 2 closed so sys.stdout/stderr are None) and read launch-log.txt after a bad upload."""
import os, sys, time, subprocess, urllib.request, urllib.error
work, home, tmp = sys.argv[1], sys.argv[2], sys.argv[3]
env = dict(os.environ, BROWSER="true", HOME=home, TMPDIR=tmp)
for f in ("launch-log.txt", "crosswalk.pid", ".installed"):
    p = os.path.join(work, f)
    if os.path.exists(p): os.remove(p)
def closefds():
    os.close(1); os.close(2)
p = subprocess.Popen([sys.executable, "launch.py"], cwd=work, env=env, stdin=subprocess.DEVNULL, preexec_fn=closefds)
def req(path, method="GET", data=None, headers=None, timeout=5):
    r = urllib.request.Request(f"http://127.0.0.1:8765{path}", data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(r, timeout=timeout) as x:
        return x.status, x.read()
for _ in range(200):
    try: req("/api/alive"); break
    except Exception: time.sleep(0.25)
def multipart(name, content):
    b = "----x"
    body = (f'--{b}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + content + f"\r\n--{b}--\r\n".encode()
    return body, {"Content-Type": f"multipart/form-data; boundary={b}"}
for name, content in [("Smith Maria 123-45-6789 intake.docx", b"not a table"),
                      ("good.csv", b"First_Name,Last_Name\nZebulon,Quillfeather\n")]:
    body, hdr = multipart(name, content)
    try: print("upload", name, "->", req("/api/sources/upload", "POST", body, hdr)[0])
    except urllib.error.HTTPError as e: print("upload", name, "-> HTTP", e.code)
try: req("/api/quit", "POST", b"{}")
except Exception as e: print("quit:", e)
for _ in range(60):
    if p.poll() is not None: break
    time.sleep(0.25)
if p.poll() is None: p.kill()
print("exit", p.poll())
print("----- launch-log.txt")
print(open(os.path.join(work, "launch-log.txt")).read()[-4000:])
