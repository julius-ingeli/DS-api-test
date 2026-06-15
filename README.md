# Benefit Router API

Benefit Router API is a small FastAPI service for public testing of symptom-to-benefit routing. A user enters symptom text, the engine evaluates it against `rules/rules.json`, and the API returns a selected category, service/clinic suggestions, a benefit, and trace data.

This README is intentionally bilingual. Slovak documentation is first, English documentation follows.

---

# Slovensky

## Prehlad

Benefit Router API je jednoducha REST sluzba s verejnou testovacou strankou. Pouzivatel zada symptomy, aplikacia ich normalizuje, porovna s pravidlami v `rules/rules.json` a vrati odporucanu kategoriu, dve sluzby/ambulancie a benefit.

Projekt nepouziva LLM ani generativne hadanie. Vysledok je deterministicky a zalezi iba od pravidiel v JSON subore a matching logiky v kode.

## Co aplikacia obsahuje

- FastAPI backend v `app/main.py`
- Matching engine v `app/engine.py`
- Normalizaciu textu v `app/utils.py`
- Pydantic request/response modely v `app/models.py`
- Pravidla v `rules/rules.json`
- Verejnu testovaciu HTML stranku v `app/static/index.html`
- Render konfiguraciu v `render.yaml`
- Volitelny Dockerfile pre kontajnerovy beh

## Verejne endpointy

| Metoda | Endpoint | Popis |
| --- | --- | --- |
| `GET` | `/` | Verejna testovacia stranka s inputom a outputom |
| `GET` | `/docs` | Swagger/OpenAPI dokumentacia FastAPI |
| `GET` | `/health` | Health check pre Render |
| `GET` | `/version` | Vrati verziu nacitanych pravidiel |
| `POST` | `/route` | Hlavny API endpoint pre routing symptomov |
| `GET` | `/route?symptom_value=...` | Jednoduchy GET variant pre priame testovanie |

Endpoint `/reload` nie je dostupny v live deploymente. Pravidla sa nacitaju pri starte aplikacie. Zmeny v `rules/rules.json` sa nasadzuju cez Git commit a novy deploy.

## Web UI

Po nasadeni na Render otvor hlavnu URL sluzby, napriklad:

```text
https://ds-api-test-9vyd.onrender.com/
```

Stranka zobrazi pole na zadanie symptomov a output panel s hodnotami:

- `category`
- `clinic_1`
- `clinic_2`
- `benefit`
- raw JSON odpoved API

## Priame volanie API

### POST `/route`

```bash
curl -X POST https://YOUR-RENDER-URL/route \
  -H "Content-Type: application/json" \
  -d '{"symptom_source":"free_text","symptom_value":"mam vyrazku na kozi"}'
```

Request body:

```json
{
  "symptom_source": "free_text",
  "symptom_value": "mam vyrazku na kozi"
}
```

`symptom_source` je informacne pole. Aktualna matching logika pouziva hlavne `symptom_value`.

### GET `/route`

```bash
curl "https://YOUR-RENDER-URL/route?symptom_value=bolest%20kolena"
```

GET variant je vhodny na rychle testovanie v browseri alebo cez curl. POST variant je hlavny API kontrakt pre integracie.

## Aktualny response format

Priklad uspechu:

```json
{
  "category": "AIP_DERM",
  "clinic_1": "Lekár na diaľku (Dermatológ)",
  "clinic_2": "AIP Derm",
  "benefit": "Facederma, DNA4Fit, Ksebe zadarmo",
  "matched_rules": ["rule_skin"],
  "selected_rule": "rule_skin",
  "fallback_used": false,
  "version": "0.9",
  "trace": {
    "normalized_input": "mam vyrazku na kozi",
    "scores": [],
    "eligible_rules": [],
    "distinct_categories": ["AIP_DERM"],
    "ambiguity_fallback": false,
    "best_score": 4,
    "duration_ms": 1
  }
}
```

`trace.scores` a `trace.eligible_rules` v realnej odpovedi obsahuju detailne skore a hity pre pravidla. Su uzitocne pri ladeni pravidiel.

## Ako funguje matching

### Normalizacia textu

Pred matchingom sa vstup aj keywords normalizuju:

- text sa zmeni na male pismena
- odstrani sa diakritika
- interpunkcia sa nahradi medzerami
- viacnasobne medzery sa zredukuju na jednu medzeru

Priklad: `Mám vyrážku na koži!` sa zmeni na `mam vyrazku na kozi`.

### Skorovanie pravidiel

Engine prejde vsetky pravidla okrem fallbacku:

1. Ak vstup obsahuje niektore `exclude_keywords`, pravidlo je vyradene.
2. Kazdy najdeny keyword prida skore.
3. Default vaha jednoslovneho keywordu je `1`.
4. Default vaha frazy s medzerou je `3`.
5. `keyword_weights` v pravidle moze default vahu prepisat.
6. Pravidlo je eligible, ak `score >= min_score`. Ak `min_score` chyba, pouzije sa `1`.
7. Ak matchne viac roznych kategorii naraz, engine pouzije fallback ako nejednoznacny vysledok.
8. Ak matchne jedna kategoria, vyberie sa pravidlo s najvyssim skore.
9. Ak nematchne nic, pouzije sa fallback pravidlo.

## Format `rules/rules.json`

Aktivny rules subor ma format:

```json
{
  "version": "0.9",
  "logic": {
    "rules": [
      {
        "id": "rule_skin",
        "match_type": "keyword_any",
        "keywords": ["koza", "vyrazka", "svrbenie"],
        "exclude_keywords": ["po jedle"],
        "keyword_weights": {
          "vyrazka po jedle": 12
        },
        "min_score": 1,
        "category": "AIP_DERM",
        "clinic_1": "Lekár na diaľku (Dermatológ)",
        "clinic_2": "AIP Derm",
        "benefit": "Facederma, DNA4Fit, Ksebe zadarmo"
      },
      {
        "id": "rule_fallback",
        "match_type": "fallback",
        "category": "Neindentifikovane",
        "clinic_1": "Lekar na dialku",
        "clinic_2": "Samodiagnostika",
        "benefit": "Dr. Max"
      }
    ]
  }
}
```

Povinne polia pre `keyword_any` pravidlo:

- `id`
- `match_type: "keyword_any"`
- `keywords`
- `category`
- `clinic_1`
- `clinic_2`
- `benefit`

Volitelne polia:

- `exclude_keywords`
- `keyword_weights`
- `min_score`

Fallback pravidlo musi mat `match_type: "fallback"` a vystupne polia `category`, `clinic_1`, `clinic_2`, `benefit`.

## Lokalny beh bez Dockeru

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Potom otvor:

```text
http://127.0.0.1:8010/
```

Alebo testuj API:

```bash
curl -X POST http://127.0.0.1:8010/route \
  -H "Content-Type: application/json" \
  -d '{"symptom_source":"free_text","symptom_value":"mam vyrazku na kozi"}'
```

## Docker beh

```bash
docker build -t benefit-router:local .
docker run --rm -p 3000:3000 benefit-router:local
```

Overenie:

```bash
curl http://localhost:3000/health
```

Dockerfile pouziva public base image `python:3.11-slim` a startuje Uvicorn cez `PORT` environment variable.

## Render deploy

Repo obsahuje `render.yaml`, ktory definuje web service:

```yaml
services:
  - type: web
    name: benefit-router-api
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
```

Postup:

1. Pushni repo do GitHub/GitLab/Bitbucket.
2. V Render vytvor novy Web Service alebo Blueprint z repozitara.
3. Nastav branch na `main`.
4. Auto-Deploy nastav na `On Commit`, ak chces deploy po kazdom commite do `main`.
5. Po deployi otvor URL sluzby.

Render pouziva `.python-version` a `PYTHON_VERSION=3.11`, aby aplikacia bezala na Pythone 3.11.

## Struktura projektu

```text
app/
  main.py              FastAPI routes, CORS, web UI serving
  engine.py            scoring and routing engine
  utils.py             text normalization
  models.py            request/response models
  config.py            rules loading at startup
  static/index.html    public test UI
clients/call.py        manual Python API client
rules/rules.json       active routing rules
render.yaml            Render deployment config
Dockerfile             optional container deployment
requirements.txt       Python dependencies
```

## Prevadzka a bezpecnost

- `/reload` je odstraneny, pravidla sa menia cez Git deploy.
- `CORS_ALLOW_ORIGINS` je defaultne `*`, co je vhodne na public testovanie. Pre produkciu nastav konkretne domeny.
- API nema autentifikaciu. Ak bude endpoint verejne pouzivany mimo testovania, zvaz API key alebo rate limiting.
- Odpoved obsahuje `trace`, ktory je uzitocny pre testovanie. Pre produkcne pouzitie sa da skryt alebo rozdelit na debug endpoint.

---

# English

## Overview

Benefit Router API is a lightweight REST service with a public testing page. A user enters symptoms, the app normalizes the text, evaluates it against `rules/rules.json`, and returns a selected category, two service/clinic suggestions, a benefit, and trace data.

The project does not use an LLM or generative guessing. The result is deterministic and depends only on the JSON rules and the matching logic in the code.

## What the app contains

- FastAPI backend in `app/main.py`
- Matching engine in `app/engine.py`
- Text normalization in `app/utils.py`
- Pydantic request/response models in `app/models.py`
- Rules in `rules/rules.json`
- Public test page in `app/static/index.html`
- Render deployment config in `render.yaml`
- Optional Dockerfile for container deployment

## Public endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Public testing page with symptom input and output panel |
| `GET` | `/docs` | FastAPI Swagger/OpenAPI documentation |
| `GET` | `/health` | Health check for Render |
| `GET` | `/version` | Returns the loaded rules version |
| `POST` | `/route` | Main API endpoint for symptom routing |
| `GET` | `/route?symptom_value=...` | Simple GET variant for direct testing |

The `/reload` endpoint is not available in live deployment. Rules are loaded when the app starts. Changes to `rules/rules.json` are deployed through Git commits and redeploys.

## Web UI

After deploying to Render, open the service URL, for example:

```text
https://ds-api-test-9vyd.onrender.com/
```

The page shows a symptom input and an output panel with:

- `category`
- `clinic_1`
- `clinic_2`
- `benefit`
- raw API JSON response

## Direct API usage

### POST `/route`

```bash
curl -X POST https://YOUR-RENDER-URL/route \
  -H "Content-Type: application/json" \
  -d '{"symptom_source":"free_text","symptom_value":"mam vyrazku na kozi"}'
```

Request body:

```json
{
  "symptom_source": "free_text",
  "symptom_value": "mam vyrazku na kozi"
}
```

`symptom_source` is informational. The current matching logic primarily uses `symptom_value`.

### GET `/route`

```bash
curl "https://YOUR-RENDER-URL/route?symptom_value=bolest%20kolena"
```

The GET variant is useful for quick browser or curl testing. The POST variant is the main API contract for integrations.

## Current response format

Example successful response:

```json
{
  "category": "AIP_DERM",
  "clinic_1": "Lekár na diaľku (Dermatológ)",
  "clinic_2": "AIP Derm",
  "benefit": "Facederma, DNA4Fit, Ksebe zadarmo",
  "matched_rules": ["rule_skin"],
  "selected_rule": "rule_skin",
  "fallback_used": false,
  "version": "0.9",
  "trace": {
    "normalized_input": "mam vyrazku na kozi",
    "scores": [],
    "eligible_rules": [],
    "distinct_categories": ["AIP_DERM"],
    "ambiguity_fallback": false,
    "best_score": 4,
    "duration_ms": 1
  }
}
```

In real responses, `trace.scores` and `trace.eligible_rules` include detailed rule scores and keyword hits. They are useful for rule debugging.

## How matching works

### Text normalization

Before matching, both user input and keywords are normalized:

- text is lowercased
- diacritics are removed
- punctuation is replaced with spaces
- repeated whitespace is collapsed

Example: `Mám vyrážku na koži!` becomes `mam vyrazku na kozi`.

### Rule scoring

The engine evaluates every non-fallback rule:

1. If the input contains any `exclude_keywords`, the rule is excluded.
2. Each matched keyword adds score.
3. The default weight for a single-word keyword is `1`.
4. The default weight for a phrase containing a space is `3`.
5. `keyword_weights` can override defaults per rule.
6. A rule is eligible if `score >= min_score`. If `min_score` is missing, `1` is used.
7. If multiple distinct categories match at the same time, the engine returns fallback as an ambiguous result.
8. If one category matches, the highest-scoring rule is selected.
9. If nothing matches, the fallback rule is selected.

## `rules/rules.json` format

The active rules file has this shape:

```json
{
  "version": "0.9",
  "logic": {
    "rules": [
      {
        "id": "rule_skin",
        "match_type": "keyword_any",
        "keywords": ["koza", "vyrazka", "svrbenie"],
        "exclude_keywords": ["po jedle"],
        "keyword_weights": {
          "vyrazka po jedle": 12
        },
        "min_score": 1,
        "category": "AIP_DERM",
        "clinic_1": "Lekár na diaľku (Dermatológ)",
        "clinic_2": "AIP Derm",
        "benefit": "Facederma, DNA4Fit, Ksebe zadarmo"
      },
      {
        "id": "rule_fallback",
        "match_type": "fallback",
        "category": "Neindentifikovane",
        "clinic_1": "Lekar na dialku",
        "clinic_2": "Samodiagnostika",
        "benefit": "Dr. Max"
      }
    ]
  }
}
```

Required fields for a `keyword_any` rule:

- `id`
- `match_type: "keyword_any"`
- `keywords`
- `category`
- `clinic_1`
- `clinic_2`
- `benefit`

Optional fields:

- `exclude_keywords`
- `keyword_weights`
- `min_score`

The fallback rule must have `match_type: "fallback"` and output fields `category`, `clinic_1`, `clinic_2`, and `benefit`.

## Run locally without Docker

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Then open:

```text
http://127.0.0.1:8010/
```

Or test the API:

```bash
curl -X POST http://127.0.0.1:8010/route \
  -H "Content-Type: application/json" \
  -d '{"symptom_source":"free_text","symptom_value":"mam vyrazku na kozi"}'
```

## Run with Docker

```bash
docker build -t benefit-router:local .
docker run --rm -p 3000:3000 benefit-router:local
```

Verify:

```bash
curl http://localhost:3000/health
```

The Dockerfile uses the public base image `python:3.11-slim` and starts Uvicorn with the `PORT` environment variable.

## Render deployment

The repo includes `render.yaml`, which defines the web service:

```yaml
services:
  - type: web
    name: benefit-router-api
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
```

Steps:

1. Push the repo to GitHub/GitLab/Bitbucket.
2. In Render, create a new Web Service or Blueprint from the repo.
3. Set the branch to `main`.
4. Set Auto-Deploy to `On Commit` if you want each commit to `main` to deploy automatically.
5. After deployment, open the service URL.

Render uses `.python-version` and `PYTHON_VERSION=3.11` so the app runs on Python 3.11.

## Project structure

```text
app/
  main.py              FastAPI routes, CORS, web UI serving
  engine.py            scoring and routing engine
  utils.py             text normalization
  models.py            request/response models
  config.py            rules loading at startup
  static/index.html    public test UI
clients/call.py        manual Python API client
rules/rules.json       active routing rules
render.yaml            Render deployment config
Dockerfile             optional container deployment
requirements.txt       Python dependencies
```

## Operations and security

- `/reload` has been removed; rules change through Git deploys.
- `CORS_ALLOW_ORIGINS` defaults to `*`, which is convenient for public testing. For production, set explicit domains.
- The API has no authentication. If the endpoint is used beyond testing, consider an API key or rate limiting.
- Responses include `trace`, which is useful for testing. For production use, it can be hidden or moved behind a debug endpoint.
