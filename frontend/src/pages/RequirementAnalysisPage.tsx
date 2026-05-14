import { Button, Card, Descriptions, Form, Input, List, Modal, Select, Space, Table, Tag, Typography, Upload, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { UploadOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import {
  createRequirementRecommendation,
  createRequirementAnalysis,
  deleteRequirementRecommendation,
  downloadRequirementTemplate,
  fetchAiConfig,
  fetchRequirementTemplate,
  AiConfig,
  RequirementAnalysis,
  RequirementBatchUploadResult,
  RequirementRecommendation,
  RequirementTemplate,
  updateRequirementRecommendation,
  uploadRequirementTable,
} from "../api/client";
import { useProjects } from "../context/ProjectContext";

const STANDARD_REQUIREMENT_TEMPLATE = `需求标题：DNBSEQ-G99 RFID 二供供应商导入验证
产品型号：DNBSEQ-G99
变更对象：RFID
变更背景：现有 RFID 物料需引入二供供应商以降低供应风险
变更内容：同步引入康奈特 RFID，保持功能规格和接口定义一致`;

export default function RequirementAnalysisPage() {
  const { currentProject } = useProjects();
  const [analysis, setAnalysis] = useState<RequirementAnalysis | null>(null);
  const [batchResult, setBatchResult] = useState<RequirementBatchUploadResult | null>(null);
  const [batchFile, setBatchFile] = useState<File | null>(null);
  const [template, setTemplate] = useState<RequirementTemplate | null>(null);
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null);
  const [editingRecommendation, setEditingRecommendation] = useState<RequirementRecommendation | null>(null);
  const [isRecommendationModalOpen, setIsRecommendationModalOpen] = useState(false);
  const [form] = Form.useForm<{ description: string }>();
  const [recommendationForm] = Form.useForm<{
    group: string;
    title: string;
    source_type: string;
    source_id: string;
    reason: string;
    evidence: string;
    review_status: string;
  }>();

  useEffect(() => {
    fetchRequirementTemplate().then(setTemplate).catch(() => setTemplate(null));
    fetchAiConfig().then(setAiConfig).catch(() => setAiConfig(null));
  }, []);

  async function submit(values: { description: string }) {
    if (!currentProject) return;
    if (batchFile) {
      const result = await uploadRequirementTable(currentProject.id, batchFile);
      setBatchResult(result);
      setAnalysis(null);
      const successCount = result.items.filter((item) => item.analysis).length;
      message.success(`已分析 ${result.items.length} 条需求，其中 ${successCount} 条完成分析`);
      return;
    }
    const result = await createRequirementAnalysis(currentProject.id, values.description);
    setAnalysis(result);
    setBatchResult(null);
    message.success("需求分析完成");
  }

  function handleTableUpload(file: File) {
    setBatchFile(file);
    setBatchResult(null);
    message.success(`已选择需求批量分析文件：${file.name}，点击开始分析后执行`);
    return false;
  }

  async function handleTemplateDownload() {
    const blob = await downloadRequirementTemplate();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "requirement-analysis-template.csv";
    link.click();
    window.URL.revokeObjectURL(url);
  }

  function openCreateRecommendation() {
    setEditingRecommendation(null);
    recommendationForm.setFieldsValue({
      group: "人工补充",
      title: "",
      source_type: "manual",
      source_id: "manual",
      reason: "人工新增",
      evidence: "人工新增推荐项",
      review_status: "confirmed",
    });
    setIsRecommendationModalOpen(true);
  }

  function openEditRecommendation(item: RequirementRecommendation) {
    setEditingRecommendation(item);
    recommendationForm.setFieldsValue(item);
    setIsRecommendationModalOpen(true);
  }

  async function saveRecommendation() {
    if (!analysis) return;
    const values = await recommendationForm.validateFields();
    const updated = editingRecommendation
      ? await updateRequirementRecommendation(analysis.id, editingRecommendation.id, values)
      : await createRequirementRecommendation(analysis.id, values);
    setAnalysis(updated);
    setIsRecommendationModalOpen(false);
    message.success(editingRecommendation ? "推荐项已更新" : "推荐项已新增");
  }

  async function setRecommendationStatus(item: RequirementRecommendation, reviewStatus: string) {
    if (!analysis) return;
    const updated = await updateRequirementRecommendation(analysis.id, item.id, { review_status: reviewStatus });
    setAnalysis(updated);
    message.success(reviewStatus === "confirmed" ? "推荐项已确认" : "推荐项已排除");
  }

  async function removeRecommendation(item: RequirementRecommendation) {
    if (!analysis) return;
    const updated = await deleteRequirementRecommendation(analysis.id, item.id);
    setAnalysis(updated);
    message.success("推荐项已删除");
  }

  function statusTag(status: string) {
    const color = status === "confirmed" ? "green" : status === "excluded" ? "red" : "gold";
    const label = status === "confirmed" ? "已确认" : status === "excluded" ? "已排除" : "待审核";
    return <Tag color={color}>{label}</Tag>;
  }

  const batchColumns: ColumnsType<RequirementBatchUploadResult["items"][number]> = [
    { title: "行号", dataIndex: "row_number", width: 80 },
    {
      title: "状态",
      render: (_, item) => item.missing_fields.length > 0 ? <Tag color="red">缺少必填项</Tag> : <Tag color="green">已分析</Tag>,
    },
    {
      title: "缺失字段",
      dataIndex: "missing_fields",
      render: (fields: string[]) => fields.length > 0 ? fields.join("、") : "-",
    },
    {
      title: "解析对象",
      render: (_, item) => item.analysis?.parse_result.test_object ?? "-",
    },
    {
      title: "推荐数",
      render: (_, item) => item.analysis?.recommendations.length ?? "-",
    },
  ];

  return (
    <section>
      <Typography.Title level={2}>需求分析</Typography.Title>
      <Typography.Paragraph type="secondary">
        输入或上传新开发需求/变更需求，系统将结合测试归口包、历史方案、Jira 和 DFMEA 风险项推荐测试条目。
      </Typography.Paragraph>
      {aiConfig && (
        <Typography.Paragraph type="secondary">
          AI 状态：<Tag color={aiConfig.configured ? "green" : "default"}>{aiConfig.configured ? `已接入 ${aiConfig.model}` : "本地规则兜底"}</Tag>
        </Typography.Paragraph>
      )}
      <Card title="标准需求格式" className="section-card">
        <Typography.Paragraph type="secondary">
          必填字段为需求标题、产品型号、变更对象、变更背景和变更内容。所属子系统、变更类型、影响范围、验收标准和已知风险为可选字段，可由系统推断或用户补充确认。
        </Typography.Paragraph>
        {template && (
          <Space wrap className="section-card">
            {template.fields.map((field) => (
              <Tag key={field.name} color={field.required ? "red" : "default"}>{field.required ? "必填" : "可选"}：{field.name}</Tag>
            ))}
          </Space>
        )}
        <Input.TextArea rows={10} value={STANDARD_REQUIREMENT_TEMPLATE} readOnly />
      </Card>
      <Card>
        <Form form={form} layout="vertical" onFinish={submit} initialValues={{ description: STANDARD_REQUIREMENT_TEMPLATE }}>
          <Form.Item label="需求描述" name="description" rules={[{ required: true, message: "请输入需求描述" }]}> 
            <Input.TextArea rows={8} placeholder="例如：DNBSEQ-G99 同步引入二供供应商康奈特 RFID..." />
          </Form.Item>
          <Space wrap>
            <Button type="primary" htmlType="submit">开始分析</Button>
            <Button onClick={handleTemplateDownload}>下载需求批量分析模版</Button>
            <Upload beforeUpload={handleTableUpload} showUploadList={false} accept=".csv">
              <Button icon={<UploadOutlined />}>{batchFile ? `已选择：${batchFile.name}` : "上传需求批量分析"}</Button>
            </Upload>
          </Space>
        </Form>
      </Card>
      {batchResult && (
        <Card title={`批量分析结果：${batchResult.filename}`} className="section-card">
          <Table rowKey="row_number" columns={batchColumns} dataSource={batchResult.items} pagination={false} />
        </Card>
      )}
      {analysis && (
        <Card title="分析结果" className="section-card">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="测试对象">{analysis.parse_result.test_object}</Descriptions.Item>
            <Descriptions.Item label="变更类型">{analysis.parse_result.change_type}</Descriptions.Item>
            <Descriptions.Item label="产品型号">{analysis.parse_result.product_model ?? "待确认"}</Descriptions.Item>
            <Descriptions.Item label="子系统">{analysis.parse_result.subsystem}</Descriptions.Item>
          </Descriptions>
          <List
            className="section-card"
            header={<Space><span>推荐测试条目</span><Button size="small" onClick={openCreateRecommendation}>新增推荐项</Button></Space>}
            dataSource={analysis.recommendations}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button key="confirm" size="small" type="link" onClick={() => setRecommendationStatus(item, "confirmed")}>确认</Button>,
                  <Button key="exclude" size="small" type="link" danger onClick={() => setRecommendationStatus(item, "excluded")}>排除</Button>,
                  <Button key="edit" size="small" type="link" onClick={() => openEditRecommendation(item)}>编辑</Button>,
                  <Button key="delete" size="small" type="link" danger onClick={() => removeRecommendation(item)}>删除</Button>,
                ]}
              >
                <List.Item.Meta
                  title={<><Tag color="blue">{item.group}</Tag>{statusTag(item.review_status)}{item.title}</>}
                  description={`${item.reason}；依据：${item.evidence}`}
                />
              </List.Item>
            )}
          />
        </Card>
      )}
      <Modal
        title={editingRecommendation ? "编辑推荐项" : "新增推荐项"}
        open={isRecommendationModalOpen}
        onOk={saveRecommendation}
        onCancel={() => setIsRecommendationModalOpen(false)}
        destroyOnHidden
      >
        <Form form={recommendationForm} layout="vertical">
          <Form.Item label="分组" name="group" rules={[{ required: true, message: "请输入分组" }]}> 
            <Input placeholder="必测/建议/条件触发/人工补充" />
          </Form.Item>
          <Form.Item label="测试条目" name="title" rules={[{ required: true, message: "请输入测试条目" }]}> 
            <Input />
          </Form.Item>
          <Form.Item label="状态" name="review_status" rules={[{ required: true, message: "请选择状态" }]}> 
            <Select
              options={[
                { label: "待审核", value: "pending" },
                { label: "已确认", value: "confirmed" },
                { label: "已排除", value: "excluded" },
              ]}
            />
          </Form.Item>
          <Form.Item label="来源类型" name="source_type" rules={[{ required: true, message: "请输入来源类型" }]}> 
            <Input />
          </Form.Item>
          <Form.Item label="来源 ID" name="source_id" rules={[{ required: true, message: "请输入来源 ID" }]}> 
            <Input />
          </Form.Item>
          <Form.Item label="推荐原因" name="reason" rules={[{ required: true, message: "请输入推荐原因" }]}> 
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="依据" name="evidence" rules={[{ required: true, message: "请输入依据" }]}> 
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
