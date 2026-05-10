from datetime import datetime, timezone
from typing import Any

from app.models.analysis_task import AnalysisTask


def _normalize_standards(value: object) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def build_export_payload(analysis_task: AnalysisTask) -> dict[str, Any]:
    result_payload = analysis_task.result_payload or {}
    rule_results: list[dict[str, Any]] = result_payload.get("ruleResults", [])
    for rule in rule_results:
        standards = rule.get("standards")
        if isinstance(standards, dict):
            standards["gb"] = _normalize_standards(standards.get("gb"))
            standards["mh"] = _normalize_standards(standards.get("mh"))
    return {
        "analysisTaskId": analysis_task.id,
        "importTaskId": analysis_task.import_batch_id,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": result_payload.get("summary", ""),
        "obstacleCount": result_payload.get("obstacleCount", 0),
        "selectedTargets": result_payload.get("selectedTargets", []),
        "ruleResults": rule_results,
    }
