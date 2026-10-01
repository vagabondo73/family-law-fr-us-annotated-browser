"""Sharded output for the static site (imported by site_build.py).

- corpus light index  data/corpus/<cid>.json      {corpus, paths:[[{label,id}…]…], chunks:{t:n, i:n},
                                                   norms:[{id,num,heading,kind,status,axes,side,lang,corpus,p,ni,tc,ic,fixture}]}
- norm text chunks    data/corpus/<cid>/t<k>.json  {norms:[full records]}              (≤ ~600 KB each)
- interp chunks       data/corpus/<cid>/i<k>.json  {interps:{id: record}}              (per group of norms, ≤ ~1.2 MB)
- authority chunks    data/interps/<auth>/<k>.json {interps:[…]};  data/interp-index.json  id -> [auth, k]
- search index        data/search/meta.json, docs/<k>.json, p/<key>.json               (prebuilt, see build_search)
"""
import json, re, unicodedata

TEXT_BUDGET = 600_000
INTERP_BUDGET = 1_200_000
AUTH_BUDGET = 1_000_000


def jlen(o):
    return len(json.dumps(o, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def write_corpus(out, cid, lst, interps, dump):
    paths, pidx = [], {}
    light, tchunks, cur, cur_size = [], [], [], 0
    for n in lst:
        s = jlen(n)
        if cur and cur_size + s > TEXT_BUDGET:
            tchunks.append(cur); cur, cur_size = [], 0
        cur.append(n); cur_size += s
    if cur:
        tchunks.append(cur)
    tc_of = {n["id"]: k for k, ch in enumerate(tchunks) for n in ch}
    # interpretation buckets follow tree order; a bucket never splits one norm's interpretations
    ichunks, cur, cur_size, seen = [], {}, 0, set()
    ic_of = {}
    for n in lst:
        ids = [i for i in dict.fromkeys((n.get("interps") or []) + (n.get("rule_sources") or [])) if i in interps]
        if not ids:
            continue
        add = {i: interps[i] for i in ids if i not in cur}
        s = sum(jlen(v) for v in add.values())
        if s > INTERP_BUDGET:  # one norm alone exceeds the budget (e.g. a heavily cited rule): give it several chunks
            if cur:
                ichunks.append(cur); cur, cur_size = {}, 0
            ks, part, psz = [], {}, 0
            for i in ids:
                v = jlen(interps[i])
                if part and psz + v > INTERP_BUDGET:
                    ks.append(len(ichunks)); ichunks.append(part); part, psz = {}, 0
                part[i] = interps[i]; psz += v
            ks.append(len(ichunks)); ichunks.append(part)
            ic_of[n["id"]] = ks
            continue
        if cur and cur_size + s > INTERP_BUDGET:
            ichunks.append(cur); cur, cur_size = {}, 0
            add = {i: interps[i] for i in ids}
            s = sum(jlen(v) for v in add.values())
        cur.update(add); cur_size += s
        ic_of[n["id"]] = len(ichunks)
    if cur:
        ichunks.append(cur)
    for n in lst:
        key = json.dumps(n.get("path") or [], ensure_ascii=False, sort_keys=True)
        if key not in pidx:
            pidx[key] = len(paths); paths.append(n.get("path") or [])
        r = {k: n[k] for k in ("id", "num", "heading", "kind", "status", "side", "lang", "corpus") if n.get(k) is not None}
        r.update({"axes": n["axes"], "p": pidx[key], "ni": len(n.get("interps") or []), "tc": tc_of[n["id"]], "ic": ic_of.get(n["id"], -1)})
        if n.get("fixture"):
            r["fixture"] = True
        light.append(r)
    dump(out / "corpus" / f"{cid}.json", {"corpus": cid, "paths": paths, "chunks": {"t": len(tchunks), "i": len(ichunks)}, "norms": light})
    for k, ch in enumerate(tchunks):
        dump(out / "corpus" / cid / f"t{k}.json", {"norms": ch})
    for k, ch in enumerate(ichunks):
        dump(out / "corpus" / cid / f"i{k}.json", {"interps": ch})


def write_authorities(out, by_auth, dump):
    index = {}
    for aid, lst in by_auth.items():
        chunks, cur, cur_size = [], [], 0
        for it in lst:
            s = jlen(it)
            if cur and cur_size + s > AUTH_BUDGET:
                chunks.append(cur); cur, cur_size = [], 0
            cur.append(it); cur_size += s
        if cur:
            chunks.append(cur)
        for k, ch in enumerate(chunks):
            dump(out / "interps" / aid / f"{k}.json", {"authority": aid, "chunk": k, "interps": ch})
            for it in ch:
                index[it["id"]] = [aid, k]
    dump(out / "interp-index.json", index)
    return index


# ------------------------------------------------------------------ search (must mirror site/assets/js/search.js)
STOP = set(("le la les de des du un une et en au aux a l d est que qui dans par pour sur ne pas se ce il elle ou "
            "the of and to in is for on by an be or as at that with this it from are any shall may").split())
TOK = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")


def fold(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if not ("\u0300" <= ch <= "\u036f"))
    return s.lower().replace("’", "'").replace("‘", "'")


def tokens(s):
    out = []
    for m in TOK.finditer(fold(s)):
        w = m.group(0)
        out.append(w)
        if "-" in w or "." in w:
            out += [p for p in re.split(r"[-.]", w) if p]
    return out


def shard_key(tok):
    return tok[:2] if len(tok) >= 2 else "_" + tok


def norm_title(n):  # mirror of components.js normTitle
    num = str(n.get("num") or "")
    kind = n.get("kind")
    if kind == "judge-made-rule":
        return n.get("heading") or num
    if n.get("lang") == "fr":
        return f"Article {num}" if kind in ("article", "treaty-article") else num
    if re.search(r"§|U\.S\.C|C\.F\.R|Rule|Art\.", num):
        return num
    if kind in ("treaty-article", "article"):
        return f"Article {num}"
    if kind == "rule":
        return f"Rule {num}"
    if n.get("corpus") == "mo-rsmo":
        return f"Section {num}, RSMo"
    if kind == "section":
        return f"§ {num}"
    return num


GROUP_OF_SIDE = {"fr": "fr", "eu": "eu-int", "int": "eu-int", "us": "us", "mo": "mo"}
GROUPS = ["fr", "eu-int", "us", "mo"]


def group_of_auth(a):
    a = a or ""
    return "fr" if a.startswith("fr-") else "us" if a.startswith("us-") else "mo" if a.startswith("mo-") else "eu-int"


def build_search(out, norms, interps, corpus_order, ce_labels, dump, docs_per_chunk=400, lead=240):
    """Prebuilt inverted index.
    meta.json: {n, chunk, facets:"<one char per doc>", shards:{key: size}, stop:[…]}
      facet char = chr(48 + group*12 + type*6 + axesbits*2 + ce)  (group 0-3, type 0 norm/1 interp, axesbits 0-2 → 1 fam, 2 proc, 3 both→2?)
    docs/<k>.json: [[type, id, title, sub, group, src, date, fixture, lead], …]
    p/<key>.json: {token: [doc, weight, doc, weight, …]}   (docs ascending; weight = summed field weights, capped)
    """
    docs = []
    for n in sorted(norms.values(), key=lambda n: (GROUPS.index(GROUP_OF_SIDE.get(n.get("side"), "eu-int")), corpus_order.get(n["corpus"], 99), n["corpus"])):
        text = n.get("text") or n.get("summary_rule") or ""
        docs.append(({"t": 0, "id": n["id"], "title": norm_title(n), "sub": n.get("heading") or "", "g": GROUP_OF_SIDE.get(n.get("side"), "eu-int"),
                      "src": n["corpus"], "date": n.get("in_force_since") or "", "fx": 1 if n.get("fixture") else 0, "lead": text[:lead],
                      "axes": n.get("axes") or ["family"], "ce": 0},
                     [(n.get("num"), 12), (norm_title(n), 6), (n.get("heading"), 5), (" ".join(p.get("label", "") for p in n.get("path") or []), 1),
                      (text, 1), (n["id"], 8)]))
    for it in sorted(interps.values(), key=lambda i: (GROUPS.index(group_of_auth(i.get("authority"))), i.get("authority") or "", i.get("date") or "")):
        ce = list(it.get("classement_ce") or []) + [ce_labels[x] for x in it.get("issues") or [] if x in ce_labels]
        text = " … ".join(x for x in [it.get("summary")] + list(it.get("excerpts") or []) if x)
        ax = set()
        for l in it.get("norms") or []:
            ax.update(norms[l["norm"]].get("axes") or ["family"]) if l.get("norm") in norms else None
        docs.append(({"t": 1, "id": it["id"], "title": it.get("citation") or it["id"], "sub": it.get("court") or "", "g": group_of_auth(it.get("authority")),
                      "src": it.get("authority"), "date": it.get("date") or "", "fx": 1 if it.get("fixture") else 0, "lead": text[:lead],
                      "axes": sorted(ax) or ["family"], "ce": 1 if ce else 0},
                     [(it.get("citation"), 6), (it.get("number"), 10), (it.get("ecli"), 8), (it.get("court"), 1), (" ".join(it.get("titrage") or []), 2),
                      (it.get("summary"), 2), (" ".join(it.get("excerpts") or []), 1), (" ".join(ce), 3)]))
    post = {}
    facets = []
    for d, (doc, fields) in enumerate(docs):
        w = {}
        for txt, wt in fields:
            for tk in tokens(txt):
                if tk in STOP:
                    continue
                w[tk] = min(w.get(tk, 0) + wt, 250)
        for tk, v in w.items():
            post.setdefault(tk, []).extend((d, v))
        axb = (1 if "family" in doc["axes"] else 0) | (2 if "procedure" in doc["axes"] else 0)
        facets.append(chr(48 + GROUPS.index(doc["g"]) * 16 + doc["t"] * 8 + axb * 2 + doc["ce"]))
    shards = {}
    for tk, lst in post.items():
        shards.setdefault(shard_key(tk), {})[tk] = lst
    sizes = {}
    for key, obj in shards.items():
        dump(out / "search" / "p" / f"{key}.json", obj)
        sizes[key] = jlen(obj)
    for k in range(0, len(docs), docs_per_chunk):
        dump(out / "search" / "docs" / f"{k // docs_per_chunk}.json",
             [[d["t"], d["id"], d["title"], d["sub"], d["g"], d["src"], d["date"], d["fx"], d["lead"]] for d, _ in docs[k:k + docs_per_chunk]])
    dump(out / "search" / "meta.json", {"n": len(docs), "chunk": docs_per_chunk, "facets": "".join(facets), "groups": GROUPS,
                                        "shards": sizes, "stop": sorted(STOP), "version": 1})
    return {"docs": len(docs), "shards": len(sizes), "max_shard": max(sizes.values()) if sizes else 0,
            "total": sum(sizes.values()), "big": sorted(((v, k) for k, v in sizes.items()), reverse=True)[:5]}
