import { Button, Card, Empty, List, message, Modal, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import { checkValidationPlan, createValidationPlan, exportValidationPlan, fetchValidationPlans, ValidationPlan } from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function ValidationPlansPage() {
  const { currentProject } = useProjects();
  const [plans, setPlans] = useState<ValidationPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [activePlan, setActivePlan] = useState<ValidationPlan | null>(null);

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

  async function handleCreate() {
    if (!currentProject) return;
    setCreating(true);
    try {
      await createValidationPlan(currentProject.id);
      message.success("验证方案草稿已生成");
      await loadPlans();
    } catch (error: unknown) {
      message.error(`生成失败：${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setCreating(false);
    }
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
    { title: "关联需求", dataIndex: "requirement_analysis_ids", render: (ids: string[]) => `${ids.length} 条` },
    { title: "测试项目", dataIndex: "items", render: (items: ValidationPlan["items"]) => items.length },
    { title: "状态", dataIndex: "status", render: (status: string) => <Tag color="blue">{status}</Tag> },
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
      <Typography.Title level={2}>验证方案</Typography.Title>
      <Typography.Paragraph type="secondary">
        基于当前项目所有已分析需求批量生成整体验证方案，完成完整性校验后导出 Word。
      </Typography.Paragraph>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" loading={creating} disabled={!currentProject} onClick={handleCreate}>
            为当前项目生成验证方案
          </Button>
        </Space>
        {plans.length === 0 && !loading ? (
          <Empty description="暂无验证方案。完成需求分析后点击上方按钮批量生成。" />
        ) : (
          <Table rowKey="id" loading={loading} columns={columns} dataSource={plans} pagination={false} />
        )}
      </Card>
      <Modal title="验证方案详情" open={Boolean(activePlan)} onCancel={() => setActivePlan(null)} footer={null} width={860}>
        {activePlan && (
          <>
            <Typography.Paragraph>{activePlan.overview}</Typography.Paragraph>
            <Typography.Text type="secondary">DUT：{activePlan.dut_description}</Typography.Text>
            <List
              style={{ marginTop: 16 }}
              dataSource={activePlan.items}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta title={`${item.sequence}. ${item.title}`} description={`${item.objective}；依据：${item.evidence}`} />
                </List.Item>
              )}
            />
          </>
        )}
      </Modal>
    </section>
  );
}
