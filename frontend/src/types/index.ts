// types/index.ts

/**
 * Represents the structure of a task when its creation is initiated.
 * Matches TaskCreationResponse from backend/app/api/wiki.py
 */
export interface TaskCreationResponse {
  task_id: string;
  message: string;
  repo_url: string; // HttpUrl is string in JS/TS
}

/**
 * Represents the detailed status of a task.
 * Matches TaskStatusDetailResponse from backend/app/api/status.py
 */
export interface TaskStatusDetail {
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED' | 'PROGRESS' | 'UNKNOWN' | 'ERROR_FETCHING_STATUS';
  result?: any;    // Can be any type of data from Celery task, or error string
  details?: any;   // Additional metadata, often a dict
}

/**
 * Represents a source document for a query answer.
 * Matches FormattedSourceDocument from backend/app/api/query.py
 */
export interface FormattedSourceDocument {
  content: string;
  meta: Record<string, any>; // Generic dictionary for metadata
}

/**
 * Represents the response from the /api/query/ask endpoint.
 * Matches AskQueryResponse from backend/app/api/query.py
 */
export interface QueryAPIResponse {
  query: string;
  repo_url: string; // HttpUrl is string in JS/TS
  answer: string;
  documents: FormattedSourceDocument[];
}

/**
 * Represents a navigation item for a Wiki.
 * Matches NavItemStructure from frontend/src/components/WikiNavigation/WikiNavigation.tsx
 */
export interface NavItem {
  id: string;
  title: string;
  href?: string;
  level?: number;
  children?: NavItem[];
  isHeader?: boolean;
}

/**
 * Represents the data structure for a Wiki page.
 * This is a frontend-defined structure, assuming what might be needed.
 */
export interface WikiPageData {
  title: string;
  markdownContent: string;
  navigationData?: NavItem[]; // Using the NavItem defined above
  repoSlug: string; // e.g., "owner/repo"
}

/**
 * Generic API Error structure for frontend handling, if needed.
 * Alternatively, functions can just throw Errors.
 */
export interface ApiError {
  detail: string | { msg: string; type: string; loc: (string | number)[] }[];
  // Add other fields if your backend returns more structured errors
}

/**
 * Represents a single message in the chat interface.
 * Used by QueryInterface.tsx.
 */
export interface ChatMessage {
  id: string; // Unique ID for the message
  type: 'question' | 'answer' | 'error' | 'loading'; // Type of message
  text: string; // Content of the message
  sources?: FormattedSourceDocument[]; // Optional: for answers, list of source documents
}
