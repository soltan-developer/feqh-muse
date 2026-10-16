# -*- coding: utf-8 -*-
"""Non-juristic three-valued C2 proof-question evaluator.

This does NOT establish the scholarly truth of a premise or allow any
MethodRule into the historic engine. Only validates tri-state input routing.
"""
VALID_STATES={"true","false","unknown","conflict"}

def preflight(questions, asserted_states):
    if not isinstance(questions,list) or not questions:
        raise ValueError("Non-empty question list required")
    if set(asserted_states).difference(questions):
        raise ValueError("Unexpected question cannot be silently admitted")
    states=[]
    for question in questions:
        val=asserted_states.get(question,"unknown")
        if val not in VALID_STATES:
            raise ValueError("Invalid tri-state proof-question value")
        states.append((question,val))
    if any(v=="conflict" for _,v in states):
        decision="STOP_CONFLICTING_PREMISES"
    elif any(v=="unknown" for _,v in states):
        decision="STOP_UNVERIFIED_PREMISES"
    elif any(v=="false" for _,v in states):
        decision="NO_CANDIDATE_ROUTE"
    else:
        decision="HOLD_SCIENTIFIC_QUALIFICATION"
    return {
        "technical_preflight":decision,
        "premises":[{"question":q,"state":s} for q,s in states],
        "historical_admission":False,
        "juristic_verdict":None,
        "note":"All true only clears an abstract software checklist, never proves the scholarly content or authorizes a historic MethodRule."
    }
