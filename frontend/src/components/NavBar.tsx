"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, Menu, X } from "lucide-react";
import { useState } from "react";

const NAV_LINKS = [
  { href: "/map",        label: "留学地图" },
  { href: "/calculator", label: "留学计算器" },
  { href: "/match",      label: "自主测验" },
  { href: "/assessment", label: "AI 学校评估" },
  { href: "/portfolio",  label: "AI 清单分析" },
  { href: "/news",       label: "留学资讯" },
];

export default function NavBar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-line/60 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6">
        {/* Logo */}
        <Link href="/" className="flex shrink-0 items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-ink text-panel shadow-sm">
            <Compass size={17} />
          </div>
          <span className="text-base font-bold tracking-tight text-ink">PathOS</span>
        </Link>

        {/* Desktop Nav - flat parallel */}
        <nav className="hidden items-center gap-0.5 md:flex">
          {NAV_LINKS.map((link) => {
            const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href as any}
                className={
                  "rounded-md px-3 py-1.5 text-sm font-medium transition-colors " +
                  (isActive
                    ? "bg-ink/10 text-ink"
                    : "text-ink/50 hover:bg-ink/5 hover:text-ink/80")
                }
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right area */}
        <div className="ml-auto flex items-center gap-3">
          <Link
            href="/match"
            className="hidden rounded-lg bg-ink px-4 py-1.5 text-sm font-semibold text-panel shadow-sm transition hover:bg-ink/90 sm:inline-flex"
          >
            开始自主测验
          </Link>
          {/* Mobile menu toggle */}
          <button
            onClick={() => setOpen(!open)}
            className="grid h-8 w-8 place-items-center rounded-lg text-ink/56 hover:bg-ink/5 md:hidden"
          >
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {/* Mobile nav */}
      {open && (
        <nav className="border-t border-line/40 bg-panel px-4 py-3 md:hidden">
          <div className="flex flex-col gap-1">
            {NAV_LINKS.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href as any}
                  onClick={() => setOpen(false)}
                  className={
                    "rounded-lg px-3 py-2 text-sm font-medium transition-colors " +
                    (isActive ? "bg-ink/8 text-ink" : "text-ink/56 hover:bg-ink/5")
                  }
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}
