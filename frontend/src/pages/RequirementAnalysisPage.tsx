import { Button, Card, Descriptions, Form, Input, List, Tag, Typography, message } from "antd";
import { useState } from "react";
import { createRequirementAnalysis, RequirementAnalysis } from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function RequirementAnalysisPage() {
  const { currentProject } = useProjects();
  const [analysis, setAnalysis] = useState<RequirementAnalysis | null>(null);

  async function submit(values: { description: string }) {
    if (!currentProject) return;
    const result = await createRequirementAnalysis(currentProject.id, values.description);
    setAnalysis(result);
    message.success("需求分析完成");
  }

  return (
    <section>
      <Typography.Title level={2}>需求分析</Typography.Title>
      <Typography.Paragraph type="secondary">
        输入新开发需求或变更需求，系统将结合测试归口包、历史方案、Jira 和 DFMEA 风险项推荐测试条目。
      </Typography.Paragraph>
      <Card>
        <Form layout="vertical" onFinish={submit} initialValues={{ description: "DNBSEQ-G99 引入二供供应商康奈特 RFID" }}>
          <Form.Item label="需求描述" name="description" rules={[{ required: true, message: "请输入需求描述" }]}>
            <Input.TextArea rows={8} placeholder="例如：DNBSEQ-G99 同步引入二供供应商康奈特 RFID..." />
          </Form.Item>
          <Button type="primary" htmlType="submit">开始分析</Button>
        </Form>
      </Card>
      {analysis && (
        <Card title="分析结果" className="section-card">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="测试对象">{analysis.parse_result.test_object}</Descriptions.Item>
            <Descriptions.Item label="变更类型">{analysis.parse_result.change_type}</Descriptions.Item>
            <Descriptions.Item label="产品型号">{analysis.parse_result.product_model ?? "待确认"}</Descriptions.Item>
            <Descriptions.Item label="子系统">{analysis.parse_result.subsystem}</Descriptions.Item>
          </Descriptions>
          <List
            className="section-card"
            header="推荐测试条目"
            dataSource={analysis.recommendations}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={<><Tag color="blue">{item.group}</Tag>{item.title}</>}
                  description={`${item.reason}；依据：${item.evidence}`}
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </section>
  );
}
