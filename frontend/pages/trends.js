import useSWR from "swr";
import MarginChart from "../components/MarginChart";
import { fetchTrends } from "../lib/api";

export default function TrendsPage() {
  const { data, error, isLoading } = useSWR("trends", fetchTrends);

  if (isLoading) return <p className="text-slate-500">Loading trends…</p>;
  if (error) return <p className="text-red-600">Failed to load trends.</p>;

  const categories = data?.categories ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Today&apos;s trending categories</h1>
        <p className="text-slate-600 text-sm">
          Derived from Google Trends rising queries and clustered into product categories by Claude.
        </p>
      </div>

      <MarginChart categories={categories} />

      <div className="overflow-x-auto bg-white border border-slate-200 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="text-left p-3">Category</th>
              <th className="text-right p-3">Products</th>
              <th className="text-right p-3">Avg margin %</th>
            </tr>
          </thead>
          <tbody>
            {categories.map((c) => (
              <tr key={c.id} className="border-t border-slate-100">
                <td className="p-3 capitalize">{c.name}</td>
                <td className="p-3 text-right tabular-nums">{c.product_count}</td>
                <td className="p-3 text-right tabular-nums">{c.avg_margin_pct?.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
