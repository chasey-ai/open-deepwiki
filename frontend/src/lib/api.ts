// lib/api.ts
import type { 
  TaskCreationResponse, 
  TaskStatusDetail, 
  WikiPageData, 
  QueryAPIResponse,
  ApiError // Assuming ApiError is defined for structured error handling
} from '../types'; // Adjust path if your types are elsewhere

const API_BASE_URL = '/api'; // Assuming Next.js proxy or same-origin deployment

async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorData: ApiError | { detail: string } = await response.json();
      if (typeof errorData.detail === 'string') {
        errorDetail = errorData.detail;
      } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0 && errorData.detail[0].msg) {
        // Handle FastAPI Pydantic validation error structure
        errorDetail = errorData.detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('; ');
      }
    } catch (e) {
      // If response is not JSON or another error occurs during error parsing
      console.error("Failed to parse error response:", e);
    }
    throw new Error(errorDetail);
  }
  // For plain text responses (like getRepositoryReadme)
  if (response.headers.get("content-type")?.includes("text/plain")) {
    return response.text() as Promise<T>; 
  }
  return response.json() as Promise<T>;
}

/**
 * Submits a repository URL to the backend to initiate processing (e.g., wiki generation task).
 * Corresponds to POST /api/wiki/generate
 */
export async function submitRepository(repoUrl: string): Promise<TaskCreationResponse> {
  const response = await fetch(`${API_BASE_URL}/wiki/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: repoUrl }), // Matches RepositoryRequest schema
  });
  return handleApiResponse<TaskCreationResponse>(response);
}

/**
 * Fetches the status of a specific task.
 * Corresponds to GET /api/status/{taskId}
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatusDetail> {
  const response = await fetch(`${API_BASE_URL}/status/${taskId}`);
  return handleApiResponse<TaskStatusDetail>(response);
}

/**
 * Fetches the generated Wiki content for a repository.
 * NOTE: The backend endpoint for this is not fully defined yet.
 * This function currently returns MOCKED data.
 * Assumed endpoint: GET /api/wiki/{owner}/{repo_name} (or similar)
 */
export async function getWikiContent(owner: string, repoName: string): Promise<WikiPageData> {
  console.warn(`getWikiContent for ${owner}/${repoName} is using MOCKED DATA. Backend endpoint needs implementation.`);
  // TODO: Replace with actual API call when backend endpoint is ready.
  // const response = await fetch(`${API_BASE_URL}/wiki/${owner}/${repoName}`);
  // return handleApiResponse<WikiPageData>(response);

  // Mocked data:
  return Promise.resolve({
    title: `${repoName} - 模拟 Wiki`,
    markdownContent: `
# ${repoName} - 模拟 Wiki 内容

这是为仓库 **${owner}/${repoName}** 生成的模拟 Wiki 页面。
实际内容将由后端任务生成并存储。

## 模拟章节 1
一些示例文本。

## 模拟章节 2
更多示例文本。
    `,
    navigationData: [
      { id: "mock-overview", title: "模拟概述", href: "#mock-overview", level: 1 },
      { id: "mock-section1", title: "模拟章节 1", href: "#mock-section1", level: 2 },
      { id: "mock-section2", title: "模拟章节 2", href: "#mock-section2", level: 2 },
    ],
    repoSlug: `${owner}/${repoName}`,
  });
}

/**
 * Submits a question about a repository and gets an answer.
 * Corresponds to POST /api/query/ask
 */
export async function askQuestion(repoUrl: string, question: string): Promise<QueryAPIResponse> {
  const response = await fetch(`${API_BASE_URL}/query/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl, question: question }), // Matches AskQueryRequest
  });
  return handleApiResponse<QueryAPIResponse>(response);
}

/**
 * Fetches the README content of a specified GitHub repository.
 * Corresponds to POST /api/github/readme
 */
export async function getRepositoryReadme(repoUrl: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/github/readme`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: repoUrl }), // Matches RepositoryRequest
  });
  // README is expected as plain text
  if (!response.ok) {
    let errorDetail = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorData: ApiError | { detail: string } = await response.json();
      if (typeof errorData.detail === 'string') {
        errorDetail = errorData.detail;
      }
    } catch (e) { /* Ignore if error response is not JSON */ }
    throw new Error(errorDetail);
  }
  return response.text();
}
