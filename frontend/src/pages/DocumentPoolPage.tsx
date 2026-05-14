import { Button, Card, Form, Input, message, Modal, Space, Table, Tag, Typography, Upload } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { UploadFile } from "antd/es/upload/interface";
import { useEffect, useState } from "react";
import {
  DocumentDirectoryScanResult,
  DocumentItem,
  fetchDocumentImportConfig,
  extractDocumentLabels,
  fetchDocuments,
  parseDocument,
  ParsingTask,
  reviewDocument,
  scanDocumentImportDirectory,
  updateDocumentLabels,
  uploadDocument,
  uploadDocuments,
} from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function DocumentPoolPage() {
  const { currentProject } = useProjects();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<DocumentItem | null>(null);
  const [lastTask, setLastTask] = useState<ParsingTask | null>(null);
  const [importDirectory, setImportDirectory] = useState("");
  const [lastScan, setLastScan] = useState<DocumentDirectoryScanResult | null>(null);
  const [batchFiles, setBatchFiles] = useState<UploadFile[]>([]);
  const [form] = Form.useForm<Record<string, string>>();

  async function loadDocuments() {
    if (!currentProject) return;
    setLoading(true);
    try {
      setDocuments(await fetchDocuments(currentProject.id));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
    fetchDocumentImportConfig()
      .then((config) => setImportDirectory(config.import_directory))
      .catch(() => setImportDirectory(""));
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
    message.success("资料已发布");
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

  const columns: ColumnsType<DocumentItem> = [
    { title: "文件名", dataIndex: "filename" },
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
      </Space>
      <Card className="section-card">
        <Typography.Paragraph type="secondary">
          服务器导入目录：{importDirectory || "未配置，请到系统设置中配置资料导入目录"}
        </Typography.Paragraph>
      </Card>
      <Card>
        <Table rowKey="id" loading={loading} columns={columns} dataSource={documents} pagination={false} />
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
            <Input placeholder="例如 RFID" />
          </Form.Item>
          <Form.Item label="文档类型" name="document_type">
            <Input placeholder="例如 验证方案" />
          </Form.Item>
          <Form.Item label="变更类型" name="change_type">
            <Input placeholder="例如 供应商变更" />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
