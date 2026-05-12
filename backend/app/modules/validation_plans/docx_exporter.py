from pathlib import Path

from docxtpl import DocxTemplate
from docx import Document

from app.modules.validation_plans.schemas import ValidationPlanRead


def ensure_default_template(template_path: Path) -> None:
    if template_path.exists():
        return
    template_path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    document.add_heading("{{ title }}", level=1)
    document.add_heading("文档履历", level=2)
    history = document.add_table(rows=2, cols=5)
    history.style = "Table Grid"
    for index, value in enumerate(["版本", "日期", "新增/修订内容概述", "编制/修订人", "批准人"]):
        history.rows[0].cells[index].text = value
    for index, value in enumerate(["V0.1", "{{ generated_date }}", "AI 生成验证方案草稿", "AI Assistant", "待审核"]):
        history.rows[1].cells[index].text = value

    document.add_heading("1. 概述", level=2)
    document.add_heading("1.1 验证的背景、目的和范围", level=3)
    document.add_paragraph("{{ overview }}")
    document.add_heading("1.2 DUT描述", level=3)
    document.add_paragraph("{{ dut_description }}")
    document.add_heading("1.3 参考文档", level=3)
    document.add_paragraph("{% for reference in reference_documents %}{{ loop.index }}. {{ reference }}\n{% endfor %}")

    document.add_heading("2. 测试项目列表", level=2)
    document.add_paragraph("{% for item in items %}{{ item.sequence }}. {{ item.title }}（{{ item.group }}）\n{% endfor %}")

    document.add_heading("3. 测试项目", level=2)
    document.add_paragraph(
        "{% for item in items %}"
        "3.{{ item.sequence }} {{ item.title }}\n"
        "3.{{ item.sequence }}.1 测试目的/测试标准\n{{ item.objective }}\n"
        "3.{{ item.sequence }}.2 测试方法/原理\n{{ item.method }}\n"
        "3.{{ item.sequence }}.3 测试工具\n待确认\n"
        "3.{{ item.sequence }}.4 测试步骤\n按模板执行并记录过程数据。\n"
        "3.{{ item.sequence }}.5 测试连接图或照片\n待补充\n"
        "3.{{ item.sequence }}.6 测试记录\n{{ item.record_template }}\n"
        "3.{{ item.sequence }}.7 需求符合性和BUG信息\n{{ item.evidence }}\n\n"
        "{% endfor %}"
    )
    document.save(template_path)


def render_validation_plan_docx(plan: ValidationPlanRead, template_path: Path, output_path: Path) -> None:
    ensure_default_template(template_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    template = DocxTemplate(template_path)
    template.render(
        {
            "title": plan.title,
            "generated_date": plan.created_at.date().isoformat(),
            "overview": plan.overview,
            "dut_description": plan.dut_description,
            "reference_documents": plan.reference_documents,
            "items": [item.model_dump() for item in plan.items],
        }
    )
    template.save(output_path)
