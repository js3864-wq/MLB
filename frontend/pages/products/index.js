import { useRouter } from "next/router";
import useSWR from "swr";
import ProductTable from "../../components/ProductTable";
import { fetchProducts } from "../../lib/api";

export default function ProductsPage() {
  const router = useRouter();
  const { data, error, isLoading } = useSWR("products", () => fetchProducts());

  if (isLoading) return <p className="text-slate-500">Loading products…</p>;
  if (error) return <p className="text-red-600">Failed to load products.</p>;

  const initialCategory = router.query.category ?? "ALL";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Products</h1>
        <p className="text-slate-600 text-sm">
          Retail price shown is CJ&apos;s suggested retail, not a verified Amazon price.
        </p>
      </div>
      <ProductTable key={initialCategory} products={data?.products ?? []} initialCategory={initialCategory} />
    </div>
  );
}
