// This module is shared by Server and Client. Do not import Prisma here.
export const ROLES = ["ADMIN", "MANAGER", "MEMBER"] as const;
export const STATUSES = ["ACTIVE", "INVITED", "SUSPENDED"] as const;
export const SORT_COLUMNS = ["name", "email", "role", "status", "createdAt"] as const;

export type Role = (typeof ROLES)[number];
export type Status = (typeof STATUSES)[number];
export type SortColumn = (typeof SORT_COLUMNS)[number];
export type UserRow = {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: Status;
  createdAt: string;
};
export type SortRule = { id: SortColumn; desc: boolean };
export type TableQuery = {
  pageIndex: number;
  pageSize: number;
  name: string;
  email: string;
  roles: Role[];
  statuses: Status[];
  from: string;
  to: string;
  sorting: SortRule[];
};

export const DEFAULT_QUERY: TableQuery = {
  pageIndex: 0, pageSize: 20, name: "", email: "", roles: [], statuses: [],
  from: "", to: "", sorting: [{ id: "createdAt", desc: true }],
};

type QuerySource = { get(key: string): string | null };
function parseList<T extends string>(input: string | null, choices: readonly T[]): T[] {
  const values = input?.split(",") ?? [];
  return choices.filter((choice) => values.includes(choice));
}
function positiveInt(input: string | null, fallback: number): number {
  const n = Number(input);
  return input && Number.isSafeInteger(n) && n >= 0 ? n : fallback;
}
function isoDay(value: string | null): string {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
  const date = new Date(value + "T00:00:00.000Z");
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value ? value : "";
}
function parseSorting(value: string | null): SortRule[] {
  const found: SortRule[] = [];
  for (const part of (value ?? "").split(",")) {
    const [key, direction, extra] = part.split(":");
    if (extra !== undefined || !SORT_COLUMNS.some((v) => v === key)) continue;
    if (direction !== "asc" && direction !== "desc") continue;
    const id = key as SortColumn;
    if (!found.some((v) => v.id === id)) found.push({ id, desc: direction === "desc" });
    if (found.length === 3) break;
  }
  return found.length ? found : DEFAULT_QUERY.sorting;
}

export function parseTableQuery(source: QuerySource): TableQuery {
  const size = positiveInt(source.get("size"), DEFAULT_QUERY.pageSize);
  return {
    pageIndex: Math.min(100_000, positiveInt(source.get("page"), 0)),
    pageSize: [10, 20, 50, 100].includes(size) ? size : 20,
    name: (source.get("name") ?? "").slice(0, 100),
    email: (source.get("email") ?? "").slice(0, 100),
    roles: parseList(source.get("roles"), ROLES),
    statuses: parseList(source.get("statuses"), STATUSES),
    from: isoDay(source.get("from")),
    to: isoDay(source.get("to")),
    sorting: parseSorting(source.get("sort")),
  };
}

export function serializeTableQuery(query: TableQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.pageIndex) params.set("page", String(query.pageIndex));
  if (query.pageSize !== 20) params.set("size", String(query.pageSize));
  if (query.name) params.set("name", query.name);
  if (query.email) params.set("email", query.email);
  if (query.roles.length) params.set("roles", query.roles.join(","));
  if (query.statuses.length) params.set("statuses", query.statuses.join(","));
  if (query.from) params.set("from", query.from);
  if (query.to) params.set("to", query.to);
  if (query.sorting.length) {
    params.set("sort", query.sorting.map(({ id, desc }) => `${id}:${desc ? "desc" : "asc"}`).join(","));
  }
  return params;
}
