from dataclasses import dataclass


@dataclass(frozen=True)
class SeedUser:
    id: str
    username: str
    password: str
    display_name: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class SeedProject:
    id: str
    code: str
    name: str
    description: str
    members: dict[str, str]
    document_rules: tuple[dict[str, str], ...]


USERS = {
    "admin": SeedUser(
        id="user-admin",
        username="admin",
        password="admin123",
        display_name="管理员",
        roles=("admin",),
    ),
    "tester": SeedUser(
        id="user-tester",
        username="tester",
        password="tester123",
        display_name="测试工程师",
        roles=("tester",),
    ),
}

PROJECTS = {
    "project-g99-rfid": SeedProject(
        id="project-g99-rfid",
        code="DNBSEQ-G99-RFID",
        name="DNBSEQ-G99 RFID 供应商变更验证",
        description="用于验证康奈特 RFID 二供供应商导入相关测试闭环。",
        members={"user-admin": "owner", "user-tester": "member"},
        document_rules=(
            {"label_key": "product_model", "label_value": "DNBSEQ-G99"},
            {"label_key": "subsystem", "label_value": "RFID"},
            {"label_key": "change_type", "label_value": "供应商变更"},
        ),
    ),
    "project-mgi-platform": SeedProject(
        id="project-mgi-platform",
        code="MGI-PLATFORM",
        name="测序仪平台级资料治理",
        description="跨项目复用测试规范、风险知识和通用测试资产。",
        members={"user-admin": "owner"},
        document_rules=(
            {"label_key": "scope", "label_value": "platform"},
        ),
    ),
}
