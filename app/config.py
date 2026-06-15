import json
import os

RULES_JSON_PATH = os.getenv("RULES_JSON_PATH", "rules/rules.json")

cfg = {}

def load_rules():

    #Načíta JSON s pravidlami z RULES_JSON_PATH a spraví základnú validáciu.

    global cfg
    with open(RULES_JSON_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    if "logic" not in cfg or "rules" not in cfg["logic"]:
        raise ValueError("Invalid rules: missing logic.rules")

    if not isinstance(cfg["logic"]["rules"], list) or len(cfg["logic"]["rules"]) == 0:
        raise ValueError("Invalid rules: logic.rules must be a non-empty list")

    # Skontroluj prítomnosť fallbacku
    has_fb = any(r.get("match_type") == "fallback" for r in cfg["logic"]["rules"])
    if not has_fb:
        raise ValueError("Missing fallback rule (match_type = 'fallback')")

# načítaj pri importe
load_rules()