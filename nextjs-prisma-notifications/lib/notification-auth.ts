/**
 * REQUIRED INTEGRATION: replace this function with your auth provider.
 * It must return the authenticated user's DB id, not a client-supplied id.
 * Throw or redirect to login for unauthenticated requests.
 *
 * Example with Auth.js (adjust to your own auth configuration):
 *   import { auth } from "@/auth";
 *   import { redirect } from "next/navigation";
 *   const session = await auth();
 *   if (!session?.user?.id) redirect("/login");
 *   return session.user.id;
 */
export async function requireNotificationUserId(): Promise<string> {
  throw new Error(
    "Configure requireNotificationUserId() in lib/notification-auth.ts before using notifications."
  );
}
