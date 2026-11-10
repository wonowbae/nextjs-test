// Illustrative snippet: call from your trusted server-side comment creation code.
// Adjust names to your domain models and avoid notifying users for their own actions.
//
// import { createNotification } from "@/lib/notifications";
//
// if (post.authorId !== comment.authorId) {
//   await createNotification({
//     userId: post.authorId,
//     type: "COMMENT",
//     title: "새로운 댓글이 달렸습니다",
//     body: `${comment.authorName}님이 댓글을 남겼습니다.`,
//     url: `/posts/${post.id}`,
//   });
// }
