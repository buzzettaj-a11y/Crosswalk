"""s31: the printable one-page summary vs the Results screen, with open proposals and with a decision undone."""
from invariants import *
import glob, re, html
sample = {os.path.basename(p): open(p, "rb").read() for p in sorted(glob.glob(ROOT + "/sample_data/*"))}
setup_standard(sample, dob=False)
h = client.get("/api/summary").text
txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))
print("Results screen:", counts_line())
body = txt[txt.find("</style>") + 1 if "</style>" in txt else 0:]; k = txt.find("Unique clients") if "Unique clients" in txt else txt.find("Goal 1"); print("printable page body:", txt[k-40:k+900])
