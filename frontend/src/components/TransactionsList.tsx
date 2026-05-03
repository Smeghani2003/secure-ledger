import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dollars, humanizeCategory, shortDate } from "@/lib/format";

type TransactionItem = {
  id: string;
  account_id: string;
  account_name: string;
  amount_cents: number;
  currency: string;
  posted_date: string;
  name: string;
  merchant_name: string | null;
  category: string | null;
  is_pending: boolean;
};

type TransactionsListResponse = {
  items: TransactionItem[];
  total: number;
  offset: number;
  limit: number;
};

export default function TransactionsList({ limit = 20 }: { limit?: number }) {
  const { token } = useAuth();
  const txns = useQuery({
    queryKey: ["transactions", { limit }],
    queryFn: () =>
      api<TransactionsListResponse>(
        `/api/transactions?limit=${limit}&offset=0`,
        { token },
      ),
    enabled: !!token,
  });

  if (txns.isLoading) {
    return <p className="text-sm text-slate-500">Loading transactions…</p>;
  }
  if (txns.isError || !txns.data) {
    return <p className="text-sm text-red-600">Could not load transactions.</p>;
  }
  if (txns.data.items.length === 0) {
    return (
      <div className="rounded-xl border bg-white p-6 text-sm text-slate-600">
        No transactions yet.
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-white shadow-sm">
      <div className="flex items-baseline justify-between border-b px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Recent transactions
        </h2>
        <span className="text-xs text-slate-500">
          showing {txns.data.items.length} of {txns.data.total}
        </span>
      </div>
      <ul className="divide-y">
        {txns.data.items.map((t) => {
          const isOutflow = t.amount_cents > 0;
          return (
            <li
              key={t.id}
              className="flex items-center gap-3 px-4 py-3 text-sm"
            >
              <div className="w-16 shrink-0 text-xs text-slate-500">
                {shortDate(t.posted_date)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium text-slate-900">
                  {t.merchant_name ?? t.name}
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="truncate">{t.account_name}</span>
                  {t.category && (
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
                      {humanizeCategory(t.category)}
                    </span>
                  )}
                  {t.is_pending && (
                    <span className="rounded bg-amber-50 px-1.5 py-0.5 text-amber-700">
                      pending
                    </span>
                  )}
                </div>
              </div>
              <div
                className={`shrink-0 font-mono text-sm tabular-nums ${
                  isOutflow ? "text-slate-900" : "text-emerald-700"
                }`}
              >
                {isOutflow ? "" : "+"}
                {dollars(Math.abs(t.amount_cents))}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
