import { Button, Card, Form, Input, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(values: { username: string; password: string }) {
    try {
      await login(values.username, values.password);
      navigate("/");
    } catch {
      message.error("账号或密码错误");
    }
  }

  return (
    <main className="login-page">
      <Card className="login-card">
        <Typography.Title level={3}>基因测序仪 AI 测试平台</Typography.Title>
        <Typography.Paragraph type="secondary">
          登录后进入项目工作台、统一资料池和验证方案生成流程。
        </Typography.Paragraph>
        <Form layout="vertical" initialValues={{ username: "admin", password: "admin123" }} onFinish={handleSubmit}>
          <Form.Item label="账号" name="username" rules={[{ required: true, message: "请输入账号" }]}>
            <Input placeholder="请输入账号" />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true, message: "请输入密码" }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Button type="primary" block htmlType="submit">
            登录
          </Button>
        </Form>
      </Card>
    </main>
  );
}
