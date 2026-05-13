import { Button, Card, Descriptions, Form, Input, InputNumber, Select, Space, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { AiConfig, fetchAiConfig, updateAiConfig } from "../api/client";

type AiSettingsForm = {
  provider: string;
  base_url: string;
  api_key: string;
  model: string;
  timeout_seconds: number;
};

export default function SettingsPage() {
  const [form] = Form.useForm<AiSettingsForm>();
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

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

  useEffect(() => {
    loadConfig();
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
    </section>
  );
}
