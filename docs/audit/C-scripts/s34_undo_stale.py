"""s34: undo of a group decision: what the screen shows (cached identity) vs a from-scratch computation."""
from invariants import *
import messy
setup_standard(messy.make(), dob=True)
print("0 after Process                  :", counts_line())
decide("idconflict", "accept_all")
print("1 after 'accept all' on idconflict:", counts_line())
client.post("/api/review/undo")
print("2 after Undo, as the screen shows :", counts_line())
print("2 same state, computed from scratch:", counts_line(True))
uc = export_df("unique_clients"); cl = export_df("clean")
print("   Unique_Clients covers", int(uc["Source_Record_Count"].astype(int).sum()), "source rows; Final_Clean_Mapped has", len(cl))
