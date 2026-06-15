import os
from fastapi import FastAPI, HTTPException
from app.models import RouteRequest, RouteResponse
from app.engine import route_symptoms
from app.config import load_rules, cfg

app = FastAPI(
    title="Benefit Router API (Local)",
    version="1.2.0",
    description="Lokálne, manuálne volaný router nad JSON pravidlami."
)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/version")
def version():
    return {"version": cfg["version"]}

@app.post("/reload")
def reload_rules():
    try:
        load_rules()
        return {"reloaded": True, "version": cfg["version"]}
    except Exception as e:
        raise HTTPException(422, f"Invalid rules: {str(e)}")

@app.post("/route", response_model=RouteResponse)
def route(req: RouteRequest):
    if not req.symptom_source or not req.symptom_value:
        raise HTTPException(400, "Missing 'symptom_source' or 'symptom_value'")
    return route_symptoms(req.symptom_source, req.symptom_value)