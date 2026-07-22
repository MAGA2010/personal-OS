const fs = require("fs");
const path = require("path");

const CATEGORY_MAP = {
  "studying-abroad": "admissions", "careers-advice": "career",
  "choosing-university": "admissions", "scholarship-advice": "admissions",
  "university-news": "life", "where-to-study": "life",
  "courses": "admissions", "rankings-articles": "ranking",
};

async function fetchSitemap() {
  const resp = await fetch("https://xuanxiao.org/sitemaps/articles.xml", {
    headers: { "User-Agent": "Mozilla/5.0" }
  });
  const xml = await resp.text();
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
}

async function scrapeArticle(url) {
  const resp = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" }, signal: AbortSignal.timeout(10000) });
  const html = await resp.text();
  const title = (html.match(/<title>([^<]+)<\/title>/) || [])[1]?.replace(/ \| 选校$/, "").trim() || "";
  const desc = (html.match(/<meta[^>]*name="description"[^>]*content="([^"]*)"/) || [])[1] || "";
  const dateStr = (html.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/) || []);
  let isoDate = new Date().toISOString();
  if (dateStr) isoDate = dateStr[1] + "-" + dateStr[2].padStart(2,"0") + "-" + dateStr[3].padStart(2,"0") + "T00:00:00Z";
  const author = (html.match(/原作[：:]\s*([^<\n]{2,30})/) || [])[1] || "";
  const pageCat = (html.match(/articles\/category\/([^"\/]+)/) || [])[1] || "studying-abroad";
  return { title, titleEn: title, summary: desc.substring(0, 400), source: "选校 · " + (author || "QS"), url, publishedAt: isoDate, category: CATEGORY_MAP[pageCat] || "admissions" };
}

async function main() {
  const args = process.argv.slice(2);
  const count = parseInt(args[0]) || 100;
  const startFrom = parseInt(args[1]) || 0;
  const outputPath = args[2] || path.join(__dirname, "..", "frontend", "src", "data", "news.json");
  
  console.log("Fetching sitemap...");
  const allUrls = await fetchSitemap();
  const toScrape = allUrls.filter(u => !u.includes("/en/") && u !== "https://xuanxiao.org/articles" && !u.includes("/category/"));
  const batch = toScrape.slice(startFrom, startFrom + count);
  
  console.log("Scraping " + batch.length + " articles (offset " + startFrom + ")...");
  const results = [];
  for (let i = 0; i < batch.length; i += 10) {
    const chunk = batch.slice(i, i + 10);
    const scraped = await Promise.all(chunk.map(u => scrapeArticle(u).catch(() => null)));
    scraped.forEach(a => { if (a) results.push(a); });
    process.stdout.write(".");
  }
  
  console.log("\nScraped " + results.length + " articles");
  
  // Merge with existing
  let existing = { articles: [] };
  if (fs.existsSync(outputPath)) {
    existing = JSON.parse(fs.readFileSync(outputPath, "utf-8"));
  }
  
  const existingUrls = new Set(existing.articles.map(a => a.url));
  let counter = existing.articles.length + 1;
  results.forEach(a => {
    if (!existingUrls.has(a.url)) {
      a.id = "xx-" + String(counter).padStart(3, "0");
      existing.articles.push(a);
      existingUrls.add(a.url);
      counter++;
    }
  });
  
  existing.articles.sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
  fs.writeFileSync(outputPath, JSON.stringify(existing, null, 2), "utf-8");
  console.log("Saved " + existing.articles.length + " total articles to " + outputPath);
}

main().catch(console.error);
