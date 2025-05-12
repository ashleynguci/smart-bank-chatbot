// Generates a unique user ID for each session and stores it in sessionStorage.
// This way, the backend will be able to distinguish between different users.

export function getOrCreateUserId() {
  if (typeof window === "undefined") return null; // Server-side guard

  let userId = sessionStorage.getItem("userId");
  if (!userId) {
    userId = crypto.randomUUID();
    sessionStorage.setItem("userId", userId);
  }
  return userId;
}