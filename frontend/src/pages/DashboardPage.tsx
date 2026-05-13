import { Card, Col, Descriptions, List, Row, Statistic, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { AcceptanceStatus, AiConfig, fetchAcceptanceStatus, fetchAiConfig } from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function DashboardPage() {
  const { currentProject } = useProjects();
  const [acceptance, setAcceptance] = useState<AcceptanceStatus | null>(null);
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null);

  useEffect(() => {
    fetchAcceptanceStatus().then(setAcceptance).catch(() => setAcceptance(null));
    fetchAiConfig().then(setAiConfig).catch(() => setAiConfig(null));
  }, []);

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
      {aiConfig && (
        <Card title="AI 大模型接入与调用" className="section-card">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="模型接入状态">
              <Tag color={aiConfig.configured ? "green" : "default"}>
                {aiConfig.configured ? "已接入" : "本地规则兜底"}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="模型提供方">{aiConfig.provider}</Descriptions.Item>
            <Descriptions.Item label="模型名称">{aiConfig.model}</Descriptions.Item>
            <Descriptions.Item label="本地 AI 调用">
              需求分析优先调用 OpenAI 兼容模型抽取结构化字段；模型未配置或调用失败时自动回退本地规则。
            </Descriptions.Item>
            <Descriptions.Item label="外部模型策略">
              联网大模型仅作为受控外部参考，需脱敏、标记来源，并经人工审核后进入验证方案。
            </Descriptions.Item>
            <Descriptions.Item label="接口入口">
              /api/ai/validate 用于校验结构化输出，/api/ai/runs 用于记录可追溯调用。
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
      {acceptance && (
        <Card title="MVP 验收状态" className="section-card">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="已完成阶段">{acceptance.completed_stages.join(", ")}</Descriptions.Item>
            <Descriptions.Item label="后端测试数">{acceptance.backend_test_count}</Descriptions.Item>
            <Descriptions.Item label="前端构建">{acceptance.frontend_build}</Descriptions.Item>
          </Descriptions>
          <List
            size="small"
            header="剩余风险"
            dataSource={acceptance.remaining_risks}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        </Card>
      )}
    </section>
  );
}
