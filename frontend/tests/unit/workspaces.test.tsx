import React from "react";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import WorkspaceHubPage from "@/app/page";
import * as workspacesApi from "@/lib/api/workspaces";
import { ToastProvider } from "@/components/ui/Toast";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { setStoredPasskey, getStoredPasskey, clearStoredPasskey } from "@/lib/auth/passkey";

vi.mock("@/lib/api/workspaces");

const mockWorkspaces = [
  {
    id: "ws-1",
    name: "Legal Review 2026",
    created_at: "2026-03-01T12:00:00Z",
    updated_at: "2026-03-01T12:00:00Z",
  },
  {
    id: "ws-2",
    name: "Medical Trials Audit",
    created_at: "2026-03-02T15:30:00Z",
    updated_at: "2026-03-02T15:30:00Z",
  },
];

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <AuthProvider>
      <ToastProvider>{ui}</ToastProvider>
    </AuthProvider>
  );
}

describe("Workspace Hub Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearStoredPasskey();
  });

  it("renders workspace list when data is loaded", async () => {
    vi.mocked(workspacesApi.listWorkspaces).mockResolvedValue(mockWorkspaces);

    renderWithProviders(<WorkspaceHubPage />);

    expect(await screen.findByText("Legal Review 2026")).toBeInTheDocument();
    expect(screen.getByText("Medical Trials Audit")).toBeInTheDocument();
  });

  it("renders empty state when no workspaces exist", async () => {
    vi.mocked(workspacesApi.listWorkspaces).mockResolvedValue([]);

    renderWithProviders(<WorkspaceHubPage />);

    expect(await screen.findByText("No workspaces found")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Workspace" })).toBeInTheDocument();
  });

  it("creates a new workspace via modal dialog", async () => {
    vi.mocked(workspacesApi.listWorkspaces).mockResolvedValue([]);
    const createdWorkspace = {
      id: "ws-new",
      name: "Financial Disclosures",
      created_at: "2026-03-10T10:00:00Z",
      updated_at: "2026-03-10T10:00:00Z",
    };
    vi.mocked(workspacesApi.createWorkspace).mockResolvedValue(createdWorkspace);

    renderWithProviders(<WorkspaceHubPage />);

    const newBtn = await screen.findByRole("button", { name: /new workspace/i });
    fireEvent.click(newBtn);

    const input = screen.getByLabelText(/workspace name/i);
    fireEvent.change(input, { target: { value: "Financial Disclosures" } });

    const dialog = screen.getByRole("dialog");
    const submitBtn = within(dialog).getByRole("button", { name: "Create Workspace" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(workspacesApi.createWorkspace).toHaveBeenCalledWith({
        name: "Financial Disclosures",
      });
    });

    expect(await screen.findByText("Financial Disclosures")).toBeInTheDocument();
  });

  it("handles workspace deletion confirmation", async () => {
    vi.mocked(workspacesApi.listWorkspaces).mockResolvedValue([mockWorkspaces[0]]);
    vi.mocked(workspacesApi.deleteWorkspace).mockResolvedValue(null);

    renderWithProviders(<WorkspaceHubPage />);

    expect(await screen.findByText("Legal Review 2026")).toBeInTheDocument();

    const deleteBtn = screen.getByTitle("Delete workspace");
    fireEvent.click(deleteBtn);

    expect(screen.getByText(/Are you sure you want to delete workspace/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: /delete permanently/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(workspacesApi.deleteWorkspace).toHaveBeenCalledWith("ws-1");
    });
  });
});

describe("Passkey Storage & Isolation", () => {
  beforeEach(() => {
    clearStoredPasskey();
  });

  it("stores and retrieves passkey in session storage and memory", () => {
    expect(getStoredPasskey()).toBeNull();
    setStoredPasskey("secret-passkey-123");
    expect(getStoredPasskey()).toBe("secret-passkey-123");
    clearStoredPasskey();
    expect(getStoredPasskey()).toBeNull();
  });
});
