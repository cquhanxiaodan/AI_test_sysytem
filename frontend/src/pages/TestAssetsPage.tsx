import { Button, Card, Collapse, Form, Input, message, Radio, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import {
  confirmTestItem,
  fetchTestItems,
  fetchTestPackages,
  generateRfidSupplierPackage,
  publishTestPackage,
  fetchRisks,
  parseRisks,
  RiskItem,
  splitDocumentToTestItems,
  TestItemAsset,
  TestPackageAsset,
} from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function TestAssetsPage() {
  const { currentProject } = useProjects();
  const [items, setItems] = useState<TestItemAsset[]>([]);
  const [packages, setPackages] = useState<TestPackageAsset[]>([]);
  const [risks, setRisks] = useState<RiskItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm<{ documentId: string }>();

  async function loadItems() {
    if (!currentProject) return;
    setLoading(true);
    try {
      setItems(await fetchTestItems(currentProject.id));
      setPackages(await fetchTestPackages(currentProject.id));
      setRisks(await fetchRisks(currentProject.id));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadItems();
  }, [currentProject?.id]);

  async function splitDocument(values: { documentId: string }) {
    const result = await splitDocumentToTestItems(values.documentId);
    message.success(`已生成 ${result.items.length} 个测试条目`);
    await loadItems();
  }

  async function publishItem(item: TestItemAsset) {
    await confirmTestItem(item.id);
    message.success("测试条目已发布");
    await loadItems();
  }

  async function generatePackage() {
    if (!currentProject) return;
    await generateRfidSupplierPackage(currentProject.id);
    message.success("RFID 供应商变更验证包已生成");
    await loadItems();
  }

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
    { title: "对象", dataIndex: "test_object" },
    { title: "主子系统", dataIndex: "primary_subsystem" },
    { title: "测试层级", dataIndex: "test_level" },
    { title: "测试类型", dataIndex: "test_type" },
    { title: "状态", dataIndex: "status", render: (status) => <Tag color="blue">{status}</Tag> },
    {
      title: "操作",
      render: (_, item) => (
        <Button size="small" type="primary" disabled={item.status === "published"} onClick={() => publishItem(item)}>
          发布
        </Button>
      ),
    },
  ];

  const packageColumns: ColumnsType<TestPackageAsset> = [
    { title: "归口包", dataIndex: "name" },
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
    { title: "子系统", dataIndex: "subsystem" },
    { title: "RPN", dataIndex: "rpn", render: (value) => value ?? "-" },
    { title: "建议测试", dataIndex: "suggested_test" },
  ];

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
                    测试条目来自已发布的验证方案、测试规范或测试报告。正常流程在资料池发布后自动生成。
                  </Typography.Paragraph>
                  <Table rowKey="id" loading={loading} columns={columns} dataSource={items} pagination={false} />
                </Space>
              ),
            },
            {
              key: "packages",
              label: "测试归口包",
              children: (
                <Space direction="vertical" className="full-width" size="middle">
                  <Typography.Paragraph type="secondary">
                    归口包由测试条目自动归并生成，用于需求分析阶段推荐必测、建议和条件触发测试。
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
                    风险知识源来自统一资料池中已发布的 Jira 导出和 DFMEA 文件。上传文件并发布后即可入库。
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
                          <Form.Item name="documentId" rules={[{ required: true, message: "请输入资料 ID" }]}> 
                            <Input placeholder="仅用于补救：输入资料 ID" className="wide-input" />
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
    </section>
  );
}
