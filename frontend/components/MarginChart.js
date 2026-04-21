import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function MarginChart({ categories }) {
  const data = categories.map((c) => ({ name: c.name, margin: c.avg_margin_pct }));
  return (
    <div className="w-full h-72 bg-white rounded-lg border border-slate-200 p-4">
      <h3 className="text-sm font-semibold text-slate-700 mb-2">Avg margin % by category</h3>
      <ResponsiveContainer width="100%" height="90%">
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" angle={-25} textAnchor="end" interval={0} height={60} fontSize={11} />
          <YAxis unit="%" />
          <Tooltip />
          <Bar dataKey="margin" fill="#2563eb" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
