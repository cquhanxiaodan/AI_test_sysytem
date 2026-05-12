import { Button, Card, Form, Input, Typography } from "antd";

export default function RequirementAnalysisPage() {
  return (
    <section>
      <Typography.Title level={2}>需求分析</Typography.Title>
      <Typography.Paragraph type="secondary">
        输入新开发需求或变更需求，系统将结合测试归口包、历史方案、Jira 和 DFMEA 风险项推荐测试条目。
      </Typography.Paragraph>
      <Card>
        <Form layout="vertical">
          <Form.Item label="需求描述">
            <Input.TextArea rows={8} placeholder="例如：DNBSEQ-G99 同步引入二供供应商康奈特 RFID..." />
          </Form.Item>
          <Button type="primary">开始分析</Button>
        </Form>
      </Card>
    </section>
  );
}
