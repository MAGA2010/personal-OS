import type { Metadata } from "next";
import { PortfolioEntry } from "@/components/entry/PortfolioEntry";

export const metadata: Metadata = {
  title: "申请清单入口",
  description: "进入 PathOS 的冲刺、匹配与保底清单结构分析。",
};

export default function PortfolioEntryPage() {
  return <PortfolioEntry />;
}
