// Stage 7B-A.3.3 — News Credits route.
//
// Public route that lists the 9 campus photographs used in the
// `/news` hero with full attribution. Required by §十 of the
// directive. Keeps the credits accessible from a stable URL so
// they are reachable from search engines and from the bottom of
// every `/news` page.

import NewsCreditsPage from "@/components/news/NewsCreditsPage";

export const metadata = {
  title: "校园摄影来源与授权 · PathOS",
  description: "PathOS /news 入口动画中所使用的 9 张校园摄影的来源、摄影师与许可协议。",
};

export default function Page() {
  return <NewsCreditsPage />;
}
