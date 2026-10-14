/**
 * ProofLens AI — Workspace Passkey Security Manager
 * Strictly utilizes sessionStorage and memory. Never writes to localStorage or cookies.
 */

const PASSKEY_SESSION_KEY = "prooflens_workspace_passkey";
let inMemoryPasskey: string | null = null;

export function getStoredPasskey(): string | null {
  if (inMemoryPasskey) return inMemoryPasskey;
  if (typeof window !== "undefined" && window.sessionStorage) {
    try {
      const stored = window.sessionStorage.getItem(PASSKEY_SESSION_KEY);
      if (stored) {
        inMemoryPasskey = stored;
        return stored;
      }
    } catch {
      // sessionStorage might be restricted in some privacy modes
    }
  }
  return null;
}

export function setStoredPasskey(passkey: string): void {
  const trimmed = passkey.trim();
  inMemoryPasskey = trimmed;
  if (typeof window !== "undefined" && window.sessionStorage) {
    try {
      window.sessionStorage.setItem(PASSKEY_SESSION_KEY, trimmed);
    } catch {
      // Memory fallback active
    }
  }
}

export function clearStoredPasskey(): void {
  inMemoryPasskey = null;
  if (typeof window !== "undefined" && window.sessionStorage) {
    try {
      window.sessionStorage.removeItem(PASSKEY_SESSION_KEY);
    } catch {
      // Memory cleared
    }
  }
}
