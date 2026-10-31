"""Staleness (SPEC 10.4, C-18, H13). Every node has a fingerprint over its own inputs and its parent's fingerprint. A result
stores the fingerprints it was made from; a node whose live fingerprint differs is stale."""
import hashlib

NODES = ("sources", "tables", "steps", "mappings", "standardized", "checks", "geo", "copies", "decisions", "identity",
         "programs", "counts", "confidence", "exports")
# Set-up sections and the node each feeds. The reviewer's name and calibration runs are not nodes.
SECTION_NODE = {"sources": "sources", "tables": "tables", "systems": "tables", "steps": "steps", "schema": "mappings", "mappings": "mappings",
                "defaults": "standardized", "date_orders": "standardized", "program_columns": "programs", "run_settings": "geo",
                "export_settings": "exports"}


class StaleResults(Exception):
    def __init__(self, nodes):
        super().__init__(", ".join(n for n in NODES if n in nodes))
        self.nodes = frozenset(nodes)


def downstream(node):
    """The node and every node after it."""
    return frozenset(NODES[NODES.index(node):])


def earliest(nodes):
    return min(nodes, key=NODES.index) if nodes else None


def fingerprints(own_inputs):
    """own_inputs: node -> a stable string of that node's own inputs. Returns node -> fingerprint."""
    out, parent = {}, ""
    for n in NODES:
        parent = hashlib.sha256((parent + "\x1f" + n + "\x1f" + own_inputs.get(n, "")).encode("utf-8")).hexdigest()
        out[n] = parent
    return out


def stale(live, stored):
    if stored is None:
        return frozenset(NODES)
    return frozenset(n for n in NODES if live[n] != stored.get(n))
