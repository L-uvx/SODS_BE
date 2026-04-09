from fastapi import FastAPI

from app.core.config import Settings

app = FastAPI()
app.state.settings = Settings.from_env()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
