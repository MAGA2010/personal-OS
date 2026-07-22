import Link from "next/link";
import type { Route } from "next";
import { ClipboardCheck, Sparkles, Map, Bookmark, Stethoscope, ArrowRight } from "lucide-react";

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
    step: "01",
    title: "建立学生画像",
    subtitle: "成绩、预算、专业与家庭偏好",
    icon: ClipboardCheck
  },
  {
    id: "match",
    href: "/match",
    step: "02",
    title: "智能匹配学校",
    subtitle: "按六大指标生成优先级",
    icon: Sparkles
  },
  {
    id: "map",
    href: "/map",
    step: "03",
    title: "地图验证环境",
    subtitle: "安全、就业、华人社区与成本",
    icon: Map
  },
  {
    id: "portfolio",
    href: "/portfolio",
    step: "04",
    title: "沉淀选校清单",
    subtitle: "管理、对比并导出方案",
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
                {index < STEPS.length - 1 && <ArrowRight size={12} className="hidden text-ink/18 sm:block" />}
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
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-cobalt/80">PathOS workflow</p>
          <h2 className="mt-1 text-lg font-semibold text-ink">从画像到选校单，一条连续决策路径</h2>
        </div>
        <Stethoscope size={20} className="hidden text-ink/28 sm:block" />
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        {STEPS.map((item, index) => {
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
              {index < STEPS.length - 1 && (
                <ArrowRight className="absolute -right-2 top-1/2 hidden h-4 w-4 -translate-y-1/2 rounded-full bg-panel text-ink/24 md:block" />
              )}
            </Link>
          );
        })}
      </div>
    </section>
  );
}
