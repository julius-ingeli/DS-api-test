import time
from typing import Dict, Any, List, Optional
from app.config import cfg
from app.utils import normalize_text

def _safe_get_clinic(rule: Dict[str, Any]) -> Optional[str]:
    for key in rule.keys():
        # odstránime NBSP, BOM, taby, whitespace
        cleaned = key.strip().replace("\uFEFF", "").replace("\u00A0", "")
        if cleaned == "clinic":
            return rule[key]
    return None

def _collect_rule_benefits(rule: Dict[str, Any]) -> List[str]:
    """
    Vytiahne benefit_1..3 z pravidla, ignoruje prázdne/None a zachová poradie.
    """
    out: List[str] = []
    for key in ("benefit_1", "benefit_2"):
        val = rule.get(key)
        if isinstance(val, str) and val.strip():
            out.append(val.strip())
    return out

def route_symptoms(symptom_source: str, symptom_value: str) -> Dict[str, Any]:
    t0 = time.time()

    # ✅ fix: už nečítame cfg["engine"]["normalization"]
    norm_input = normalize_text(symptom_value)

    rules: List[Dict[str, Any]] = cfg["logic"]["rules"]

    hits: List[Dict[str, Any]] = []      # pre audit: všetky hity (aj nevybrané)
    matched_rules: List[str] = []        # ID všetkých zhodnutých pravidiel
    selected_rule_id: Optional[str] = None
    selected_clinic: Optional[str] = None
    selected_benefits: List[str] = []

    # First-match-wins: vyber prvú zhodu podľa poradia v JSON-e
    for rule in rules:
        if rule.get("match_type") == "fallback":
            continue

        rule_hits: List[str] = []
        for kw in (rule.get("keywords") or []):
            kn = normalize_text(kw)
            if kn and kn in norm_input:
                rule_hits.append(kw)

        if rule_hits:
            hits.append({"rule_id": rule["id"], "keywords_hit": rule_hits})
            matched_rules.append(rule["id"])

            
            print("DEBUG MATCH RULE:", rule["id"], "clinic=", rule.get("clinic"))
            print("DEBUG HITS:", rule_hits)
            print()

            if selected_rule_id is None:
                selected_rule_id = rule["id"]
                selected_clinic = _safe_get_clinic(rule)
                selected_benefits = _collect_rule_benefits(rule)

    # Fallback, ak nič netrafí
    fallback_used = False
    if selected_rule_id is None:
        fb = next(r for r in rules if r.get("match_type") == "fallback")
        selected_rule_id = fb["id"]
        selected_clinic = _safe_get_clinic(fb)
        selected_benefits = _collect_rule_benefits(fb)
        matched_rules = [fb["id"]]
        hits = []  # fallback nemá keyword hity
        fallback_used = True

    # benefit_1..3
    b1 = selected_benefits[0] if len(selected_benefits) > 0 else None
    b2 = selected_benefits[1] if len(selected_benefits) > 1 else None

    return {
        "clinic": selected_clinic,
        "benefit_1": b1,
        "benefit_2": b2,

        "matched_rules": matched_rules,
        "selected_rule": selected_rule_id,
        "fallback_used": fallback_used,
        "version": cfg.get("version", "unknown"),

        "trace": {
            "normalized_input": norm_input,
            "hits": hits,
            "duration_ms": int((time.time() - t0) * 1000)
        }
    }