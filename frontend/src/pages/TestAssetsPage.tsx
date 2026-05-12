import { Button, Card, Form, Input, message, Radio, Space, Table, Tabs, Tag, Typography } from "antd";
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
        管理测试条目资产、测试归口包和风险覆盖关系。
      </Typography.Paragraph>
      <Card>
        <Tabs
          items={[
            {
              key: "items",
              label: "测试条目",
              children: (
                <Space direction="vertical" className="full-width" size="middle">
                  <Form form={form} layout="inline" onFinish={splitDocument}>
                    <Form.Item name="documentId" rules={[{ required: true, message: "请输入资料 ID" }]}>
                      <Input placeholder="输入资料 ID 后拆分测试条目" className="wide-input" />
                    </Form.Item>
                    <Button type="primary" htmlType="submit">拆分方案</Button>
                  </Form>
                  <Table rowKey="id" loading={loading} columns={columns} dataSource={items} pagination={false} />
                </Space>
              ),
            },
            {
              key: "packages",
              label: "测试归口包",
              children: (
                <Space direction="vertical" className="full-width" size="middle">
                  <Button type="primary" onClick={generatePackage}>生成 RFID 供应商变更验证包</Button>
                  <Table rowKey="id" loading={loading} columns={packageColumns} dataSource={packages} pagination={false} />
                </Space>
              ),
            },
            {
              key: "risks",
              label: "风险知识源",
              children: (
                <Space direction="vertical" className="full-width" size="middle">
                  <Form layout="vertical" onFinish={parseRiskSource} initialValues={{ sourceType: "jira" }}>
                    <Form.Item label="来源类型" name="sourceType">
                      <Radio.Group options={[{ label: "Jira", value: "jira" }, { label: "DFMEA", value: "dfmea" }]} />
                    </Form.Item>
                    <Form.Item label="CSV 内容" name="content" rules={[{ required: true, message: "请输入 CSV 内容" }]}>
                      <Input.TextArea rows={5} placeholder="例如：key,title,description\nG99-1,RFID读取失败,更换供应商后偶发读取失败" />
                    </Form.Item>
                    <Button type="primary" htmlType="submit">解析风险源</Button>
                  </Form>
                  <Table rowKey="id" loading={loading} columns={riskColumns} dataSource={risks} pagination={false} />
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </section>
  );
}
