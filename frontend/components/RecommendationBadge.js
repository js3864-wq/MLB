const STYLES = {
  PURSUE: "bg-green-100 text-green-800 border-green-300",
  MONITOR: "bg-yellow-100 text-yellow-800 border-yellow-300",
  AVOID: "bg-red-100 text-red-800 border-red-300",
};

export default function RecommendationBadge({ value }) {
  const cls = STYLES[value] || "bg-slate-100 text-slate-700 border-slate-300";
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {value || "—"}
    </span>
  );
}
