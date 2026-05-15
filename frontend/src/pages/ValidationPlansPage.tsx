import { Button, Card, Empty, Form, Input, List, message, Modal, Select, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import { bulkDeleteValidationPlans, checkValidationPlan, createValidationPlan, deleteValidationPlan, exportValidationPlan, fetchValidationPlans, updateValidationPlanStatus, ValidationPlan, ValidationPlanCheckResult } from "../api/client";
import { useProjects } from "../context/ProjectContext";

const PLAN_STATUSES = [
  { label: "草稿", value: "draft", color: "blue" },
  { label: "评审中", value: "reviewing", color: "gold" },
  { label: "已批准", value: "approved", color: "green" },
  { label: "已导出", value: "exported", color: "purple" },
  { label: "已归档", value: "archived", color: "default" },
];

function statusMeta(status: string) {
  return PLAN_STATUSES.find((item) => item.value === status) ?? { label: status, value: status, color: "default" };
}

export default function ValidationPlansPage() {
  const { currentProject } = useProjects();
  const [plans, setPlans] = useState<ValidationPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [activePlan, setActivePlan] = useState<ValidationPlan | null>(null);
  const [selectedPlanIds, setSelectedPlanIds] = useState<React.Key[]>([]);
  const [exportingPlan, setExportingPlan] = useState<ValidationPlan | null>(null);
  const [exportForm] = Form.useForm<{ export_directory: string }>();

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
    showCheckResult(result);
  }

  function showCheckResult(result: ValidationPlanCheckResult) {
    const renderMessages = (title: string, messages: string[], emptyText: string) => (
      <div style={{ marginTop: 12 }}>
        <Typography.Text strong>{title}（{messages.length}）</Typography.Text>
        {messages.length > 0 ? (
          <List size="small" dataSource={messages} renderItem={(item) => <List.Item>{item}</List.Item>} />
        ) : (
          <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>{emptyText}</Typography.Paragraph>
        )}
      </div>
    );
    Modal.info({
      title: "完整性校验",
      width: 720,
      content: (
        <div>
          <Typography.Paragraph type="secondary">
            校验用于检查验证方案是否具备可执行性：阻断项会影响导出后的执行，警告项需要人工确认，提示项用于优化方案完整度。本地规则会检查测试项目、DUT 和参考文档；AI 已配置时会追加语义检查建议。
          </Typography.Paragraph>
          {renderMessages("阻断项", result.blocking, "没有发现阻断项。")}
          {renderMessages("警告项", result.warnings, "没有发现警告项。")}
          {renderMessages("提示项", result.suggestions, "没有发现提示项。")}
        </div>
      ),
    });
  }

  function openExportDialog(plan: ValidationPlan) {
    setExportingPlan(plan);
    exportForm.setFieldsValue({ export_directory: "" });
  }

  async function exportPlan(values: { export_directory: string }) {
    if (!exportingPlan) return;
    const result = await exportValidationPlan(exportingPlan.id, values.export_directory);
    message.success(`已生成导出记录：${result.filename}`);
    setExportingPlan(null);
    await loadPlans();
  }

  async function changePlanStatus(plan: ValidationPlan, nextStatus: string) {
    try {
      const updated = await updateValidationPlanStatus(plan.id, nextStatus);
      setPlans((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      if (activePlan?.id === updated.id) setActivePlan(updated);
      message.success("方案状态已更新");
    } catch (error: unknown) {
      message.error(`状态更新失败：${error instanceof Error ? error.message : String(error)}`);
    }
  }

  function confirmDeletePlan(plan: ValidationPlan) {
    Modal.confirm({
      title: "删除验证方案",
      content: `确认删除“${plan.title}”？`,
      okText: "删除",
      okButtonProps: { danger: true },
      onOk: async () => {
        await deleteValidationPlan(plan.id);
        message.success("验证方案已删除");
        if (activePlan?.id === plan.id) setActivePlan(null);
        setSelectedPlanIds((ids) => ids.filter((id) => id !== plan.id));
        await loadPlans();
      },
    });
  }

  function confirmBulkDelete() {
    if (selectedPlanIds.length === 0) return;
    Modal.confirm({
      title: "批量删除验证方案",
      content: `确认删除选中的 ${selectedPlanIds.length} 个验证方案？`,
      okText: "批量删除",
      okButtonProps: { danger: true },
      onOk: async () => {
        const result = await bulkDeleteValidationPlans(selectedPlanIds.map(String));
        message.success(`已删除 ${result.deleted_ids.length} 个验证方案`);
        if (result.skipped.length > 0) message.warning(`有 ${result.skipped.length} 个方案未删除`);
        setSelectedPlanIds([]);
        if (activePlan && result.deleted_ids.includes(activePlan.id)) setActivePlan(null);
        await loadPlans();
      },
    });
  }

  const columns: ColumnsType<ValidationPlan> = [
    { title: "方案标题", dataIndex: "title" },
    { title: "关联需求", dataIndex: "requirement_analysis_ids", render: (ids: string[]) => `${ids.length} 条` },
    { title: "测试项目", dataIndex: "items", render: (items: ValidationPlan["items"]) => items.length },
    {
      title: "状态",
      dataIndex: "status",
      render: (status: string, plan) => (
        <Select
          size="small"
          value={status}
          style={{ width: 112 }}
          options={PLAN_STATUSES.map((item) => ({ label: item.label, value: item.value }))}
          onChange={(value) => changePlanStatus(plan, value)}
        />
      ),
    },
    {
      title: "操作",
      render: (_, plan) => (
        <Space>
          <Button size="small" onClick={() => setActivePlan(plan)}>查看</Button>
          <Button size="small" onClick={() => checkPlan(plan)}>校验</Button>
          <Button size="small" type="primary" onClick={() => openExportDialog(plan)}>导出</Button>
          <Button size="small" danger onClick={() => confirmDeletePlan(plan)}>删除</Button>
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
      <Card className="section-card">
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          导出时可填写本次 Word 文件保存到后端服务器的目录；留空时使用默认本地存储 exports 目录。状态支持草稿、评审中、已批准、已导出和已归档；导出成功后会自动切换为已导出。
        </Typography.Paragraph>
      </Card>
      <Card>
        <Space style={{ marginBottom: 16 }} wrap>
          <Button type="primary" loading={creating} disabled={!currentProject} onClick={handleCreate}>
            为当前项目生成验证方案
          </Button>
          <Button danger disabled={selectedPlanIds.length === 0} onClick={confirmBulkDelete}>
            批量删除{selectedPlanIds.length > 0 ? `（${selectedPlanIds.length}）` : ""}
          </Button>
        </Space>
        {plans.length === 0 && !loading ? (
          <Empty description="暂无验证方案。完成需求分析后点击上方按钮批量生成。" />
        ) : (
          <Table
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={plans}
            pagination={false}
            rowSelection={{ selectedRowKeys: selectedPlanIds, onChange: setSelectedPlanIds }}
          />
        )}
      </Card>
      <Modal title="验证方案详情" open={Boolean(activePlan)} onCancel={() => setActivePlan(null)} footer={null} width={860}>
        {activePlan && (
          <>
            <Typography.Paragraph>{activePlan.overview}</Typography.Paragraph>
            <Space direction="vertical" size={4}>
              <Typography.Text type="secondary">DUT：{activePlan.dut_description}</Typography.Text>
              <Typography.Text type="secondary">状态：<Tag color={statusMeta(activePlan.status).color}>{statusMeta(activePlan.status).label}</Tag></Typography.Text>
            </Space>
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
      <Modal
        title="导出验证方案"
        open={Boolean(exportingPlan)}
        onCancel={() => setExportingPlan(null)}
        okText="导出"
        onOk={() => exportForm.submit()}
      >
        <Typography.Paragraph type="secondary">
          请输入后端服务器上的保存目录。留空时使用默认本地存储 exports 目录。
        </Typography.Paragraph>
        <Form form={exportForm} layout="vertical" onFinish={exportPlan}>
          <Form.Item name="export_directory" label="本次导出目录" extra="示例：/data/gene-test-exports。该路径需要后端服务进程可写。">
            <Input placeholder="/data/gene-test-exports" />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
