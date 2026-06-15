import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.models import RouteRequest, RouteResponse
from app.engine import route_symptoms
from app.request_logger import log_route_result
from app.config import cfg

app = FastAPI(
    title="Benefit Router API",
    version="1.2.0",
    description="Router symptomov nad JSON pravidlami."
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _route_with_logging(method: str, symptom_source: str, symptom_value: str):
    result = route_symptoms(symptom_source, symptom_value)
    return log_route_result(method, symptom_source, symptom_value, result)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/version")
def version():
    return {"version": cfg["version"]}


@app.post("/route", response_model=RouteResponse)
def route(req: RouteRequest):
    if not req.symptom_source or not req.symptom_value:
        raise HTTPException(400, "Missing 'symptom_source' or 'symptom_value'")
    return _route_with_logging("POST", req.symptom_source, req.symptom_value)


@app.get("/route", response_model=RouteResponse)
def route_get(
    symptom_value: str = Query(..., min_length=1),
    symptom_source: str = Query("free_text")
):
    return _route_with_logging("GET", symptom_source, symptom_value)
