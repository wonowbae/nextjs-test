import "server-only";
import type { Prisma } from "@/generated/prisma/client";
import { prisma } from "@/lib/prisma";
import type { TableQuery, UserRow } from "@/lib/table-query";

export async function getUsers(query: TableQuery): Promise<{ rows: UserRow[]; rowCount: number }> {
  // AND between different keys; OR (IN) between selected values of the same key.
  const where: Prisma.UserWhereInput = {
    ...(query.name && { name: { contains: query.name, mode: "insensitive" } }),
    ...(query.email && { email: { contains: query.email, mode: "insensitive" } }),
    ...(query.roles.length && { role: { in: query.roles } }),
    ...(query.statuses.length && { status: { in: query.statuses } }),
    ...((query.from || query.to) && {
      createdAt: {
        ...(query.from && { gte: new Date(query.from + "T00:00:00.000Z") }),
        ...(query.to && { lt: new Date(new Date(query.to + "T00:00:00.000Z").getTime() + 86_400_000) }),
      },
    }),
  };

  // Whitelisted, validated sort fields only. Add stable PK tie-breaker.
  const orderBy: Prisma.UserOrderByWithRelationInput[] = query.sorting.map(({ id, desc }) => ({
    [id]: desc ? "desc" : "asc",
  }));
  orderBy.push({ id: "asc" });

  const [rows, rowCount] = await prisma.$transaction([
    prisma.user.findMany({
      where, orderBy, skip: query.pageIndex * query.pageSize, take: query.pageSize,
      select: { id: true, name: true, email: true, role: true, status: true, createdAt: true },
    }),
    prisma.user.count({ where }),
  ]);
  return { rows: rows.map((row) => ({ ...row, createdAt: row.createdAt.toISOString() })), rowCount };
}
