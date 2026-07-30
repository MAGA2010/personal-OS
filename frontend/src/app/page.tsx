import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowUpRight,
  BookmarkCheck,
  Calculator,
  ClipboardCheck,
  Map,
  Newspaper,
  SlidersHorizontal,
} from "lucide-react";
import { FlipModuleCard } from "@/components/home/FlipModuleCard";
import styles from "./home.module.css";

export const metadata: Metadata = {
  title: "PathOS — 面向中国家庭的留学选校数据平台",
  description:
    "以可追溯的院校与州级数据，连接留学地图、测评、预算和申请规划。",
};

const CORE_MODULES = [
  {
    index: "01",
    title: "留学地图",
    eyebrow: "EXPLORE",
    description: "在真实 Preview 数据上查看院校与四项州级区域指标。",
    reveal: "打开地图章节，在真实 Preview 数据上探索院校与四项州级区域指标。",
    href: "/entry/map",
    icon: Map,
  },
  {
    index: "02",
    title: "费用计算",
    eyebrow: "BUDGET",
    description: "比较院校费用信息，未报告字段保持缺失语义。",
    reveal: "核对院校费用信息与预算区间，未报告内容始终保持缺失语义。",
    href: "/calculator",
    icon: Calculator,
  },
  {
    index: "03",
    title: "自主匹配",
    eyebrow: "MATCH",
    description: "用可调整的个人偏好，建立清晰、可解释的选校参考。",
    reveal: "调整你的偏好与权重，建立清晰、可解释的自主匹配参考。",
    href: "/entry/match",
    icon: SlidersHorizontal,
  },
  {
    index: "04",
    title: "学校评估",
    eyebrow: "ASSESS",
    description: "整理学生画像与目标院校之间需要进一步核实的问题。",
    reveal: "输入学生画像与目标院校，让 AI 梳理风险和需要继续核实的问题。",
    href: "/entry/assessment",
    icon: ClipboardCheck,
  },
  {
    index: "05",
    title: "申请清单",
    eyebrow: "PORTFOLIO",
    description: "从冲刺、匹配与保底结构审视候选院校组合。",
    reveal: "让 AI 从冲刺、匹配与保底结构审视你的候选院校组合。",
    href: "/entry/portfolio",
    icon: BookmarkCheck,
  },
  {
    index: "06",
    title: "留学资讯",
    eyebrow: "JOURNAL",
    description: "进入 PathOS 的编辑式资讯入口，追踪申请与校园动态。",
    reveal: "翻开 PathOS Journal，追踪申请趋势、院校动态与真实校园影像。",
    href: "/news",
    icon: Newspaper,
  },
] as const;

const VERIFIED_BOUNDARY = [
  ["62", "所院校"],
  ["904", "条已验证记录"],
  ["51", "个州级辖区"],
  ["4", "项州级区域指标"],
] as const;

function WaveField() {
  const paths = Array.from({ length: 15 }, (_, index) => {
    const y = 58 + index * 14;
    const amplitude = 20 + index * 1.8;
    return `M -30 ${y} C 130 ${y - amplitude}, 245 ${y + amplitude}, 410 ${y} S 685 ${
      y - amplitude * 0.72
    }, 850 ${y} S 1120 ${y + amplitude}, 1470 ${y}`;
  });

  return (
    <svg
      className={styles.waveField}
      viewBox="0 0 1440 310"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {paths.map((path, index) => (
        <path key={index} d={path} />
      ))}
    </svg>
  );
}

export default function HomePage() {
  return (
    <main className={styles.root} data-integration-source="hybrid-visual-extraction">
      <section className={styles.hero} aria-labelledby="home-title">
        <div className={styles.heroEarth} aria-hidden="true" />
        <div className={styles.heroGrid} aria-hidden="true" />
        <WaveField />

        <div className={styles.heroFrame}>
          <div className={styles.heroRail}>
            <span>STUDY ABROAD DECISION SYSTEM</span>
            <span>PREVIEW / 2026</span>
          </div>

          <div className={styles.heroBody}>
            <div className={styles.bracketLeft} aria-hidden="true" />
            <p className={styles.kicker}>PATHOS / 路径与选择</p>
            <h1 id="home-title" className={styles.wordmark}>
              PathOS
            </h1>
            <p className={styles.heroStatement}>
              为中国留学家庭建立一条
              <br />
              <span>更清晰、更可信的决策路径。</span>
            </p>
            <div className={styles.heroActions}>
              <Link href="/entry/map" className={styles.primaryAction}>
                探索留学地图 <ArrowUpRight aria-hidden="true" size={17} />
              </Link>
              <Link href="/entry/match" className={styles.secondaryAction}>
                开始自主匹配
              </Link>
            </div>
            <div className={styles.bracketRight} aria-hidden="true" />
          </div>

          <p className={styles.heroNote}>
            数据不是答案，而是让每一次家庭讨论更接近事实。
          </p>
        </div>
      </section>

      <section className={styles.boundary} aria-labelledby="boundary-title">
        <div className={styles.sectionHeading}>
          <p>VERIFIED PREVIEW</p>
          <h2 id="boundary-title">从可信边界开始，而不是从承诺开始。</h2>
          <p className={styles.sectionLead}>
            PathOS 将已验证事实、待补充信息与暂未开放能力明确区分。
          </p>
        </div>

        <dl className={styles.statGrid}>
          {VERIFIED_BOUNDARY.map(([value, label]) => (
            <div key={label} className={styles.statItem}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>

        <p className={styles.previewNotice}>
          Preview · 数据来源可追溯 · 结果不构成录取保证
        </p>
      </section>

      <section className={styles.modules} aria-labelledby="modules-title">
        <div className={styles.sectionHeading}>
          <p>ONE SYSTEM / DISTINCT CHAPTERS</p>
          <h2 id="modules-title">把复杂选择拆成可以行动的六个章节。</h2>
        </div>

        <div className={styles.moduleGrid}>
          {CORE_MODULES.map((module) => {
            const Icon = module.icon;
            return (
              <FlipModuleCard
                key={module.href}
                index={module.index}
                eyebrow={module.eyebrow}
                title={module.title}
                description={module.description}
                reveal={module.reveal}
                href={module.href}
                icon={<Icon aria-hidden="true" size={24} />}
              />
            );
          })}
        </div>
      </section>
    </main>
  );
}
