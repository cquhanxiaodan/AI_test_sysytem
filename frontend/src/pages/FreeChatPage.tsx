import { Alert, Button, Card, Form, Input, List, Space, Switch, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { askFreeChat, fetchAiConfig, FreeChatMessage, FreeChatResponse } from "../api/client";
import { useProjects } from "../context/ProjectContext";

type ChatForm = {
  question: string;
  use_project_knowledge: boolean;
  use_external_model: boolean;
};

export default function FreeChatPage() {
  const { currentProject } = useProjects();
  const [form] = Form.useForm<ChatForm>();
  const [loading, setLoading] = useState(false);
  const [aiTimeoutSeconds, setAiTimeoutSeconds] = useState(120);
  const [lastAiStatus, setLastAiStatus] = useState<Pick<FreeChatResponse, "ai_status" | "ai_message" | "used_model"> | null>(null);
  const [messages, setMessages] = useState<Array<FreeChatMessage & {
    used_model?: boolean;
    sources?: FreeChatResponse["sources"];
    ai_status?: string;
    ai_message?: string;
  }>>([]);

  useEffect(() => {
    fetchAiConfig()
      .then((config) => setAiTimeoutSeconds(config.timeout_seconds))
      .catch(() => undefined);
  }, []);

  function submit(values: ChatForm) {
    if (!currentProject) return;
    const history = messages.map((item) => ({ role: item.role, content: item.content }));
    const userMessage: FreeChatMessage = { role: "user", content: values.question };
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), (aiTimeoutSeconds + 10) * 1000);
    setMessages((current) => [...current, userMessage]);
    setLoading(true);
    askFreeChat(currentProject.id, values.question, values.use_project_knowledge, values.use_external_model, history, controller.signal)
      .then((result) => {
        setLastAiStatus({ ai_status: result.ai_status, ai_message: result.ai_message, used_model: result.used_model });
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: result.answer,
            used_model: result.used_model,
            sources: result.sources,
            ai_status: result.ai_status,
            ai_message: result.ai_message,
          },
        ]);
        form.setFieldsValue({ question: "" });
      })
      .catch((error: Error) => {
        setMessages((current) => current.slice(0, -1));
        if (!error.message.includes("登录已过期")) {
          setLastAiStatus({ ai_status: "failed", ai_message: error.message, used_model: false });
        }
        message.error(`提问失败：${error.message}`);
      })
      .finally(() => {
        window.clearTimeout(timeoutId);
        setLoading(false);
      });
  }

  return (
    <section>
      <Typography.Title level={2}>自由应用</Typography.Title>
      <Typography.Paragraph type="secondary">
        面向当前项目空间连续对话式提问。开启项目资料库时，系统会把命中的本地资料作为参考提供给大模型；关闭后，大模型会基于当前对话和通用知识自由回答。
      </Typography.Paragraph>
      <Card
        title="当前对话"
        className="section-card"
        extra={<Button onClick={() => setMessages([])} disabled={messages.length === 0}>清空对话</Button>}
      >
        {messages.length === 0 ? (
          <Typography.Paragraph type="secondary">当前还没有对话。输入问题后可连续追问，系统会带上本轮会话上下文。</Typography.Paragraph>
        ) : (
          <List
            dataSource={messages}
            renderItem={(item, index) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color={item.role === "user" ? "blue" : item.used_model ? "green" : "default"}>
                        {getMessageTag(item)}
                      </Tag>
                      <span>第 {index + 1} 条</span>
                    </Space>
                  }
                  description={<Typography.Paragraph style={{ whiteSpace: "pre-wrap" }}>{item.content}</Typography.Paragraph>}
                />
                {item.role === "assistant" && item.ai_message && (
                  <Alert
                    style={{ marginBottom: 12 }}
                    type={item.used_model ? "success" : item.ai_status === "failed" ? "warning" : "info"}
                    showIcon
                    message={getAiStatusTitle(item)}
                    description={item.ai_message}
                  />
                )}
                {item.sources && item.sources.length > 0 && (
                  <List
                    size="small"
                    header="引用来源"
                    dataSource={item.sources}
                    renderItem={(source) => (
                      <List.Item>
                        <List.Item.Meta title={`[${source.source_type}] ${source.title}`} description={source.text} />
                      </List.Item>
                    )}
                  />
                )}
              </List.Item>
            )}
          />
        )}
      </Card>
      <Card title="继续提问" className="section-card">
        {lastAiStatus && (
          <Alert
            style={{ marginBottom: 16 }}
            type={lastAiStatus.used_model ? "success" : lastAiStatus.ai_status === "failed" ? "warning" : "info"}
            showIcon
            message={getLastAiStatusTitle(lastAiStatus)}
            description={lastAiStatus.ai_message}
          />
        )}
        <Form form={form} layout="vertical" onFinish={submit} initialValues={{ use_project_knowledge: true, use_external_model: true }}>
          <Form.Item name="question" label="问题" rules={[{ required: true, message: "请输入问题" }]}> 
            <Input.TextArea rows={4} placeholder="例如：G99 ECR4.0 需要重点关注哪些历史风险和回归测试？也可以继续追问：这些风险里哪些要进入验证方案？" />
          </Form.Item>
          <Form.Item name="use_project_knowledge" label="带上当前项目资料库参考" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="use_external_model" label="调用已配置大模型" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>提交问题</Button>
        </Form>
      </Card>
    </section>
  );
}

function getMessageTag(item: FreeChatMessage & { used_model?: boolean; ai_status?: string; sources?: FreeChatResponse["sources"] }) {
  if (item.role === "user") return "我";
  if (item.used_model) return "大模型回答";
  if (item.ai_status === "failed") return "AI 调用失败";
  return item.sources && item.sources.length > 0 ? "本地资料命中" : "本地兜底回答";
}

function getAiStatusTitle(status: { ai_status?: string; used_model?: boolean }) {
  if (status.used_model) return "AI 模型已成功响应";
  if (status.ai_status === "failed") return "AI 模型未返回有效回答";
  if (status.ai_status === "not_configured") return "AI 模型未配置";
  return "已使用本地资料回答";
}

function getLastAiStatusTitle(status: Pick<FreeChatResponse, "ai_status" | "used_model">) {
  if (status.used_model) return "上次提问已成功调用 AI 模型";
  if (status.ai_status === "failed") return "上次提问 AI 模型未返回有效回答";
  if (status.ai_status === "not_configured") return "上次提问未配置 AI 模型";
  return "上次提问使用本地资料回答";
}
