#!/usr/bin/env python3
"""U.S. Constitution provisions (SCOPE §4.2) -> data/norms/us-const.json.
Text read verbatim from the National Archives transcriptions (archives.gov); official_url = constitution.congress.gov."""
import html, json, re, os, sys, urllib.request, datetime, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import ROOT, RAW

SRC = {"const": "https://www.archives.gov/founding-docs/constitution-transcript",
       "bor": "https://www.archives.gov/founding-docs/bill-of-rights-transcript",
       "am": "https://www.archives.gov/founding-docs/amendments-11-27"}
os.makedirs(RAW + "/const", exist_ok=True)


def text_of(k):
    fn = f"{RAW}/const/{k}.html"
    if not os.path.exists(fn) or "--refresh" in sys.argv:
        req = urllib.request.Request(SRC[k], headers={"User-Agent": "Mozilla/5.0 flb"})
        open(fn, "wb").write(urllib.request.urlopen(req, timeout=60).read())
    s = html.unescape(re.sub(r"<[^>]+>", " ", open(fn, encoding="utf-8", errors="ignore").read()))
    return re.sub(r"\s+", " ", s)


def cut(s, start, end):
    i = s.index(start); j = s.index(end, i) + len(end)
    return s[i:j]


P = [
    ("art1-s8-cl1", "Art. I, § 8, cl. 1", "Spending Clause (Taxing and Spending Power)", "const",
     "The Congress shall have Power To lay and collect Taxes", "shall be uniform throughout the United States;", "1789-03-04",
     "https://constitution.congress.gov/browse/article-1/section-8/clause-1/", ["us.support.title-iv-d", "us.constitution.federalism"]),
    ("art2-s2-cl2", "Art. II, § 2, cl. 2", "Treaty Clause", "const",
     "He shall have Power, by and with the Advice and Consent of the Senate, to make Treaties", "or in the Heads of Departments.", "1789-03-04",
     "https://constitution.congress.gov/browse/article-2/section-2/clause-2/", ["us.constitution.treaties"]),
    ("art4-s1", "Art. IV, § 1", "Full Faith and Credit Clause", "const",
     "Full Faith and Credit shall be given", "and the Effect thereof.", "1789-03-04",
     "https://constitution.congress.gov/browse/article-4/section-1/", ["us.jurisdiction.full-faith-credit"]),
    ("art6-cl2", "Art. VI, cl. 2", "Supremacy Clause", "const",
     "This Constitution, and the Laws of the United States", "to the Contrary notwithstanding.", "1789-03-04",
     "https://constitution.congress.gov/browse/article-6/clause-2/", ["us.constitution.treaties", "us.constitution.preemption"]),
    ("amend5", "Amend. V", "Fifth Amendment (Due Process; equal-protection component)", "bor",
     "No person shall be held to answer", "without just compensation.", "1791-12-15",
     "https://constitution.congress.gov/constitution/amendment-5/", ["us.constitution.due-process"]),
    ("amend14-s1", "Amend. XIV, § 1", "Fourteenth Amendment — Citizenship, Due Process, Equal Protection", "am",
     "All persons born or naturalized in the United States", "the equal protection of the laws.", "1868-07-09",
     "https://constitution.congress.gov/browse/amendment-14/section-1/", ["us.constitution.due-process", "us.constitution.equal-protection"]),
]


def main():
    norms = []
    for nid, num, head, src, a, b, d, url, iss in P:
        t = cut(text_of(src), a, b)
        norms.append({"id": "us-const-" + nid, "corpus": "us-const", "side": "us", "lang": "en", "kind": "article",
                      "num": "U.S. Const. " + num, "heading": head, "path": [{"label": "Constitution of the United States"}],
                      "text": t, "in_force_since": d, "status": "in force", "applies_to": ["US"],
                      "official_url": url, "alt_urls": [{"label": "National Archives transcription", "url": SRC[src]}],
                      "source_ids": {"const": num, "text_sha1": hashlib.sha1(t.encode()).hexdigest()},
                      "d_method": "entry into force of the Constitution (1789-03-04) / ratification of the amendment; never amended",
                      "issues": iss, "xrefs": [], "interps": []})
    json.dump({"corpus": "us-const", "generated": datetime.date.today().isoformat(), "norms": norms},
              open(ROOT + "/data/norms/us-const.json", "w"), indent=2, ensure_ascii=False)
    print(len(norms))


if __name__ == "__main__":
    main()
