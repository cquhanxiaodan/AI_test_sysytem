import { Button, Card, Descriptions, Form, Input, InputNumber, Select, Space, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import {
  AiConfig,
  DocumentImportConfig,
  fetchAiConfig,
  fetchDocumentImportConfig,
  fetchSystemConfig,
  SystemConfig,
  SystemConfigUpdate,
  restoreSystemConfigBackup,
  updateAiConfig,
  updateDocumentImportConfig,
  updateSystemConfig,
} from "../api/client";
import { useAuth } from "../context/AuthContext";

type AiSettingsForm = {
  provider: string;
  base_url: string;
  api_key: string;
  model: string;
  timeout_seconds: number;
};

type DocumentImportForm = {
  import_directory: string;
};

type DictionaryForm = Required<Omit<SystemConfigUpdate, "template_section_aliases">>;

const SECTION_ALIAS_LABELS: Record<string, string> = {
  objective: "测试目的/测试标准",
  method: "测试方法/原理",
  tools: "测试工具",
  steps: "测试步骤",
  connection_media: "测试连接图或照片",
  record_template: "测试记录",
  compliance_bug_info: "需求符合性和 BUG 信息",
};

export default function SettingsPage() {
  const { user } = useAuth();
  const [form] = Form.useForm<AiSettingsForm>();
  const [documentImportForm] = Form.useForm<DocumentImportForm>();
  const [dictionaryForm] = Form.useForm<DictionaryForm>();
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null);
  const [documentImportConfig, setDocumentImportConfig] = useState<DocumentImportConfig | null>(null);
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  const [templateSectionAliases, setTemplateSectionAliases] = useState<Record<string, string[]>>({});
  const [subsystemModules, setSubsystemModules] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingDocumentImport, setSavingDocumentImport] = useState(false);
  const [savingDictionaries, setSavingDictionaries] = useState(false);
  const isAdmin = user?.roles.includes("admin") ?? false;

  function loadConfig() {
    setLoading(true);
    fetchAiConfig()
      .then((config) => {
        setAiConfig(config);
        form.setFieldsValue({
          provider: config.provider,
          base_url: config.base_url,
          api_key: "",
          model: config.model === "local-rule-engine" ? "" : config.model,
          timeout_seconds: config.timeout_seconds,
        });
      })
      .catch((error: Error) => message.error(`读取 AI 配置失败：${error.message}`))
      .finally(() => setLoading(false));
  }

  function loadDocumentImportConfig() {
    fetchDocumentImportConfig()
      .then((config) => {
        setDocumentImportConfig(config);
        documentImportForm.setFieldsValue({ import_directory: config.import_directory });
      })
      .catch((error: Error) => message.error(`读取资料导入配置失败：${error.message}`));
  }

  function loadSystemConfig() {
    fetchSystemConfig()
      .then((config) => {
        setSystemConfig(config);
        setTemplateSectionAliases(config.template_section_aliases);
        setSubsystemModules(config.subsystem_modules || {});
        dictionaryForm.setFieldsValue({
          subsystem_catalog: config.subsystem_catalog,
          subsystem_modules: config.subsystem_modules,
          document_types: config.document_types,
          test_levels: config.test_levels,
          test_types: config.test_types,
          change_types: config.change_types,
        });
      })
      .catch((error: Error) => message.error(`读取系统字典失败：${error.message}`));
  }

  useEffect(() => {
    loadConfig();
    loadDocumentImportConfig();
    loadSystemConfig();
  }, []);

  function save(values: AiSettingsForm) {
    setSaving(true);
    updateAiConfig(values)
      .then((config) => {
        setAiConfig(config);
        form.setFieldsValue({ api_key: "" });
        message.success("AI 模型设置已保存");
      })
      .catch((error: Error) => message.error(`保存失败：${error.message}`))
      .finally(() => setSaving(false));
  }

  function saveDocumentImport(values: DocumentImportForm) {
    setSavingDocumentImport(true);
    updateDocumentImportConfig(values.import_directory)
      .then((config) => {
        setDocumentImportConfig(config);
        message.success("资料导入目录已保存");
      })
      .catch((error: Error) => message.error(`保存失败：${error.message}`))
      .finally(() => setSavingDocumentImport(false));
  }

  function saveDictionaries(values: DictionaryForm) {
    setSavingDictionaries(true);
    updateSystemConfig({ ...values, subsystem_modules: subsystemModules, template_section_aliases: templateSectionAliases })
      .then((config) => {
        setSystemConfig(config);
        setTemplateSectionAliases(config.template_section_aliases);
        setSubsystemModules(config.subsystem_modules || {});
        dictionaryForm.setFieldsValue({
          subsystem_catalog: config.subsystem_catalog,
          subsystem_modules: config.subsystem_modules,
          document_types: config.document_types,
          test_levels: config.test_levels,
          test_types: config.test_types,
          change_types: config.change_types,
        });
        message.success("系统字典和模板适配已保存");
      })
      .catch((error: Error) => message.error(`保存失败：${error.message}`))
      .finally(() => setSavingDictionaries(false));
  }

  function restoreDictionaries() {
    setSavingDictionaries(true);
    restoreSystemConfigBackup()
      .then((config) => {
        setSystemConfig(config);
        setTemplateSectionAliases(config.template_section_aliases);
        setSubsystemModules(config.subsystem_modules || {});
        dictionaryForm.setFieldsValue({
          subsystem_catalog: config.subsystem_catalog,
          subsystem_modules: config.subsystem_modules,
          document_types: config.document_types,
          test_levels: config.test_levels,
          test_types: config.test_types,
          change_types: config.change_types,
        });
        message.success("已恢复上一版系统字典");
      })
      .catch((error: Error) => message.error(`恢复失败：${error.message}`))
      .finally(() => setSavingDictionaries(false));
  }

  return (
    <section>
      <Typography.Title level={2}>系统设置</Typography.Title>
      <Typography.Paragraph type="secondary">
        管理当前账号的 AI 模型网关和资料导入目录。系统字典由管理员统一维护，普通用户使用管理员发布的全局选项。
      </Typography.Paragraph>

      <Card title="AI 模型状态" className="section-card" loading={loading}>
        {aiConfig && (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="接入状态">
              <Tag color={aiConfig.configured ? "green" : "default"}>{aiConfig.configured ? "已接入" : "本地规则兜底"}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="模型提供方">{aiConfig.provider}</Descriptions.Item>
            <Descriptions.Item label="接口地址">{aiConfig.base_url || "未配置"}</Descriptions.Item>
            <Descriptions.Item label="模型名称">{aiConfig.model}</Descriptions.Item>
            <Descriptions.Item label="API Key">{aiConfig.api_key_masked || "未配置"}</Descriptions.Item>
            <Descriptions.Item label="超时时间">{aiConfig.timeout_seconds} 秒</Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      <Card title="AI 模型配置" className="section-card">
        <Typography.Paragraph type="secondary">
          AI 模型配置按当前账号保存，保存后用于当前账号发起的 AI 调用。
        </Typography.Paragraph>
        <Form form={form} layout="vertical" onFinish={save} initialValues={{ provider: "local", timeout_seconds: 20 }}>
          <Form.Item name="provider" label="模型提供方" rules={[{ required: true, message: "请选择模型提供方" }]}>
            <Select
              options={[
                { label: "本地规则兜底", value: "local" },
                { label: "OpenAI 兼容接口", value: "openai-compatible" },
              ]}
            />
          </Form.Item>
          <Form.Item name="base_url" label="Base URL" extra="示例：https://your-model-gateway.example.com/v1">
            <Input placeholder="https://your-model-gateway.example.com/v1" />
          </Form.Item>
          <Form.Item name="model" label="模型名称">
            <Input placeholder="your-model-name" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key" extra="留空会保留当前 API Key；切换到本地规则兜底会清空运行时 API Key。">
            <Input.Password placeholder={aiConfig?.api_key_configured ? "已配置，留空保持不变" : "请输入 API Key"} autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="timeout_seconds" label="调用超时时间" rules={[{ required: true, message: "请输入调用超时时间" }]}>
            <InputNumber min={1} max={120} addonAfter="秒" className="full-width" />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={saving}>保存设置</Button>
            <Button onClick={loadConfig}>刷新状态</Button>
          </Space>
        </Form>
      </Card>

      <Card title="统一资料池导入目录" className="section-card">
        <Typography.Paragraph type="secondary">
          资料导入目录按当前账号保存。统一资料池页面点击扫描新增资料时，会读取当前账号配置目录下的普通文件并按 hash 去重导入。
        </Typography.Paragraph>
        {documentImportConfig && (
          <Descriptions column={1} size="small" className="section-card">
            <Descriptions.Item label="配置状态">
              <Tag color={documentImportConfig.configured ? "green" : "default"}>{documentImportConfig.configured ? "已配置" : "未配置"}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="当前目录">{documentImportConfig.import_directory || "未配置"}</Descriptions.Item>
          </Descriptions>
        )}
        <Form form={documentImportForm} layout="vertical" onFinish={saveDocumentImport}>
          <Form.Item name="import_directory" label="个人资料导入目录" extra="示例：/data/gene-test-imports。该路径需要后端服务进程可读取。">
            <Input placeholder="/data/gene-test-imports" />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={savingDocumentImport}>保存导入目录</Button>
            <Button onClick={loadDocumentImportConfig}>刷新目录配置</Button>
          </Space>
        </Form>
      </Card>

      <Card title={isAdmin ? "系统字典配置" : "系统字典"} className="section-card">
        <Typography.Paragraph type="secondary">
          {isAdmin ? "管理测试资产、资料标签和需求分析中使用的全局可选项。保存后，测试资产编辑弹窗会使用最新选项。" : "测试资产、资料标签和需求分析使用管理员维护的全局可选项。"}
        </Typography.Paragraph>
        {systemConfig && (
          <Descriptions column={1} size="small" className="section-card">
            <Descriptions.Item label="当前子系统">{systemConfig.subsystem_catalog.join("、")}</Descriptions.Item>
            <Descriptions.Item label="当前模块字典">{Object.entries(systemConfig.subsystem_modules || {}).map(([subsystem, modules]) => `${subsystem}：${modules.join("、")}`).join("；")}</Descriptions.Item>
            <Descriptions.Item label="当前测试层级">{systemConfig.test_levels.join("、")}</Descriptions.Item>
            <Descriptions.Item label="当前测试类型">{systemConfig.test_types.join("、")}</Descriptions.Item>
          </Descriptions>
        )}
        {isAdmin ? (
          <Form form={dictionaryForm} layout="vertical" onFinish={saveDictionaries}>
            <Form.Item name="subsystem_catalog" label="子系统目录" extra="用于测试资产的主子系统和关联子系统选项。">
              <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入后回车添加，例如 电子子系统" />
            </Form.Item>
            <Form.Item label="子系统-模块联动字典" extra="每个子系统维护独立模块选项，资料标签和测试条目编辑会按子系统联动展示。">
              <SubsystemModuleEditor subsystems={dictionaryForm.getFieldValue("subsystem_catalog") || systemConfig?.subsystem_catalog || []} value={subsystemModules} onChange={setSubsystemModules} />
            </Form.Item>
            <Form.Item name="test_levels" label="测试层级">
              <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入后回车添加，例如 子系统级" />
            </Form.Item>
            <Form.Item name="test_types" label="测试类型">
              <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入后回车添加，例如 功能测试" />
            </Form.Item>
            <Form.Item name="document_types" label="资料类型">
              <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入后回车添加，例如 验证方案" />
            </Form.Item>
            <Form.Item name="change_types" label="变更类型">
              <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入后回车添加，例如 供应商变更" />
            </Form.Item>
            <Form.Item label="测试条目模板适配" extra="维护不同验证方案/测试规范中的段落别名。每个字段对应一个规范段落，输入后回车添加。">
              <SectionAliasEditor value={templateSectionAliases} onChange={setTemplateSectionAliases} />
            </Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={savingDictionaries}>保存系统字典</Button>
              <Button onClick={restoreDictionaries} loading={savingDictionaries}>恢复上一版</Button>
              <Button onClick={loadSystemConfig}>刷新字典</Button>
            </Space>
          </Form>
        ) : (
          <Button onClick={loadSystemConfig}>刷新字典</Button>
        )}
      </Card>
    </section>
  );
}

function SectionAliasEditor({ value = {}, onChange }: { value?: Record<string, string[]>; onChange?: (value: Record<string, string[]>) => void }) {
  function updateAlias(key: string, aliases: string[]) {
    onChange?.({ ...value, [key]: aliases });
  }

  return (
    <Space direction="vertical" className="full-width" size="middle">
      {Object.entries(SECTION_ALIAS_LABELS).map(([key, label]) => (
        <div key={key}>
          <Typography.Text strong>{label}</Typography.Text>
          <Select
            mode="tags"
            className="full-width"
            tokenSeparators={[",", "，"]}
            value={value[key] || []}
            placeholder={`输入${label}的模板别名`}
            onChange={(aliases) => updateAlias(key, aliases)}
          />
        </div>
      ))}
    </Space>
  );
}

function SubsystemModuleEditor({ subsystems, value = {}, onChange }: { subsystems: string[]; value?: Record<string, string[]>; onChange?: (value: Record<string, string[]>) => void }) {
  function updateModules(subsystem: string, modules: string[]) {
    onChange?.({ ...value, [subsystem]: modules });
  }

  return (
    <Space direction="vertical" className="full-width" size="middle">
      {subsystems.map((subsystem) => (
        <div key={subsystem}>
          <Typography.Text strong>{subsystem}</Typography.Text>
          <Select
            mode="tags"
            className="full-width"
            tokenSeparators={[",", "，"]}
            value={value[subsystem] || []}
            placeholder={`输入${subsystem}下的模块，回车添加`}
            onChange={(modules) => updateModules(subsystem, modules)}
          />
        </div>
      ))}
    </Space>
  );
}
