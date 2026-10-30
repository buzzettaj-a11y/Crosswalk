"""Run launch.py for real and time its self-stop behaviour; inspect log, pid, marker."""
import os, sys, time, subprocess, json, urllib.request, shutil, socket

work = sys.argv[1]
mode = sys.argv[2]     # idle | bye | log
env = dict(os.environ, BROWSER="true", HOME=sys.argv[3], TMPDIR=sys.argv[4])

def req(path, method="GET", data=None, headers=None, port=8765, timeout=3):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(r, timeout=timeout) as x:
        return x.status, x.read()

def multipart(name, content):
    b = "----x"
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{name}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + content + f"\r\n--{b}--\r\n".encode()
    return body, {"Content-Type": f"multipart/form-data; boundary={b}"}

for f in ("launch-log.txt", "crosswalk.pid", ".installed"):
    p = os.path.join(work, f)
    if os.path.exists(p): os.remove(p)

t0 = time.time()
p = subprocess.Popen([sys.executable, "launch.py"], cwd=work, env=env,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
up = None
for _ in range(200):
    try:
        st, body = req("/api/alive"); up = time.time(); break
    except Exception:
        time.sleep(0.25)
print("server answering after %.1fs" % (up - t0), json.loads(body))
print("files while running:", sorted(f for f in os.listdir(work) if f in ("launch-log.txt","crosswalk.pid",".installed")))
for _ in range(40):
    if os.path.exists(os.path.join(work, "crosswalk.pid")): break
    time.sleep(0.1)
print("pid file:", open(os.path.join(work, "crosswalk.pid")).read(), "(launcher pid %d)" % p.pid)

if mode == "idle":
    # one heartbeat, then silence: the 'window was closed without saying goodbye' case
    req("/api/heartbeat")
    t_hb = time.time()
    while p.poll() is None and time.time() - t_hb < 200:
        time.sleep(0.5)
    print("IDLE: stopped %.1fs after the last heartbeat (exit code %s)" % (time.time() - t_hb, p.poll()))
elif mode == "bye":
    req("/api/heartbeat")
    time.sleep(1)
    req("/api/bye", "POST", b"")
    t_b = time.time()
    while p.poll() is None and time.time() - t_b < 120:
        time.sleep(0.25)
    print("BYE: stopped %.1fs after the goodbye (exit code %s)" % (time.time() - t_b, p.poll()))
elif mode == "log":
    req("/api/heartbeat")
    for name, content in [("Maria Gonzalez intake 123-45-6789.pdf", b"%PDF-1.4 not a table"),
                          ("Delgado, Pedro - referral.docx", b"hello"),
                          ("good.csv", b"First_Name,Last_Name\nZebulon,Quillfeather\n")]:
        body, hdr = multipart(name, content)
        try:
            st, _ = req("/api/sources/upload", "POST", body, hdr)
            print("upload", name, "->", st)
        except urllib.error.HTTPError as e:
            print("upload", name, "-> HTTP", e.code)
        except Exception as e:
            print("upload", name, "->", repr(e))
    try:
        req("/api/quit", "POST", b"{}")
    except Exception as e:
        print("quit", e)
    for _ in range(40):
        if p.poll() is not None: break
        time.sleep(0.25)
    print("exit code", p.poll())
if p.poll() is None:
    p.kill()
out, err = p.communicate()
print("--- process stdout/stderr (what a console would show):")
print(out.decode()[-500:], err.decode()[-1500:])
print("--- files after:", sorted(f for f in os.listdir(work) if f in ("launch-log.txt","crosswalk.pid",".installed")))
print("--- launch-log.txt:")
print(open(os.path.join(work, "launch-log.txt")).read()[-3500:])
