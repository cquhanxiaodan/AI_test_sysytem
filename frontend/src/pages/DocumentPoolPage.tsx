import { Button, Card, Form, Input, message, Modal, Select, Space, Table, Tag, Typography, Upload } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { UploadFile } from "antd/es/upload/interface";
import { useEffect, useState } from "react";
import {
  bulkDeleteDocuments,
  DocumentDirectoryScanResult,
  DocumentItem,
  fetchDocumentImportConfig,
  fetchSystemConfig,
  extractDocumentLabels,
  fetchDocuments,
  parseDocument,
  ParsingTask,
  reviewDocument,
  scanDocumentImportDirectory,
  updateDocumentLabels,
  uploadDocument,
  uploadDocuments,
  SystemConfig,
} from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function DocumentPoolPage() {
  const { currentProject, projects } = useProjects();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<DocumentItem | null>(null);
  const [lastTask, setLastTask] = useState<ParsingTask | null>(null);
  const [importDirectory, setImportDirectory] = useState("");
  const [lastScan, setLastScan] = useState<DocumentDirectoryScanResult | null>(null);
  const [batchFiles, setBatchFiles] = useState<UploadFile[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<React.Key[]>([]);
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  const [form] = Form.useForm<Record<string, string>>();

  async function loadDocuments() {
    setLoading(true);
    try {
      setDocuments(await fetchDocuments());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
    fetchDocumentImportConfig()
      .then((config) => setImportDirectory(config.import_directory))
      .catch(() => setImportDirectory(""));
    fetchSystemConfig().then(setSystemConfig).catch(() => setSystemConfig(null));
  }, [currentProject?.id]);

  async function handleUpload(file: File) {
    if (!currentProject) return false;
    await uploadDocument(currentProject.id, file);
    message.success("资料已上传，请确认标签；管理员发布后系统会自动沉淀对应测试资产");
    await loadDocuments();
    return false;
  }

  function handleBatchUpload(file: UploadFile) {
    setBatchFiles((current) => [...current, file]);
    return false;
  }

  async function submitBatchUpload() {
    if (!currentProject) return false;
    const files = batchFiles.flatMap((file) => file.originFileObj ? [file.originFileObj as File] : []);
    if (files.length === 0) {
      message.warning("请先选择批量上传文件");
      return false;
    }
    const result = await uploadDocuments(currentProject.id, files);
    setBatchFiles([]);
    message.success(`已批量上传 ${result.documents.length} 个资料，请确认标签`);
    await loadDocuments();
    return false;
  }

  async function scanImportDirectory() {
    if (!currentProject) return;
    const result = await scanDocumentImportDirectory(currentProject.id);
    setLastScan(result);
    message.success(`扫描完成，新增导入 ${result.imported.length} 个资料`);
    await loadDocuments();
  }

  function openLabelModal(document: DocumentItem) {
    const suggestedLabels = Object.fromEntries(
      document.label_suggestions.map((suggestion) => [suggestion.label_key, suggestion.label_value]),
    );
    form.setFieldsValue({ ...suggestedLabels, ...document.labels });
    setEditing(document);
  }

  async function saveLabels() {
    if (!editing) return;
    await updateDocumentLabels(editing.id, form.getFieldsValue());
    message.success("标签已提交审核");
    setEditing(null);
    await loadDocuments();
  }

  async function publishDocument(document: DocumentItem) {
    await reviewDocument(document.id, "publish", "前端审核通过");
    const documentType = document.labels.document_type || document.label_suggestions.find((suggestion) => suggestion.label_key === "document_type")?.label_value || "";
    if (["验证方案", "测试规范", "测试报告"].includes(documentType)) {
      message.success("资料已发布，系统已自动拆分测试条目；RFID 资料会同步生成归口包");
    } else if (["Jira导出", "DFMEA"].includes(documentType)) {
      message.success("资料已发布，系统已自动解析风险知识源");
    } else {
      message.success("资料已发布；请确认 document_type 标签后可触发对应资产沉淀流程");
    }
    await loadDocuments();
  }

  async function runParse(document: DocumentItem) {
    const task = await parseDocument(document.id);
    setLastTask(task);
    message.success(task.message);
  }

  async function runLabelExtraction(document: DocumentItem) {
    const task = await extractDocumentLabels(document.id);
    setLastTask(task);
    message.success(task.message);
    await loadDocuments();
  }

  async function deleteSelectedDocuments() {
    if (selectedDocumentIds.length === 0) return;
    const result = await bulkDeleteDocuments(selectedDocumentIds.map(String));
    setSelectedDocumentIds([]);
    if (result.deleted_ids.length > 0) {
      message.success(`已删除 ${result.deleted_ids.length} 个资料`);
    }
    if (result.skipped.length > 0) {
      message.warning(`有 ${result.skipped.length} 个资料未删除，请检查权限或资料状态`);
    }
    await loadDocuments();
  }

  const columns: ColumnsType<DocumentItem> = [
    { title: "文件名", dataIndex: "filename" },
    { title: "所属项目", dataIndex: "project_id", render: (projectId) => projects.find((project) => project.id === projectId)?.name ?? projectId },
    { title: "状态", dataIndex: "status", render: (status) => <Tag color="blue">{status}</Tag> },
    {
      title: "系统建议标签",
      dataIndex: "label_suggestions",
      render: (suggestions: DocumentItem["label_suggestions"]) => suggestions.map((item) => (
        <Tag key={`${item.label_key}-${item.label_value}`}>{item.label_key}: {item.label_value}</Tag>
      )),
    },
    {
      title: "已确认标签",
      dataIndex: "labels",
      render: (labels: Record<string, string>) => Object.entries(labels).map(([key, value]) => <Tag key={key} color="green">{key}: {value}</Tag>),
    },
    {
      title: "操作",
      render: (_, document) => (
        <Space>
          <Button size="small" onClick={() => runParse(document)}>解析切片</Button>
          <Button size="small" onClick={() => runLabelExtraction(document)}>AI 标签</Button>
          <Button size="small" onClick={() => openLabelModal(document)}>确认标签</Button>
          <Button size="small" type="primary" disabled={document.status !== "pending_review"} onClick={() => publishDocument(document)}>
            发布
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <section>
      <Space className="page-title" align="start">
        <div>
          <Typography.Title level={2}>统一资料池</Typography.Title>
          <Typography.Paragraph type="secondary">
            上传测试规范、验证方案、测试报告、Jira 导出和 DFMEA 文件。资料发布后会按文档类型自动进入解析、测试条目拆分、归口包生成或风险知识源入库流程。
          </Typography.Paragraph>
        </div>
        <Upload beforeUpload={handleUpload} showUploadList={false}>
          <Button type="primary" disabled={!currentProject}>上传资料</Button>
        </Upload>
        <Upload
          beforeUpload={handleBatchUpload}
          fileList={batchFiles}
          onRemove={(file) => setBatchFiles((current) => current.filter((item) => item.uid !== file.uid))}
          multiple
        >
          <Button disabled={!currentProject}>选择批量文件</Button>
        </Upload>
        <Button disabled={!currentProject || batchFiles.length === 0} onClick={submitBatchUpload}>提交批量上传</Button>
        <Button disabled={!currentProject || !importDirectory} onClick={scanImportDirectory}>扫描新增资料</Button>
        <Button danger disabled={selectedDocumentIds.length === 0} onClick={deleteSelectedDocuments}>删除选中资料</Button>
      </Space>
      <Card className="section-card">
        <Typography.Paragraph type="secondary">
          服务器导入目录：{importDirectory || "未配置，请到系统设置中配置资料导入目录"}
        </Typography.Paragraph>
      </Card>
      <Card>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={documents}
          pagination={false}
          rowSelection={{
            selectedRowKeys: selectedDocumentIds,
            onChange: setSelectedDocumentIds,
          }}
        />
      </Card>
      {lastTask && (
        <Card title="最近解析任务" className="section-card">
          <Typography.Paragraph>{lastTask.message}</Typography.Paragraph>
          {lastTask.chunks.map((chunk) => (
            <Typography.Paragraph key={chunk.id} type="secondary">
              {chunk.sequence}. {chunk.text}
            </Typography.Paragraph>
          ))}
        </Card>
      )}
      {lastScan && (
        <Card title="最近目录扫描结果" className="section-card">
          <Typography.Paragraph>目录：{lastScan.import_directory}</Typography.Paragraph>
          <Typography.Paragraph>新增导入：{lastScan.imported.length} 个；跳过：{lastScan.skipped.length} 个；失败：{lastScan.errors.length} 个</Typography.Paragraph>
          {lastScan.imported.map((document) => <Tag key={document.id} color="green">{document.filename}</Tag>)}
          {lastScan.errors.map((error) => <Typography.Paragraph key={error} type="danger">{error}</Typography.Paragraph>)}
        </Card>
      )}
      <Modal title="确认资料标签" open={Boolean(editing)} onCancel={() => setEditing(null)} onOk={saveLabels}>
        <Form form={form} layout="vertical">
          <Form.Item label="产品型号" name="product_model">
            <Input placeholder="例如 DNBSEQ-G99" />
          </Form.Item>
          <Form.Item label="子系统" name="subsystem">
            <Select showSearch allowClear placeholder="请选择子系统" options={toOptions(systemConfig?.subsystem_catalog || [])} />
          </Form.Item>
          <Form.Item label="模块" name="module">
            <Select showSearch allowClear placeholder="请选择或输入模块" options={toOptions(["RFID"])} />
          </Form.Item>
          <Form.Item label="文档类型" name="document_type">
            <Select showSearch allowClear placeholder="请选择文档类型" options={toOptions(systemConfig?.document_types || [])} />
          </Form.Item>
          <Form.Item label="变更类型" name="change_type">
            <Select showSearch allowClear placeholder="请选择变更类型" options={toOptions(systemConfig?.change_types || [])} />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}

function toOptions(values: string[]) {
  return values.map((value) => ({ label: value, value }));
}
