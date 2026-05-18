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
    document.add_paragraph("{% for item in items %}3.{{ item.sequence }} {{ item.title }}")
    document.add_paragraph("3.{{ item.sequence }}.1 测试目的/测试标准\n{{ item.objective }}")
    document.add_paragraph("3.{{ item.sequence }}.2 测试方法/原理\n{{ item.method }}")
    document.add_paragraph("3.{{ item.sequence }}.3 测试工具\n{% for tool in item.tools %}{{ loop.index }}. {{ tool }}\n{% endfor %}")
    document.add_paragraph("3.{{ item.sequence }}.4 测试步骤\n{% for step in item.steps %}{{ loop.index }}. {{ step }}\n{% endfor %}")
    document.add_paragraph("3.{{ item.sequence }}.5 测试连接图或照片\n{{ item.connection_media }}")
    document.add_paragraph("3.{{ item.sequence }}.6 测试记录\n{{ item.record_template }}")
    document.add_paragraph("3.{{ item.sequence }}.7 需求符合性和BUG信息\n{{ item.compliance_bug_info }}\n依据：{{ item.evidence }}")
    document.add_paragraph("{% if item.source_section_text %}原始测试项目章节\n{{ item.source_section_text }}{% endif %}")
    document.add_paragraph("{% endfor %}")
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
    rewrite_test_item_section(output_path, plan)


def rewrite_test_item_section(output_path: Path, plan: ValidationPlanRead) -> None:
    document = Document(output_path)
    start_index = next((index for index, paragraph in enumerate(document.paragraphs) if paragraph.text.strip() == "3. 测试项目"), None)
    if start_index is None:
        return
    remove_paragraphs_after(document, start_index)
    for item in plan.items:
        document.add_heading(f"3.{item.sequence} {item.title}", level=3)
        add_test_item_subsection(document, item.sequence, 1, "测试目的/测试标准", item.objective)
        add_test_item_subsection(document, item.sequence, 2, "测试方法/原理", item.method)
        add_test_item_subsection(document, item.sequence, 3, "测试工具", numbered_lines(item.tools, "待确认"))
        add_test_item_subsection(document, item.sequence, 4, "测试步骤", numbered_lines(item.steps, "按模板执行并记录过程数据。"))
        add_test_item_subsection(document, item.sequence, 5, "测试连接图或照片", item.connection_media or "待补充")
        add_test_item_subsection(document, item.sequence, 6, "测试记录", item.record_template)
        add_test_item_subsection(document, item.sequence, 7, "需求符合性和BUG信息", item.compliance_bug_info)
    document.save(output_path)


def remove_paragraphs_after(document: Document, start_index: int) -> None:
    for paragraph in list(document.paragraphs[start_index + 1 :]):
        paragraph._element.getparent().remove(paragraph._element)


def add_test_item_subsection(document: Document, sequence: int, subsection: int, title: str, body: str) -> None:
    document.add_heading(f"3.{sequence}.{subsection} {title}", level=4)
    document.add_paragraph(body or "待补充")


def numbered_lines(values: list[str], fallback: str) -> str:
    usable_values = [value for value in values if value]
    if not usable_values:
        return fallback
    return "\n".join(f"{index}. {value}" for index, value in enumerate(usable_values, start=1))
