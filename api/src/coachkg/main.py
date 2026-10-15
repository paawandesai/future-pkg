from fastapi import FastAPI

app = FastAPI(title="coachkg", docs_url=None, redoc_url=None)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Configuration-level health only: never calls a model or reads a secret."""
    return {"status": "ok"}
