import { prisma } from "@/lib/prisma";
import type { NotificationType } from "@/generated/prisma/client";

export type CreateNotificationInput = {
  userId: string;
  type?: NotificationType;
  title: string;
  body: string;
  url?: string;
};

/** Allow only same-site absolute paths; reject external/protocol-relative URLs. */
export function normalizeNotificationUrl(url?: string): string | null {
  if (url == null || url === "") return null;
  if (!url.startsWith("/") || url.startsWith("//") || url.includes("\\")) {
    throw new Error("Notification URL must be an internal absolute path.");
  }
  // Reject ASCII control chars (including newlines) and scheme-like tricks.
  if (/[\u0000-\u001F\u007F]/.test(url)) {
    throw new Error("Notification URL contains forbidden characters.");
  }
  return url;
}

export async function createNotification(input: CreateNotificationInput) {
  return prisma.notification.create({
    data: {
      userId: input.userId,
      type: input.type ?? "SYSTEM",
      title: input.title,
      body: input.body,
      url: normalizeNotificationUrl(input.url),
    },
  });
}

export async function getNotifications(userId: string, take = 30) {
  return prisma.notification.findMany({
    where: { userId, deletedAt: null },
    orderBy: [{ createdAt: "desc" }, { id: "desc" }],
    take: Math.min(Math.max(take, 1), 100),
  });
}

export async function getUnreadCount(userId: string) {
  return prisma.notification.count({
    where: { userId, readAt: null, deletedAt: null },
  });
}

export async function markAsRead(userId: string, id: string) {
  return prisma.notification.updateMany({
    where: { id, userId, readAt: null, deletedAt: null },
    data: { readAt: new Date() },
  });
}

export async function markAllAsRead(userId: string) {
  return prisma.notification.updateMany({
    where: { userId, readAt: null, deletedAt: null },
    data: { readAt: new Date() },
  });
}

/** Soft delete: hide notification from the user, retain DB row. */
export async function deleteNotification(userId: string, id: string) {
  return prisma.notification.updateMany({
    where: { id, userId, deletedAt: null },
    data: { deletedAt: new Date() },
  });
}
