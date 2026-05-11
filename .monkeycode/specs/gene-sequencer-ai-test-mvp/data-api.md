# 数据模型与核心 API 设计

## 1. 数据对象总览

MVP 核心对象包括：用户权限、项目空间、统一资料池、文档切片、测试条目资产、测试归口资产、风险知识源、需求分析、验证方案。

```text
Project
→ RequirementAnalysis
→ RequirementRecommendation
→ ValidationPlan

Document
→ DocumentChunk
→ TestItemAsset
→ TestPackageAsset
→ RiskItem
```

## 2. 用户与权限

### users

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 用户 ID |
| username | varchar | 用户名 |
| display_name | varchar | 显示名 |
| email | varchar | 邮箱 |
| status | enum | active / disabled |
| created_at | timestamp | 创建时间 |

### roles

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 角色 ID |
| code | varchar | system_admin / project_admin / test_engineer / reviewer |
| name | varchar | 角色名称 |

## 3. 项目模型

### projects

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 项目 ID |
| name | varchar | 项目名称 |
| product_line | varchar | 产品线 |
| product_models | text[] | 产品型号 |
| stage | enum | development / verification / transfer / maintenance |
| status | enum | active / archived |
| created_by | uuid | 创建人 |
| created_at | timestamp | 创建时间 |

### project_document_rules

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 规则 ID |
| project_id | uuid | 项目 |
| product_line | varchar | 产品线过滤 |
| product_models | text[] | 产品型号过滤 |
| document_types | text[] | 文档类型过滤 |
| domains | text[] | 一级系统域 |
| subsystems | text[] | 二级子系统 |
| confidentiality_max | enum | 最大可访问保密等级 |
| status_required | varchar | 默认 published |

## 4. 资料池模型

### documents

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 文档 ID |
| title | varchar | 文档标题 |
| original_filename | varchar | 原始文件名 |
| document_type | enum | validation_plan / test_report / dfmea / jira / spec / requirement / change_request / technical_requirement |
| product_line | varchar | 产品线 |
| product_models | text[] | 产品型号 |
| object_name_raw | varchar | 原始对象名 |
| normalized_object_name | varchar | 标准对象名 |
| primary_domain | varchar | 一级系统域 |
| primary_subsystem | varchar | 二级子系统 |
| related_subsystems | text[] | 关联子系统 |
| version | varchar | 文档版本 |
| lifecycle_stage | text[] | 适用阶段 |
| confidentiality | enum | normal / internal / controlled |
| file_hash | varchar | 文件 hash |
| content_hash | varchar | 正文 hash |
| storage_path | varchar | MinIO 路径 |
| parse_status | enum | pending / running / success / failed |
| review_status | enum | draft / pending_review / published / rejected / deprecated |
| uploaded_by | uuid | 上传人 |
| reviewed_by | uuid | 审核人 |
| reviewed_at | timestamp | 审核时间 |
| created_at | timestamp | 创建时间 |
| updated_at | timestamp | 更新时间 |

### document_chunks

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 切片 ID |
| document_id | uuid | 文档 ID |
| chunk_index | int | 序号 |
| section_no | varchar | 章节号 |
| section_title | varchar | 章节标题 |
| page_no | varchar | 页码 |
| content | text | 正文 |
| content_type | enum | paragraph / table / list / image_caption |
| metadata | jsonb | 附加信息 |
| embedding | vector | 向量 |
| created_at | timestamp | 创建时间 |

## 5. 测试条目资产模型

### test_item_assets

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 条目 ID |
| code | varchar | 可读编号 |
| name | varchar | 测试项目名称 |
| source_type | enum | historical_plan_split / ai_generated / manual_created / template_imported |
| source_document_id | uuid | 来源文档 |
| source_section_no | varchar | 来源章节 |
| object_name_raw | varchar | 原始对象 |
| normalized_object_name | varchar | 标准对象 |
| primary_domain | varchar | 主一级系统域 |
| primary_subsystem | varchar | 主二级子系统 |
| related_domains | text[] | 关联一级系统域 |
| related_subsystems | text[] | 关联二级子系统 |
| product_line | varchar | 产品线 |
| product_models | text[] | 产品型号 |
| test_levels | text[] | 测试层级 |
| test_types | text[] | 测试类型 |
| test_purpose | text | 测试目的 |
| test_standard | text | 测试标准 |
| method_principle | text | 测试方法/原理 |
| test_steps | jsonb | 测试步骤 |
| connection_diagram | varchar | 图片路径或 / |
| test_record_template | jsonb | 测试记录模板 |
| sample_quantity | varchar | 样本量 |
| estimated_hours | numeric | 预估用时 |
| status | enum | draft / pending_review / published / deprecated |
| is_reusable | boolean | 是否可复用 |
| reuse_scope | enum | global / product_line / product_model / project |

### test_item_evidences

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 依据 ID |
| test_item_id | uuid | 测试条目 |
| evidence_type | enum | 依据类型 |
| document_id | uuid | 来源文档 |
| chunk_id | uuid | 来源切片 |
| quote_text | text | 引用原文 |
| relevance_score | numeric | 相关度 |
| used_for | enum | purpose / method / standard / risk / classification |

## 6. 测试归口资产模型

### test_package_assets

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 归口包 ID |
| code | varchar | 可读编号 |
| name | varchar | 名称 |
| package_type | enum | object / change / subsystem / system |
| normalized_object_name | varchar | 标准对象 |
| change_type | enum | supplier_change / model_change / structure_change / material_change / process_change / parameter_change / market_change / reliability_improvement / risk_mitigation / compatibility_extension |
| primary_domain | varchar | 主一级系统域 |
| primary_subsystem | varchar | 主二级子系统 |
| related_subsystems | text[] | 关联子系统 |
| product_models | text[] | 产品型号 |
| status | enum | draft / pending_review / published / deprecated |

### test_package_items

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 关系 ID |
| package_id | uuid | 归口包 |
| test_item_id | uuid | 测试条目 |
| relation_level | enum | required / recommended / conditional |
| trigger_condition | text | 条件触发 |
| relation_reason | text | 关联原因 |
| confidence | numeric | 置信度 |
| order_no | int | 排序 |

## 7. 风险知识源模型

### risk_items

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 风险 ID |
| risk_code | varchar | Jira/DFMEA/RM 编号 |
| source_type | enum | jira / dfmea / risk_management / test_report_issue |
| title | varchar | 标题 |
| description | text | 描述 |
| normalized_object_name | varchar | 标准对象 |
| primary_domain | varchar | 一级系统域 |
| primary_subsystem | varchar | 二级子系统 |
| failure_mode | text | 失效模式 |
| failure_effect | text | 失效后果 |
| failure_cause | text | 失效原因 |
| occurrence_condition | text | 发生条件 |
| detection_method | text | 探测方式 |
| prevention_control | text | 预防控制 |
| corrective_action | text | 纠正措施 |
| severity | varchar | 严重度 |
| occurrence | varchar | 发生度 |
| detection | varchar | 探测度 |
| rpn | numeric | RPN |
| action_priority | varchar | AP |
| issue_status | varchar | 状态 |
| source_document_id | uuid | 来源文档 |
| embedding | vector | 向量 |

## 8. 需求分析模型

### requirement_analyses

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 分析 ID |
| project_id | uuid | 项目 |
| requirement_type | enum | new_development / change_request |
| requirement_code | varchar | 编号 |
| title | varchar | 标题 |
| input_text | text | 原文 |
| applicable_product_models | text[] | 产品型号 |
| parsed_summary | text | 需求摘要 |
| change_objects | text[] | 变更对象 |
| change_types | text[] | 变更类型 |
| affected_subsystems | text[] | 影响子系统 |
| affected_test_levels | text[] | 影响测试层级 |
| risk_points | text[] | 风险点 |
| missing_information | text[] | 缺失信息 |
| status | enum | draft / analyzed / reviewed / plan_generated |

### requirement_recommendations

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 推荐 ID |
| analysis_id | uuid | 分析 |
| source_type | enum | package / test_item / jira_risk / dfmea_risk / ai_supplement / web_reference |
| source_id | uuid | 来源 ID |
| test_item_id | uuid | 关联测试条目 |
| generated_item_snapshot | jsonb | 生成条目快照 |
| recommendation_level | enum | required / recommended / conditional / supplement |
| recommendation_reason | text | 推荐理由 |
| evidence_map | jsonb | 依据映射 |
| condition_question | text | 条件问题 |
| user_decision | enum | accepted / modified / rejected / pending |
| final_item_snapshot | jsonb | 审核后的条目 |

## 9. 验证方案模型

### validation_plans

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | 方案 ID |
| name | varchar | 名称 |
| code | varchar | 文档编号 |
| project_id | uuid | 项目 |
| product_name | varchar | 产品名称 |
| product_models | text[] | 产品型号 |
| requirement_analysis_id | uuid | 来源分析 |
| version | varchar | 版本 |
| author_id | uuid | 编写人 |
| approver | varchar | 批准人 |
| status | enum | draft / pending_review / exported / published / deprecated |
| document_history | jsonb | 文档履历 |
| overview | jsonb | 概述 |
| dut_list | jsonb | DUT |
| reference_documents | jsonb | 参考文档 |

### validation_plan_items

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid | ID |
| plan_id | uuid | 方案 |
| test_item_id | uuid | 测试条目资产 |
| item_snapshot | jsonb | 条目快照 |
| section_no | varchar | 3.x |
| order_no | int | 排序 |
| included_risk_ids | uuid[] | 覆盖风险 |
| included_jira_ids | uuid[] | 关联 Jira |

## 10. 核心 API

### 认证与项目

```text
POST /api/auth/login
GET  /api/auth/me
GET  /api/projects
POST /api/projects
GET  /api/projects/{project_id}
PUT  /api/projects/{project_id}
```

### 资料池

```text
GET  /api/documents
POST /api/documents/upload
GET  /api/documents/{document_id}
PUT  /api/documents/{document_id}/labels
POST /api/documents/{document_id}/submit-review
POST /api/documents/{document_id}/review
GET  /api/documents/{document_id}/chunks
GET  /api/documents/{document_id}/duplicates
```

### 智能识别与拆分

```text
POST /api/documents/{document_id}/analyze-labels
GET  /api/documents/{document_id}/label-suggestions
POST /api/documents/{document_id}/confirm-labels
POST /api/documents/{document_id}/check-duplicates
POST /api/documents/{document_id}/split-test-items
GET  /api/documents/{document_id}/split-result
POST /api/documents/{document_id}/confirm-split-result
```

### 测试资产

```text
GET  /api/test-items
GET  /api/test-items/{test_item_id}
PUT  /api/test-items/{test_item_id}
POST /api/test-items/{test_item_id}/review
GET  /api/test-packages
POST /api/test-packages
GET  /api/test-packages/{package_id}
PUT  /api/test-packages/{package_id}
POST /api/test-packages/{package_id}/review
```

### 风险知识源

```text
GET  /api/risks
GET  /api/risks/{risk_id}
POST /api/documents/{document_id}/parse-risks
GET  /api/documents/{document_id}/risk-items
```

### 需求分析

```text
POST /api/requirement-analyses
GET  /api/requirement-analyses/{analysis_id}
POST /api/requirement-analyses/{analysis_id}/parse
POST /api/requirement-analyses/{analysis_id}/generate-recommendations
GET  /api/requirement-analyses/{analysis_id}/recommendations
PUT  /api/requirement-recommendations/{recommendation_id}/decision
POST /api/requirement-analyses/{analysis_id}/finalize
```

### 验证方案

```text
POST /api/validation-plans/from-analysis/{analysis_id}
GET  /api/validation-plans/{plan_id}
PUT  /api/validation-plans/{plan_id}
POST /api/validation-plans/{plan_id}/validate
POST /api/validation-plans/{plan_id}/export
GET  /api/export-records/{export_id}/download
```
