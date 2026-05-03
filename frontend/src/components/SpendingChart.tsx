import { useQuery } from "@tanstack/react-query";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dollars, humanizeCategory } from "@/lib/format";

type CategorySpend = {
  category: string;
  total_cents: number;
  count: number;
};

type SpendingResponse = {
  days: number;
  start_date: string;
  end_date: string;
  by_category: CategorySpend[];
  total_cents: number;
};

// Slate ramp; first slot is the brand dark, then steps lighter.
const COLORS = [
  "#0f172a",
  "#1e293b",
  "#334155",
  "#475569",
  "#64748b",
  "#94a3b8",
  "#cbd5e1",
  "#e2e8f0",
];

export default function SpendingChart({ days = 30 }: { days?: number }) {
  const { token } = useAuth();
  const spending = useQuery({
    queryKey: ["spending", days],
    queryFn: () =>
      api<SpendingResponse>(`/api/transactions/spending?days=${days}`, { token }),
    enabled: !!token,
  });

  if (spending.isLoading) {
    return <p className="text-sm text-slate-500">Loading spending…</p>;
  }
  if (spending.isError || !spending.data) {
    return <p className="text-sm text-red-600">Could not load spending.</p>;
  }
  if (spending.data.by_category.length === 0) {
    return (
      <div className="rounded-xl border bg-white p-6 text-sm text-slate-600">
        No spending in the last {days} days yet.
      </div>
    );
  }

  const data = spending.data.by_category.map((c) => ({
    name: humanizeCategory(c.category),
    value: c.total_cents,
    count: c.count,
  }));

  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Spending — last {days} days
        </h2>
        <span className="text-lg font-semibold text-slate-900">
          {dollars(spending.data.total_cents)}
        </span>
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={1}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => dollars(value)}
              contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0" }}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              wrapperStyle={{ fontSize: 12 }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
