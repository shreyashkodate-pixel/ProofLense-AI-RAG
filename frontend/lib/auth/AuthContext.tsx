"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getStoredPasskey, setStoredPasskey, clearStoredPasskey } from "./passkey";
import { verifyAuthPasskey } from "@/lib/api/workspaces";

interface AuthContextType {
  passkey: string | null;
  isAuthenticated: boolean;
  isPasskeyModalOpen: boolean;
  openPasskeyModal: () => void;
  closePasskeyModal: () => void;
  loginWithPasskey: (key: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [passkey, setPasskeyState] = useState<string | null>(null);
  const [isPasskeyModalOpen, setIsPasskeyModalOpen] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const existingKey = getStoredPasskey();
    if (existingKey) {
      setPasskeyState(existingKey);
    } else {
      setIsPasskeyModalOpen(true);
    }
    setIsInitialized(true);

    const handleUnauthorized = () => {
      setIsPasskeyModalOpen(true);
    };

    window.addEventListener("prooflens:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("prooflens:unauthorized", handleUnauthorized);
    };
  }, []);

  const loginWithPasskey = useCallback(async (key: string): Promise<boolean> => {
    setStoredPasskey(key);
    try {
      await verifyAuthPasskey();
      setPasskeyState(key);
      setIsPasskeyModalOpen(false);
      return true;
    } catch {
      clearStoredPasskey();
      setPasskeyState(null);
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    clearStoredPasskey();
    setPasskeyState(null);
    setIsPasskeyModalOpen(true);
  }, []);

  const openPasskeyModal = useCallback(() => setIsPasskeyModalOpen(true), []);
  const closePasskeyModal = useCallback(() => {
    // Only allow manual closing if a passkey is already active
    if (passkey) {
      setIsPasskeyModalOpen(false);
    }
  }, [passkey]);

  return (
    <AuthContext.Provider
      value={{
        passkey,
        isAuthenticated: Boolean(passkey),
        isPasskeyModalOpen,
        openPasskeyModal,
        closePasskeyModal,
        loginWithPasskey,
        logout,
      }}
    >
      {isInitialized ? children : null}
    </AuthContext.Provider>
  );
};
