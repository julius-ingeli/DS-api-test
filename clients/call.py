#!/usr/bin/env python3
import sys
import json
import argparse
from urllib import request, error


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.URLError as e:
        print(f"[ERROR] Cannot reach {url}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manual client for Benefit Router API")
    parser.add_argument("--url", default="http://localhost:3000/route", help="Route endpoint")
    parser.add_argument("--show-trace", action="store_true", help="Print trace scores from scoring engine")
    parser.add_argument("symptoms", nargs="*", help="Symptom text")
    args = parser.parse_args()

    text = " ".join(args.symptoms) or "svrbenie koze"

    payload = {
        "symptom_source": "free_text",
        "symptom_value": text
    }

    print(f">> POST {args.url}")
    print(f">> payload: {json.dumps(payload, ensure_ascii=False)}\n")

    resp = post_json(args.url, payload)

    print("=== Response (pretty) ===")
    print(json.dumps(resp, indent=2, ensure_ascii=False))

    print("\n=== Summary ===")
    
    print("Category:", resp.get("category"))
    print("Clinic 1:", resp.get("clinic_1"))
    print("Clinic 2:", resp.get("clinic_2"))
    print("Benefit:", resp.get("benefit"))

    print("Selected rule:", resp.get("selected_rule"))
    print("Matched rules:", ", ".join(resp.get("matched_rules", [])))
    print("Fallback used:", resp.get("fallback_used"))

    if args.show_trace:
        trace = resp.get("trace", {})
        print("\n=== Trace ===")
        print("Normalized input:", trace.get("normalized_input"))
        print("Best score:", trace.get("best_score"))

        scores = trace.get("scores", [])
        if scores:
            print("\nRule scores:")
            for s in scores:
                print(
                    f" - {s.get('rule_id')}: "
                    f"score={s.get('score')}, "
                    f"excluded={s.get('excluded')}, "
                    f"hits={s.get('hits')}"
                )

        print("\nDuration (ms):", trace.get("duration_ms"))