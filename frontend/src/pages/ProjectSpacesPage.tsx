import { Button, Card, Form, Input, Modal, Space, Table, Tag, Typography, message } from "antd";
import { useState } from "react";
import { createProject, deleteProject, Project, ProjectCreatePayload } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useProjects } from "../context/ProjectContext";

export default function ProjectSpacesPage() {
  const { user } = useAuth();
  const { projects, currentProject, reloadProjects, selectProject } = useProjects();
  const [form] = Form.useForm<ProjectCreatePayload>();
  const [deleteForm] = Form.useForm<{ password: string }>();
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [targetProject, setTargetProject] = useState<Project | null>(null);
  const canDeleteProject = user?.roles.includes("admin") ?? false;

  function submit(values: ProjectCreatePayload) {
    setCreating(true);
    createProject(values)
      .then((project) => {
        message.success("项目空间已创建");
        form.resetFields();
        return reloadProjects().then(() => selectProject(project.id));
      })
      .catch((error: Error) => message.error(`创建失败：${error.message}`))
      .finally(() => setCreating(false));
  }

  function confirmDelete(values: { password: string }) {
    if (!targetProject) return;
    setDeleting(true);
    deleteProject(targetProject.id, values.password)
      .then(() => {
        message.success("项目空间已删除");
        setTargetProject(null);
        deleteForm.resetFields();
        return reloadProjects();
      })
      .catch((error: Error) => message.error(`删除失败：${error.message}`))
      .finally(() => setDeleting(false));
  }

  return (
    <section>
      <Typography.Title level={2}>项目空间</Typography.Title>
      <Typography.Paragraph type="secondary">
        创建和选择项目空间。项目空间通常对应某个产品项目的综合变更，例如 G99 ECR4.0，用于隔离资料、测试资产、风险知识和验证方案上下文。删除项目空间仅管理员可操作。
      </Typography.Paragraph>

      <Card title="创建项目空间" className="section-card">
        <Form form={form} layout="vertical" onFinish={submit}>
          <Form.Item name="code" label="项目编码" rules={[{ required: true, message: "请输入项目编码" }]}>
            <Input placeholder="例如 G99-ECR4.0" />
          </Form.Item>
          <Form.Item name="name" label="项目名称" rules={[{ required: true, message: "请输入项目名称" }]}>
            <Input placeholder="例如 G99 ECR4.0 综合变更验证" />
          </Form.Item>
          <Form.Item name="description" label="项目说明">
            <Input.TextArea rows={3} placeholder="说明综合变更背景、范围或资料治理口径" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={creating}>创建项目空间</Button>
        </Form>
      </Card>

      <Card title="已有项目空间" className="section-card">
        <Table
          rowKey="id"
          dataSource={projects}
          pagination={false}
          columns={[
            { title: "项目编码", dataIndex: "code" },
            { title: "项目名称", dataIndex: "name" },
            { title: "角色", dataIndex: "role", render: (role) => <Tag color={role === "owner" ? "green" : "blue"}>{role}</Tag> },
            { title: "项目说明", dataIndex: "description" },
            {
              title: "操作",
              render: (_, project) => (
                <Space>
                  <Button type={currentProject?.id === project.id ? "primary" : "default"} onClick={() => selectProject(project.id)}>
                    {currentProject?.id === project.id ? "当前项目" : "切换到此项目"}
                  </Button>
                  {canDeleteProject && <Button danger onClick={() => setTargetProject(project)}>删除</Button>}
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        title="删除项目空间"
        open={targetProject !== null}
        confirmLoading={deleting}
        onCancel={() => setTargetProject(null)}
        onOk={() => deleteForm.submit()}
        okText="确认删除"
        okButtonProps={{ danger: true }}
      >
        <Typography.Paragraph>
          将删除项目空间 `{targetProject?.name}`。请再次输入当前账号密码完成确认。
        </Typography.Paragraph>
        <Form form={deleteForm} layout="vertical" onFinish={confirmDelete}>
          <Form.Item name="password" label="登录密码" rules={[{ required: true, message: "请输入登录密码" }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
