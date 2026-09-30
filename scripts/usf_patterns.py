"""Regex patterns (per candidate group) used to enumerate opinions citing/discussing the included norms/rules."""
import re

US = r"U\.\s?S\.\s?C\.(?:\s?A\.)?\s*(?:§§?|[Ss]ec(?:tion)?s?\.?)?\s*"


def st(title, secs):
    return rf"\b{title}\s*{US}(?:{secs})(?![0-9])"


G = {
 "icara": [st(42, "1160[1-9]|11610|11611"), st(22, "900[1-9]|9010|9011"), r"International Child Abduction Remedies Act",
           r"Hague Convention on the Civil Aspects", r"\bICARA\b", r"Hague Convention[^.]{0,80}(?:abduct|wrongful(?:ly)? (?:removal|removed|retain|retention))"],
 "pkpa": [r"1738A", r"Parental Kidnap(?:p)?ing Prevention Act"],
 "ffccsoa": [r"1738B", r"Full Faith and Credit for Child Support Orders"],
 "doma": [r"1738C", r"Defense of Marriage Act", r"Respect for Marriage Act", st(1, "7")],
 "evidence-service": [st(28, "1781|1782"), r"§\s*1782\b", r"Hague Service Convention", r"Hague Evidence Convention",
                      r"Convention on the Service Abroad", r"Convention on the Taking of Evidence Abroad"],
 "iaa": [r"Intercountry Adoption Act", st(42, r"149\d\d"), r"Hague Adoption Convention", r"Convention on Protection of Children and Co-operation in Respect of Intercountry Adoption"],
 "ipkca": [r"International Parental Kidnap(?:p)?ing Crime Act", st(18, "1204"), r"§\s*1204\b"],
 "goldman": [r"Goldman International Child Abduction", st(22, r"91[0-4]\d")],
 "title-iv-d": [r"Title IV-D", r"\bIV-D\b", st(42, r"6(?:5[1-9]|6[0-9])[a-b]?"), r"Child Support Enforcement Amendments", r"Family Support Act of 1988"],
 "tax-alimony": [st(26, r"71|215"), r"(?:§|[Ss]ection)\s*71\((?:a|b|c|f)\)", r"(?:§|[Ss]ection)\s*215\b[^.]{0,120}alimony", r"alimony[^.]{0,120}(?:§|[Ss]ection)\s*(?:71|215)\b"],
 "tax-1041": [st(26, "1041"), r"(?:§|[Ss]ection)\s*1041\b"],
 "tax-dependency": [r"152\(e\)", r"dependency exemption", r"child tax credit", st(26, r"24")],
 "tax-marital-deduction": [r"marital deduction", st(26, r"2056A?|2523"), r"qualified domestic trust", r"(?:§|[Ss]ection)\s*(?:2056|2523)\b"],
 "tax-6015": [st(26, "6015"), r"(?:§|[Ss]ection)\s*6015\b", r"innocent spouse"],
 "qdro": [r"qualified domestic relations order", r"\bQDRO", r"1056\(d\)", r"414\(p\)"],
 "usfspa": [r"Uniformed Services Former Spouses", st(10, "1408"), r"§\s*1408\b"],
 "social-security-spouse": [st(42, r"402|416"), r"divorced (?:wife|husband|spouse)", r"surviving divorced", r"(?:wife's|husband's|widow's|widower's) (?:insurance )?benefits"],
 "bankruptcy-dso": [r"523\(a\)\((?:5|15)\)", r"domestic support obligation", r"362\(b\)\(2\)", r"507\(a\)\(1\)", r"101\(14A\)", r"523\(a\)\(18\)"],
 "imm-family": [st(8, r"1186a|1154|1151"), r"1186a", r"1154\((?:a|c)\)", r"1101\(b\)\((?:1|2)\)", r"1151\(b\)\(2\)", r"immediate relative",
                r"sham marriage", r"conditional (?:permanent )?resident", r"marriage fraud", r"bona fide marriage"],
 "nationality": [st(8, r"1401|1409|1431|1433"), r"Child Citizenship Act", r"1401\((?:a|g)\)", r"1409\((?:a|c)\)", r"derivative citizenship", r"(?:§|[Ss]ection)\s*1432\b"],
 "dv-federal": [st(18, r"2261A?|2262|2265"), r"2261A", r"interstate domestic violence", r"interstate (?:stalking|violation of (?:a )?protection order)", r"§\s*226[125]\b"],
 "dv-firearms": [r"922\(g\)\((?:8|9)\)", r"921\(a\)\(33\)", r"misdemeanor crime of domestic violence"],
 "domestic-relations-exception": [r"domestic[- ]relations exception", r"Ankenbrandt", r"Barber v\. Barber", r"In re Burrus", r"probate exception"],
 "rooker-feldman-family": [r"Rooker[- ]Feldman"],
 "younger-family": [r"Younger v\. Harris", r"Younger abstention", r"Moore v\. Sims"],
 "parental-rights": [r"parental rights", r"Meyer v\. Nebraska", r"Pierce v\. Society of Sisters", r"Stanley v\. Illinois", r"Santosky", r"Troxel",
                     r"Lehr v\. Robertson", r"Quilloin", r"Caban v\. Mohammed", r"Michael H\. v\. Gerald D", r"Lassiter v\. Department of Social",
                     r"Prince v\. Massachusetts", r"Wisconsin v\. Yoder", r"Parham v\. J", r"M\.\s?L\.\s?B\. v\. S\.\s?L\.\s?J", r"familial (?:association|integrity|privacy)",
                     r"Moore v\. (?:City of )?East Cleveland", r"Smith v\. Organization of Foster Families", r"care, custody,? and (?:control|management)"],
 "marriage-right": [r"right to marry", r"Loving v\. Virginia", r"Zablocki", r"Obergefell", r"same-sex marriage", r"Turner v\. Safley"],
 "pj-family": [r"Kulko", r"May v\. Anderson"],
 "ffc-judgments-family": [r"Full Faith and Credit Clause", r"Williams v\. North Carolina", r"Estin v\. Estin", r"Sherrer v\. Sherrer", r"Vanderbilt v\. Vanderbilt", r"divisible divorce",
                          r"[Ff]ull [Ff]aith and [Cc]redit[^.]{0,200}(?:divorce|custody|adoption|alimony|child support|decree of)"],
 "federal-preemption-family": [r"Hisquierdo", r"McCarty v\. McCarty", r"Mansell", r"Hillman v\. Maretta", r"Egelhoff", r"Boggs v\. Boggs", r"Ridgway v\. Ridgway",
                               r"Rose v\. Rose", r"Wissner v\. Wissner", r"Free v\. Bland", r"community property[^.]{0,120}preempt"],
 "nonmarital-children-ep": [r"illegitima(?:te|cy)[^.]{0,200}[Ee]qual [Pp]rotection", r"[Ee]qual [Pp]rotection[^.]{0,200}illegitima", r"nonmarital child",
                            r"Trimble v\. Gordon", r"Clark v\. Jeter", r"Levy v\. Louisiana", r"Mills v\. Habluetzel", r"Gomez v\. Perez", r"Lalli v\. Lalli"],
 "sex-classifications-family": [r"Orr v\. Orr", r"Stanton v\. Stanton", r"Kirchberg", r"Califano v\. Goldfarb", r"Weinberger v\. Wiesenfeld", r"Morales-Santana", r"Nguyen v\. INS|Tuan Anh Nguyen"],
 "contempt-support": [r"Turner v\. Rogers", r"Hicks v\. Feiock", r"civil contempt[^.]{0,150}(?:child support|alimony|maintenance)"],
 "access-divorce": [r"Boddie v\. Connecticut", r"Sosna v\. Iowa"],
}

COMPILED = {g: [re.compile(p) for p in ps] for g, ps in G.items()}

# groups requiring family context when matched only by generic doctrine patterns
FAMILY_CTX = re.compile(r"custody|divorce|child support|parental|visitation|adoption|marital|dissolution|alimony|maintenance|guardian|juvenile|foster|paternity|spous", re.I)
NEEDS_CTX = {"rooker-feldman-family", "younger-family", "parental-rights", "marriage-right", "ffc-judgments-family"}


def match_groups(text):
    """Return {group: [ (start,end) ... ]} of matches."""
    out = {}
    for g, ps in COMPILED.items():
        spans = []
        for p in ps:
            for m in p.finditer(text):
                spans.append((m.start(), m.end()))
                if len(spans) > 60:
                    break
        if spans:
            if g in NEEDS_CTX and len(FAMILY_CTX.findall(text)) < 5:
                continue
            out[g] = sorted(spans)
    return out
