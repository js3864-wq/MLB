import "../styles/globals.css";
import Link from "next/link";

export default function App({ Component, pageProps }) {
  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-6">
          <Link href="/" className="font-bold text-lg">Dropship Finder</Link>
          <Link href="/trends" className="text-slate-700 hover:text-slate-900">Trends</Link>
          <Link href="/products" className="text-slate-700 hover:text-slate-900">Products</Link>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">
        <Component {...pageProps} />
      </main>
    </div>
  );
}
