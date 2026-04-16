from datetime import datetime, timezone
from typing import Any

from app.models.analysis_task import AnalysisTask


def build_export_payload(analysis_task: AnalysisTask) -> dict[str, Any]:
    result_payload = analysis_task.result_payload or {}
    return {
        "analysisTaskId": analysis_task.id,
        "importTaskId": analysis_task.import_batch_id,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": result_payload.get("summary", ""),
        "obstacleCount": result_payload.get("obstacleCount", 0),
        "selectedTargets": result_payload.get("selectedTargets", []),
    }
