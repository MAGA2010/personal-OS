import type { Metadata } from "next";
import { MatchEntry } from "@/components/entry/MatchEntry";

export const metadata: Metadata = {
  title: "自主匹配入口",
  description: "进入 PathOS 可解释的自主匹配体验。",
};

export default function MatchEntryPage() {
  return <MatchEntry />;
}
