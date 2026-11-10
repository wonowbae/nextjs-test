import { Suspense } from "react";
import { AdminTable } from "@/components/admin-table";
import { getUsers } from "@/lib/users";
import { parseTableQuery } from "@/lib/table-query";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
export default async function Page({ searchParams }: { searchParams: SearchParams }) {
  const input = await searchParams;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(input)) {
    if (typeof value === "string") params.set(key, value);
  }
  const query = parseTableQuery(params);
  const result = await getUsers(query);
  return (
    <main className="layout">
      <header><h1>Users · Admin Table</h1><p>Server-side filtering, multi-sort & pagination with URL state</p></header>
      <Suspense fallback={<p>Loading table…</p>}>
        <AdminTable rows={result.rows} rowCount={result.rowCount} query={query} />
      </Suspense>
    </main>
  );
}
