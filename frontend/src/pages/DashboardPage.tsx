import { Button, Card, Col, Descriptions, List, Row, Space, Statistic, Steps, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AcceptanceStatus, AiConfig, fetchAcceptanceStatus, fetchAiConfig, fetchProjectWorkspaceStats, ProjectWorkspaceStats } from "../api/client";
import { useProjects } from "../context/ProjectContext";

export default function DashboardPage() {
  const { currentProject } = useProjects();
  const navigate = useNavigate();
  const [acceptance, setAcceptance] = useState<AcceptanceStatus | null>(null);
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null);
  const [stats, setStats] = useState<ProjectWorkspaceStats | null>(null);

  useEffect(() => {
    fetchAcceptanceStatus().then(setAcceptance).catch(() => setAcceptance(null));
    fetchAiConfig().then(setAiConfig).catch(() => setAiConfig(null));
  }, []);

  useEffect(() => {
    if (!currentProject) {
      setStats(null);
      return;
    }
    fetchProjectWorkspaceStats(currentProject.id).then(setStats).catch(() => setStats(null));
  }, [currentProject?.id]);

  return (
    <section>
      <Typography.Title level={2}>项目工作台</Typography.Title>
      <Typography.Paragraph type="secondary">
        查看当前项目空间的资料治理、测试资产、风险覆盖、AI 接入和下一步工作建议。
      </Typography.Paragraph>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} xl={6}>
          <Card><Statistic title="已发布资料" value={stats?.published_documents ?? 0} suffix="份" /></Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card><Statistic title="测试条目资产" value={stats?.test_items ?? 0} suffix="项" /></Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card><Statistic title="风险知识项" value={stats?.risk_items ?? 0} suffix="条" /></Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card><Statistic title="验证方案草稿" value={stats?.validation_plans ?? 0} suffix="个" /></Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} className="section-card">
        <Col xs={24} lg={12}>
          <Card title="当前项目状态">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="项目空间">{currentProject?.name ?? "未选择"}</Descriptions.Item>
              <Descriptions.Item label="资料基础">
                <Tag color={(stats?.published_documents ?? 0) > 0 ? "green" : "default"}>{(stats?.published_documents ?? 0) > 0 ? "已建立" : "待建立"}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="测试资产">
                <Tag color={(stats?.test_items ?? 0) > 0 ? "green" : "default"}>{(stats?.test_items ?? 0) > 0 ? "已有条目" : "待拆分"}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="风险知识源">
                <Tag color={(stats?.risk_items ?? 0) > 0 ? "green" : "default"}>{(stats?.risk_items ?? 0) > 0 ? "已有风险" : "待导入"}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="测试归口包">
                <Tag color={(stats?.test_packages ?? 0) > 0 ? "green" : "default"}>{(stats?.test_packages ?? 0) > 0 ? "已归口" : "待生成"}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="AI 模型">
                <Tag color={stats?.ai_configured ? "green" : "default"}>{stats?.ai_configured ? "已接入" : "本地规则兜底"}</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="推荐下一步">
            <Steps
              direction="vertical"
              size="small"
              current={0}
              items={(stats?.next_steps.length ? stats.next_steps : ["当前项目已具备基础数据，可继续进行需求分析或验证方案导出。"]).map((step) => ({ title: step }))}
            />
          </Card>
        </Col>
      </Row>
      <Card title="快捷入口" className="section-card">
        <Space wrap>
          <Button onClick={() => navigate("/projects")}>创建/切换项目空间</Button>
          <Button type="primary" onClick={() => navigate("/documents")}>上传资料</Button>
          <Button onClick={() => navigate("/test-assets")}>查看测试资产</Button>
          <Button onClick={() => navigate("/requirements")}>开始需求分析</Button>
          <Button onClick={() => navigate("/validation-plans")}>生成验证方案</Button>
          <Button onClick={() => navigate("/free-chat")}>自由提问</Button>
          <Button onClick={() => navigate("/settings")}>配置 AI</Button>
        </Space>
      </Card>
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
            <Descriptions.Item label="配置入口">
              <Button size="small" onClick={() => navigate("/settings")}>进入系统设置</Button>
            </Descriptions.Item>
            <Descriptions.Item label="本地 AI 调用">
              标签识别、条目拆分、风险解析、需求推荐和方案检查都会优先基于本地知识，再调用 AI 进行 JSON 补全。
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
