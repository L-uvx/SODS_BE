from pathlib import Path
from typing import Any

from docx import Document


# 生成分析结果的 Word 报告文件。
def build_analysis_report_docx(payload: dict[str, Any], output_path: Path) -> None:
    document = Document()
    document.add_heading("多边形障碍物分析报告", level=1)
    document.add_paragraph(f"分析任务编号: {payload['analysisTaskId']}")
    document.add_paragraph(f"导入任务编号: {payload['importTaskId']}")
    document.add_paragraph(f"生成时间: {payload['generatedAt']}")
    document.add_paragraph(f"障碍物数量: {payload['obstacleCount']}")
    document.add_paragraph(f"结论摘要: {payload['summary']}")

    document.add_heading("选中目标", level=2)
    selected_targets = payload.get("selectedTargets", [])
    if not selected_targets:
        document.add_paragraph("无")
    else:
        for target in selected_targets:
            document.add_paragraph(
                f"{target['name']} ({target['category']})",
                style="List Bullet",
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
