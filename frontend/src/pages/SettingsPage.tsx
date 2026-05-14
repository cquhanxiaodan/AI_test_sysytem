import { Button, Card, Descriptions, Form, Input, InputNumber, Select, Space, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { AiConfig, DocumentImportConfig, fetchAiConfig, fetchDocumentImportConfig, updateAiConfig, updateDocumentImportConfig } from "../api/client";

type AiSettingsForm = {
  provider: string;
  base_url: string;
  api_key: string;
  model: string;
  timeout_seconds: number;
};

type DocumentImportForm = {
  import_directory: string;
};

export default function SettingsPage() {
  const [form] = Form.useForm<AiSettingsForm>();
  const [documentImportForm] = Form.useForm<DocumentImportForm>();
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null);
  const [documentImportConfig, setDocumentImportConfig] = useState<DocumentImportConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingDocumentImport, setSavingDocumentImport] = useState(false);

  function loadConfig() {
    setLoading(true);
    fetchAiConfig()
      .then((config) => {
        setAiConfig(config);
        form.setFieldsValue({
          provider: config.provider,
          base_url: config.base_url,
          api_key: "",
          model: config.model === "local-rule-engine" ? "" : config.model,
          timeout_seconds: config.timeout_seconds,
        });
      })
      .catch((error: Error) => message.error(`读取 AI 配置失败：${error.message}`))
      .finally(() => setLoading(false));
  }

  function loadDocumentImportConfig() {
    fetchDocumentImportConfig()
      .then((config) => {
        setDocumentImportConfig(config);
        documentImportForm.setFieldsValue({ import_directory: config.import_directory });
      })
      .catch((error: Error) => message.error(`读取资料导入配置失败：${error.message}`));
  }

  useEffect(() => {
    loadConfig();
    loadDocumentImportConfig();
  }, []);

  function save(values: AiSettingsForm) {
    setSaving(true);
    updateAiConfig(values)
      .then((config) => {
        setAiConfig(config);
        form.setFieldsValue({ api_key: "" });
        message.success("AI 模型设置已保存");
      })
      .catch((error: Error) => message.error(`保存失败：${error.message}`))
      .finally(() => setSaving(false));
  }

  function saveDocumentImport(values: DocumentImportForm) {
    setSavingDocumentImport(true);
    updateDocumentImportConfig(values.import_directory)
      .then((config) => {
        setDocumentImportConfig(config);
        message.success("资料导入目录已保存");
      })
      .catch((error: Error) => message.error(`保存失败：${error.message}`))
      .finally(() => setSavingDocumentImport(false));
  }

  return (
    <section>
      <Typography.Title level={2}>系统设置</Typography.Title>
      <Typography.Paragraph type="secondary">
        管理 AI 模型网关配置。所有登录用户都可以配置并调用 AI；配置保存后会立即用于当前后端进程内的标签识别、条目拆分、风险解析、需求分析和方案检查。
      </Typography.Paragraph>

      <Card title="AI 模型状态" className="section-card" loading={loading}>
        {aiConfig && (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="接入状态">
              <Tag color={aiConfig.configured ? "green" : "default"}>{aiConfig.configured ? "已接入" : "本地规则兜底"}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="模型提供方">{aiConfig.provider}</Descriptions.Item>
            <Descriptions.Item label="接口地址">{aiConfig.base_url || "未配置"}</Descriptions.Item>
            <Descriptions.Item label="模型名称">{aiConfig.model}</Descriptions.Item>
            <Descriptions.Item label="API Key">{aiConfig.api_key_masked || "未配置"}</Descriptions.Item>
            <Descriptions.Item label="超时时间">{aiConfig.timeout_seconds} 秒</Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      <Card title="AI 模型配置" className="section-card">
        <Form form={form} layout="vertical" onFinish={save} initialValues={{ provider: "local", timeout_seconds: 20 }}>
          <Form.Item name="provider" label="模型提供方" rules={[{ required: true, message: "请选择模型提供方" }]}>
            <Select
              options={[
                { label: "本地规则兜底", value: "local" },
                { label: "OpenAI 兼容接口", value: "openai-compatible" },
              ]}
            />
          </Form.Item>
          <Form.Item name="base_url" label="Base URL" extra="示例：https://your-model-gateway.example.com/v1">
            <Input placeholder="https://your-model-gateway.example.com/v1" />
          </Form.Item>
          <Form.Item name="model" label="模型名称">
            <Input placeholder="your-model-name" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key" extra="留空会保留当前 API Key；切换到本地规则兜底会清空运行时 API Key。">
            <Input.Password placeholder={aiConfig?.api_key_configured ? "已配置，留空保持不变" : "请输入 API Key"} autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="timeout_seconds" label="调用超时时间" rules={[{ required: true, message: "请输入调用超时时间" }]}>
            <InputNumber min={1} max={120} addonAfter="秒" className="full-width" />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={saving}>保存设置</Button>
            <Button onClick={loadConfig}>刷新状态</Button>
          </Space>
        </Form>
      </Card>

      <Card title="统一资料池导入目录" className="section-card">
        <Typography.Paragraph type="secondary">
          配置后端服务器上的资料目录。统一资料池页面点击扫描新增资料时，会读取该目录下普通文件并按 hash 去重导入。
        </Typography.Paragraph>
        {documentImportConfig && (
          <Descriptions column={1} size="small" className="section-card">
            <Descriptions.Item label="配置状态">
              <Tag color={documentImportConfig.configured ? "green" : "default"}>{documentImportConfig.configured ? "已配置" : "未配置"}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="当前目录">{documentImportConfig.import_directory || "未配置"}</Descriptions.Item>
          </Descriptions>
        )}
        <Form form={documentImportForm} layout="vertical" onFinish={saveDocumentImport}>
          <Form.Item name="import_directory" label="服务器资料导入目录" extra="示例：/data/gene-test-imports。该路径需要后端服务进程可读取。">
            <Input placeholder="/data/gene-test-imports" />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={savingDocumentImport}>保存导入目录</Button>
            <Button onClick={loadDocumentImportConfig}>刷新目录配置</Button>
          </Space>
        </Form>
      </Card>
    </section>
  );
}
