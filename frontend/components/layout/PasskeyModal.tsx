"use client";

import React, { useState } from "react";
import { KeyRound } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth/AuthContext";
import { useToast } from "@/components/ui/Toast";

export const PasskeyModal: React.FC = () => {
  const { isPasskeyModalOpen, closePasskeyModal, loginWithPasskey, passkey } = useAuth();
  const { addToast } = useToast();
  const [keyInput, setKeyInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyInput.trim()) {
      setErrorMessage("Passkey cannot be empty.");
      return;
    }

    setIsLoading(true);
    setErrorMessage("");

    const success = await loginWithPasskey(keyInput.trim());
    setIsLoading(false);

    if (success) {
      setKeyInput("");
      addToast({
        type: "success",
        title: "Authenticated",
        message: "Application access passkey verified successfully.",
      });
    } else {
      setErrorMessage("Invalid passkey. Access denied by ProofLens server.");
    }
  };

  return (
    <Modal
      isOpen={isPasskeyModalOpen}
      onClose={closePasskeyModal}
      title="Application Passkey"
      closeOnBackdropClick={Boolean(passkey)}
      footer={
        <>
          {Boolean(passkey) && (
            <Button
              type="button"
              variant="secondary"
              onClick={closePasskeyModal}
              disabled={isLoading}
            >
              Cancel
            </Button>
          )}
          <Button
            type="submit"
            form="passkey-form"
            variant="primary"
            isLoading={isLoading}
          >
            Authenticate
          </Button>
        </>
      }
    >
      <form id="passkey-form" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
          ProofLens AI requires an application access passkey (<code>X-Workspace-Key</code>) to interact with the backend service.
        </p>
        <Input
          label="Access Passkey"
          type="password"
          placeholder="Enter workspace passkey"
          value={keyInput}
          onChange={(e) => {
            setKeyInput(e.target.value);
            if (errorMessage) setErrorMessage("");
          }}
          errorMessage={errorMessage}
          leftIcon={<KeyRound size={16} />}
          disabled={isLoading}
          autoFocus
        />
      </form>
    </Modal>
  );
};
