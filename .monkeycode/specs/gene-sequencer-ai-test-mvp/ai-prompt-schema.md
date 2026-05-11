# AI 编排与 Prompt/Schema 设计

## 1. 设计原则

AI 不直接生成不可控的完整长文档，而是分阶段输出结构化 JSON。每个任务经过 Schema 校验、来源校验和人工确认后进入业务流程。

| 原则 | 说明 |
|---|---|
| 结构化输出 | 每个 AI 任务只输出 JSON |
| 任务拆分 | 标签、拆分、分类、归口、推荐、方案分开处理 |
| 低置信度人工确认 | 标签、分类、归口和风险映射需置信度 |
| 来源可追溯 | 关键结论必须带 evidence |
| 本地知识优先 | 内部资料、测试资产、风险资产优先 |
| 联网结果标记 | 外部参考需单独标记 |

## 2. AI 工作流

### 资料上传阶段

```text
document_label_extraction
→ document_summary
→ validation_plan_split
→ test_item_classification
→ test_package_generation
→ risk_item_extraction
```

### 需求分析阶段

```text
requirement_parsing
→ package_matching
→ risk_retrieval
→ local_evidence_retrieval
→ optional_web_reference
→ test_recommendation_generation
```

### 方案生成阶段

```text
validation_plan_overview_generation
→ dut_extraction
→ reference_document_summary
→ test_section_generation
→ plan_completeness_check
```

## 3. 通用 Prompt 骨架

```text
角色：
你是基因测序仪测试工程专家，熟悉物料、子系统、系统级功能性能验证、DFMEA、Jira 问题分析和验证方案编写。

任务：
完成指定结构化分析任务。

输入：
- 用户输入
- 项目信息
- 文档内容片段
- 已检索依据
- 可选枚举

要求：
- 只输出 JSON
- 不编造来源
- 每个关键判断给出 evidence
- 无法判断时输出 null 或 unknown
- 低置信度时标记 needs_user_confirmation = true
```

## 4. 资料标签识别 Schema

```json
{
  "document_type": {
    "value": "validation_plan",
    "confidence": 0.96,
    "evidence": ["标题包含验证方案"],
    "needs_user_confirmation": false
  },
  "title": {
    "value": "DNBSEQ-G99 ECR4.1康奈特RFID验证方案",
    "confidence": 0.98,
    "evidence": ["文件名包含完整标题"],
    "needs_user_confirmation": false
  },
  "product_models": {
    "value": ["DNBSEQ-G99"],
    "confidence": 0.93,
    "evidence": ["正文多次出现 G99"],
    "needs_user_confirmation": false
  },
  "normalized_object_name": {
    "value": "RFID",
    "confidence": 0.9,
    "evidence": ["标题和 DUT 均出现 RFID"],
    "needs_user_confirmation": false
  },
  "primary_domain": {
    "value": "耗材与试剂接口系统",
    "confidence": 0.78,
    "evidence": ["RFID 与试剂槽、芯片识别相关"],
    "needs_user_confirmation": true
  },
  "primary_subsystem": {
    "value": "试剂盒接口子系统",
    "confidence": 0.78,
    "evidence": ["测试项目包含 RFID 读取、写入、初始化"],
    "needs_user_confirmation": true
  },
  "change_type": {
    "value": "supplier_change",
    "confidence": 0.88,
    "evidence": ["正文包含二供供应商康奈特RFID"],
    "needs_user_confirmation": false
  },
  "missing_required_labels": ["confidentiality", "reuse_scope"]
}
```

## 5. 测试方案拆分 Schema

```json
{
  "document_id": "uuid",
  "items": [
    {
      "source_section_no": "3.3",
      "name": "RFID在机读取测试",
      "summary": "评估 RFID 在机读取稳定性，识别漏读、错读、串扰风险。",
      "sample_quantity": "1",
      "estimated_hours": 72,
      "test_purpose": "评估 RFID 在机读取稳定性，是否存在漏读、错读、串扰现象。",
      "test_standard": "不得存在错读、串扰现象；≥98%识别率；有3次或以上的重试机制下识别率100%。",
      "method_principle": "放入带有 RFID 标签的芯片和试剂槽共4个，在 EUI RFID 测试界面循环读取4个标签，并用串口监控工具监控收发信息。",
      "tools": [
        {
          "name": "CEIWEI CommMonitor串口监控精灵",
          "equipment_model": "/",
          "manufacturer": "/",
          "equipment_code": "/",
          "calibration_valid_until": "/"
        }
      ],
      "steps": [
        {
          "step_no": 1,
          "description": "放入带有 RFID 标签的芯片和试剂槽共4个。"
        }
      ],
      "connection_diagram": "/",
      "record_template": [
        {
          "record_no": 1,
          "record_item": "EUROPE-50mW",
          "acceptance_criteria": "不得存在错读、串扰现象；≥98%识别率；有3次或以上的重试机制下识别率100%。",
          "result_options": ["P", "F"]
        }
      ]
    }
  ],
  "warnings": []
}
```

## 6. 测试条目分类映射 Schema

```json
{
  "test_item_name": "RFID在机读取测试",
  "object_name_raw": "RFID",
  "normalized_object_name": "RFID",
  "primary_domain": "耗材与试剂接口系统",
  "primary_subsystem": "试剂盒接口子系统",
  "related_domains": ["电气与电子系统", "整机系统"],
  "related_subsystems": ["信号采集子系统", "整机性能子系统"],
  "test_levels": ["subsystem", "system"],
  "test_types": ["performance", "stability"],
  "risk_tags": ["漏读", "错读", "串扰", "识别率不足"],
  "classification_confidence": 0.86,
  "classification_evidence": [
    "测试目的包含读取稳定性",
    "判定标准包含识别率和串扰",
    "测试步骤涉及整机 EUI RFID 测试界面"
  ],
  "needs_user_confirmation": false
}
```

## 7. 测试归口包生成 Schema

```json
{
  "packages": [
    {
      "package_name": "RFID 供应商变更验证包",
      "package_type": "change",
      "normalized_object_name": "RFID",
      "change_type": "supplier_change",
      "summary": "用于 RFID 供应商变更时的装配、初始化、读取、写入和安规 EMC 验证。",
      "primary_domain": "耗材与试剂接口系统",
      "primary_subsystem": "试剂盒接口子系统",
      "related_subsystems": [
        "装配与定位子系统",
        "主控与接口子系统",
        "信号采集子系统",
        "EMC 与安全子系统",
        "整机流程子系统",
        "整机性能子系统"
      ],
      "items": [
        {
          "test_item_name": "RFID在机装配测试",
          "relation_level": "required",
          "trigger_condition": "RFID 物料、结构或供应商变更",
          "relation_reason": "验证结构安装适配"
        },
        {
          "test_item_name": "安规EMC测试",
          "relation_level": "conditional",
          "trigger_condition": "涉及电气设计、供应商切换、适用市场或法规评估",
          "relation_reason": "验证法规和 EMC 风险"
        }
      ],
      "confidence": 0.88,
      "evidence": ["概述中包含二供供应商康奈特 RFID", "测试项目均围绕 RFID 在机验证"],
      "needs_admin_review": true
    }
  ]
}
```

## 8. 风险项解析 Schema

### Jira

```json
{
  "risk_items": [
    {
      "risk_code": "G99-1234",
      "source_type": "jira",
      "title": "RFID 高湿环境下偶发漏读",
      "description": "高湿环境运行后 RFID 循环读取出现漏读。",
      "normalized_object_name": "RFID",
      "primary_domain": "耗材与试剂接口系统",
      "primary_subsystem": "试剂盒接口子系统",
      "related_subsystems": ["环境适应性子系统", "信号采集子系统"],
      "failure_mode": "RFID 漏读",
      "failure_effect": "芯片或试剂识别异常，影响测序流程",
      "failure_cause": "连接器接触稳定性和环境湿度影响",
      "occurrence_condition": "高湿环境运行后进行 RFID 循环读取",
      "severity": "High",
      "rpn": 120,
      "issue_status": "closed",
      "confidence": 0.84
    }
  ]
}
```

### DFMEA

```json
{
  "risk_items": [
    {
      "risk_code": "DFMEA-RFID-001",
      "source_type": "dfmea",
      "title": "RFID 读取功能失效",
      "normalized_object_name": "RFID",
      "primary_domain": "耗材与试剂接口系统",
      "primary_subsystem": "试剂盒接口子系统",
      "failure_mode": "RFID 标签读取失败",
      "failure_effect": "试剂或芯片识别错误，影响测序流程",
      "failure_cause": "天线距离偏差、信号干扰、标签一致性差",
      "detection_method": "循环读取测试、初始化检查",
      "severity": "8",
      "occurrence": "4",
      "detection": "5",
      "rpn": 160,
      "action_priority": "High",
      "confidence": 0.9
    }
  ]
}
```

## 9. 需求解析 Schema

```json
{
  "requirement_summary": "在 DNBSEQ-G99 上引入康奈特 RFID 作为二供供应商。",
  "change_objects": ["康奈特 RFID"],
  "normalized_objects": ["RFID"],
  "change_types": ["supplier_change"],
  "affected_product_models": ["DNBSEQ-G99"],
  "affected_domains": ["耗材与试剂接口系统", "电气与电子系统", "整机系统"],
  "affected_subsystems": ["试剂盒接口子系统", "主控与接口子系统", "信号采集子系统", "EMC 与安全子系统", "整机流程子系统"],
  "affected_test_levels": ["material", "subsystem", "system"],
  "risk_points": ["结构安装不适配", "初始化失败", "漏读", "错读", "串扰", "写入失败", "EMC 风险"],
  "missing_information": ["RFID 型号", "适用市场", "样本量", "是否涉及电气设计变化"],
  "confidence": 0.9,
  "evidence": ["需求包含二供供应商康奈特RFID", "产品型号为 G99"]
}
```

## 10. 测试推荐 Schema

```json
{
  "recommendations": [
    {
      "test_item_name": "RFID在机读取测试",
      "recommendation_level": "required",
      "source_type": "package",
      "source_ids": ["package_uuid", "test_item_uuid"],
      "test_levels": ["subsystem", "system"],
      "primary_subsystem": "试剂盒接口子系统",
      "related_subsystems": ["信号采集子系统", "整机性能子系统"],
      "test_purpose": "验证新 RFID 在机读取是否正常，是否存在漏读、错读、串扰现象。",
      "test_standard": "不得存在错读、串扰现象；≥98%识别率；有3次或以上的重试机制下识别率100%。",
      "recommendation_reason": "该条目属于 RFID 供应商变更验证包中的必测项，并覆盖 DFMEA 中 RFID 读取失败风险。",
      "evidences": [
        {"type": "historical_plan", "id": "document_uuid", "quote": "验证新RFID在机读取是否正常"},
        {"type": "dfmea", "id": "risk_uuid", "quote": "RFID 标签读取失败"}
      ],
      "risk_coverage": [
        {"risk_code": "DFMEA-RFID-001", "coverage_type": "detection_validation", "coverage_strength": "strong"}
      ],
      "condition_question": null,
      "needs_user_decision": false
    }
  ]
}
```

## 11. 验证方案完整性校验 Schema

```json
{
  "blocking_issues": [
    {
      "section": "1.2 DUT描述",
      "field": "测试数量",
      "message": "DUT 测试数量为空",
      "suggested_action": "请补充测试数量"
    }
  ],
  "warnings": [
    {
      "section": "3.3.3 测试工具",
      "field": "设备编码",
      "message": "测试工具设备编码为空",
      "suggested_action": "如需受控记录，请补充设备编码"
    }
  ],
  "tips": [
    {
      "section": "3.5 安规EMC测试",
      "message": "该测试项为条件触发项，建议填写纳入原因"
    }
  ],
  "can_export": false
}
```

## 12. Prompt 版本管理

系统应维护 `ai_prompt_templates` 和 `ai_task_runs`。每次 AI 调用记录任务类型、Prompt 版本、模型名称、输入快照、输出 JSON、校验状态和触发用户。

后端校验包括 JSON 格式、枚举值、必填字段、evidence、confidence、引用 ID、权限和文本长度。
