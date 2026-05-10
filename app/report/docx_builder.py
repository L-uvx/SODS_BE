from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate


def build_analysis_report_docx(payload: dict[str, Any], output_path: Path) -> None:
    template_path = Path(__file__).parent / "templates" / "analysis_report_template.docx"
    doc = DocxTemplate(str(template_path))
    doc.render(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
