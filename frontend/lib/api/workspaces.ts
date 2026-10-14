/**
 * ProofLens AI — Workspace API Service
 * Verified contracts for Workspace CRUD and Passkey Gatekeeper verification.
 */

import { apiFetch } from "./client";
import { AuthTestResponse, WorkspaceCreate, WorkspaceResponse } from "./types";

export async function verifyAuthPasskey(): Promise<AuthTestResponse> {
  return apiFetch<AuthTestResponse>("/api/v1/auth-test", {
    method: "GET",
  });
}

export async function listWorkspaces(): Promise<WorkspaceResponse[]> {
  return apiFetch<WorkspaceResponse[]>("/api/v1/workspaces", {
    method: "GET",
  });
}

export async function getWorkspace(workspaceId: string): Promise<WorkspaceResponse> {
  return apiFetch<WorkspaceResponse>(`/api/v1/workspaces/${workspaceId}`, {
    method: "GET",
  });
}

export async function createWorkspace(data: WorkspaceCreate): Promise<WorkspaceResponse> {
  return apiFetch<WorkspaceResponse>("/api/v1/workspaces", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteWorkspace(workspaceId: string): Promise<null> {
  return apiFetch<null>(`/api/v1/workspaces/${workspaceId}`, {
    method: "DELETE",
  });
}
