import { Button, Card, Form, Input, List, Switch, Tag, Typography, message } from "antd";
import { useState } from "react";
import { askFreeChat, FreeChatResponse } from "../api/client";
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
  const [result, setResult] = useState<FreeChatResponse | null>(null);

  function submit(values: ChatForm) {
    if (!currentProject) return;
    setLoading(true);
    askFreeChat(currentProject.id, values.question, values.use_project_knowledge, values.use_external_model)
      .then(setResult)
      .catch((error: Error) => message.error(`提问失败：${error.message}`))
      .finally(() => setLoading(false));
  }

  return (
    <section>
      <Typography.Title level={2}>自由应用</Typography.Title>
      <Typography.Paragraph type="secondary">
        面向当前项目空间自由提问。系统会优先检索已上传并沉淀的资料库，再结合已配置的大模型生成回答。
      </Typography.Paragraph>
      <Card title="自由提问" className="section-card">
        <Form form={form} layout="vertical" onFinish={submit} initialValues={{ use_project_knowledge: true, use_external_model: true }}>
          <Form.Item name="question" label="问题" rules={[{ required: true, message: "请输入问题" }]}>
            <Input.TextArea rows={4} placeholder="例如：G99 ECR4.0 需要重点关注哪些历史风险和回归测试？" />
          </Form.Item>
          <Form.Item name="use_project_knowledge" label="使用当前项目资料库" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="use_external_model" label="调用已配置大模型" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>提交问题</Button>
        </Form>
      </Card>
      {result && (
        <Card title="回答" className="section-card">
          <Tag color={result.used_model ? "green" : "default"}>{result.used_model ? "大模型回答" : "本地资料命中"}</Tag>
          <Typography.Paragraph className="section-card" style={{ whiteSpace: "pre-wrap" }}>{result.answer}</Typography.Paragraph>
          <List
            size="small"
            header="引用来源"
            dataSource={result.sources}
            renderItem={(source) => (
              <List.Item>
                <List.Item.Meta title={`[${source.source_type}] ${source.title}`} description={source.text} />
              </List.Item>
            )}
          />
        </Card>
      )}
    </section>
  );
}
