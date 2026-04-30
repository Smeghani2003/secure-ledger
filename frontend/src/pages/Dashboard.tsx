import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import PlaidLinkButton from "@/components/PlaidLinkButton";

type Account = {
  id: string;
  name: string;
  mask: string | null;
  type: string;
  subtype: string | null;
  currency: string;
  current_balance_cents: number | null;
};

function dollars(cents: number | null) {
  if (cents == null) return "—";
  return (cents / 100).toLocaleString(undefined, { style: "currency", currency: "USD" });
}

export default function Dashboard() {
  const { token } = useAuth();
  const accounts = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api<Account[]>("/api/accounts", { token }),
    enabled: !!token,
  });

  return (
    <div className="space-y-8">
      <section className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Your accounts</h1>
          <p className="text-sm text-slate-600">
            Link a sandbox bank to see balances. (Use Plaid sandbox creds:
            <code className="mx-1 rounded bg-slate-100 px-1">user_good</code> /
            <code className="mx-1 rounded bg-slate-100 px-1">pass_good</code>)
          </p>
        </div>
        <PlaidLinkButton onLinked={() => accounts.refetch()} />
      </section>

      <section>
        {accounts.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
        {accounts.isError && <p className="text-sm text-red-600">Could not load accounts.</p>}
        {accounts.data && accounts.data.length === 0 && (
          <div className="rounded-xl border bg-white p-8 text-center text-slate-600">
            No accounts yet. Click <strong>Link a bank</strong> to get started.
          </div>
        )}
        {accounts.data && accounts.data.length > 0 && (
          <ul className="grid gap-3 sm:grid-cols-2">
            {accounts.data.map((a) => (
              <li key={a.id} className="rounded-xl border bg-white p-4 shadow-sm">
                <div className="flex items-baseline justify-between">
                  <span className="font-medium">{a.name}</span>
                  <span className="text-xs uppercase text-slate-500">{a.type}</span>
                </div>
                <div className="mt-2 text-2xl font-semibold tracking-tight">
                  {dollars(a.current_balance_cents)}
                </div>
                {a.mask && <div className="text-xs text-slate-500">•••• {a.mask}</div>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
