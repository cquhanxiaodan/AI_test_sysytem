import { Alert, Button, Card, Descriptions, Form, Input, List, Modal, Select, Space, Spin, Table, Tag, Typography, Upload, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { UploadOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import type { Key } from "react";
import {
  createRequirementRecommendation,
  createLocalRequirementAnalysis,
  deleteRequirementAnalysis,
  deleteRequirementRecommendation,
  downloadRequirementTemplate,
  fetchAiConfig,
  fetchRequirementAnalyses,
  fetchRequirementTemplate,
  includeRequirementRecommendationInLocal,
  AiConfig,
  RequirementAnalysis,
  RequirementBatchUploadResult,
  RequirementRecommendation,
  RequirementTemplate,
  runRequirementAiRecommendations,
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
  const [analyses, setAnalyses] = useState<RequirementAnalysis[]>([]);
  const [selectedAnalysisIds, setSelectedAnalysisIds] = useState<Key[]>([]);
  const [batchResult, setBatchResult] = useState<RequirementBatchUploadResult | null>(null);
  const [batchFile, setBatchFile] = useState<File | null>(null);
  const [template, setTemplate] = useState<RequirementTemplate | null>(null);
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null);
  const [isLocalAnalyzing, setIsLocalAnalyzing] = useState(false);
  const [isAiAnalyzing, setIsAiAnalyzing] = useState(false);
  const [analysisStage, setAnalysisStage] = useState<"idle" | "local" | "ai_connecting" | "ai_running">("idle");
  const [analysisSeconds, setAnalysisSeconds] = useState(0);
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

  useEffect(() => {
    if (!currentProject) return;
    fetchRequirementAnalyses(currentProject.id)
      .then((history) => {
        setAnalyses(history);
        setSelectedAnalysisIds((selectedIds) => selectedIds.filter((id) => history.some((item) => item.id === id)));
        setAnalysis(history[0] ?? null);
        if (history[0]) setBatchResult(null);
      })
      .catch(() => {
        setAnalyses([]);
        setAnalysis(null);
      });
  }, [currentProject]);

  function refreshAnalyses(selectedAnalysis?: RequirementAnalysis) {
    if (!currentProject) return;
    fetchRequirementAnalyses(currentProject.id)
      .then((history) => {
        setAnalyses(history);
        setSelectedAnalysisIds((selectedIds) => selectedIds.filter((id) => history.some((item) => item.id === id)));
        if (selectedAnalysis) {
          setAnalysis(history.find((item) => item.id === selectedAnalysis.id) ?? selectedAnalysis);
          return;
        }
        setAnalysis((current) => history.find((item) => item.id === current?.id) ?? history[0] ?? null);
      })
      .catch(() => undefined);
  }

  useEffect(() => {
    if (!isLocalAnalyzing && !isAiAnalyzing) return;
    const timer = window.setInterval(() => setAnalysisSeconds((seconds) => seconds + 1), 1000);
    return () => window.clearInterval(timer);
  }, [isLocalAnalyzing, isAiAnalyzing]);

  async function submit(values: { description: string }) {
    if (!currentProject) return;
    setIsLocalAnalyzing(true);
    setAnalysisSeconds(0);
    try {
      if (batchFile) {
        setAnalysisStage("local");
        const result = await uploadRequirementTable(currentProject.id, batchFile);
        setBatchResult(result);
        setAnalysis(null);
        const successCount = result.items.filter((item) => item.analysis).length;
        message.success(`已分析 ${result.items.length} 条需求，其中 ${successCount} 条完成分析`);
        return;
      }
      setAnalysisStage("local");
      const localResult = await createLocalRequirementAnalysis(currentProject.id, values.description, AbortSignal.timeout(180000));
      setAnalysis(localResult);
      refreshAnalyses(localResult);
      setBatchResult(null);
      message.success("本地分析完成，可继续点击 AI 补充分析");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "本地分析失败");
    } finally {
      setIsLocalAnalyzing(false);
      setAnalysisStage("idle");
    }
  }

  async function runAiAnalysis() {
    if (!analysis) return;
    setIsAiAnalyzing(true);
    setAnalysisSeconds(0);
    setAnalysisStage("ai_connecting");
    const connectingTimer = window.setTimeout(() => {
      setAnalysisStage((stage) => (stage === "ai_connecting" ? "ai_running" : stage));
    }, 1000);
    try {
      const aiResult = await runRequirementAiRecommendations(analysis.id, AbortSignal.timeout(300000));
      setAnalysis(aiResult);
      refreshAnalyses(aiResult);
      message.success(aiResult.ai_message);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "AI 补充分析失败");
    } finally {
      window.clearTimeout(connectingTimer);
      setIsAiAnalyzing(false);
      setAnalysisStage("idle");
    }
  }

  function analysisStageText() {
    if (analysisStage === "local") return "正在执行本地分析：检索归口包、风险库和项目知识库。最长等待 3 分钟。";
    if (analysisStage === "ai_connecting") return "本地分析已完成，正在连接 AI 模型。连接阶段超过 1 分钟会报错。";
    if (analysisStage === "ai_running") return "AI 已开始补充识别缺失测试项。分析阶段最长等待 5 分钟。";
    return "准备分析。";
  }

  function aiStatusAlert(currentAnalysis: RequirementAnalysis) {
    const status = currentAnalysis.ai_status;
    const type = status === "failed" ? "warning" : status === "succeeded" ? "success" : "info";
    return <Alert className="section-card" type={type} showIcon message="AI 分析状态" description={currentAnalysis.ai_message} />;
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
    refreshAnalyses(updated);
    setIsRecommendationModalOpen(false);
    message.success(editingRecommendation ? "推荐项已更新" : "推荐项已新增");
  }

  async function setRecommendationStatus(item: RequirementRecommendation, reviewStatus: string) {
    if (!analysis) return;
    const updated = await updateRequirementRecommendation(analysis.id, item.id, { review_status: reviewStatus });
    setAnalysis(updated);
    refreshAnalyses(updated);
    message.success(reviewStatus === "confirmed" ? "推荐项已确认" : "推荐项已排除");
  }

  async function removeRecommendation(item: RequirementRecommendation) {
    if (!analysis) return;
    const updated = await deleteRequirementRecommendation(analysis.id, item.id);
    setAnalysis(updated);
    refreshAnalyses(updated);
    message.success("推荐项已删除");
  }

  async function removeAnalysis(item: RequirementAnalysis) {
    try {
      await deleteRequirementAnalysis(item.id);
      const nextAnalyses = analyses.filter((analysisItem) => analysisItem.id !== item.id);
      setAnalyses(nextAnalyses);
      setSelectedAnalysisIds((selectedIds) => selectedIds.filter((id) => id !== item.id));
      if (analysis?.id === item.id) setAnalysis(nextAnalyses[0] ?? null);
      message.success("历史分析结果已删除");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "历史分析结果删除失败");
    }
  }

  async function removeSelectedAnalyses() {
    const selectedIds = new Set(selectedAnalysisIds.map(String));
    try {
      await Promise.all([...selectedIds].map((analysisId) => deleteRequirementAnalysis(analysisId)));
      const nextAnalyses = analyses.filter((analysisItem) => !selectedIds.has(analysisItem.id));
      setAnalyses(nextAnalyses);
      setSelectedAnalysisIds([]);
      if (analysis && selectedIds.has(analysis.id)) setAnalysis(nextAnalyses[0] ?? null);
      message.success(`已删除 ${selectedIds.size} 条历史分析结果`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "批量删除历史分析结果失败");
      refreshAnalyses();
    }
  }

  async function includeLocalRecommendation(item: RequirementRecommendation) {
    if (!analysis) return;
    const updated = await includeRequirementRecommendationInLocal(analysis.id, item.id);
    setAnalysis(updated);
    refreshAnalyses(updated);
    message.success("已纳入本地测试条目资产草稿，当前审核状态保持不变");
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

  const analysisColumns: ColumnsType<RequirementAnalysis> = [
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 180,
      render: (value: string) => new Date(value).toLocaleString(),
    },
    {
      title: "需求摘要",
      dataIndex: "description",
      ellipsis: true,
      render: (value: string) => value.split("\n")[0] || value.slice(0, 80),
    },
    {
      title: "推荐项",
      width: 190,
      render: (_, item) => {
        const confirmed = item.recommendations.filter((recommendation) => recommendation.review_status === "confirmed").length;
        const pending = item.recommendations.filter((recommendation) => recommendation.review_status === "pending").length;
        return <Space><Tag color="green">已确认 {confirmed}</Tag><Tag color="gold">待审核 {pending}</Tag></Space>;
      },
    },
    {
      title: "操作",
      width: 150,
      render: (_, item) => (
        <Space>
          <Button size="small" onClick={() => setAnalysis(item)}>查看</Button>
          <Button
            size="small"
            danger
            onClick={() => {
              Modal.confirm({
                title: "删除历史分析结果",
                content: "删除后该分析结果和其中的推荐审核记录会从历史列表移除。",
                okText: "删除",
                okButtonProps: { danger: true },
                cancelText: "取消",
                onOk: () => removeAnalysis(item),
              });
            }}
          >
            删除
          </Button>
        </Space>
      ),
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
            <Button type="primary" htmlType="submit" loading={isLocalAnalyzing}>本地分析</Button>
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
      {analyses.length > 0 && (
        <Card title="历史分析结果" className="section-card">
          <Alert
            className="section-card"
            type="info"
            showIcon
            message="测试方案只会使用已确认的推荐测试条目，待审核和已排除条目不会进入测试方案。"
          />
          <Space className="section-card">
            <Button
              danger
              disabled={selectedAnalysisIds.length === 0}
              onClick={() => {
                Modal.confirm({
                  title: "批量删除历史分析结果",
                  content: `将删除选中的 ${selectedAnalysisIds.length} 条历史分析结果。`,
                  okText: "删除",
                  okButtonProps: { danger: true },
                  cancelText: "取消",
                  onOk: removeSelectedAnalyses,
                });
              }}
            >
              批量删除
            </Button>
            <Typography.Text type="secondary">已选择 {selectedAnalysisIds.length} 条</Typography.Text>
          </Space>
          <Table
            rowKey="id"
            size="small"
            columns={analysisColumns}
            dataSource={analyses}
            pagination={{ pageSize: 5 }}
            rowSelection={{
              selectedRowKeys: selectedAnalysisIds,
              onChange: setSelectedAnalysisIds,
            }}
            rowClassName={(item) => item.id === analysis?.id ? "ant-table-row-selected" : ""}
          />
        </Card>
      )}
      {analysis && (
        <Card title="分析结果" className="section-card">
          {aiStatusAlert(analysis)}
          <Descriptions column={2} size="small">
            <Descriptions.Item label="测试对象">{analysis.parse_result.test_object}</Descriptions.Item>
            <Descriptions.Item label="变更类型">{analysis.parse_result.change_type}</Descriptions.Item>
            <Descriptions.Item label="产品型号">{analysis.parse_result.product_model ?? "待确认"}</Descriptions.Item>
            <Descriptions.Item label="子系统">{analysis.parse_result.subsystem}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{new Date(analysis.created_at).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="方案可用项">
              <Tag color="green">{analysis.recommendations.filter((item) => item.review_status === "confirmed").length} 个已确认</Tag>
            </Descriptions.Item>
          </Descriptions>
          <List
            className="section-card"
            header={
              <Space wrap>
                <span>推荐测试条目</span>
                <Button size="small" onClick={openCreateRecommendation}>新增推荐项</Button>
                <Button size="small" type="primary" onClick={runAiAnalysis} loading={isAiAnalyzing} disabled={!analysis || isLocalAnalyzing}>
                  AI 补充分析
                </Button>
              </Space>
            }
            dataSource={analysis.recommendations}
            renderItem={(item) => (
              <List.Item
                actions={[
                  item.source_type === "ai_generated" && <Button key="include-local" size="small" type="link" onClick={() => includeLocalRecommendation(item)}>纳入本地</Button>,
                  <Button key="confirm" size="small" type="link" onClick={() => setRecommendationStatus(item, "confirmed")}>确认</Button>,
                  <Button key="exclude" size="small" type="link" danger onClick={() => setRecommendationStatus(item, "excluded")}>排除</Button>,
                  <Button key="edit" size="small" type="link" onClick={() => openEditRecommendation(item)}>编辑</Button>,
                  <Button key="delete" size="small" type="link" danger onClick={() => removeRecommendation(item)}>删除</Button>,
                ].filter(Boolean)}
              >
              <List.Item.Meta
                title={
                  <>
                    <Tag color={item.source_type === "ai_generated" ? "purple" : "blue"}>{item.group}</Tag>
                    {item.source_type === "ai_generated" && <Tag color="purple">AI新增</Tag>}
                    {item.source_type === "test_item" && item.source_id !== "manual" && item.review_status === "pending" && <Tag color="cyan">已纳入本地草稿</Tag>}
                    {statusTag(item.review_status)}{item.title}
                  </>
                }
                description={
                  <Space direction="vertical" size={2}>
                    <Typography.Text type="secondary">{item.reason}；依据：{item.evidence}</Typography.Text>
                    {(item.objective || item.method || item.record_template) && (
                      <Typography.Text type="secondary">
                        方案字段：{item.objective ?? "未填写"} / {item.method ?? "未填写"} / {item.record_template ?? "未填写"}
                      </Typography.Text>
                    )}
                  </Space>
                }
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
      {(isLocalAnalyzing || isAiAnalyzing) && (
        <Modal open footer={null} closable={false} centered>
          <Space direction="vertical" align="center" style={{ width: "100%" }}>
            <Spin />
            <Typography.Text>{analysisStageText()}</Typography.Text>
            <Typography.Text type="secondary">已耗时：{analysisSeconds} 秒</Typography.Text>
            {analysisStage === "local" && analysisSeconds > 30 && <Alert type="info" showIcon message="本地资料较多时可能需要更长时间，请等待本地结果返回。" />}
            {analysisStage === "ai_connecting" && analysisSeconds > 20 && <Alert type="warning" showIcon message="AI 连接耗时较长，请检查模型服务地址、网络和 API Key 配置。" />}
            {analysisStage === "ai_running" && analysisSeconds > 120 && <Alert type="warning" showIcon message="AI 正在分析缺失测试项，复杂需求可能耗时较长。" />}
          </Space>
        </Modal>
      )}
    </section>
  );
}
