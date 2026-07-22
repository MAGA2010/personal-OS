import Link from "next/link";
import type { Route } from "next";
import { ClipboardCheck, Sparkles, Map, Bookmark, Stethoscope } from "lucide-react";

export type JourneyStepId = "assessment" | "match" | "map" | "portfolio";

const STEPS: Array<{
  id: JourneyStepId;
  href: Route;
  step: string;
  title: string;
  subtitle: string;
  icon: typeof ClipboardCheck;
}> = [
  {
    id: "assessment",
    href: "/assessment",
    step: "AI-A",
    title: "AI 学校评估",
    subtitle: "上传画像与目标校，调用 AI 做风险体检",
    icon: ClipboardCheck
  },
  {
    id: "match",
    href: "/match",
    step: "SELF",
    title: "自主测验",
    subtitle: "学生自行拉取百分比与权重，匹配学校百分比",
    icon: Sparkles
  },
  {
    id: "map",
    href: "/map",
    step: "MAP",
    title: "地图验证环境",
    subtitle: "安全、就业、华人社区与成本",
    icon: Map
  },
  {
    id: "portfolio",
    href: "/portfolio",
    step: "AI-B",
    title: "AI 清单分析",
    subtitle: "分析冲刺、匹配、保底比例与家庭问题",
    icon: Bookmark
  }
];

export function ProductJourney({
  active,
  compact = false,
  className = ""
}: {
  active?: JourneyStepId;
  compact?: boolean;
  className?: string;
}) {
  if (compact) {
    return (
      <nav aria-label="PathOS 产品流程" className={className}>
        <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-line/50 bg-white/75 p-1.5 shadow-sm">
          {STEPS.map((item, index) => {
            const Icon = item.icon;
            const isActive = item.id === active;
            return (
              <div key={item.id} className="flex items-center gap-1.5">
                <Link
                  href={item.href}
                  className={
                    "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition-colors " +
                    (isActive
                      ? "bg-ink text-panel shadow-sm"
                      : "text-ink/56 hover:bg-paper hover:text-ink")
                  }
                >
                  <Icon size={13} />
                  <span>{item.step}</span>
                  <span className="hidden sm:inline">{item.title}</span>
                </Link>
              </div>
            );
          })}
        </div>
      </nav>
    );
  }

  return (
    <section className={"rounded-2xl border border-line/60 bg-panel p-4 shadow-sm sm:p-5 " + className}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-cobalt/80">PathOS parallel tests</p>
          <h2 className="mt-1 text-lg font-semibold text-ink">自主测验与 AI 测验并行，结果互相校验</h2>
        </div>
        <Stethoscope size={20} className="hidden text-ink/28 sm:block" />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        {STEPS.map((item) => {
          const Icon = item.icon;
          const isActive = item.id === active;
          return (
            <Link
              key={item.id}
              href={item.href}
              className={
                "group relative rounded-xl border p-4 transition-all hover:-translate-y-0.5 hover:shadow-md " +
                (isActive
                  ? "border-ink/30 bg-ink text-panel"
                  : "border-line/50 bg-white/80 hover:border-cobalt/35")
              }
            >
              <div className="mb-3 flex items-center justify-between">
                <span className={"text-[11px] font-semibold " + (isActive ? "text-panel/60" : "text-ink/32")}>{item.step}</span>
                <div className={"grid h-8 w-8 place-items-center rounded-lg " + (isActive ? "bg-panel/15" : "bg-paper text-ink/60 group-hover:text-cobalt")}>
                  <Icon size={16} />
                </div>
              </div>
              <h3 className="text-sm font-semibold">{item.title}</h3>
              <p className={"mt-1 text-xs leading-relaxed " + (isActive ? "text-panel/60" : "text-ink/48")}>{item.subtitle}</p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
