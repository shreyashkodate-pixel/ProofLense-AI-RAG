import type { Metadata } from "next";
import "@/styles/tokens.css";
import "@/styles/globals.css";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { ToastProvider } from "@/components/ui/Toast";
import { PasskeyModal } from "@/components/layout/PasskeyModal";

export const metadata: Metadata = {
  title: "ProofLens AI — Evidence-First Document Intelligence",
  description: "Grounded RAG and cross-document comparison with verifiable page-level citations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <ToastProvider>
            {children}
            <PasskeyModal />
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
