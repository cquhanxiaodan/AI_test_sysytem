import { Button, Card, Descriptions, Form, Input, List, Space, Tag, Typography, Upload, message } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import { useState } from "react";
import { createRequirementAnalysis, RequirementAnalysis, uploadRequirementDocument } from "../api/client";
import { useProjects } from "../context/ProjectContext";

const STANDARD_REQUIREMENT_TEMPLATE = `需求标题：DNBSEQ-G99 RFID 二供供应商导入验证
产品型号：DNBSEQ-G99
变更对象：RFID
所属子系统：RFID
变更类型：供应商变更
变更背景：现有 RFID 物料需引入二供供应商以降低供应风险
变更内容：同步引入康奈特 RFID，保持功能规格和接口定义一致
影响范围：在机装配、初始化、读取、写入、整机兼容性、安规 EMC 风险评估
验收标准：RFID 可稳定完成在机装配、初始化、读取和写入，测试结果满足既有验证方案要求
已知风险：二供物料可能存在读取失败、初始化异常、装配兼容性或 EMC 差异`;

export default function RequirementAnalysisPage() {
  const { currentProject } = useProjects();
  const [analysis, setAnalysis] = useState<RequirementAnalysis | null>(null);
  const [form] = Form.useForm<{ description: string }>();

  async function submit(values: { description: string }) {
    if (!currentProject) return;
    const result = await createRequirementAnalysis(currentProject.id, values.description);
    setAnalysis(result);
    message.success("需求分析完成");
  }

  async function handleUpload(file: File) {
    if (!currentProject) return false;
    const result = await uploadRequirementDocument(currentProject.id, file);
    form.setFieldsValue({ description: result.description });
    message.success(`已解析需求文档：${result.filename}`);
    return false;
  }

  function fillStandardTemplate() {
    form.setFieldsValue({ description: STANDARD_REQUIREMENT_TEMPLATE });
  }

  return (
    <section>
      <Typography.Title level={2}>需求分析</Typography.Title>
      <Typography.Paragraph type="secondary">
        输入或上传新开发需求/变更需求，系统将结合测试归口包、历史方案、Jira 和 DFMEA 风险项推荐测试条目。
      </Typography.Paragraph>
      <Card title="标准需求格式" className="section-card">
        <Typography.Paragraph type="secondary">
          建议按以下字段整理需求，系统会优先读取产品型号、变更对象、所属子系统和变更类型。
        </Typography.Paragraph>
        <Input.TextArea rows={10} value={STANDARD_REQUIREMENT_TEMPLATE} readOnly />
      </Card>
      <Card>
        <Form form={form} layout="vertical" onFinish={submit} initialValues={{ description: STANDARD_REQUIREMENT_TEMPLATE }}>
          <Form.Item label="需求描述" name="description" rules={[{ required: true, message: "请输入需求描述" }]}> 
            <Input.TextArea rows={8} placeholder="例如：DNBSEQ-G99 同步引入二供供应商康奈特 RFID..." />
          </Form.Item>
          <Space wrap>
            <Button type="primary" htmlType="submit">开始分析</Button>
            <Upload beforeUpload={handleUpload} showUploadList={false} accept=".txt,.md,.csv,.doc,.docx,.pdf">
              <Button icon={<UploadOutlined />}>上传需求文档</Button>
            </Upload>
            <Button onClick={fillStandardTemplate}>填入标准格式</Button>
          </Space>
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
