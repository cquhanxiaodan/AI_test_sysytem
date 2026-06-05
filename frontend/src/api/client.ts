const TOKEN_KEY = "gene-test-token";

export type UserProfile = {
  id: string;
  username: string;
  display_name: string;
  roles: string[];
};

export type Project = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  role: string;
  document_rules: Array<{ label_key: string; label_value: string }>;
};

export type ProjectCreatePayload = {
  code: string;
  name: string;
  description?: string;
};

export type ProjectWorkspaceStats = {
  project_id: string;
  published_documents: number;
  test_items: number;
  risk_items: number;
  validation_plans: number;
  test_packages: number;
  ai_configured: boolean;
  next_steps: string[];
};

export type DocumentItem = {
  id: string;
  project_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  file_hash: string;
  storage_path: string;
  status: string;
  labels: Record<string, string>;
  label_suggestions: Array<{ label_key: string; label_value: string; confidence: number; evidence: string }>;
  duplicate_results: Array<{ document_id: string; duplicate_type: string; similarity: number; suggestion: string }>;
  uploaded_by: string;
  created_at: string;
};

export type DocumentImportConfig = {
  import_directory: string;
  configured: boolean;
};

export type DocumentDirectoryScanResult = {
  import_directory: string;
  imported: DocumentItem[];
  skipped: string[];
  errors: string[];
};

export type DocumentBulkDeleteResult = {
  deleted_ids: string[];
  skipped: Array<{ document_id: string; reason: string }>;
};

export type ParsingTask = {
  id: string;
  document_id: string;
  task_type: string;
  status: string;
  message: string;
  created_at: string;
  completed_at: string | null;
  chunks: Array<{ id: string; document_id: string; sequence: number; heading: string | null; page_number: number | null; text: string }>;
};

export type TestItemAsset = {
  id: string;
  project_id: string;
  source_document_id: string;
  source_type: string;
  title: string;
  test_object: string;
  primary_subsystem: string;
  module: string;
  related_subsystems: string[];
  test_level: string;
  test_type: string;
  risk_tags: string[];
  objective: string;
  method: string;
  tools: string[];
  steps: string[];
  record_template: string;
  evidence: string;
  status: string;
  created_at: string;
};

export type TestItemUpdate = Partial<Pick<
  TestItemAsset,
  "title" | "test_object" | "primary_subsystem" | "module" | "related_subsystems" | "test_level" | "test_type" | "risk_tags" | "objective" | "method" | "tools" | "steps" | "record_template"
>>;

export type TestItemBulkDeleteResult = {
  deleted_ids: string[];
  skipped: Array<{ item_id: string; reason: string }>;
};

export type TestItemBulkPublishResult = {
  published_ids: string[];
  skipped: Array<{ item_id: string; reason: string }>;
};

export type TestPackageAsset = {
  id: string;
  project_id: string;
  name: string;
  package_type: string;
  test_object: string;
  subsystem: string;
  module: string;
  change_type: string;
  applicable_scope: string;
  items: Array<{ test_item_id: string; title: string; module: string; relation_type: string; trigger_condition: string | null }>;
  recommendation_level: string;
  status: string;
  evidence: string;
  created_at: string;
};

export type TestPackageUpdate = Partial<Pick<
  TestPackageAsset,
  "name" | "package_type" | "test_object" | "subsystem" | "module" | "change_type" | "applicable_scope" | "items" | "recommendation_level" | "evidence"
>>;

export type TestPackageBulkPublishResult = {
  published_ids: string[];
  skipped: Array<{ package_id: string; reason: string }>;
};

export type RiskItem = {
  id: string;
  project_id: string;
  source_type: string;
  source_id: string;
  title: string;
  description: string;
  product_model: string | null;
  test_object: string;
  subsystem: string;
  severity: string | null;
  rpn: number | null;
  failure_mode: string | null;
  failure_effect: string | null;
  root_cause: string | null;
  control_measure: string | null;
  suggested_test: string;
  status: string;
  created_at: string;
};

export type RiskUpdate = Partial<Omit<RiskItem, "id" | "project_id" | "created_at">>;

export type RiskBulkPublishResult = {
  published_ids: string[];
  skipped: Array<{ risk_id: string; reason: string }>;
};

export type RiskBulkDeleteResult = {
  deleted_ids: string[];
  skipped: Array<{ risk_id: string; reason: string }>;
};

export type RequirementAnalysis = {
  id: string;
  project_id: string;
  description: string;
  parse_result: {
    test_object: string;
    change_type: string;
    product_model: string | null;
    subsystem: string;
    missing_fields: string[];
  };
  recommendations: RequirementRecommendation[];
  ai_status: string;
  ai_message: string;
  status: string;
  created_at: string;
};

export type RequirementRecommendation = {
  id: string;
  group: string;
  title: string;
  source_type: string;
  source_id: string;
  reason: string;
  evidence: string;
  objective?: string | null;
  method?: string | null;
  record_template?: string | null;
  review_status: string;
};

export type RequirementRecommendationCreate = {
  group: string;
  title: string;
  source_type?: string;
  source_id?: string;
  reason?: string;
  evidence?: string;
  objective?: string | null;
  method?: string | null;
  record_template?: string | null;
  review_status?: string;
};

export type RequirementRecommendationUpdate = Partial<Omit<RequirementRecommendation, "id">>;

export type RequirementTemplate = {
  fields: Array<{ name: string; required: boolean; description: string }>;
  sample_rows: Array<Record<string, string>>;
};

export type RequirementBatchUploadResult = {
  filename: string;
  items: Array<{ row_number: number; description: string; missing_fields: string[]; analysis: RequirementAnalysis | null }>;
};

export type ValidationPlan = {
  id: string;
  project_id: string;
  requirement_analysis_ids: string[];
  title: string;
  template_version: string;
  overview: string;
  dut_description: string;
  reference_documents: string[];
  items: Array<{ sequence: number; title: string; group: string; objective: string; method: string; record_template: string; evidence: string }>;
  status: string;
  created_at: string;
};

export type ExportRecord = {
  id: string;
  validation_plan_id: string;
  filename: string;
  template_version: string;
  status: string;
  storage_path: string;
  download_url: string;
  created_at: string;
};

export type ValidationPlanCheckResult = {
  blocking: string[];
  warnings: string[];
  suggestions: string[];
};

export type ValidationPlanBulkDeleteResult = {
  deleted_ids: string[];
  skipped: Array<{ plan_id: string; reason: string }>;
};

export type AcceptanceStatus = {
  completed_stages: string[];
  backend_test_count: number;
  frontend_build: string;
  remaining_risks: string[];
};

export type SystemConfig = {
  subsystem_catalog: string[];
  subsystem_modules: Record<string, string[]>;
  document_types: string[];
  test_levels: string[];
  test_types: string[];
  change_types: string[];
  template_section_aliases: Record<string, string[]>;
  ai_external_reference_enabled: boolean;
  validation_template_version: string;
};

export type SystemConfigUpdate = Partial<Pick<SystemConfig, "subsystem_catalog" | "subsystem_modules" | "document_types" | "test_levels" | "test_types" | "change_types" | "template_section_aliases">>;

export type AiConfig = {
  provider: string;
  base_url: string;
  model: string;
  timeout_seconds: number;
  configured: boolean;
  external_reference_enabled: boolean;
  api_key_configured: boolean;
  api_key_masked: string | null;
};

export type AiConfigUpdate = {
  provider: string;
  base_url: string;
  api_key: string;
  model: string;
  timeout_seconds: number;
};

export type FreeChatResponse = {
  answer: string;
  used_model: boolean;
  sources: Array<{ source_type: string; source_id: string; title: string; text: string; score: number }>;
  ai_status: string;
  ai_message: string;
};

export type FreeChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type FeedbackItem = {
  id: string;
  submitter_id: string;
  submitter_name: string;
  submit_date: string;
  feedback_type: "bug" | "requirement";
  content: string;
  status: "pending" | "processing" | "resolved" | "closed";
  admin_reply: string;
  replied_by: string | null;
  replied_at: string | null;
  updated_at: string;
};

export type FeedbackCreate = Pick<FeedbackItem, "feedback_type" | "content">;

export type FeedbackAdminUpdate = Partial<Pick<FeedbackItem, "status" | "admin_reply">>;

export function getToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}


async function requestBlob(path: string, options: RequestInit = {}) {
  const token = getToken();
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.blob();
}

function abortErrorMessage(error: unknown, fallback: string) {
  return error instanceof DOMException && error.name === "AbortError" ? fallback : undefined;
}

export async function login(username: string, password: string) {
  return request<{ access_token: string; user: UserProfile }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function fetchMe() {
  return request<UserProfile>("/api/auth/me");
}

export async function fetchProjects() {
  return request<Project[]>("/api/projects");
}

export async function createProject(payload: ProjectCreatePayload) {
  return request<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteProject(projectId: string, password: string) {
  const token = getToken();
  const response = await fetch(`/api/projects/${projectId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ password }),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }
}

export async function fetchProjectWorkspaceStats(projectId: string) {
  return request<ProjectWorkspaceStats>(`/api/projects/${projectId}/workspace-stats`);
}

export async function fetchDocuments(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<DocumentItem[]>(`/api/documents${query}`);
}

export async function fetchFeedbackItems() {
  return request<FeedbackItem[]>("/api/feedback");
}

export async function createFeedback(payload: FeedbackCreate) {
  return request<FeedbackItem>("/api/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateFeedback(feedbackId: string, payload: FeedbackAdminUpdate) {
  return request<FeedbackItem>(`/api/feedback/${feedbackId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function uploadDocument(projectId: string, file: File) {
  const token = getToken();
  const body = new FormData();
  body.append("project_id", projectId);
  body.append("file", file);

  const response = await fetch("/api/documents/upload", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<{ document: DocumentItem }>;
}

export async function uploadDocuments(projectId: string, files: File[]) {
  const token = getToken();
  const body = new FormData();
  body.append("project_id", projectId);
  files.forEach((file) => body.append("files", file));

  const response = await fetch("/api/documents/upload-batch", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<{ documents: DocumentItem[] }>;
}

export async function fetchDocumentImportConfig() {
  return request<DocumentImportConfig>("/api/documents/import-config");
}

export async function updateDocumentImportConfig(importDirectory: string) {
  return request<DocumentImportConfig>("/api/documents/import-config", {
    method: "PUT",
    body: JSON.stringify({ import_directory: importDirectory }),
  });
}

export async function scanDocumentImportDirectory(projectId: string) {
  const token = getToken();
  const body = new FormData();
  body.append("project_id", projectId);
  const response = await fetch("/api/documents/scan-import-directory", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<DocumentDirectoryScanResult>;
}

export async function bulkDeleteDocuments(documentIds: string[]) {
  return request<DocumentBulkDeleteResult>("/api/documents/bulk-delete", {
    method: "POST",
    body: JSON.stringify({ document_ids: documentIds }),
  });
}

export async function updateDocumentLabels(documentId: string, labels: Record<string, string>) {
  return request<DocumentItem>(`/api/documents/${documentId}/labels`, {
    method: "PATCH",
    body: JSON.stringify({ labels }),
  });
}

export async function reviewDocument(documentId: string, action: string, comment?: string) {
  return request<DocumentItem>(`/api/documents/${documentId}/review`, {
    method: "POST",
    body: JSON.stringify({ action, comment }),
  });
}

export async function parseDocument(documentId: string) {
  return request<ParsingTask>(`/api/parsing/documents/${documentId}/parse`, { method: "POST" });
}

export async function extractDocumentLabels(documentId: string) {
  return request<ParsingTask>(`/api/parsing/documents/${documentId}/extract-labels`, { method: "POST" });
}

export async function fetchTestItems(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<TestItemAsset[]>(`/api/test-items${query}`);
}

export async function splitDocumentToTestItems(documentId: string) {
  return request<{ document_id: string; items: TestItemAsset[] }>(`/api/test-items/split/${documentId}`, { method: "POST" });
}

export async function confirmTestItem(itemId: string) {
  return request<TestItemAsset>(`/api/test-items/${itemId}/confirm`, { method: "POST" });
}

export async function updateTestItem(itemId: string, payload: TestItemUpdate) {
  return request<TestItemAsset>(`/api/test-items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function bulkDeleteTestItems(itemIds: string[]) {
  return request<TestItemBulkDeleteResult>("/api/test-items/bulk-delete", {
    method: "POST",
    body: JSON.stringify({ item_ids: itemIds }),
  });
}

export async function bulkPublishTestItems(itemIds: string[]) {
  return request<TestItemBulkPublishResult>("/api/test-items/bulk-publish", {
    method: "POST",
    body: JSON.stringify({ item_ids: itemIds }),
  });
}

export async function fetchTestPackages(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<TestPackageAsset[]>(`/api/test-packages${query}`);
}

export async function generateRfidSupplierPackage(projectId: string) {
  return request<TestPackageAsset>(`/api/test-packages/generate-rfid-supplier-change?project_id=${encodeURIComponent(projectId)}`, {
    method: "POST",
  });
}

export async function publishTestPackage(packageId: string) {
  return request<TestPackageAsset>(`/api/test-packages/${packageId}/publish`, { method: "POST" });
}

export async function updateTestPackage(packageId: string, payload: TestPackageUpdate) {
  return request<TestPackageAsset>(`/api/test-packages/${packageId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteTestPackage(packageId: string) {
  return request<{ deleted_id: string }>(`/api/test-packages/${packageId}`, { method: "DELETE" });
}

export async function bulkPublishTestPackages(packageIds: string[]) {
  return request<TestPackageBulkPublishResult>("/api/test-packages/bulk-publish", {
    method: "POST",
    body: JSON.stringify({ package_ids: packageIds }),
  });
}

export async function fetchRisks(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<RiskItem[]>(`/api/risks${query}`);
}

export async function parseRisks(projectId: string, sourceType: string, content: string) {
  return request<{ items: RiskItem[] }>("/api/risks/parse", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, source_type: sourceType, content }),
  });
}

export async function updateRisk(riskId: string, payload: RiskUpdate) {
  return request<RiskItem>(`/api/risks/${riskId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteRisk(riskId: string) {
  return request<{ deleted_id: string }>(`/api/risks/${riskId}`, { method: "DELETE" });
}

export async function publishRisk(riskId: string) {
  return request<RiskItem>(`/api/risks/${riskId}/publish`, { method: "POST" });
}

export async function bulkPublishRisks(riskIds: string[]) {
  return request<RiskBulkPublishResult>("/api/risks/bulk-publish", {
    method: "POST",
    body: JSON.stringify({ risk_ids: riskIds }),
  });
}

export async function bulkDeleteRisks(riskIds: string[]) {
  return request<RiskBulkDeleteResult>("/api/risks/bulk-delete", {
    method: "POST",
    body: JSON.stringify({ risk_ids: riskIds }),
  });
}

export async function uploadRequirementTable(projectId: string, file: File, signal?: AbortSignal) {
  const token = getToken();
  const body = new FormData();
  body.append("project_id", projectId);
  body.append("file", file);

  const response = await fetch("/api/requirement-analyses/upload-table", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body,
    signal,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<RequirementBatchUploadResult>;
}

export async function fetchRequirementTemplate() {
  return request<RequirementTemplate>("/api/requirement-analyses/template");
}

export async function downloadRequirementTemplate() {
  const token = getToken();
  const response = await fetch("/api/requirement-analyses/template/download", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.blob();
}

export async function createRequirementAnalysis(projectId: string, description: string, signal?: AbortSignal) {
  try {
    return await request<RequirementAnalysis>("/api/requirement-analyses", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, description }),
      signal,
    });
  } catch (error) {
    throw new Error(abortErrorMessage(error, "需求分析等待超时，后端可能仍在处理。请稍后刷新页面或检查 AI 配置。") ?? (error instanceof Error ? error.message : "需求分析失败"));
  }
}

export async function createLocalRequirementAnalysis(projectId: string, description: string, signal?: AbortSignal) {
  try {
    return await request<RequirementAnalysis>("/api/requirement-analyses/local", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, description }),
      signal,
    });
  } catch (error) {
    throw new Error(abortErrorMessage(error, "本地分析超时，请检查本地资料量或后端服务状态。") ?? (error instanceof Error ? error.message : "本地分析失败"));
  }
}

export async function runRequirementAiRecommendations(analysisId: string, signal?: AbortSignal) {
  try {
    return await request<RequirementAnalysis>(`/api/requirement-analyses/${analysisId}/ai-recommendations`, {
      method: "POST",
      signal,
    });
  } catch (error) {
    throw new Error(abortErrorMessage(error, "AI 分析超时，请检查模型服务响应或缩短输入内容。") ?? (error instanceof Error ? error.message : "AI 分析失败"));
  }
}

export async function fetchLatestRequirementAnalysis(projectId: string) {
  return request<RequirementAnalysis | null>(`/api/requirement-analyses/latest?project_id=${encodeURIComponent(projectId)}`);
}

export async function fetchRequirementAnalyses(projectId: string) {
  return request<RequirementAnalysis[]>(`/api/requirement-analyses?project_id=${encodeURIComponent(projectId)}`);
}

export async function deleteRequirementAnalysis(analysisId: string) {
  return request<void>(`/api/requirement-analyses/${analysisId}`, { method: "DELETE" });
}

export async function createRequirementRecommendation(analysisId: string, payload: RequirementRecommendationCreate) {
  return request<RequirementAnalysis>(`/api/requirement-analyses/${analysisId}/recommendations`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRequirementRecommendation(
  analysisId: string,
  recommendationId: string,
  payload: RequirementRecommendationUpdate,
) {
  return request<RequirementAnalysis>(`/api/requirement-analyses/${analysisId}/recommendations/${recommendationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function includeRequirementRecommendationInLocal(analysisId: string, recommendationId: string) {
  return request<RequirementAnalysis>(`/api/requirement-analyses/${analysisId}/recommendations/${recommendationId}/include-local`, {
    method: "POST",
  });
}

export async function deleteRequirementRecommendation(analysisId: string, recommendationId: string) {
  return request<RequirementAnalysis>(`/api/requirement-analyses/${analysisId}/recommendations/${recommendationId}`, {
    method: "DELETE",
  });
}

export async function fetchValidationPlans(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<ValidationPlan[]>(`/api/validation-plans${query}`);
}

export async function createValidationPlan(projectId: string) {
  return request<ValidationPlan>("/api/validation-plans", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId }),
  });
}

export async function checkValidationPlan(planId: string) {
  return request<ValidationPlanCheckResult>(`/api/validation-plans/${planId}/check`, { method: "POST" });
}

export async function exportValidationPlan(planId: string) {
  return request<ExportRecord>(`/api/validation-plans/${planId}/export`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function downloadValidationPlanExport(record: ExportRecord) {
  return requestBlob(record.download_url);
}

export async function updateValidationPlanStatus(planId: string, status: string) {
  return request<ValidationPlan>(`/api/validation-plans/${planId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function deleteValidationPlan(planId: string) {
  return request<void>(`/api/validation-plans/${planId}`, { method: "DELETE" });
}

export async function bulkDeleteValidationPlans(planIds: string[]) {
  return request<ValidationPlanBulkDeleteResult>("/api/validation-plans/bulk-delete", {
    method: "POST",
    body: JSON.stringify({ plan_ids: planIds }),
  });
}

export async function fetchAcceptanceStatus() {
  return request<AcceptanceStatus>("/api/admin/acceptance-status");
}

export async function fetchSystemConfig() {
  return request<SystemConfig>("/api/admin/config");
}

export async function updateSystemConfig(config: SystemConfigUpdate) {
  return request<SystemConfig>("/api/admin/config", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

export async function restoreSystemConfigBackup() {
  return request<SystemConfig>("/api/admin/config/restore-backup", { method: "POST" });
}

export async function fetchAiConfig() {
  return request<AiConfig>("/api/ai/config");
}

export async function updateAiConfig(config: AiConfigUpdate) {
  return request<AiConfig>("/api/ai/config", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

export async function askFreeChat(
  projectId: string,
  question: string,
  useProjectKnowledge: boolean,
  useExternalModel: boolean,
  messages: FreeChatMessage[] = [],
  signal?: AbortSignal,
) {
  try {
    return await request<FreeChatResponse>("/api/free-chat/ask", {
      method: "POST",
      signal,
      body: JSON.stringify({
        project_id: projectId,
        question,
        use_project_knowledge: useProjectKnowledge,
        use_external_model: useExternalModel,
        messages,
      }),
    });
  } catch (error) {
    throw new Error(abortErrorMessage(error, "自由应用等待超时，请检查模型服务响应或稍后重试。") ?? (error instanceof Error ? error.message : "自由应用提问失败"));
  }
}
