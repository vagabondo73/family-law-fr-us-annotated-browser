#!/usr/bin/env python3
"""Missouri civil-procedure issue tree (procedure axis, SCOPE §4.5) -> data/issues/mo-proc.json (English, ids 'proc.mo.…')
and deterministic issue assignment for Supreme Court Rules 41–101 and RSMo procedural chapters.
Run directly to (re)write data/issues/mo-proc.json."""
import os, re, json

T = [
    ("proc.mo.general", "General provisions (Rules 41–50): scope, definitions, form of action, time, clerks, terms, forms of writs", [
        ("scope-definitions", "Scope, authority, definitions and application of the Rules (Rule 41)"),
        ("form-of-action", "One form of action (Rule 42)"),
        ("service-filing-papers", "Service and filing of pleadings and other papers (Rule 43)"),
        ("time", "Computation and enlargement of time (Rule 44)"),
        ("courts-clerks", "Courts always open, clerk's duties, terms of court, vacation, forms of writs, local rules (Rules 45–50)")]),
    ("proc.mo.venue-judge", "Venue, change of venue and change of judge (Rule 51; RSMo ch. 508)", [
        ("venue", "Venue and transfer for improper venue"), ("change-of-venue", "Change of venue"),
        ("change-of-judge", "Change of judge, disqualification")]),
    ("proc.mo.parties", "Parties (Rule 52; RSMo ch. 507)", [
        ("capacity-real-party", "Real party in interest, capacity, minors and incompetents, next friend"),
        ("joinder", "Joinder of claims and parties, interpleader, third-party practice"),
        ("class-derivative", "Class actions and derivative actions"),
        ("intervention", "Intervention"), ("substitution", "Substitution of parties, death, transfer of interest")]),
    ("proc.mo.commencement-process", "Commencement of action; summons and service of process (Rules 53–54; RSMo ch. 506)", [
        ("commencement", "Commencement of a civil action"),
        ("summons-service", "Summons, service of process in and outside Missouri, service by mail and publication"),
        ("long-arm", "Personal jurisdiction over non-residents; long-arm statute (RSMo 506.500 ff.)")]),
    ("proc.mo.pleadings-motions", "Pleadings, motions and hearings (Rule 55; RSMo ch. 509)", [
        ("pleading-form", "Pleadings allowed, captions, signatures, sanctions, form of pleadings"),
        ("claims-defenses", "Claims for relief, defenses, affirmative defenses, counterclaims, cross-claims"),
        ("motions", "Motions, motions to dismiss, judgment on the pleadings, more definite statement, strike"),
        ("amendment", "Amended and supplemental pleadings, relation back"),
        ("appearance-counsel", "Appearance and withdrawal of counsel, redaction, filing requirements")]),
    ("proc.mo.discovery", "Discovery (Rules 56–61)", [
        ("general-scope", "General provisions governing discovery, scope, protective orders"),
        ("interrogatories-depositions", "Interrogatories and depositions"),
        ("production-inspection", "Production of documents and things, entry upon land"),
        ("admissions", "Requests for admission"), ("examinations", "Physical and mental examinations"),
        ("sanctions", "Enforcement of discovery; sanctions")]),
    ("proc.mo.pretrial-trial", "Pre-trial and trial (Rules 62–73; RSMo ch. 510)", [
        ("pretrial", "Pre-trial conferences, trial settings, place of trial, continuances"),
        ("consolidation-separate-trials", "Consolidation and separate trials"),
        ("dismissal", "Voluntary and involuntary dismissal"),
        ("masters-receivers", "Masters and receivers (Rule 68)"),
        ("jury", "Trial by jury, jury selection, instructions, verdicts"),
        ("directed-verdict", "Directed verdict and judgment notwithstanding the verdict"),
        ("court-trial", "Trial by court; findings of fact and conclusions of law"),
        ("evidence-witnesses", "Evidence, witnesses and conduct of trial (statutory)")]),
    ("proc.mo.judgments", "Judgments and their control (Rules 74–75, 79–80; RSMo ch. 511)", [
        ("entry-finality", "Entry of judgment, partial judgments, finality"),
        ("summary-judgment", "Summary judgment"), ("default", "Default judgment and setting aside default"),
        ("relief-from-judgment", "Relief from judgment or order; clerical mistakes"),
        ("foreign-judgments", "Registration and enforcement of foreign judgments"),
        ("liens-satisfaction", "Judgment liens, revival, satisfaction"),
        ("control", "Trial court control of judgments (30-day rule)"),
        ("judge-disability", "Disability or absence of judge")]),
    ("proc.mo.post-trial", "New trials and after-trial motions; preservation of error (Rule 78)", []),
    ("proc.mo.costs", "Costs and fees (Rule 77; RSMo ch. 514)", []),
    ("proc.mo.enforcement", "Enforcement of judgments (Rules 76, 90; RSMo ch. 513, 525)", [
        ("execution", "Executions, levy, judicial sales"), ("exemptions", "Exemptions from execution"),
        ("garnishment", "Garnishment and sequestration")]),
    ("proc.mo.provisional-remedies", "Provisional and interim remedies (Rules 85, 92, 99; RSMo ch. 515)", [
        ("attachment", "Attachment"), ("injunction", "Injunctions and temporary restraining orders"),
        ("replevin", "Replevin"), ("receivers", "Receivers (statutory)")]),
    ("proc.mo.appeals", "Appeals and appellate procedure (Rules 81, 83, 84; RSMo ch. 512)", [
        ("right-time", "Right to appeal, notice of appeal, time, bonds and stays"),
        ("record-briefs", "Record on appeal, briefs, oral argument, appellate filings"),
        ("transfer", "Transfer to the Supreme Court"),
        ("decision-rehearing", "Opinions, rehearing, mandate, damages for frivolous appeals")]),
    ("proc.mo.special-actions", "Special actions (Rules 86–100)", [
        ("condemnation", "Condemnation proceedings"), ("declaratory-judgment", "Declaratory judgments"),
        ("domestic-relations", "Domestic relations and paternity cases (Rule 88)"),
        ("ejectment-land-titles", "Ejectment and land titles; partition"),
        ("habeas-corpus", "Habeas corpus"), ("extraordinary-writs", "Mandamus, prohibition, quo warranto"),
        ("change-of-name", "Change of name"), ("administrative-review", "Judicial review of administrative decisions")]),
    ("proc.mo.limitations", "Limitation of actions (RSMo ch. 516)", []),
    ("proc.mo.associate-circuit", "Associate circuit judge proceedings and small claims (RSMo ch. 517)", []),
]


def tree():
    nodes = []
    for nid, label, kids in T:
        nodes.append({"id": nid, "label": label, "children": [{"id": f"{nid}.{k}", "label": l, "children": []} for k, l in kids]})
    return {"side": "mo", "axis": "procedure", "lang": "en", "nodes": nodes}


def ids():
    out = set()
    for n in tree()["nodes"]:
        out.add(n["id"]); out |= {c["id"] for c in n["children"]}
    return out


def _sub(num):
    return [int(x) for x in re.findall(r"\d+", num)]


def proc_rule_issues(num):
    r = _sub(num)
    rule = r[0]
    sub = float(num.split(" ")[0]) if re.match(r"^\d+\.\d+$", num) else None
    g = "proc.mo."
    if rule == 41: return [g + "general.scope-definitions"]
    if rule == 42: return [g + "general.form-of-action"]
    if rule == 43: return [g + "general.service-filing-papers"]
    if rule == 44: return [g + "general.time"]
    if 45 <= rule <= 50: return [g + "general.courts-clerks"]
    if rule == 51:
        if num in ("51.01", "51.02", "51.045"): return [g + "venue-judge.venue"]
        if num in ("51.05", "51.06", "51.07", "51.15"): return [g + "venue-judge.change-of-judge"]
        return [g + "venue-judge.change-of-venue"]
    if rule == 52:
        m = {"52.01": "capacity-real-party", "52.02": "capacity-real-party", "52.03": "capacity-real-party", "52.04": "joinder",
             "52.05": "joinder", "52.06": "joinder", "52.07": "joinder", "52.08": "class-derivative", "52.09": "class-derivative",
             "52.10": "class-derivative", "52.11": "joinder", "52.12": "intervention", "52.13": "substitution"}
        return [g + "parties." + m.get(num, "joinder")]
    if rule == 53: return [g + "commencement-process.commencement"]
    if rule == 54: return [g + "commencement-process.summons-service"]
    if rule == 55:
        if num in ("55.01", "55.02", "55.03", "55.04", "55.12", "55.13", "55.14", "55.15", "55.16", "55.17", "55.18", "55.19", "55.20", "55.21", "55.22", "55.24"):
            return [g + "pleadings-motions.pleading-form"]
        if num in ("55.025", "55.035"): return [g + "pleadings-motions.appearance-counsel"]
        if num in ("55.05", "55.06", "55.07", "55.08", "55.09", "55.10", "55.11", "55.32"): return [g + "pleadings-motions.claims-defenses"]
        if num == "55.33": return [g + "pleadings-motions.amendment"]
        return [g + "pleadings-motions.motions"]
    if rule == 56: return [g + "discovery.general-scope"]
    if rule == 57: return [g + "discovery.interrogatories-depositions"]
    if rule == 58: return [g + "discovery.production-inspection"]
    if rule == 59: return [g + "discovery.admissions"]
    if rule == 60: return [g + "discovery.examinations"]
    if rule == 61: return [g + "discovery.sanctions"]
    if rule in (62, 63, 64, 65): return [g + "pretrial-trial.pretrial"]
    if rule == 66: return [g + "pretrial-trial.consolidation-separate-trials"]
    if rule == 67: return [g + "pretrial-trial.dismissal"]
    if rule == 68: return [g + "pretrial-trial.masters-receivers"]
    if rule in (69, 70, 71): return [g + "pretrial-trial.jury"]
    if rule == 72: return [g + "pretrial-trial.directed-verdict"]
    if rule == 73: return [g + "pretrial-trial.court-trial"]
    if rule == 74:
        m = {"74.04": "summary-judgment", "74.05": "default", "74.06": "relief-from-judgment", "74.14": "foreign-judgments",
             "74.07": "liens-satisfaction", "74.08": "liens-satisfaction", "74.09": "liens-satisfaction", "74.10": "liens-satisfaction",
             "74.11": "liens-satisfaction", "74.12": "liens-satisfaction", "74.13": "liens-satisfaction"}
        return [g + "judgments." + m.get(num, "entry-finality")]
    if rule == 75: return [g + "judgments.control"]
    if rule == 76: return [g + "enforcement.execution"]
    if rule == 77: return [g + "costs"]
    if rule == 78: return [g + "post-trial"]
    if rule in (79, 80): return [g + "judgments.judge-disability"]
    if rule == 81:
        return [g + "appeals.record-briefs"] if num in ("81.12", "81.13", "81.14", "81.15", "81.16", "81.17", "81.18", "81.19") else [g + "appeals.right-time"]
    if rule == 83: return [g + "appeals.transfer"]
    if rule == 84:
        return [g + "appeals.decision-rehearing"] if num in ("84.14", "84.15", "84.16", "84.17", "84.18", "84.19", "84.19", "84.20") else [g + "appeals.record-briefs"]
    if rule == 85: return [g + "provisional-remedies.attachment"]
    if rule == 86: return [g + "special-actions.condemnation"]
    if rule == 87: return [g + "special-actions.declaratory-judgment"]
    if rule == 88: return [g + "special-actions.domestic-relations"]
    if rule in (89, 93, 96): return [g + "special-actions.ejectment-land-titles"]
    if rule == 90: return [g + "enforcement.garnishment"]
    if rule == 91: return [g + "special-actions.habeas-corpus"]
    if rule == 92: return [g + "provisional-remedies.injunction"]
    if rule in (94, 97, 98): return [g + "special-actions.extraordinary-writs"]
    if rule == 95: return [g + "special-actions.change-of-name"]
    if rule == 99: return [g + "provisional-remedies.replevin"]
    if rule == 100: return [g + "special-actions.administrative-review"]
    return ["proc.mo.general"]


def proc_rsmo_issues(sec, heading=""):
    ch = sec.split(".")[0]
    h = (heading or "").lower()
    g = "proc.mo."
    if ch == "506":
        k = int(sec.split(".")[1])
        if 500 <= k <= 520: return [g + "commencement-process.long-arm"]
        if "summons" in h or "service" in h or "process" in h: return [g + "commencement-process.summons-service"]
        return [g + "general.scope-definitions"]
    if ch == "507": return [g + "parties"]
    if ch == "508":
        return [g + "venue-judge.venue"] if "venue" in h and "change" not in h else [g + "venue-judge.change-of-venue"]
    if ch == "509": return [g + "pleadings-motions"]
    if ch == "510":
        if "jur" in h: return [g + "pretrial-trial.jury"]
        if "dismiss" in h or "nonsuit" in h: return [g + "pretrial-trial.dismissal"]
        return [g + "pretrial-trial.evidence-witnesses"]
    if ch == "511": return [g + "judgments"]
    if ch == "512": return [g + "appeals"]
    if ch == "513":
        return [g + "enforcement.exemptions"] if "exempt" in h else [g + "enforcement.execution"]
    if ch == "514": return [g + "costs"]
    if ch == "515": return [g + "provisional-remedies.receivers"]
    if ch == "516": return [g + "limitations"]
    if ch == "517": return [g + "associate-circuit"]
    if ch == "525": return [g + "enforcement.garnishment"]
    return []


if __name__ == "__main__":
    p = "/home/user/workspace/flb/data/issues/mo-proc.json"
    json.dump(tree(), open(p, "w"), indent=2, ensure_ascii=False)
    print("wrote", p, len(ids()), "nodes")
