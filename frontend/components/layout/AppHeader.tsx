"use client";

import React from "react";
import Link from "next/link";
import { ShieldCheck, KeyRound, LogOut } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth/AuthContext";
import styles from "./AppHeader.module.css";

export interface AppHeaderProps {
  workspaceName?: string;
}

export const AppHeader: React.FC<AppHeaderProps> = ({ workspaceName }) => {
  const { openPasskeyModal, logout, isAuthenticated } = useAuth();

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Link href="/" className={styles.logo}>
          <ShieldCheck size={22} className={styles.logoIcon} />
          <span>ProofLens AI</span>
        </Link>
        {workspaceName && (
          <>
            <span className={styles.workspaceDivider}>/</span>
            <span className={styles.workspaceName}>{workspaceName}</span>
          </>
        )}
      </div>

      <div className={styles.right}>
        <div className={styles.connectionBadge}>
          <span className={styles.pulseDot} />
          <span>{isAuthenticated ? "Authenticated" : "Unauthenticated"}</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={openPasskeyModal}
          leftIcon={<KeyRound size={15} />}
          title="Change Workspace Passkey"
        >
          Passkey
        </Button>
        {isAuthenticated && (
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            leftIcon={<LogOut size={15} />}
            title="Disconnect"
          >
            Disconnect
          </Button>
        )}
      </div>
    </header>
  );
};
