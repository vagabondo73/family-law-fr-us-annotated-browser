# Run with: python3 -m pplx_sdk.exec < scripts/int_fetch_texts.py   (pplx_sdk pre-bound). Saves raw texts to raw/int/texts/<key>.txt
import json, os
D = "/home/user/workspace/flb/raw/int/texts"
URLS = {
 "crc": "https://www.ohchr.org/en/instruments-mechanisms/instruments/convention-rights-child",
 "crc-opac": "https://www.ohchr.org/en/instruments-mechanisms/instruments/optional-protocol-convention-rights-child-involvement-children",
 "crc-opsc": "https://www.ohchr.org/en/instruments-mechanisms/instruments/optional-protocol-convention-rights-child-sale-children-child",
 "crc-opic": "https://www.ohchr.org/en/instruments-mechanisms/instruments/optional-protocol-convention-rights-child-communications-procedure",
 "iccpr": "https://www.ohchr.org/en/instruments-mechanisms/instruments/international-covenant-civil-and-political-rights",
 "icescr": "https://www.ohchr.org/en/instruments-mechanisms/instruments/international-covenant-economic-social-and-cultural-rights",
 "cedaw": "https://www.ohchr.org/en/instruments-mechanisms/instruments/convention-elimination-all-forms-discrimination-against-women",
 "crpd": "https://www.ohchr.org/en/instruments-mechanisms/instruments/convention-rights-persons-disabilities",
 "marriage1962": "https://www.ohchr.org/en/instruments-mechanisms/instruments/convention-consent-marriage-minimum-age-marriage-and-registration",
 "maint1956": "https://treaties.un.org/doc/Treaties/1957/05/19570525%2001-08%20AM/Ch_XX_1p.pdf",
 "ciec-table": "https://ciec1.org/wp-content/uploads/2025/03/Tableau.pdf",
 "ciec-list": "https://ciec1.org/conventions/",
 "tif2026": "https://www.state.gov/wp-content/uploads/2026/06/Treaties-in-Force-2026.pdf",
 "ssa-fr": "https://www.ssa.gov/international/Agreement_Texts/french.html",
 "consular1966": "https://treaties.un.org/doc/Publication/UNTS/Volume%20700/volume-700-I-10044-English.pdf",
}
keys = [k for k in URLS if not os.path.exists(os.path.join(D, k + ".txt"))]
res = pplx_sdk.content.fetch([URLS[k] for k in keys])
for k, r in zip(keys, res):
    if r.content:
        open(os.path.join(D, k + ".txt"), "w").write(r.content)
    print(k, r.error, len(r.content or ""))
