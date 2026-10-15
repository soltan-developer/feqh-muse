# -*- coding: utf-8 -*-
"""
Ansari Engine v0.1 — reference implementation of the decision pipeline
extracted from Faraid al-Usul (29 rules). Deterministic, auditable:
every ruling comes with a trace of the nodes that fired.

Input : a structured "case" dict (see cases.json / DESIGN doc schema).
Output: {ruling, state: categorical|conditional|abstain, trace: [...], rule_refs: [...]}

Judgment-layer inputs (zuhur assessment, narrator wuthuq, subject diagnosis)
are INPUTS to this engine, not computed by it — exactly the boundary the
blind test identified.
"""

VALID_AMARA = {"zuhur", "khabar_wuthuq", "bayyina"}          # rule 7, 11
INVALID_AMARA = {"ijma_manqul", "shuhra", "qiyas", "zann_tashkhis_zuhur"}  # rules 8,9,10,13

def run(case):
    t = []          # trace
    refs = []       # Faraid rule numbers (from the extraction document)
    def out(ruling, state="categorical"):
        return {"ruling": ruling, "state": state, "trace": t, "rule_refs": refs}

    # ---------- L0: qat' ----------
    if case.get("qat"):
        t.append("L0: qat' attained -> follow it (hujjiyya dhatiyya)"); refs.append("Q1")
        return out(case["qat_ruling"])
    if case.get("ilm_ijmali") and case.get("qat_i_violation"):
        t.append("L0: ilm ijmali -> qat'i violation forbidden"); refs.append("Q4")
        return out("حرمت مخالفت قطعیه")

    # ---------- overriding situational principles (before istishab) ----------
    # asalat al-sihha after faragh / yad govern over istishab (rule 25)
    if case.get("override") == "sihha_faragh":
        t.append("OVERRIDE: asalat al-sihha (post-faragh) governs over istishab"); refs.append("Q25")
        return out(case["override_ruling"])
    if case.get("override") == "yad":
        t.append("OVERRIDE: yad governs over istishab"); refs.append("Q25")
        return out(case["override_ruling"])

    # ---------- L1: authorized zann ----------
    amaras = case.get("amaras", [])
    valid = [a for a in amaras if a["type"] in VALID_AMARA]
    for a in amaras:
        if a["type"] in INVALID_AMARA:
            t.append(f"L1: amara '{a['type']}' has no hujjiyya of its own -> discarded"); refs.append("Q6")
    if len(valid) >= 2 and case.get("conflict"):
        c = case["conflict"]
        if c.get("jam_possible"):
            t.append("L3: jam' urfi is possible -> combine (precedes all tarjih)"); refs.append("Q27")
            return out(c["jam_ruling"])
        if c.get("azhar"):
            t.append("L3: tarjih dalali (azhar) precedes other murajjihat"); refs.append("Q27")
            return out(c["azhar_ruling"])
        if c.get("murajjih"):
            t.append(f"L3: murajjih applies -> {c['murajjih']}"); refs.append("Q28")
            return out(c["murajjih_ruling"])
        t.append("L3: takafu' after full fahs of murajjihat -> takhyir (not tasaqut)"); refs.append("Q29")
        return out("تخییر میان دو حجت", state="conditional")
    if len(valid) == 1:
        t.append(f"L1: valid amara '{valid[0]['type']}' -> act on its mu'adda"); refs += ["Q7", "Q11"]
        return out(valid[0]["ruling"])

    # ---------- fahs gate ----------
    if not case.get("fahs_done", False) and case.get("shak_kind"):
        t.append("GATE: fahs not done -> engine cannot proceed to asl (rule: fahs is the sole condition)")
        refs.append("Q15")
        return out("نیازمند فحص از دلیل", state="abstain")

    # ---------- L2: istishab (before the other three usul) ----------
    s = case.get("sabiqa")
    if s:
        blocked = None
        if not s.get("continuity_established"):
            blocked = "continuity of mustashab not established (tafsiil: no istishab in shak fi muqtadi)"
        elif not s.get("doubt_in_rafi"):
            blocked = "doubt is not in a rafi'"
        elif not s.get("subject_survives"):
            blocked = "subject's survival in the later time is not verified (ihraz baqa' al-mawdu')"
        if blocked is None:
            # conflict between two istishabs?
            rival = case.get("rival_istishab")
            if rival:
                if s.get("governs_over_rival"):
                    t.append("L2: two istishabs conflict -> the governing (sababi/hakim) one wins"); refs.append("Q26")
                    return out(s["ruling"])
                t.append("L2: two musabbab istishabs, ilm ijmali one lapsed, no murajjih -> tasaqut"); refs.append("Q26")
                return out("تساقط دو استصحاب", state="conditional")
            t.append("L2: istishab conditions complete -> istishab, prior to bara'a/ishtighal/takhyir")
            refs += ["Q20", "Q21", "Q24", "Q25"]
            return out(s["ruling"])
        t.append(f"L2: istishab BLOCKED -> {blocked}")
        refs += ["Q21", "Q24"]
        if case.get("fallback_asl"):
            t.append(f"L2: fallback asl applies -> {case['fallback_asl']['name']}")
            return out(case["fallback_asl"]["ruling"])
        # else fall through to shak classification

    # ---------- mawdu'i asl precedes hukmi asl ----------
    if case.get("asl_mawdui"):
        t.append(f"L2: mawdu'i asl '{case['asl_mawdui']['name']}' precedes hukmi principles"); refs.append("Q25")
        return out(case["asl_mawdui"]["ruling"])

    # ---------- shak classification ----------
    k = case.get("shak_kind")
    if k == "taklif":
        t.append("L2: shak fi taklif, no ilm ijmali -> BARA'A (ibaha zahiriyya)"); refs.append("Q14")
        return out(case.get("baraa_ruling", "اباحه ظاهری (برائت)"))
    if k == "aqall_akthar":
        t.append("L2: doubt in juz'iyya (aqall/akthar) -> bara'a from the extra part"); refs.append("Q18")
        return out(case.get("baraa_ruling", "برائت از جزء مشکوک"))
    if k == "mukallaf_bih":
        if case.get("ilm_ijmali") and case.get("mahsura"):
            t.append("L2: shak fi mukallaf bih + ilm ijmali + mahsura -> IHTIYAT (avoid all sides)"); refs.append("Q16")
            return out(case.get("ihtiyat_ruling", "وجوب اجتناب از همه اطراف (احتیاط)"))
        if case.get("ilm_ijmali"):
            t.append("L2: ghayr mahsura -> ihtiyat not obligatory (limits apply)"); refs.append("Q17")
            return out(case.get("ihtiyat_ruling", "احتیاط واجب نیست"), state="conditional")
    if k == "ishtighal_dhimma":
        t.append("L2: dhimma certainly engaged, doubt in its release -> ISHTIGHAL (release needs certainty/owner consent)"); refs.append("Q16")
        return out(case.get("ishtighal_ruling", "اشتغال ذمه؛ برائت نیازمند یقین"))
    if k == "dawaran_mahzurayn":
        t.append("L2: dawaran bayn wujub/hurma -> takhyir in action, tawaqquf in iltizam"); refs.append("Q19")
        return out("تخییر عملی؛ توقف در التزام", state="conditional")

    t.append("No node fired: inputs insufficient or outside v1 scope")
    return out("نامعین — ارجاع به لایه قضاوت", state="abstain")
