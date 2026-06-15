# Obsah

1. #prehľad
2. #architektúra-a-princíp
3. #formát-pravidiel-rulesjson
4. #normalizácia-textu-a-matching
5. #api-špecifikácia
6. #spustenie-lokálne-docker-desktop
7. #manuálne-volanie-klienti
8. #hot-reload-pravidiel
9. #troubleshooting
10. #bezpečnosť-a-prevádzka
11. #testovanie-a-kvalita
12. #roadmap--rozšírenia


# Prehľad
Benefit Router API je ľahká REST služba, ktorá:

- číta pravidlá z JSON súboru (rules.json),
- normalizuje vstupný text (bez diakritiky, malé písmená, odstránená interpunkcia, zbalené medzery),
- nájde prvé zhodnuté pravidlo (v poradí ako sú v JSON),
- vráti vybranú ambulanciu (clinic) a tri benefity (benefit_1..3),
- ak nič netrafí → použije sa fallback pravidlo.

Deterministická logika (žiadne LLM „hádanie“), vhodné pre integrácie, testovanie a konzistentné správanie.

# Architektúra a princíp
```
clients (curl / call.py / Postman)
          │
          ▼
    FastAPI (Uvicorn)
      ├─ /route  → route_symptoms()
      ├─ /reload → load_rules()
      └─ /version / /health
          │
          ▼
       rules.json  (jednoduchý formát s rules[])
```

- First‑match wins: prvé pravidlo v logic.rules[] s aspoň jedným zasiahnutým kľúčovým slovom → vybraná klinika.
- Výstup: clinic, benefit_1..3, selected_rule, matched_rules, fallback_used, version, trace.

# Formát pravidiel (rules.json)
Minimalistický, osekali sme všetku „engine“ konfiguráciu – ostali iba dáta potrebné pre matching a výstup.
Príklad (aktuálna pracovná verzia):
```
{
  "version": "0.6",
  "logic": {
    "rules": [
      {
        "id": "rule_skin",
        "match_type": "keyword_any",
        "keywords": [
          "koza",
          "vyrazka",
          "svrbenie",
          "..."
        ],
        "clinic": "AIP_DERM",
        "benefit_1": "Samodiagnostický nástroj",
        "benefit_2": "Dr.Max 20% off",
        "benefit_3": "Lacnejšie kúpele"
      },
      {
        "id": "rule_musculoskeletal",
        "match_type": "keyword_any",
        "keywords": [
          "koleno",
          "chrbat",
          "rameno",
          "..."
        ],
        "clinic": "AIP_FYZIO",
        "benefit_1": "Samodiagnostický nástroj",
        "benefit_2": "Dr.Max 20% off",
        "benefit_3": "Lacnejšie kúpele"
      },
      {
        "id": "rule_psychological",
        "match_type": "keyword_any",
        "keywords": [
          "depresia",
          "uzkost",
          "stres",
          "..."
        ],
        "clinic": "Psychologicke poradenstvo",
        "benefit_1": "Hedepy+",
        "benefit_2": "Podpora pre duševné zdravie",
        "benefit_3": "Animoterapia"
      },
      {
        "id": "rule_fallback",
        "match_type": "fallback",
        "clinic": "Lekar na dialku",
        "benefit_1": "Samodiagnostický nástroj",
        "benefit_2": "Dr.Max 20% off",
        "benefit_3": "Linka pre zdravie"
      }
    ]
  }
}
```

Povinné polia pre keyword_any pravidlá:

- id (string)
- match_type: "keyword_any"
- keywords: string[]
- clinic: string (interný kód ambulancie, napr. AIP_DERM)
- benefit_1..3: stringy (môžu byť aj "", ale odporúčame mať aspoň benefit_1)

Povinné polia pre fallback:

- id
- match_type: "fallback"
- clinic
- benefit_1..3


# Normalizácia textu a matching
Normalizácia je fixná v kóde:

- lowercase (na malé písmená),
- strip diacritics (odstránenie diakritiky),
- remove punctuation (ponechávajú sa len písmená/čísla/medzery),
- collapse whitespace (viacnásobné medzery → jedna, trim).

Matching: substring – po normalizácii sa považuje kľúčové slovo za zhodené, ak je podreťazcom normalizovaného vstupu.
Dôsledky:

- svrbenie zachytí aj „svrbenie kože“, „mám svrbenie“ atď.
- Pozor na „otvorené kmene“ (napr. svrb, vyrazk) – vedia zachytiť viac, než je zámer. Odporúčame ich používať cielene.


# API špecifikácia
POST /route
Request body
```
{ 
  "symptom_source": "free_text", 
  "symptom_value": "Mam vyrazku"
}
```

- symptom_source: "free_text" alebo "predefined_option" (inform. parameter, logika ho nevyužíva, ale je v modeli)
- symptom_value: vstupné symptómy

Response (200) – match
```
{
  "clinic": "AIP_DERM",
  "benefit_1": "Samodiagnostický nástroj",
  "benefit_2": "Dr.Max 20% off",
  "benefit_3": "Lacnejšie kúpele",
  "matched_rules": [
    "rule_skin"
  ],
  "selected_rule": "rule_skin",
  "fallback_used": false,
  "version": "0.6",
  "trace": {
    "normalized_input": "mam vyrazku",
    "hits": [
      {
        "rule_id": "rule_skin",
        "keywords_hit": [
          "vyrazku",
          "vyrazk"
        ]
      }
    ],
    "duration_ms": 0
  }
}
```
Response (200) – fallback
```
{
  "clinic": "Lekar na dialku",
  "benefit_1": "Samodiagnostický nástroj",
  "benefit_2": "Dr.Max 20% off",
  "benefit_3": "Linka pre zdravie",
  "matched_rules": [
    "rule_fallback"
  ],
  "selected_rule": "rule_fallback",
  "fallback_used": true,
  "version": "0.6",
  "trace": {
    "normalized_input": "bolest brucha",
    "hits": [],
    "duration_ms": 1
  }
}
```
Chybové stavy

- 400 – chýba symptom_source alebo symptom_value
- 422 – chyba pri /reload (nevalidný JSON)
- 500 – interná chyba


Ostatné endpointy

- GET /health → {"ok": true}
- GET /version → {"version": "0.6"}
- POST /reload → {"reloaded": true, "version": "0.6"}
  - načíta pravidlá z disku bez reštartu (lokálne bez autentifikácie)

# Spustenie lokálne (Docker Desktop)
Dockerfile (zjednodušený):
```Dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY rules ./rules

ENV RULES_JSON_PATH=/app/rules/rules.json
ENV PORT=3000
EXPOSE 3000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
```
Build a run
```PowerShell
docker build --no-cache -t benefit-router:local .
docker run --rm -p 3000:3000 benefit-router:local
```
Overenie
```PowerShell
curl.exe http://localhost:3000/health
```


Poznámka: --host 0.0.0.0 je potrebné, aby bol server prístupný z hosta (Windows → Docker Desktop VM → kontajner).


# Manuálne volanie (klienti)
Python klient (clients/call.py)

```Python
#!/usr/bin/env python3
import sys, json, argparse
from urllib import request, error
def post_json(url: str, payload: dict) -> dict:       
  data = json.dumps(payload).encode("utf-8")
  req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")    
  with request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
  if __name__ == "__main__":
        p = argparse.ArgumentParser()
        p.add_argument("--url", default="http://localhost:3000/route")
        p.add_argument("symptoms", nargs="*")
        args = p.parse_args()    
        
        text = " ".join(args.symptoms) or "svrbenie koze"    
        payload = {"symptom_source": "free_text", "symptom_value": text}
        print(f">> POST {args.url}")
        print(f">> payload: {json.dumps(payload, ensure_ascii=False)}\n")    resp = post_json(args.url, payload)    
        print("=== Response (pretty) ===")    
        print(json.dumps(resp, indent=2, ensure_ascii=False))    
        print("\n=== Summary ===")    
        print("Clinic (ID):", resp.get("clinic"))    
        print("Benefit 1:", resp.get("benefit_1"))    
        print("Benefit 2:", resp.get("benefit_2"))    
        print("Benefit 3:", resp.get("benefit_3"))    
        print("Selected rule:", resp.get("selected_rule"))    
        print("Matched rules:", ", ".join(resp.get("matched_rules", [])))    
        print("Fallback used:", resp.get("fallback_used"))
```
Použitie:

```bash 
python clients/call.py "Mam vyrazku"
```
Alternatíva – curl:

```Shell
curl -s -X POST http://localhost:3000/route \
  -H "Content-Type: application/json" \  
  -d '{"symptom_source":"free_text","symptom_value":"Mam vyrazku"}' | jq .
```

Hot-reload pravidiel
Ak meníš rules.json, máš dve možnosti:

1. Zabalené v image – rebuilduj image.
2. Mount z hosta – bez rebuildu + zavolaj /reload:
```PowerShell
docker run --rm -p 3000:3000 -v "C:\abs\path\to\project\rules:/app/rules" benefit-router:local
curl -X POST http://localhost:3000/reload
```



Pozor na Windows cesty – používaj absolútnu cestu. Netreba :Z (to je pre Podman/SELinux).


Troubleshooting
1. clinic je null (None)

- Over, že API odpoveď obsahuje polia clinic a selected_rule.
→ Musia byť definované v RouteResponse modeli, inak ich FastAPI odfiltruje.
- Skontroluj, že engine vybral pravidlo (trace.hits nie je prázdne) a že toto pravidlo v JSONe obsahuje clinic.
- Ak je podozrenie na skryté unicode vo názve kľúča (NBSP, BOM), engine obsahuje helper _safe_get_clinic() (odporúčané nechať zapnuté).

2. KeyError: 'engine'

- Používaš osekaný JSON bez engine sekcie – uisti sa, že engine.py používa fixnú normalizáciu (žiadne cfg["engine"]["normalization"]).

3. ImportError: cannot import name 'RouteRequest'

V app/models.py musí byť definovaný:
```Python
class RouteRequest(BaseModel):
  symptom_source: str
  symptom_value: str
```
a main.py importuje RouteRequest, RouteResponse.

4. Zmeny v kóde sa neprejavujú

- Buildni image bez cache:
```Shell
docker build --no-cache -t benefit-router:local .
```

Over obsah súborov priamo v kontajneri:
```Shell
docker run --rm benefit-router:local cat /app/app/engine.py
docker run --rm benefit-router:local cat /app/app/models.py
docker run --rm benefit-router:local cat /app/rules/rules.json
```


5. ConnectionRefusedError pri volaní klienta

- Kontajner musí bežať s -p 3000:3000.
- Uvicorn musí ísť s --host 0.0.0.0.
- Otestuj GET /health.


# Bezpečnosť a prevádzka

- Lokálne: API key netreba.
- Interná sieť / cloud: odporúčame aspoň API kľúč (hlavička x-api-key) pre citlivejšie endpointy (/reload).
- Rate limiting, CORS, logging – podľa potrieb (dajú sa ľahko doplniť).


# Testovanie a kvalita

- Unit testy: test matching (match/fallback) s fixnými vstupmi.
- Golden tests: sada vstup → očakávaný výstup (regresné testy pri úpravách slovníkov).
- Load test: nie je obvykle potrebný; substring matching nad desiatkami až stovkami kľúčových slov je veľmi rýchly.


# Roadmap / rozšírenia

- Konfigurovateľný počet vracaných benefitov (output_top_k) – momentálne fixne 3 polia.
- Admin UI na správu rules.json (CRUD + validácie).
- Rozdelenie podľa kliník (vrátiť aj benefits_by_clinic v trace alebo v tele).
- Skórovanie („pravidlo s najväčším počtom zásahov vyhráva“), ak niekedy zmeníte zo first‑match wins.


# Kontakt / podpora
Ak budeš chcieť:

doplniť validátor JSON,
pridať API key ochranu na /reload,
pripraviť šablónu testov,
alebo postaviť malý admin UI,

napíš – pripravím to ako ďalší commit / balík. 😊


Verzia dokumentácie: 1.0 (platná k verzii rules.json = 0.6)