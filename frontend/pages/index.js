import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Dropshipping Product Opportunity Finder</h1>
      <p className="text-slate-600 max-w-2xl">
        This dashboard surfaces trending product categories and ranks CJ Dropshipping
        listings by estimated margin and supplier reliability. Retail prices shown are
        <span className="font-semibold"> CJ&apos;s suggested retail</span>, not verified
        Amazon / eBay prices.
      </p>
      <div className="flex gap-3">
        <Link
          href="/trends"
          className="px-4 py-2 bg-slate-900 text-white rounded hover:bg-slate-700"
        >
          View today&apos;s trends
        </Link>
        <Link
          href="/products"
          className="px-4 py-2 bg-white border border-slate-300 text-slate-800 rounded hover:bg-slate-100"
        >
          Browse products
        </Link>
      </div>
    </div>
  );
}
