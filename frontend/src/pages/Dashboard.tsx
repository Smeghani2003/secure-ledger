import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useSyncMutation } from "@/lib/sync";
import { relativeTime } from "@/lib/format";
import PlaidLinkButton from "@/components/PlaidLinkButton";
import AccountsSection, { type Account } from "@/components/AccountsSection";
import SpendingChart from "@/components/SpendingChart";
import TransactionsList from "@/components/TransactionsList";

function mostRecent(accounts: Account[]): string | null {
  const stamps = accounts
    .map((a) => a.last_synced_at)
    .filter((s): s is string => !!s);
  if (stamps.length === 0) return null;
  return stamps.sort().at(-1) ?? null;
}

export default function Dashboard() {
  const { token } = useAuth();
  const accounts = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api<Account[]>("/api/accounts", { token }),
    enabled: !!token,
  });
  const sync = useSyncMutation();

  const lastSynced = accounts.data ? mostRecent(accounts.data) : null;
  const syncError = sync.error
    ? sync.error instanceof ApiError
      ? `Sync failed: ${(sync.error.body as { detail?: string } | null)?.detail ?? "unknown error"}`
      : "Sync failed — please try again"
    : null;

  const hasAccounts = accounts.data && accounts.data.length > 0;

  return (
    <div className="space-y-8">
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Your accounts</h1>
          <p className="text-sm text-slate-600">
            Link a sandbox bank to see balances. (Use Plaid sandbox creds:
            <code className="mx-1 rounded bg-slate-100 px-1">user_good</code> /
            <code className="mx-1 rounded bg-slate-100 px-1">pass_good</code>)
          </p>
          {lastSynced && (
            <p className="mt-2 text-xs text-slate-500">
              Last synced {relativeTime(lastSynced)}
            </p>
          )}
          {syncError && <p className="mt-2 text-xs text-red-600">{syncError}</p>}
        </div>
        <div className="flex items-start gap-2">
          {hasAccounts && (
            <button
              onClick={() => sync.mutate()}
              disabled={sync.isPending}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {sync.isPending ? "Refreshing…" : "Refresh"}
            </button>
          )}
          <PlaidLinkButton onLinked={() => accounts.refetch()} />
        </div>
      </section>

      {accounts.isLoading && (
        <p className="text-sm text-slate-500">Loading…</p>
      )}
      {accounts.isError && (
        <p className="text-sm text-red-600">Could not load accounts.</p>
      )}

      {accounts.data && accounts.data.length === 0 && (
        <div className="rounded-xl border bg-white p-8 text-center text-slate-600">
          No accounts yet. Click <strong>Link a bank</strong> to get started.
        </div>
      )}

      {hasAccounts && (
        <>
          <AccountsSection accounts={accounts.data!} />

          <div className="grid gap-6 lg:grid-cols-2">
            <SpendingChart />
            <TransactionsList limit={20} />
          </div>
        </>
      )}
    </div>
  );
}
