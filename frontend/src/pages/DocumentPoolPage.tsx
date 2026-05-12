import { Button, Card, Form, Input, message, Modal, Space, Table, Tag, Typography, Upload } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import {
  DocumentItem,
  extractDocumentLabels,
  fetchDocuments,
  parseDocument,
  ParsingTask,
  reviewDocument,
  updateDocumentLabels,
  uploadDocument,
} from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function DocumentPoolPage() {
  const { currentProject } = useProjects();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<DocumentItem | null>(null);
  const [lastTask, setLastTask] = useState<ParsingTask | null>(null);
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
  }, [currentProject?.id]);

  async function handleUpload(file: File) {
    if (!currentProject) return false;
    await uploadDocument(currentProject.id, file);
    message.success("资料已上传，等待标签确认");
    await loadDocuments();
    return false;
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
            上传测试规范、验证方案、测试报告、Jira 导出和 DFMEA 文件，经过标签确认、去重和管理员审核后进入可用资料池。
          </Typography.Paragraph>
        </div>
        <Upload beforeUpload={handleUpload} showUploadList={false}>
          <Button type="primary" disabled={!currentProject}>上传资料</Button>
        </Upload>
      </Space>
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
