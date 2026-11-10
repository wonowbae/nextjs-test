# Next.js + Prisma + PostgreSQL: In-App Notifications

Minimal, **server-rendered** notification feature: user-specific notifications, type enum, title/body/internal link, unread/read, soft delete, and "mark all read". **No polling, realtime transports, TanStack Query, or separate notification REST API.**

## Assumptions

- Next.js App Router and React Server Components/Server Actions.
- PostgreSQL datasource and Prisma Client already set up.
- Your project already has `User` and `@/lib/prisma` (a singleton Prisma Client). Keep your current Prisma client import convention.
- Your app uses the `@/*` TypeScript path alias.
- Files assume Prisma Client generated at `@/generated/prisma/client`. **Adjust** `lib/notifications.ts` import path if different. For projects with the older `@prisma/client` generator, import the type from `@prisma/client` instead.
- The provided schema assumes `User.id` is `String`. Match the type if your schema uses Int/UUID in a different representation.

## Installation

1. Merge `prisma/notification.prisma` into **your existing** `prisma/schema.prisma`: add the `NotificationType` enum and `Notification` model; add `notifications Notification[]` to your existing `User` model. This file is a snippet, **not** a standalone Prisma schema.
2. Copy `lib/notifications.ts`, `lib/notification-auth.ts`, and `app/notifications/` to the corresponding directories of your project. Do not overwrite existing files without reviewing.
3. **Required**: implement `requireNotificationUserId()` in `lib/notification-auth.ts` using your current authentication/session mechanism. It intentionally throws until implemented. Never trust userId provided by a browser.
4. Ensure `@/lib/prisma` exports `prisma`, and fix generated Prisma Client import path if needed.
5. Apply the schema in development and generate your client:

   ```bash
   npx prisma migrate dev --name add_notifications
   npx prisma generate
   ```

   Commit the **generated migration directory** under `prisma/migrations/` along with this code. No migration SQL is bundled because the correct migration depends on your existing schema/database and should be generated in your project. In deployment use `npx prisma migrate deploy`.
6. Start Next.js and visit `/notifications` while authenticated.
7. To create notifications, call `createNotification()` from trusted server-side domain code. See `examples/create-comment-notification.ts`.

## API of `lib/notifications.ts`

- `createNotification({ userId, type?, title, body, url? })`
- `getNotifications(userId, take = 30)` (latest up to 100)
- `getUnreadCount(userId)`
- `markAsRead(userId, notificationId)`
- `markAllAsRead(userId)`
- `deleteNotification(userId, notificationId)` (soft delete)

Server Actions in `app/notifications/actions.ts` authenticate on **every call**, scope mutations to the current user, and invalidate `/notifications` after a change. `openNotificationAction` reads the owned notification, marks it read, then redirects only to an internal relative URL.

## Notes / decisions

- `readAt === null` means unread. `deletedAt !== null` means soft deleted.
- The enum is a **Prisma schema enum**, mapped to a PostgreSQL native enum. Adding or changing values requires a reviewed Prisma migration. In particular, renaming/removing values with existing rows requires care.
- `url` must be an internal absolute path (e.g. `/posts/123`). Do not use it to bypass destination page authorization.
- Current implementation displays 30 newest notifications; pagination can be added later.
- The UI displays times in `Asia/Seoul`; adjust time zone for your app.
- Notifications are fetched on server page render/navigation, not pushed to clients. Depending on your Next.js caching setup, ensure user-specific pages are rendered per authenticated request; the auth/session access normally makes this dynamic.
- No notification creation endpoint is exposed, to avoid arbitrary user-to-user notification spam. Create notifications from server-side application events.
- For critical events, consider using a transaction/outbox and a deduplication key later to avoid lost/duplicate notifications.
