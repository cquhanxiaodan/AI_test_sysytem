import { Button, Card, Form, Input, message, Modal, Select, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import { createFeedback, FeedbackItem, fetchFeedbackItems, updateFeedback } from "../api/client";
import { useAuth } from "../context/AuthContext";

const STATUS_OPTIONS = [
  { label: "待处理", value: "pending" },
  { label: "处理中", value: "processing" },
  { label: "已解决", value: "resolved" },
  { label: "已关闭", value: "closed" },
];

export default function FeedbackPage() {
  const { user } = useAuth();
  const isAdmin = user?.roles.includes("admin") ?? false;
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<FeedbackItem | null>(null);
  const [form] = Form.useForm<{ feedback_type: "bug" | "requirement"; content: string }>();
  const [adminForm] = Form.useForm<{ status: FeedbackItem["status"]; admin_reply: string }>();

  async function loadItems() {
    setLoading(true);
    try {
      setItems(await fetchFeedbackItems());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadItems();
  }, []);

  async function submitFeedback(values: { feedback_type: "bug" | "requirement"; content: string }) {
    await createFeedback(values);
    message.success("反馈已提交");
    form.resetFields();
    await loadItems();
  }

  function openAdminModal(item: FeedbackItem) {
    setEditing(item);
    adminForm.setFieldsValue({ status: item.status, admin_reply: item.admin_reply });
  }

  async function saveAdminUpdate() {
    if (!editing) return;
    const values = await adminForm.validateFields();
    await updateFeedback(editing.id, values);
    message.success("反馈处理信息已更新");
    setEditing(null);
    adminForm.resetFields();
    await loadItems();
  }

  const columns: ColumnsType<FeedbackItem> = [
    { title: "提交人", dataIndex: "submitter_name", width: 120 },
    { title: "日期", dataIndex: "submit_date", width: 180, render: (value: string) => new Date(value).toLocaleString() },
    { title: "类型", dataIndex: "feedback_type", width: 120, render: (value: string) => <Tag color={value === "bug" ? "red" : "blue"}>{value === "bug" ? "Bug" : "需求"}</Tag> },
    { title: "详细内容", dataIndex: "content", ellipsis: true },
    { title: "状态", dataIndex: "status", width: 120, render: statusTag },
    { title: "管理员回复", dataIndex: "admin_reply", ellipsis: true, render: (value: string) => value || "-" },
    { title: "回复日期", dataIndex: "replied_at", width: 180, render: (value: string | null) => value ? new Date(value).toLocaleString() : "-" },
    { title: "最近更新", dataIndex: "updated_at", width: 180, render: (value: string) => new Date(value).toLocaleString() },
    {
      title: "操作",
      width: 120,
      render: (_, item) => isAdmin ? <Button size="small" onClick={() => openAdminModal(item)}>回复/更新</Button> : null,
    },
  ];

  return (
    <section>
      <Typography.Title level={2}>Bug与需求反馈</Typography.Title>
      <Typography.Paragraph type="secondary">
        普通用户和管理员都可以提交使用过程中的 Bug 或新增需求。管理员会在本页回复并更新处理状态。
      </Typography.Paragraph>
      <Card title="提交反馈" className="section-card">
        <Form form={form} layout="vertical" onFinish={submitFeedback} initialValues={{ feedback_type: "bug" }}>
          <Form.Item label="Bug/需求" name="feedback_type" rules={[{ required: true, message: "请选择反馈类型" }]}> 
            <Select options={[{ label: "Bug", value: "bug" }, { label: "新增需求", value: "requirement" }]} />
          </Form.Item>
          <Form.Item label="详细内容" name="content" rules={[{ required: true, message: "请输入详细内容" }]}> 
            <Input.TextArea rows={5} placeholder="请描述复现步骤、期望结果、实际结果，或新增需求的使用场景和目标。" />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">提交反馈</Button>
            <Typography.Text type="secondary">当前提交人：{user?.display_name ?? "当前用户"}；提交日期由系统自动记录。</Typography.Text>
          </Space>
        </Form>
      </Card>
      <Card title={isAdmin ? "全部反馈" : "我的反馈"}>
        <Table rowKey="id" loading={loading} columns={columns} dataSource={items} pagination={{ pageSize: 10 }} />
      </Card>
      <Modal title="管理员回复与状态更新" open={Boolean(editing)} onCancel={() => setEditing(null)} onOk={saveAdminUpdate} destroyOnHidden>
        <Form form={adminForm} layout="vertical">
          <Form.Item label="处理状态" name="status" rules={[{ required: true, message: "请选择处理状态" }]}> 
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item label="管理员回复" name="admin_reply"> 
            <Input.TextArea rows={5} placeholder="填写处理说明、解决方案或后续计划。" />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}

function statusTag(status: FeedbackItem["status"]) {
  const labelMap: Record<FeedbackItem["status"], string> = {
    pending: "待处理",
    processing: "处理中",
    resolved: "已解决",
    closed: "已关闭",
  };
  const colorMap: Record<FeedbackItem["status"], string> = {
    pending: "gold",
    processing: "blue",
    resolved: "green",
    closed: "default",
  };
  return <Tag color={colorMap[status]}>{labelMap[status]}</Tag>;
}
