import { Button, Card, Collapse, Descriptions, Form, Input, message, Modal, Radio, Select, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import {
  bulkDeleteTestItems,
  confirmTestItem,
  fetchSystemConfig,
  fetchDocuments,
  fetchTestItems,
  fetchTestPackages,
  generateRfidSupplierPackage,
  publishTestPackage,
  fetchRisks,
  parseRisks,
  RiskItem,
  splitDocumentToTestItems,
  SystemConfig,
  DocumentItem,
  TestItemAsset,
  TestPackageAsset,
  TestItemUpdate,
  updateTestItem,
} from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function TestAssetsPage() {
  const { currentProject, projects } = useProjects();
  const [items, setItems] = useState<TestItemAsset[]>([]);
  const [packages, setPackages] = useState<TestPackageAsset[]>([]);
  const [risks, setRisks] = useState<RiskItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedItemIds, setSelectedItemIds] = useState<React.Key[]>([]);
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  const [editingItem, setEditingItem] = useState<TestItemAsset | null>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm<{ documentId: string }>();
  const [editForm] = Form.useForm<TestItemUpdate>();

  async function loadItems() {
    setLoading(true);
    try {
      setItems(await fetchTestItems());
      setPackages(await fetchTestPackages());
      setRisks(await fetchRisks());
      setDocuments(await fetchDocuments());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadItems();
    fetchSystemConfig().then(setSystemConfig).catch(() => setSystemConfig(null));
  }, [currentProject?.id]);

  async function splitDocument(values: { documentId: string }) {
    const result = await splitDocumentToTestItems(values.documentId);
    message.success(`已生成 ${result.items.length} 个测试条目`);
    form.resetFields();
    await loadItems();
  }

  async function publishItem(item: TestItemAsset) {
    await confirmTestItem(item.id);
    message.success("测试条目已发布");
    await loadItems();
  }

  async function deleteSelectedItems() {
    if (selectedItemIds.length === 0) return;
    const result = await bulkDeleteTestItems(selectedItemIds.map(String));
    setSelectedItemIds([]);
    if (result.deleted_ids.length > 0) {
      message.success(`已删除 ${result.deleted_ids.length} 个测试条目`);
    }
    if (result.skipped.length > 0) {
      message.warning(`有 ${result.skipped.length} 个测试条目未删除`);
    }
    await loadItems();
  }

  function openEditItem(item: TestItemAsset) {
    setEditingItem(item);
    editForm.setFieldsValue(item);
  }

  async function saveEditingItem() {
    if (!editingItem) return;
    await updateTestItem(editingItem.id, editForm.getFieldsValue());
    message.success("测试条目已更新");
    setEditingItem(null);
    await loadItems();
  }

  async function generatePackage() {
    if (!currentProject) return;
    const packageAsset = await generateRfidSupplierPackage(currentProject.id);
    message.success(`RFID 供应商变更验证包已生成，包含 ${packageAsset.items.length} 个条目`);
    await loadItems();
  }

  const splittableDocuments = documents.filter((document) => {
    const type = document.labels.document_type || document.label_suggestions.find((suggestion) => suggestion.label_key === "document_type")?.label_value || "";
    return ["验证方案", "测试规范", "测试报告"].includes(type);
  });

  async function publishPackage(packageAsset: TestPackageAsset) {
    await publishTestPackage(packageAsset.id);
    message.success("测试归口包已发布");
    await loadItems();
  }

  async function parseRiskSource(values: { sourceType: string; content: string }) {
    if (!currentProject) return;
    const result = await parseRisks(currentProject.id, values.sourceType, values.content);
    message.success(`已解析 ${result.items.length} 条风险项`);
    await loadItems();
  }

  const columns: ColumnsType<TestItemAsset> = [
    { title: "测试条目", dataIndex: "title" },
    { title: "所属项目", dataIndex: "project_id", render: (projectId) => projects.find((project) => project.id === projectId)?.name ?? projectId },
    { title: "对象", dataIndex: "test_object" },
    { title: "主子系统", dataIndex: "primary_subsystem" },
    { title: "测试层级", dataIndex: "test_level" },
    { title: "测试类型", dataIndex: "test_type" },
    { title: "状态", dataIndex: "status", render: (status) => <Tag color="blue">{status}</Tag> },
    {
      title: "操作",
      render: (_, item) => (
        <Space>
          <Button size="small" onClick={() => openEditItem(item)}>编辑</Button>
          <Button size="small" type="primary" disabled={item.status === "published"} onClick={() => publishItem(item)}>
            发布
          </Button>
        </Space>
      ),
    },
  ];

  const packageColumns: ColumnsType<TestPackageAsset> = [
    { title: "归口包", dataIndex: "name" },
    { title: "所属项目", dataIndex: "project_id", render: (projectId) => projects.find((project) => project.id === projectId)?.name ?? projectId },
    { title: "对象", dataIndex: "test_object" },
    { title: "变更类型", dataIndex: "change_type" },
    { title: "条目数", dataIndex: "items", render: (items: TestPackageAsset["items"]) => items.length },
    { title: "状态", dataIndex: "status", render: (status) => <Tag color="purple">{status}</Tag> },
    {
      title: "操作",
      render: (_, packageAsset) => (
        <Button size="small" type="primary" disabled={packageAsset.status === "published"} onClick={() => publishPackage(packageAsset)}>
          发布
        </Button>
      ),
    },
  ];

  const riskColumns: ColumnsType<RiskItem> = [
    { title: "来源", dataIndex: "source_type", render: (value) => <Tag>{value}</Tag> },
    { title: "风险标题", dataIndex: "title" },
    { title: "所属项目", dataIndex: "project_id", render: (projectId) => projects.find((project) => project.id === projectId)?.name ?? projectId },
    { title: "子系统", dataIndex: "subsystem" },
    { title: "RPN", dataIndex: "rpn", render: (value) => value ?? "-" },
    { title: "建议测试", dataIndex: "suggested_test" },
  ];

  function renderItemDetails(item: TestItemAsset) {
    return (
      <Descriptions column={1} size="small">
        <Descriptions.Item label="测试目的">{item.objective}</Descriptions.Item>
        <Descriptions.Item label="测试方法/标准">{item.method}</Descriptions.Item>
        <Descriptions.Item label="测试工具">{item.tools.length > 0 ? item.tools.join("、") : "未提取"}</Descriptions.Item>
        <Descriptions.Item label="测试步骤">{item.steps.length > 0 ? item.steps.join("；") : "未提取"}</Descriptions.Item>
        <Descriptions.Item label="记录模板">{item.record_template}</Descriptions.Item>
        <Descriptions.Item label="风险标签">{item.risk_tags.length > 0 ? item.risk_tags.join("、") : "未提取"}</Descriptions.Item>
        <Descriptions.Item label="来源证据">{item.evidence}</Descriptions.Item>
      </Descriptions>
    );
  }

  return (
    <section>
      <Typography.Title level={2}>测试资产</Typography.Title>
      <Typography.Paragraph type="secondary">
        查看由统一资料池自动沉淀的测试条目、测试归口包和风险知识项。验证方案/测试规范发布后自动拆分测试条目并生成归口包，Jira/DFMEA 发布后自动解析为风险知识源。
      </Typography.Paragraph>
      <Card className="section-card">
        <Typography.Title level={4}>自动生成规则</Typography.Title>
        <Typography.Paragraph>
          在统一资料池上传资料并确认标签，管理员发布资料后，系统按文档类型自动处理：验证方案/测试规范生成测试条目和归口包，Jira/DFMEA 生成风险知识项。本页用于查看、审核和发布资产。
        </Typography.Paragraph>
      </Card>
      <Card>
        <Tabs
          items={[
            {
              key: "items",
              label: "测试条目",
              children: (
                <Space direction="vertical" className="full-width" size="middle">
                  <Typography.Paragraph type="secondary">
                    测试条目来自全局共享资产库，所有项目空间均可查看全部条目。资料池中的验证方案、测试规范、测试报告在管理员发布后会自动拆分；维护工具可对已上传资料重新补拆。
                  </Typography.Paragraph>
                  <Button danger disabled={selectedItemIds.length === 0} onClick={deleteSelectedItems}>删除选中测试条目</Button>
                  <Table
                    rowKey="id"
                    loading={loading}
                    columns={columns}
                    dataSource={items}
                    pagination={false}
                    rowSelection={{ selectedRowKeys: selectedItemIds, onChange: setSelectedItemIds }}
                    expandable={{ expandedRowRender: renderItemDetails }}
                  />
                </Space>
              ),
            },
            {
              key: "packages",
              label: "测试归口包",
              children: (
                <Space direction="vertical" className="full-width" size="middle">
                  <Typography.Paragraph type="secondary">
                    归口包由测试条目自动归并生成，作为全局共享资产用于需求分析阶段推荐必测、建议和条件触发测试。
                  </Typography.Paragraph>
                  <Table rowKey="id" loading={loading} columns={packageColumns} dataSource={packages} pagination={false} />
                </Space>
              ),
            },
            {
              key: "risks",
              label: "风险知识源",
              children: (
                <Space direction="vertical" className="full-width" size="middle">
                  <Typography.Paragraph type="secondary">
                    风险知识源来自统一资料池中已发布的 Jira 导出和 DFMEA 文件，所有项目空间均可查看全部风险知识项。
                  </Typography.Paragraph>
                  <Table rowKey="id" loading={loading} columns={riskColumns} dataSource={risks} pagination={false} />
                </Space>
              ),
            },
            {
              key: "maintenance",
              label: "维护工具",
              children: (
                <Collapse
                  items={[
                    {
                      key: "split",
                      label: "手动补拆测试条目",
                      children: (
                        <Form form={form} layout="inline" onFinish={splitDocument}>
                          <Form.Item name="documentId" rules={[{ required: true, message: "请选择资料" }]}> 
                            <Select
                              showSearch
                              className="wide-input"
                              placeholder="选择已上传的验证方案/测试规范/测试报告"
                              optionFilterProp="label"
                              options={splittableDocuments.map((document) => ({
                                label: `${document.filename}（${projects.find((project) => project.id === document.project_id)?.name ?? document.project_id}，${document.status}）`,
                                value: document.id,
                              }))}
                            />
                          </Form.Item>
                          <Button type="primary" htmlType="submit">补拆条目</Button>
                        </Form>
                      ),
                    },
                    {
                      key: "package",
                      label: "手动补生成归口包",
                      children: <Button type="primary" onClick={generatePackage}>补生成 RFID 供应商变更验证包</Button>,
                    },
                    {
                      key: "risk",
                      label: "手动补解析风险源",
                      children: (
                        <Form layout="vertical" onFinish={parseRiskSource} initialValues={{ sourceType: "jira" }}>
                          <Form.Item label="来源类型" name="sourceType">
                            <Radio.Group options={[{ label: "Jira", value: "jira" }, { label: "DFMEA", value: "dfmea" }]} />
                          </Form.Item>
                          <Form.Item label="CSV 内容" name="content" rules={[{ required: true, message: "请输入 CSV 内容" }]}> 
                            <Input.TextArea rows={5} placeholder="仅用于补救：key,title,description\nG99-1,RFID读取失败,更换供应商后偶发读取失败" />
                          </Form.Item>
                          <Button type="primary" htmlType="submit">补解析风险源</Button>
                        </Form>
                      ),
                    },
                  ]}
                />
              ),
            },
          ]}
        />
      </Card>
      <Modal title="编辑测试条目" open={Boolean(editingItem)} onCancel={() => setEditingItem(null)} onOk={saveEditingItem} width={760}>
        <Form form={editForm} layout="vertical">
          <Form.Item label="测试条目" name="title">
            <Input />
          </Form.Item>
          <Form.Item label="测试对象" name="test_object">
            <Input placeholder="例如：RFID 读写模块" />
          </Form.Item>
          <Form.Item label="主子系统" name="primary_subsystem">
            <Select showSearch options={(systemConfig?.subsystem_catalog ?? []).map((value) => ({ label: value, value }))} />
          </Form.Item>
          <Form.Item label="关联子系统" name="related_subsystems">
            <Select mode="multiple" options={(systemConfig?.subsystem_catalog ?? []).map((value) => ({ label: value, value }))} />
          </Form.Item>
          <Form.Item label="测试层级" name="test_level">
            <Select showSearch options={(systemConfig?.test_levels ?? []).map((value) => ({ label: value, value }))} />
          </Form.Item>
          <Form.Item label="测试类型" name="test_type">
            <Select showSearch options={(systemConfig?.test_types ?? []).map((value) => ({ label: value, value }))} />
          </Form.Item>
          <Form.Item label="风险标签" name="risk_tags">
            <Select mode="tags" tokenSeparators={[",", "，"]} />
          </Form.Item>
          <Form.Item label="测试目的" name="objective">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="测试方法" name="method">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="测试工具" name="tools">
            <Select mode="tags" tokenSeparators={[",", "，"]} />
          </Form.Item>
          <Form.Item label="测试步骤" name="steps">
            <Select mode="tags" tokenSeparators={[",", "，"]} />
          </Form.Item>
          <Form.Item label="记录模板" name="record_template">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
