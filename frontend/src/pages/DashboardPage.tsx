import { Card, Col, Descriptions, Row, Statistic, Tag, Typography } from "antd";
import { useProjects } from "../context/ProjectContext";

export default function DashboardPage() {
  const { currentProject } = useProjects();

  return (
    <section>
      <Typography.Title level={2}>项目工作台</Typography.Title>
      <Typography.Paragraph type="secondary">
        追踪资料治理、测试资产沉淀、风险覆盖和验证方案生成进度。
      </Typography.Paragraph>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={6}>
          <Card><Statistic title="已发布资料" value={0} suffix="份" /></Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card><Statistic title="测试条目资产" value={0} suffix="项" /></Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card><Statistic title="风险知识项" value={0} suffix="条" /></Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card><Statistic title="验证方案草稿" value={0} suffix="个" /></Card>
        </Col>
      </Row>
      {currentProject && (
        <Card title="当前项目资料范围" className="section-card">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="项目编码">{currentProject.code}</Descriptions.Item>
            <Descriptions.Item label="项目角色">{currentProject.role}</Descriptions.Item>
            <Descriptions.Item label="项目说明">{currentProject.description}</Descriptions.Item>
            <Descriptions.Item label="资料规则">
              {currentProject.document_rules.map((rule) => (
                <Tag key={`${rule.label_key}-${rule.label_value}`} color="blue">
                  {rule.label_key}: {rule.label_value}
                </Tag>
              ))}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </section>
  );
}
