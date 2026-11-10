"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { requireNotificationUserId } from "@/lib/notification-auth";
import {
  deleteNotification,
  markAllAsRead,
  markAsRead,
  normalizeNotificationUrl,
} from "@/lib/notifications";

const PAGE = "/notifications";

export async function markNotificationReadAction(id: string) {
  const userId = await requireNotificationUserId();
  await markAsRead(userId, id);
  revalidatePath(PAGE);
}

export async function markAllNotificationsReadAction() {
  const userId = await requireNotificationUserId();
  await markAllAsRead(userId);
  revalidatePath(PAGE);
}

export async function deleteNotificationAction(id: string) {
  const userId = await requireNotificationUserId();
  await deleteNotification(userId, id);
  revalidatePath(PAGE);
}

/** Find a notification owned by this user, mark read, then navigate internally. */
export async function openNotificationAction(id: string) {
  const userId = await requireNotificationUserId();
  const notification = await prisma.notification.findFirst({
    where: { id, userId, deletedAt: null },
    select: { url: true },
  });

  if (!notification) {
    redirect(PAGE);
  }

  await markAsRead(userId, id);
  revalidatePath(PAGE);

  let target: string | null = null;
  try {
    target = normalizeNotificationUrl(notification.url ?? undefined);
  } catch {
    // Defensive for any legacy data created outside createNotification().
  }
  redirect(target ?? PAGE);
}
