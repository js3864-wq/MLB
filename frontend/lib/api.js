import { mockCategories, mockProducts } from "./mockData";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export async function fetchTrends() {
  if (USE_MOCK) return { categories: mockCategories };
  return get("/trends");
}

export async function fetchProducts({ recommendation } = {}) {
  if (USE_MOCK) {
    const products = recommendation
      ? mockProducts.filter((p) => p.recommendation === recommendation)
      : mockProducts;
    return { products };
  }
  const qs = recommendation ? `?recommendation=${encodeURIComponent(recommendation)}` : "";
  return get(`/products${qs}`);
}

export async function fetchProduct(id) {
  if (USE_MOCK) return mockProducts.find((p) => p.id === id) || null;
  return get(`/products/${id}`);
}

export async function triggerPipeline() {
  if (USE_MOCK) return { mock_mode: true, categories: mockCategories.length, products: mockProducts.length };
  const res = await fetch(`${API_BASE}/run-pipeline`, { method: "POST" });
  return res.json();
}
