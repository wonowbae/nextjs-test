"use client";

import { useMemo, useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  flexRender, functionalUpdate, getCoreRowModel, useReactTable,
  type ColumnDef, type PaginationState, type SortingState,
} from "@tanstack/react-table";
import {
  DEFAULT_QUERY, ROLES, STATUSES, serializeTableQuery,
  type Role, type Status, type TableQuery, type UserRow, type SortColumn,
} from "@/lib/table-query";

function SortHeader({ label, direction, rank }: { label: string; direction?: "asc" | "desc"; rank?: number }) {
  return <span>{label} <span className="sort-symbol">{direction === "asc" ? "↑" : direction === "desc" ? "↓" : "↕"}{rank ? ` ${rank}` : ""}</span></span>;
}
function CheckboxGroup<T extends string>({ title, options, selected, onChange }: {
  title: string; options: readonly T[]; selected: T[]; onChange: (values: T[]) => void;
}) {
  return <fieldset className="checkbox-group"><legend>{title}</legend>{options.map((value) => (
    <label key={value}><input type="checkbox" checked={selected.includes(value)} onChange={(e) =>
      onChange(e.target.checked ? [...selected, value] : selected.filter((item) => item !== value))} /> {value}</label>
  ))}</fieldset>;
}

export function AdminTable({ rows, rowCount, query }: { rows: UserRow[]; rowCount: number; query: TableQuery }) {
  const router = useRouter();
  const pathname = usePathname();
  const [pending, startTransition] = useTransition();
  // Text input draft is local so we avoid making a DB request on every keystroke.
  const [draftName, setDraftName] = useState(query.name);
  const [draftEmail, setDraftEmail] = useState(query.email);

  const updateUrl = (next: TableQuery) => {
    const search = serializeTableQuery(next).toString();
    startTransition(() => router.replace(search ? `${pathname}?${search}` : pathname, { scroll: false }));
  };
  const changeFilters = (patch: Partial<TableQuery>) => updateUrl({ ...query, ...patch, pageIndex: 0 });
  const pagination: PaginationState = { pageIndex: query.pageIndex, pageSize: query.pageSize };
  const sorting: SortingState = query.sorting;

  const columns = useMemo<ColumnDef<UserRow>[]>(() => [
    { accessorKey: "name", header: "Name", cell: ({ getValue }) => <strong>{getValue<string>()}</strong> },
    { accessorKey: "email", header: "Email" },
    { accessorKey: "role", header: "Role", cell: ({ getValue }) => <span className="tag">{getValue<string>()}</span> },
    { accessorKey: "status", header: "Status", cell: ({ getValue }) => <span className="tag">{getValue<string>()}</span> },
    { accessorKey: "createdAt", header: "Created (UTC)", cell: ({ getValue }) => getValue<string>().slice(0, 10) },
  ], []);

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    rowCount,
    state: { pagination, sorting },
    onPaginationChange: (updater) => {
      const next = functionalUpdate(updater, pagination);
      updateUrl({ ...query, pageIndex: next.pageIndex, pageSize: next.pageSize });
    },
    onSortingChange: (updater) => {
      const requested = functionalUpdate(updater, sorting)
        .filter((s) => ["name", "email", "role", "status", "createdAt"].includes(s.id))
        .slice(0, 3)
        .map((s) => ({ id: s.id as SortColumn, desc: s.desc }));
      updateUrl({ ...query, sorting: requested.length ? requested : DEFAULT_QUERY.sorting, pageIndex: 0 });
    },
    enableMultiSort: true,
    maxMultiSortColCount: 3,
    isMultiSortEvent: (event) => (event as MouseEvent).shiftKey,
  });

  const totalPages = table.getPageCount();
  const first = rowCount ? query.pageIndex * query.pageSize + 1 : 0;
  const last = Math.min((query.pageIndex + 1) * query.pageSize, rowCount);
  return <section className="panel" aria-busy={pending}>
    <form className="filters" onSubmit={(e) => {
      e.preventDefault(); changeFilters({ name: draftName.trim(), email: draftEmail.trim() });
    }}>
      <div className="text-filter"><label htmlFor="filter-name">Name contains</label>
        <input id="filter-name" value={draftName} onChange={(e) => setDraftName(e.target.value)} maxLength={100} placeholder="Search names" /></div>
      <div className="text-filter"><label htmlFor="filter-email">Email contains</label>
        <input id="filter-email" value={draftEmail} onChange={(e) => setDraftEmail(e.target.value)} maxLength={100} placeholder="Search emails" /></div>
      <button type="submit">Apply text filters</button>
      <button type="button" className="secondary" onClick={() => {
        setDraftName(""); setDraftEmail(""); updateUrl(DEFAULT_QUERY);
      }}>Reset all</button>
    </form>
    <div className="filter-grid">
      <CheckboxGroup<Role> title="Roles (OR)" options={ROLES} selected={query.roles} onChange={(roles) => changeFilters({ roles })} />
      <CheckboxGroup<Status> title="Statuses (OR)" options={STATUSES} selected={query.statuses} onChange={(statuses) => changeFilters({ statuses })} />
      <fieldset className="date-group"><legend>Created (inclusive, UTC)</legend>
        <label>From <input type="date" value={query.from} max={query.to || undefined} onChange={(e) => changeFilters({ from: e.target.value })} /></label>
        <label>To <input type="date" value={query.to} min={query.from || undefined} onChange={(e) => changeFilters({ to: e.target.value })} /></label>
      </fieldset>
    </div>
    <p className="hint">Different fields combine with AND. Multiple values within Role/Status combine with OR. Click headers to sort; Shift+click adds a second/third sorting key.</p>
    <div className="table-scroll"><table><thead>{table.getHeaderGroups().map((group) => <tr key={group.id}>
      {group.headers.map((header) => {
        const sort = header.column.getIsSorted();
        const rank = sort ? header.column.getSortIndex() + 1 : undefined;
        return <th key={header.id}>
          <button className="head-button" type="button" onClick={header.column.getToggleSortingHandler()} disabled={!header.column.getCanSort()}>
            <SortHeader label={typeof header.column.columnDef.header === "string" ? header.column.columnDef.header : header.id}
              direction={sort || undefined} rank={rank} />
          </button>
        </th>;
      })}
    </tr>)}</thead><tbody>
      {table.getRowModel().rows.length ? table.getRowModel().rows.map((row) => <tr key={row.id}>
        {row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}
      </tr>) : <tr><td colSpan={columns.length} className="empty">No users match these filters.</td></tr>}
    </tbody></table></div>
    <footer className="pagination">
      <span>{first}–{last} of {rowCount.toLocaleString()} users {pending && "· Loading…"}</span>
      <div className="pages">
        <button type="button" className="secondary" disabled={!table.getCanPreviousPage() || pending} onClick={() => table.setPageIndex(0)}>« First</button>
        <button type="button" className="secondary" disabled={!table.getCanPreviousPage() || pending} onClick={() => table.previousPage()}>‹ Prev</button>
        <span>Page {query.pageIndex + 1} / {Math.max(1, totalPages)}</span>
        <button type="button" className="secondary" disabled={!table.getCanNextPage() || pending} onClick={() => table.nextPage()}>Next ›</button>
        <button type="button" className="secondary" disabled={!table.getCanNextPage() || pending} onClick={() => table.setPageIndex(Math.max(0, totalPages - 1))}>Last »</button>
        <select aria-label="Rows per page" value={query.pageSize} onChange={(e) => updateUrl({ ...query, pageIndex: 0, pageSize: Number(e.target.value) })}>
          {[10, 20, 50, 100].map((n) => <option key={n} value={n}>{n} / page</option>)}
        </select>
      </div>
    </footer>
  </section>;
}
