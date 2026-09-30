"""Shared config for the Missouri (mo-const / mo-rsmo / mo-rules) pipeline."""
import os
ROOT = "/home/user/workspace/flb"
RAW = os.path.join(ROOT, "raw", "mo")
BASE = "https://revisor.mo.gov"

# Whole chapters (every section) per SCOPE §4.3
FULL_CHAPTERS = ["451", "452", "453", "454", "455"]

# Partial chapters: explicit selections / ranges (inclusive) per SCOPE §4.3 "as relevant"/"as needed"
PARTIAL = {
    "210": {"ranges": [("210.817", "210.854"), ("210.109", "210.118"), ("210.125", "210.165"),
                       ("210.183", "210.183"), ("210.620", "210.650"), ("210.950", "210.950")]},
    "211": {"ranges": [("211.031", "211.031"), ("211.442", "211.487")]},
    "193": {"list": ["193.015", "193.075", "193.085", "193.087", "193.095", "193.115", "193.125",
                     "193.128", "193.135", "193.185", "193.195", "193.205", "193.215", "193.255"]},
    "474": {"ranges": [("474.010", "474.300"), ("474.420", "474.420")]},
    "432": {"list": ["432.010"]},
    "516": {"list": ["516.100", "516.110", "516.120", "516.350"]},
    "565": {"ranges": [("565.002", "565.002"), ("565.072", "565.076"), ("565.150", "565.160")]},
}

# Missouri Constitution sections (revisor ids use "ART    N" padding)
CONST = [("I", "2"), ("I", "10"), ("I", "33"), ("V", "5")]


def secnum_key(s):
    ch, sec = s.split(".")
    return (int(ch), int(sec))


def in_scope(ch, sec):
    """sec = full section number e.g. 452.025 (family OR procedure axis)"""
    return in_family(ch, sec) or ch in PROC_CHAPTERS


def axes_for(ch, sec):
    a = []
    if in_family(ch, sec):
        a.append("family")
    if ch in PROC_CHAPTERS:
        a.append("procedure")
    return a


def all_chapters():
    return list(dict.fromkeys(FULL_CHAPTERS + list(PARTIAL) + PROC_CHAPTERS))


def in_family(ch, sec):
    if ch in FULL_CHAPTERS:
        return True
    cfg = PARTIAL.get(ch)
    if not cfg:
        return False
    if sec in cfg.get("list", []):
        return True
    k = secnum_key(sec)
    for a, b in cfg.get("ranges", []):
        if secnum_key(a) <= k <= secnum_key(b):
            return True
    return False


# ---- Procedure axis (SCOPE §4.5, added 2026-09-30) ----
# courts.mo.gov page-id block holding Rules 41-101 (sequential ids; swept exhaustively, index copy via pplx_sdk)
RULES_SWEEP = [(199300, 200720)]
# page ids of subdivisions re-issued under new ids after amendment (located via the Perplexity web index, courts.mo.gov domain)
RULES_EXTRA_IDS = [221733, 221753, 209293, 196457]
PROC_RULES = (41, 101)          # every rule/subdivision in force
PROC_CHAPTERS = ["506", "507", "508", "509", "510", "511", "512", "513", "514", "515", "516", "517", "525"]
# family-axis rule set (pre-existing corpus)
FAMILY_RULES = ("55", "74", "75", "78", "88")
FAMILY_RULE_NUMS = ("84.16",)

# Supreme Court of Missouri orders amending Rules 41-101 after the index copies were taken (Missouri Bar copies:
# https://images.magnetmail.net/images/clients/MOBAR/attach/Orders/<n>.pdf). mode: full | sub:(x) | title | new
MOBAR_ORDERS = "https://images.magnetmail.net/images/clients/MOBAR/attach/Orders/"
ORDERS_OVERLAY = [
    {"order": 3091, "dated": "2025-03-04", "effective": "2026-01-01", "num": "41.08", "mode": "sub:(a)"},
    {"order": 3118, "dated": "2025-06-30", "effective": "2026-01-01", "num": "52.08", "mode": "full"},
    {"order": 3125, "dated": "2025-08-12", "effective": "2026-07-01", "num": "55.08", "mode": "full"},
    {"order": 3125, "dated": "2025-08-12", "effective": "2026-07-01", "num": "78.04", "mode": "title", "title": "Motion for New Trial or to Amend – Time for Filing"},
    {"order": 3125, "dated": "2025-08-12", "effective": "2026-07-01", "num": "81.05", "mode": "sub:(a)"},
    {"order": 3138, "dated": "2025-11-25", "effective": "2026-07-01", "num": "51.12", "mode": "full"},
    {"order": 3138, "dated": "2025-11-25", "effective": "2026-07-01", "num": "51.13", "mode": "full"},
    {"order": 3143, "dated": "2025-12-16", "effective": "2026-07-01", "num": "55.025", "mode": "full"},
    {"order": 3143, "dated": "2025-12-16", "effective": "2026-07-01", "num": "55.0275", "mode": "new", "title": "Sealing a Court Record",
     "comment_order": 3167, "comment_dated": "2026-04-21"},
    {"order": 3143, "dated": "2025-12-16", "effective": "2026-07-01", "num": "84.015", "mode": "full"},
    # adopted, not yet in force (recorded as pending versions in data/mo-history/rule-<num>.json)
    {"order": 3156, "dated": "2026-02-24", "effective": "2027-01-01", "num": "56.01", "mode": "pending"},
    {"order": 3163, "dated": "2026-03-31", "effective": "2027-01-01", "num": "43.01", "mode": "pending"},
    {"order": 3163, "dated": "2026-03-31", "effective": "2027-01-01", "num": "74.14", "mode": "pending"},
    {"order": 3170, "dated": "2026-06-02", "effective": "2027-01-01", "num": "57.01", "mode": "pending"},
    {"order": 3170, "dated": "2026-06-02", "effective": "2027-01-01", "num": "58.01", "mode": "pending"},
    {"order": 3170, "dated": "2026-06-02", "effective": "2027-01-01", "num": "59.01", "mode": "pending"},
    {"order": 3170, "dated": "2026-06-02", "effective": "2027-01-01", "num": "74.04", "mode": "pending"},
]
