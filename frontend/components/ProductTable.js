import Link from "next/link";
import { useMemo, useState } from "react";
import RecommendationBadge from "./RecommendationBadge";

const FILTERS = ["ALL", "PURSUE", "MONITOR", "AVOID"];

export default function ProductTable({ products }) {
  const [filter, setFilter] = useState("ALL");
  const [sortDesc, setSortDesc] = useState(true);

  const rows = useMemo(() => {
    const filtered = filter === "ALL" ? products : products.filter((p) => p.recommendation === filter);
    return [...filtered].sort((a, b) =>
      sortDesc ? b.margin_pct - a.margin_pct : a.margin_pct - b.margin_pct
    );
  }, [products, filter, sortDesc]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-600">Filter:</span>
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 text-xs rounded border ${
              filter === f
                ? "bg-slate-900 text-white border-slate-900"
                : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
            }`}
          >
            {f}
          </button>
        ))}
        <button
          onClick={() => setSortDesc((v) => !v)}
          className="ml-auto px-2 py-1 text-xs rounded border bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
        >
          Sort by margin {sortDesc ? "↓" : "↑"}
        </button>
      </div>

      <div className="overflow-x-auto bg-white border border-slate-200 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="text-left p-3">Image</th>
              <th className="text-left p-3">Title</th>
              <th className="text-right p-3">Supply</th>
              <th className="text-right p-3" title="CJ suggested retail, not a verified Amazon price">
                Est. Retail (CJ)
              </th>
              <th className="text-right p-3">Net Margin %</th>
              <th className="text-right p-3">Risk Score</th>
              <th className="text-left p-3">Recommendation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="p-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={p.image_url} alt="" className="w-12 h-12 object-cover rounded" />
                </td>
                <td className="p-3">
                  <Link href={`/products/${p.id}`} className="text-blue-600 hover:underline">
                    {p.title}
                  </Link>
                </td>
                <td className="p-3 text-right tabular-nums">${p.supply_price?.toFixed(2)}</td>
                <td className="p-3 text-right tabular-nums">${p.sell_price?.toFixed(2)}</td>
                <td className="p-3 text-right tabular-nums">{p.margin_pct?.toFixed(1)}%</td>
                <td className="p-3 text-right tabular-nums">{p.supplier_risk_score?.toFixed(0)}</td>
                <td className="p-3">
                  <RecommendationBadge value={p.recommendation} />
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="p-6 text-center text-slate-500">
                  No products match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
