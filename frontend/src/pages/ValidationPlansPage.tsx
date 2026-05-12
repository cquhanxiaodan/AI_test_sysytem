import { Button, Card, Empty, Space, Typography } from "antd";

export default function ValidationPlansPage() {
  return (
    <section>
      <Space className="page-title" align="start">
        <div>
          <Typography.Title level={2}>验证方案</Typography.Title>
          <Typography.Paragraph type="secondary">
            基于审核后的测试条目生成验证方案草稿，完成完整性校验后导出 Word。
          </Typography.Paragraph>
        </div>
        <Button type="primary">新建方案</Button>
      </Space>
      <Card>
        <Empty description="验证方案列表将在后续任务接入 API" />
      </Card>
    </section>
  );
}
