import type { Metadata } from "next";
import { MapEntry } from "@/components/entry/MapEntry";

export const metadata: Metadata = {
  title: "留学地图入口",
  description: "进入 PathOS 真实 Preview 数据驱动的留学地图。",
};

export default function MapEntryPage() {
  return <MapEntry />;
}
