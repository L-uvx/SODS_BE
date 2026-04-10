from fastapi import FastAPI

from app.api.polygon_obstacle import router as polygon_obstacle_router
from app.core.config import Settings

app = FastAPI()
app.state.settings = Settings.from_env()
app.include_router(polygon_obstacle_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
