import type {
  ResearchRequest,
  ResearchTask,
  ResearchReport,
  ResearchReportList,
} from "./researchTypes";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Start a new market research task using Manus AI
 */
export async function startResearch(request: ResearchRequest): Promise<ResearchTask> {
  const response = await fetch(`${API_BASE}/api/research/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to start research" }));
    throw new Error(error.detail || "Failed to start research");
  }

  return response.json();
}

/**
 * Check the status of a research task
 */
export async function getResearchStatus(taskId: string): Promise<ResearchTask> {
  const response = await fetch(`${API_BASE}/api/research/status/${taskId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get task status" }));
    throw new Error(error.detail || "Failed to get task status");
  }

  return response.json();
}

/**
 * List all completed research reports
 */
export async function listResearchReports(): Promise<ResearchReportList> {
  const response = await fetch(`${API_BASE}/api/research/reports`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to list reports" }));
    throw new Error(error.detail || "Failed to list reports");
  }

  return response.json();
}

/**
 * Get a specific research report by ID
 */
export async function getResearchReport(reportId: string): Promise<ResearchReport> {
  const response = await fetch(`${API_BASE}/api/research/reports/${reportId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Report not found" }));
    throw new Error(error.detail || "Report not found");
  }

  return response.json();
}

/**
 * Get the pre-generated research markdown
 */
export async function getResearchMarkdown(): Promise<{ content: string; filename: string }> {
  const response = await fetch(`${API_BASE}/api/research/markdown`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to load research" }));
    throw new Error(error.detail || "Failed to load research");
  }

  return response.json();
}

/**
 * Poll for task completion with callback
 */
export async function pollResearchTask(
  taskId: string,
  onUpdate: (task: ResearchTask) => void,
  pollInterval: number = 5000,
  maxPolls: number = 120,
): Promise<ResearchTask> {
  for (let i = 0; i < maxPolls; i++) {
    const task = await getResearchStatus(taskId);
    onUpdate(task);

    if (task.status === "completed" || task.status === "failed") {
      return task;
    }

    await new Promise((resolve) => setTimeout(resolve, pollInterval));
  }

  throw new Error("Research task timed out");
}
