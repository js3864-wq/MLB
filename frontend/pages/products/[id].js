import { useRouter } from "next/router";
import Link from "next/link";
import useSWR from "swr";
import RecommendationBadge from "../../components/RecommendationBadge";
import { fetchProduct } from "../../lib/api";

const FIELD_GROUPS = [
  {
    title: "Pricing",
    fields: [
      ["supply_price", "CJ supply price", "currency"],
      ["sell_price", "Est. retail (CJ)", "currency"],
      ["shipping_cost", "Shipping", "currency"],
      ["platform_fee", "Platform fee (15%)", "currency"],
      ["net_margin", "Net margin", "currency"],
      ["margin_pct", "Margin %", "percent"],
    ],
  },
  {
    title: "Supplier",
    fields: [
      ["supplier_rating", "Rating", "number"],
      ["sold_count", "Fulfilled orders", "int"],
      ["stock", "Stock", "int"],
      ["supplier_risk_score", "Risk score /100", "number"],
    ],
  },
];

function format(value, kind) {
  if (value === null || value === undefined) return "—";
  if (kind === "currency") return `$${Number(value).toFixed(2)}`;
  if (kind === "percent") return `${Number(value).toFixed(2)}%`;
  if (kind === "int") return Number(value).toLocaleString();
  return Number(value).toFixed(2);
}

export default function ProductDetail() {
  const router = useRouter();
  const { id } = router.query;
  const { data: product, error, isLoading } = useSWR(
    id ? ["product", id] : null,
    () => fetchProduct(id)
  );

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (error) return <p className="text-red-600">Failed to load product.</p>;
  if (!product) return <p className="text-slate-500">Not found.</p>;

  const cjUrl = `https://www.cjdropshipping.com/product/detail.html?pid=${product.cj_product_id}`;

  return (
    <div className="space-y-6">
      <Link href="/products" className="text-sm text-blue-600 hover:underline">← Back to products</Link>

      <div className="flex gap-6 items-start">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={product.image_url} alt="" className="w-40 h-40 object-cover rounded border border-slate-200" />
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">{product.title}</h1>
          <RecommendationBadge value={product.recommendation} />
          <p className="text-slate-700 max-w-xl">{product.explanation}</p>
          <a
            href={cjUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-sm text-blue-600 hover:underline"
          >
            View on CJ Dropshipping ↗
          </a>
        </div>
      </div>

      <p className="text-xs text-slate-500 italic">
        Retail price is CJ suggested retail, not verified Amazon price.
      </p>

      <div className="grid md:grid-cols-2 gap-6">
        {FIELD_GROUPS.map((group) => (
          <div key={group.title} className="bg-white border border-slate-200 rounded-lg p-4">
            <h2 className="font-semibold text-slate-700 mb-3">{group.title}</h2>
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              {group.fields.map(([key, label, kind]) => (
                <div key={key} className="contents">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="text-right tabular-nums">{format(product[key], kind)}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </div>
  );
}
