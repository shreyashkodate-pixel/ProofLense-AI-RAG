/**
 * ProofLens AI — Cross-Document Comparison API Service (Phase 6)
 * Communicates with /api/v1/workspaces/{workspace_id}/comparisons endpoints.
 */

import { apiFetch } from "./client";
import { ComparisonRequest, ComparisonResponse, SavedComparisonResponse } from "./types";

export async function executeComparison(
  workspaceId: string,
  payload: ComparisonRequest
): Promise<ComparisonResponse> {
  return apiFetch<ComparisonResponse>(
    `/api/v1/workspaces/${workspaceId}/comparisons`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function listComparisons(
  workspaceId: string,
  limit = 50,
  offset = 0
): Promise<SavedComparisonResponse[]> {
  return apiFetch<SavedComparisonResponse[]>(
    `/api/v1/workspaces/${workspaceId}/comparisons?limit=${limit}&offset=${offset}`,
    {
      method: "GET",
    }
  );
}

export async function getComparison(
  workspaceId: string,
  comparisonId: string
): Promise<SavedComparisonResponse> {
  return apiFetch<SavedComparisonResponse>(
    `/api/v1/workspaces/${workspaceId}/comparisons/${comparisonId}`,
    {
      method: "GET",
    }
  );
}
