"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProductJourney } from "@/components/ProductJourney";
import { Search, Globe, ExternalLink, Loader2 } from "lucide-react";

interface Uni { id: string; slug: string; name: string; nameEn: string; country: string; countryCode: string; rank: number; logoUrl: string; }

const COUNTRY_FLAGS: Record<string, string> = {
  "美国": "🇺🇸",
  "英国": "🇬🇧",
  "澳大利亚": "🇦🇺",
  "加拿大": "🇨🇦",
  "德国": "🇩🇪",
  "日本": "🇯🇵",
  "中国": "🇨🇳",
  "法国": "🇫🇷",
  "新加坡": "🇸🇬",
  "中国香港": "🇭🇰",
};

export default function XuanxiaoPage() {
  const [unis, setUnis] = useState<Uni[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [selectedCountry, setSelectedCountry] = useState("");

  useEffect(() => {
    fetch("/api/xuanxiao/universities")
      .then(function(r) { return r.json(); })
      .then(function(res) { if (res.success) setUnis(res.data); else setError(res.error || "加载失败"); })
      ["catch"](function(e) { setError(e.message); })
      .finally(function() { setLoading(false); });
  }, []);

  const countrySet: string[] = [];
  unis.forEach(function(u) {
    if (u.country && countrySet.indexOf(u.country) === -1) countrySet.push(u.country);
  });
  const countries = countrySet.sort();

  const filtered = unis.filter(function(u) {
    if (search && u.name.indexOf(search) === -1 && u.nameEn.toLowerCase().indexOf(search.toLowerCase()) === -1) return false;
    if (selectedCountry && u.country !== selectedCountry) return false;
    return true;
  });

  return (
    <div>
      <header className="border-b border-line bg-panel px-5 py-3">
        <div className="mx-auto flex max-w-6xl items-center gap-3">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-cobalt text-panel"><Globe size={18} /></div>
          <div><h1 className="text-base font-semibold text-ink">全球大学库</h1><p className="text-xs text-ink/52">数据合作方 · 选校</p></div>
          <Link href="/match" className="ml-auto text-xs text-cobalt hover:underline">← 返回智能匹配</Link>
        </div>
      </header>
      <div className="mx-auto max-w-6xl px-4 pt-4"><ProductJourney active="match" compact /></div>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <div className="mb-6 flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/30" />
            <input type="text" value={search} onChange={function(e) { setSearch(e.target.value); }}
              placeholder="搜索大学..."
              className="w-full rounded-lg border border-line/60 bg-white/90 py-2.5 pl-9 pr-3 text-sm text-ink outline-none focus:border-cobalt/50" />
          </div>
          <select value={selectedCountry} onChange={function(e) { setSelectedCountry(e.target.value); }}
            className="rounded-lg border border-line/60 bg-white/90 px-3 py-2.5 text-sm text-ink outline-none focus:border-cobalt/50">
            <option value="">全部国家</option>
            {countries.map(function(c) { return (<option key={c} value={c}>{(COUNTRY_FLAGS[c] || "") + " " + c}</option>); })}
          </select>
        </div>

        {loading && <div className="flex items-center justify-center py-20 text-ink/40"><Loader2 size={20} className="animate-spin mr-2" /> 加载中...</div>}
        {error && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-500">{error}</div>}

        {!loading && !error && (
          <>
            <p className="mb-4 text-xs text-ink/40">共 {filtered.length} 所大学</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filtered.map(function(u) {
                return (
                  <a key={u.id} href={"https://xuanxiao.org/universities/" + u.slug}
                    target="_blank" rel="noopener noreferrer"
                    className="group rounded-xl border border-line/40 bg-white/90 p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md hover:border-cobalt/30">
                    <div className="flex items-start justify-between mb-3">
                      {u.logoUrl ? (
                        <img src={u.logoUrl} alt={u.name} className="w-10 h-10 rounded-lg object-contain" />
                      ) : (
                        <div className="w-10 h-10 rounded-lg bg-ink/5 flex items-center justify-center text-lg">{u.name.charAt(0)}</div>
                      )}
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-700">#{u.rank || "?"}</span>
                        <ExternalLink size={12} className="text-ink/20 group-hover:text-cobalt transition-colors" />
                      </div>
                    </div>
                    <h3 className="text-sm font-semibold text-ink group-hover:text-cobalt transition-colors line-clamp-1">{u.name}</h3>
                    {u.nameEn && <p className="text-xs text-ink/40 mt-0.5">{u.nameEn}</p>}
                    <p className="mt-1.5 text-xs text-ink/50">{(COUNTRY_FLAGS[u.country] || u.countryCode) + " " + u.country}</p>
                  </a>
                );
              })}
            </div>
            {filtered.length === 0 && <div className="text-center py-16 text-ink/40 text-sm">未找到匹配的大学</div>}
          </>
        )}

        <div className="mt-10 rounded-xl border border-line/40 bg-white/80 p-4 text-center text-xs text-ink/40">
          数据由 <a href="https://xuanxiao.org" target="_blank" rel="noopener noreferrer" className="text-cobalt hover:underline">选校</a> 提供 · 点击卡片查看详细排名和信息
        </div>
      </main>
    </div>
  );
}