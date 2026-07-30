import Link from "next/link";
import { Compass, Github } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-line/50 bg-ink/95 text-panel/70">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <div className="grid gap-8 sm:grid-cols-3">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2">
              <div className="grid h-8 w-8 place-items-center rounded-lg bg-panel/15 text-panel">
                <Compass size={16} />
              </div>
              <span className="text-base font-bold text-panel">PathOS</span>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-panel/60">
              面向中国家庭的留学选校数据平台。<br />
              数据驱动，让选校更理性。
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="mb-3 text-sm font-semibold text-panel/85">平台功能</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <Link href="/entry/map" className="transition-colors hover:text-panel">留学地图</Link>
              <Link href="/calculator" className="transition-colors hover:text-panel">留学计算器</Link>
              <Link href="/entry/match" className="transition-colors hover:text-panel">自主测验</Link>
              <Link href="/entry/assessment" className="transition-colors hover:text-panel">AI 学校评估</Link>
              <Link href="/entry/portfolio" className="transition-colors hover:text-panel">AI 清单分析</Link>
              <Link href="/news" className="transition-colors hover:text-panel">留学资讯</Link>
            </div>
          </div>

          {/* About */}
          <div>
            <h3 className="mb-3 text-sm font-semibold text-panel/85">关于</h3>
            <div className="flex flex-col gap-2 text-sm">
              <span className="text-panel/60">PathOS MVP · 2026</span>
              <span className="text-panel/60">数据来源可追溯 · Preview / Demo</span>
              <a
                href="https://github.com/MAGA2010/PathOS"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-panel/60 transition-colors hover:text-panel"
              >
                <Github size={14} /> GitHub
              </a>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-panel/10 pt-6 text-center text-xs text-panel/40">
          PathOS — 面向中国家庭的留学选校决策平台
        </div>
      </div>
    </footer>
  );
}
