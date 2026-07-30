import type { Metadata } from "next";
import { AssessmentEntry } from "@/components/entry/AssessmentEntry";

export const metadata: Metadata = {
  title: "学校评估入口",
  description: "进入 PathOS 基于真实 Preview 数据边界的学校评估。",
};

export default function AssessmentEntryPage() {
  return <AssessmentEntry />;
}
