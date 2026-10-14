"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Files,
  MessageSquareText,
  Scale,
  ArrowLeft,
  BarChart3,
} from "lucide-react";
import styles from "./Sidebar.module.css";

export interface SidebarProps {
  workspaceId: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ workspaceId }) => {
  const pathname = usePathname();

  const navItems: Array<{
    label: string;
    href: string;
    icon: React.ReactNode;
    exact: boolean;
    disabled: boolean;
    badge?: string;
  }> = [
    {
      label: "Overview",
      href: `/workspaces/${workspaceId}`,
      icon: <LayoutDashboard size={18} />,
      exact: true,
      disabled: false,
    },
    {
      label: "Documents",
      href: `/workspaces/${workspaceId}/documents`,
      icon: <Files size={18} />,
      exact: false,
      disabled: false,
    },
    {
      label: "Grounded Q&A",
      href: `/workspaces/${workspaceId}/queries`,
      icon: <MessageSquareText size={18} />,
      exact: false,
      disabled: false,
    },
    {
      label: "Comparison",
      href: `/workspaces/${workspaceId}/compare`,
      icon: <Scale size={18} />,
      exact: false,
      disabled: false,
    },
    {
      label: "Evaluation",
      href: "/evaluation",
      icon: <BarChart3 size={18} />,
      exact: true,
      disabled: false,
    },
  ];

  const isLinkActive = (href: string, exact: boolean) => {
    if (exact) return pathname === href;
    return pathname.startsWith(href);
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.navGroup}>
        <div className={styles.groupLabel}>Workspace Navigation</div>
        {navItems.map((item) => {
          const active = isLinkActive(item.href, item.exact);
          return (
            <Link
              key={item.href}
              href={item.disabled ? "#" : item.href}
              className={`${styles.navLink} ${active ? styles.navLinkActive : ""} ${
                item.disabled ? styles.navLinkDisabled : ""
              }`}
              aria-current={active ? "page" : undefined}
              aria-disabled={item.disabled}
            >
              <div className={styles.linkLeft}>
                {item.icon}
                <span>{item.label}</span>
              </div>
              {item.badge && <span className={styles.phaseBadge}>{item.badge}</span>}
            </Link>
          );
        })}
      </div>

      <div className={styles.footer}>
        <Link href="/" className={styles.navLink}>
          <div className={styles.linkLeft}>
            <ArrowLeft size={16} />
            <span>Workspace Hub</span>
          </div>
        </Link>
      </div>
    </aside>
  );
};
