const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export async function fetchTrends() {
  return get("/trends");
}

export async function fetchProducts({ recommendation } = {}) {
  const qs = recommendation ? `?recommendation=${encodeURIComponent(recommendation)}` : "";
  return get(`/products${qs}`);
}

export async function fetchProduct(id) {
  return get(`/products/${id}`);
}

export async function triggerPipeline() {
  const res = await fetch(`${API_BASE}/run-pipeline`, { method: "POST" });
  return res.json();
}
