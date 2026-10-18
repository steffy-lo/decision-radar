"use client";

import { GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { getPersonalFirebaseAuth } from "@/lib/auth/firebase";

export async function signInToWorkspace() {
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  return signInWithPopup(getPersonalFirebaseAuth(), provider);
}

export function googleSignInError(value: unknown): string {
  const code = typeof value === "object" && value !== null && "code" in value ? value.code : null;
  if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") return "Sign-in was cancelled. Choose Continue with Google to try again.";
  if (code === "auth/popup-blocked") return "Allow pop-ups for this app, then choose Continue with Google again.";
  if (code === "auth/unauthorized-domain") return "Google sign-in is not configured for this app address. Please contact the app owner.";
  return "Google sign-in could not be completed. Please try again.";
}
