/**
 * ProofLens AI — Grounded Q&A API Service (Phase 5)
 * Communicates with /api/v1/workspaces/{workspace_id}/queries endpoints.
 */

import { apiFetch } from "./client";
import { QueryRequest, QueryResponse } from "./types";

export async function executeQuery(
  workspaceId: string,
  payload: QueryRequest
): Promise<QueryResponse> {
  return apiFetch<QueryResponse>(
    `/api/v1/workspaces/${workspaceId}/queries`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function listQueries(
  workspaceId: string,
  limit = 50,
  offset = 0
): Promise<QueryResponse[]> {
  return apiFetch<QueryResponse[]>(
    `/api/v1/workspaces/${workspaceId}/queries?limit=${limit}&offset=${offset}`,
    {
      method: "GET",
    }
  );
}

export async function getQuery(
  workspaceId: string,
  queryRunId: string
): Promise<QueryResponse> {
  return apiFetch<QueryResponse>(
    `/api/v1/workspaces/${workspaceId}/queries/${queryRunId}`,
    {
      method: "GET",
    }
  );
}
