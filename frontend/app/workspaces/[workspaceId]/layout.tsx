import React from "react";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";

export interface WorkspaceLayoutProps {
  children: React.ReactNode;
  params: Promise<{ workspaceId: string }>;
}

export default async function WorkspaceLayout({
  children,
  params,
}: WorkspaceLayoutProps) {
  const { workspaceId } = await params;

  return <WorkspaceShell workspaceId={workspaceId}>{children}</WorkspaceShell>;
}
