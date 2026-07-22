import { NextResponse } from "next/server";

const XUANXIAO_URL = "https://xuanxiao.org/universities";

interface XuanxiaoUni {
  id: string;
  slug: string;
  name: string;
  nameEn: string | null;
  country: string;
  countryCode: string;
  displayOrder: number;
  logoUrl: string;
}

function extractUnis(html: string): XuanxiaoUni[] {
  const results: XuanxiaoUni[] = [];
  const cardRegex = /<a\s+href="https:\/\/xuanxiao\.org\/universities\/([^"]+)"[^>]*wire:key="featured-(\d+)"[^>]*>([\s\S]*?)<\/a>/g;
  let cardMatch;

  while ((cardMatch = cardRegex.exec(html)) !== null) {
    const slug = cardMatch[1];
    const id = cardMatch[2];
    const card = cardMatch[3];

    const nameMatch = card.match(/class="font-medium[^"]*text-sm[^"]*">\s*([^<]+?)\s*<\//);
    const name = nameMatch ? nameMatch[1].trim() : slug;

    const enMatch = card.match(/>\s*\(([A-Za-z0-9 &-]+)\)\s*<\//);
    const nameEn = enMatch ? enMatch[1].trim() : null;

    const countryDiv = card.match(/mt-1\.5 text-xs[^>]*>\s*([\s\S]*?)<\/div>/);
    let country = "", countryCode = "", city = "";
    if (countryDiv) {
      const cHtml = countryDiv[1];
      const flagMatch = cHtml.match(/((?:[\uD83C-\uDBFF][\uDC00-\uDFFF]){1,2})/);
      countryCode = flagMatch ? flagMatch[1] : "";
      const cnMatch = cHtml.match(/[\u4e00-\u9fff]{2,10}/);
      country = cnMatch ? cnMatch[0].trim() : "";
      const cityMatch = cHtml.match(/&middot;\s*([^<]+?)\s*<\!/);
      city = cityMatch ? cityMatch[1].trim() : "";
    }

    const orderMatch = card.match(/>\s*(\d+)\s*<\/div>\s*<\!--/);
    const displayOrder = orderMatch ? parseInt(orderMatch[1], 10) : 0;

    const logoMatch = card.match(/src="([^"]*\/coat_of_arms\.webp)"/);
    const logoUrl = logoMatch ? logoMatch[1] : "";

    results.push({ id, slug, name, nameEn, country, countryCode, displayOrder, logoUrl });
  }
  return results;
}

let cached: XuanxiaoUni[] | null = null;
let cacheTime = 0;
const CACHE_TTL = 5 * 60 * 1000;

export async function GET() {
  try {
    if (cached && Date.now() - cacheTime < CACHE_TTL) {
      return NextResponse.json({ success: true, data: cached, count: cached.length, cached: true });
    }
    const resp = await fetch(XUANXIAO_URL, {
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "text/html" },
    });
    const html = await resp.text();
    const data = extractUnis(html);
    cached = data;
    cacheTime = Date.now();
    return NextResponse.json({ success: true, data, count: data.length });
  } catch (err: any) {
    if (cached) return NextResponse.json({ success: true, data: cached, count: cached.length, cached: true, stale: true });
    return NextResponse.json({ success: false, error: err.message }, { status: 502 });
  }
}
