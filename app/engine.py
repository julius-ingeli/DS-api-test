import time
from typing import Dict, Any, List, Optional
from app.config import cfg
from app.utils import normalize_text



def _get_category(rule: Dict[str, Any]) -> Optional[str]:
    return rule.get("category")

def _get_screen(screen_id: Any) -> Optional[Dict[str, Any]]:
    if screen_id is None:
        return None
    screen = cfg.get("screens", {}).get(str(screen_id))
    if isinstance(screen, dict):
        return dict(screen)
    return None


def _collect_screens(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for key in ("screen_1_id", "screen_2_id"):
        screen = _get_screen(rule.get(key))
        if screen is not None:
            out.append(screen)
    return out


def _default_weight(term: str) -> int:
    """
    Default vaha keywordu:
    - fraza (obsahuje medzeru): 3
    - jednoduche slovo: 1
    """
    return 3 if " " in term.strip() else 1


def _score_rule(rule: Dict[str, Any], norm_input: str) -> Dict[str, Any]:
    """
    Vypocita skore pravidla.
    """
    if rule.get("match_type") == "fallback":
        return {
            "score": -1,
            "excluded": False,
            "hits": []
        }

    # tvrdy blok cez exclude_keywords
    for ex in (rule.get("exclude_keywords") or []):
        exn = normalize_text(ex)
        if exn and exn in norm_input:
            return {
                "score": -1,
                "excluded": True,
                "hits": []
            }

    score = 0
    hits: List[str] = []
    weights = rule.get("keyword_weights") or {}

    for kw in (rule.get("keywords") or []):
        kn = normalize_text(kw)
        if kn and kn in norm_input:
            hits.append(kw)
            score += weights.get(kw, _default_weight(kw))

    return {
        "score": score,
        "excluded": False,
        "hits": hits
    }


def route_symptoms(symptom_source: str, symptom_value: str) -> Dict[str, Any]:
    t0 = time.time()

    norm_input = normalize_text(symptom_value)
    rules: List[Dict[str, Any]] = cfg["logic"]["rules"]

    fallback_rule = next(
        (r for r in rules if r.get("match_type") == "fallback"),
        None
    )

    trace_scores: List[Dict[str, Any]] = []
    eligible_rules: List[Dict[str, Any]] = []

    # 1) Spočítaj skóre všetkých rules
    for rule in rules:
        if rule.get("match_type") == "fallback":
            continue

        result = _score_rule(rule, norm_input)
        category = _get_category(rule)

        min_score = rule.get("min_score", 1)

        trace_scores.append({
            "rule_id": rule.get("id"),
            "category": category,
            "score": result["score"],
            "excluded": result["excluded"],
            "hits": result["hits"],
            "min_score": min_score
        })

        # eligible = nie je excluded a splnil threshold
        if (not result["excluded"]) and result["score"] >= min_score:
            eligible_rules.append({
                "rule": rule,
                "category": category,
                "score": result["score"],
                "hits": result["hits"]
            })

    # 2) Zisti, kolko roznych kategorii matchlo
    distinct_categories = sorted({
        e["category"] for e in eligible_rules if e["category"] is not None
    })


    fallback_used = False
    ambiguity_fallback = False

    # 3) Ak matchlo viac kategorii naraz -> fallback
    if len(distinct_categories) > 1:
        best_rule = fallback_rule
        fallback_used = True
        ambiguity_fallback = True
        best_score = -1

    # 4) Ak matchla prave jedna kategoria -> vyber najlepsi rule
    elif len(eligible_rules) == 1:
        best_rule = eligible_rules[0]["rule"]
        best_score = eligible_rules[0]["score"]

    elif len(eligible_rules) > 1:
        # viac rules, ale stale ta ista kategoria
        best = max(eligible_rules, key=lambda x: x["score"])
        best_rule = best["rule"]
        best_score = best["score"]

    # 5) Ak nic nematchlo -> fallback
    else:
        best_rule = fallback_rule
        fallback_used = True
        best_score = -1



    selected_category = _get_category(best_rule) if best_rule else None
    selected_screens = _collect_screens(best_rule) if best_rule else []
    s1 = selected_screens[0] if len(selected_screens) > 0 else None
    s2 = selected_screens[1] if len(selected_screens) > 1 else None



    return {
        "category": selected_category,
        "screen_1": s1,
        "screen_2": s2,
        "matched_rules": [e["rule"]["id"] for e in eligible_rules],
        "selected_rule": best_rule.get("id") if best_rule else None,
        "fallback_used": fallback_used,
        "version": cfg.get("version", "unknown"),
        "trace": {
            "normalized_input": norm_input,
            "scores": trace_scores,
            "eligible_rules": [
                {
                    "rule_id": e["rule"]["id"],
                    "category": e["category"],
                    "score": e["score"],
                    "hits": e["hits"]
                }
                for e in eligible_rules
            ],
            "distinct_categories": distinct_categories,
            "ambiguity_fallback": ambiguity_fallback,
            "best_score": best_score,
            "duration_ms": int((time.time() - t0) * 1000)
        }
    }
