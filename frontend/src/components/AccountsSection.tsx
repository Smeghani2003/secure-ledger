import { dollars } from "@/lib/format";

export type Account = {
  id: string;
  name: string;
  mask: string | null;
  type: string;
  subtype: string | null;
  currency: string;
  current_balance_cents: number | null;
  institution_name: string | null;
  last_synced_at: string | null;
};

type Group = { institution: string; accounts: Account[] };

function groupByInstitution(accounts: Account[]): Group[] {
  const map = new Map<string, Account[]>();
  for (const a of accounts) {
    const key = a.institution_name ?? "Other";
    const list = map.get(key) ?? [];
    list.push(a);
    map.set(key, list);
  }
  return Array.from(map.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([institution, accounts]) => ({ institution, accounts }));
}

export default function AccountsSection({ accounts }: { accounts: Account[] }) {
  if (accounts.length === 0) return null;
  const groups = groupByInstitution(accounts);
  return (
    <section className="space-y-6">
      {groups.map((group) => (
        <div key={group.institution}>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            {group.institution}
          </h2>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {group.accounts.map((a) => (
              <li
                key={a.id}
                className="rounded-xl border bg-white p-4 shadow-sm"
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-medium">{a.name}</span>
                  <span className="text-xs uppercase text-slate-500">
                    {a.subtype ?? a.type}
                  </span>
                </div>
                <div className="mt-2 text-2xl font-semibold tracking-tight">
                  {dollars(a.current_balance_cents)}
                </div>
                {a.mask && (
                  <div className="text-xs text-slate-500">•••• {a.mask}</div>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
