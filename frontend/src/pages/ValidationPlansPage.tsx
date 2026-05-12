import { Button, Card, Form, Input, List, message, Modal, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import { checkValidationPlan, createValidationPlan, exportValidationPlan, fetchValidationPlans, ValidationPlan } from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function ValidationPlansPage() {
  const { currentProject } = useProjects();
  const [plans, setPlans] = useState<ValidationPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [activePlan, setActivePlan] = useState<ValidationPlan | null>(null);
  const [form] = Form.useForm<{ analysisId: string }>();

  async function loadPlans() {
    if (!currentProject) return;
    setLoading(true);
    try {
      setPlans(await fetchValidationPlans(currentProject.id));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPlans();
  }, [currentProject?.id]);

  async function createPlan(values: { analysisId: string }) {
    await createValidationPlan(values.analysisId);
    message.success("验证方案草稿已生成");
    await loadPlans();
  }

  async function checkPlan(plan: ValidationPlan) {
    const result = await checkValidationPlan(plan.id);
    Modal.info({ title: "完整性校验", content: `阻断 ${result.blocking.length} 项，警告 ${result.warnings.length} 项，提示 ${result.suggestions.length} 项` });
  }

  async function exportPlan(plan: ValidationPlan) {
    const result = await exportValidationPlan(plan.id);
    message.success(`已生成导出记录：${result.filename}`);
  }

  const columns: ColumnsType<ValidationPlan> = [
    { title: "方案标题", dataIndex: "title" },
    { title: "模板", dataIndex: "template_version" },
    { title: "测试项目", dataIndex: "items", render: (items: ValidationPlan["items"]) => items.length },
    { title: "状态", dataIndex: "status", render: (status) => <Tag color="blue">{status}</Tag> },
    {
      title: "操作",
      render: (_, plan) => (
        <Space>
          <Button size="small" onClick={() => setActivePlan(plan)}>查看</Button>
          <Button size="small" onClick={() => checkPlan(plan)}>校验</Button>
          <Button size="small" type="primary" onClick={() => exportPlan(plan)}>导出</Button>
        </Space>
      ),
    },
  ];

  return (
    <section>
      <Space className="page-title" align="start">
        <div>
          <Typography.Title level={2}>验证方案</Typography.Title>
          <Typography.Paragraph type="secondary">
            基于审核后的测试条目生成验证方案草稿，完成完整性校验后导出 Word。
          </Typography.Paragraph>
        </div>
      </Space>
      <Card>
        <Form form={form} layout="inline" onFinish={createPlan} className="form-row">
          <Form.Item name="analysisId" rules={[{ required: true, message: "请输入需求分析 ID" }]}>
            <Input placeholder="输入需求分析 ID 生成方案" className="wide-input" />
          </Form.Item>
          <Button type="primary" htmlType="submit">生成方案草稿</Button>
        </Form>
        <Table rowKey="id" loading={loading} columns={columns} dataSource={plans} pagination={false} />
      </Card>
      <Modal title="验证方案详情" open={Boolean(activePlan)} onCancel={() => setActivePlan(null)} footer={null} width={860}>
        {activePlan && (
          <List
            header={activePlan.overview}
            dataSource={activePlan.items}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta title={`${item.sequence}. ${item.title}`} description={`${item.objective}；依据：${item.evidence}`} />
              </List.Item>
            )}
          />
        )}
      </Modal>
    </section>
  );
}
