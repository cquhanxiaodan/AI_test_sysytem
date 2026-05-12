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

export type DocumentItem = {
  id: string;
  project_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  file_hash: string;
  status: string;
  labels: Record<string, string>;
  label_suggestions: Array<{ label_key: string; label_value: string; confidence: number; evidence: string }>;
  duplicate_results: Array<{ document_id: string; duplicate_type: string; similarity: number; suggestion: string }>;
  uploaded_by: string;
  created_at: string;
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
  title: string;
  test_object: string;
  primary_subsystem: string;
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

export type TestPackageAsset = {
  id: string;
  project_id: string;
  name: string;
  package_type: string;
  test_object: string;
  change_type: string;
  applicable_scope: string;
  items: Array<{ test_item_id: string; title: string; relation_type: string; trigger_condition: string | null }>;
  recommendation_level: string;
  status: string;
  evidence: string;
  created_at: string;
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
  recommendations: Array<{ group: string; title: string; source_type: string; source_id: string; reason: string; evidence: string }>;
  status: string;
  created_at: string;
};

export type ValidationPlan = {
  id: string;
  project_id: string;
  requirement_analysis_id: string;
  title: string;
  template_version: string;
  overview: string;
  dut_description: string;
  reference_documents: string[];
  items: Array<{ sequence: number; title: string; group: string; objective: string; method: string; record_template: string; evidence: string }>;
  status: string;
  created_at: string;
};

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

  return response.json() as Promise<T>;
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

export async function fetchDocuments(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<DocumentItem[]>(`/api/documents${query}`);
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

export async function createRequirementAnalysis(projectId: string, description: string) {
  return request<RequirementAnalysis>("/api/requirement-analyses", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, description }),
  });
}

export async function fetchValidationPlans(projectId?: string) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<ValidationPlan[]>(`/api/validation-plans${query}`);
}

export async function createValidationPlan(requirementAnalysisId: string) {
  return request<ValidationPlan>("/api/validation-plans", {
    method: "POST",
    body: JSON.stringify({ requirement_analysis_id: requirementAnalysisId }),
  });
}

export async function checkValidationPlan(planId: string) {
  return request<{ blocking: string[]; warnings: string[]; suggestions: string[] }>(`/api/validation-plans/${planId}/check`, { method: "POST" });
}

export async function exportValidationPlan(planId: string) {
  return request<{ id: string; filename: string; status: string; template_version: string }>(`/api/validation-plans/${planId}/export`, { method: "POST" });
}
