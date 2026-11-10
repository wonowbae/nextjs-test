import { requireNotificationUserId } from "@/lib/notification-auth";
import { getNotifications, getUnreadCount } from "@/lib/notifications";
import {
  deleteNotificationAction,
  markAllNotificationsReadAction,
  markNotificationReadAction,
  openNotificationAction,
} from "./actions";
import styles from "./notifications.module.css";

export default async function NotificationsPage() {
  const userId = await requireNotificationUserId();
  const [notifications, unreadCount] = await Promise.all([
    getNotifications(userId),
    getUnreadCount(userId),
  ]);

  return (
    <main className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1>알림</h1>
          <p>읽지 않은 알림 {unreadCount}개</p>
        </div>
        {unreadCount > 0 && (
          <form action={markAllNotificationsReadAction}>
            <button type="submit" className={styles.secondaryButton}>
              모두 읽음 처리
            </button>
          </form>
        )}
      </header>

      {notifications.length === 0 ? (
        <p className={styles.empty}>표시할 알림이 없습니다.</p>
      ) : (
        <ul className={styles.list}>
          {notifications.map((notification) => (
            <li
              key={notification.id}
              className={`${styles.item} ${notification.readAt ? "" : styles.unread}`}
            >
              <div className={styles.content}>
                <div className={styles.titleRow}>
                  <h2>{notification.title}</h2>
                  {!notification.readAt && <span className={styles.dot} aria-label="읽지 않음" />}
                </div>
                <p>{notification.body}</p>
                <small>
                  {notification.type} · {notification.createdAt.toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}
                </small>
              </div>
              <div className={styles.actions}>
                {notification.url && (
                  <form action={openNotificationAction.bind(null, notification.id)}>
                    <button type="submit" className={styles.primaryButton}>열기</button>
                  </form>
                )}
                {!notification.readAt && (
                  <form action={markNotificationReadAction.bind(null, notification.id)}>
                    <button type="submit" className={styles.secondaryButton}>읽음</button>
                  </form>
                )}
                <form action={deleteNotificationAction.bind(null, notification.id)}>
                  <button type="submit" className={styles.dangerButton}>삭제</button>
                </form>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
