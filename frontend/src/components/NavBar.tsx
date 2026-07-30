"use client";

// Stage 7A closing patch — the ONE authoritative global navigation.
//
// Rules this component enforces:
//   - 6 items total: 留学地图 / 留学计算器 / 自主测验 / AI 学校评估 /
//     AI 清单分析 / 留学资讯. No second tier.
//   - Active state uses the real Next.js pathname; only one route
//     can be active at a time.
//   - Logo + nav items live inside a `max-w-page` container and
//     flex-shrink so they don't overflow at 1024–1920px widths.
//   - Below `lg`, the nav collapses to a hamburger; an Escape
//     handler closes the drawer.
//   - The right-side CTA is hidden on mobile to free horizontal
//     space; the theme toggle is always visible.
//   - All buttons/links use the new design tokens (`h-control`,
//     `rounded-control`, `text-text-secondary`, …).

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";

const NAV_LINKS = [
  { href: "/entry/map",  label: "留学地图" },
  { href: "/calculator", label: "留学计算器" },
  { href: "/entry/match", label: "自主测验" },
  { href: "/entry/assessment", label: "AI 学校评估" },
  { href: "/entry/portfolio", label: "AI 清单分析" },
  { href: "/news",       label: "留学资讯" },
] as const;

function isPathActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  const canonicalHref = href.startsWith("/entry/") ? href.slice("/entry".length) : href;
  return (
    pathname === href ||
    pathname.startsWith(href + "/") ||
    pathname === canonicalHref ||
    pathname.startsWith(canonicalHref + "/")
  );
}

export default function NavBar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Close on Escape when the mobile menu is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // Close on route change.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <header
      role="banner"
      className="sticky top-0 z-50 h-nav border-b border-border-soft bg-surface-1/95 backdrop-blur supports-[backdrop-filter]:bg-surface-1/80 dark:bg-surface-1/90"
    >
      <div className="mx-auto flex h-nav w-full max-w-page items-center gap-3 px-4 sm:gap-4 sm:px-6">
        {/* Logo — shrink-0 protects it from being clipped on narrow widths */}
        <Link
          href="/"
          aria-label="PathOS 首页"
          className="flex shrink-0 items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring rounded"
        >
          <div className="grid h-8 w-8 place-items-center rounded-control bg-ink text-paper dark:bg-paper dark:text-ink">
            <Compass size={17} aria-hidden="true" />
          </div>
          <span className="hidden text-[15px] font-semibold tracking-tight text-text-primary sm:inline">
            PathOS
          </span>
        </Link>

        {/* Desktop nav */}
        <nav
          aria-label="主导航"
          className="hidden min-w-0 flex-1 items-center gap-0.5 lg:flex"
        >
          {NAV_LINKS.map((link) => {
            const active = isPathActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href as any}
                aria-current={active ? "page" : undefined}
                className={
                  "rounded-control px-2.5 py-1.5 text-[13px] font-medium transition-colors " +
                  (active
                    ? "bg-ink/8 text-text-primary"
                    : "text-text-secondary hover:bg-surface-muted hover:text-text-primary")
                }
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right cluster — always visible, including mobile */}
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <Link
            href="/entry/match"
            className="hidden h-control items-center gap-1.5 rounded-control bg-ink px-3 text-[13px] font-semibold text-paper transition hover:bg-ink/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring sm:inline-flex"
          >
            开始自主测验
          </Link>
          <ThemeToggle />
          <button
            type="button"
            aria-label={open ? "关闭菜单" : "打开菜单"}
            aria-expanded={open}
            aria-controls="mobile-nav-drawer"
            onClick={() => setOpen((v) => !v)}
            className="grid h-9 w-9 place-items-center rounded-control border border-border-soft bg-surface-1 text-text-secondary transition hover:border-cobalt/40 hover:text-cobalt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lg:hidden"
          >
            {open ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <nav
          id="mobile-nav-drawer"
          aria-label="主导航（移动端）"
          className="border-t border-border-soft bg-surface-1 px-4 py-3 lg:hidden"
        >
          <div className="flex flex-col gap-1">
            {NAV_LINKS.map((link) => {
              const active = isPathActive(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href as any}
                  aria-current={active ? "page" : undefined}
                  className={
                    "rounded-control px-3 py-2 text-[14px] font-medium transition-colors " +
                    (active
                      ? "bg-ink/8 text-text-primary"
                      : "text-text-secondary hover:bg-surface-muted hover:text-text-primary")
                  }
                >
                  {link.label}
                </Link>
              );
            })}
            <Link
              href="/entry/match"
              className="mt-2 inline-flex h-control items-center justify-center gap-1.5 rounded-control bg-ink px-3 text-[13px] font-semibold text-paper"
            >
              开始自主测验
            </Link>
          </div>
        </nav>
      )}
    </header>
  );
}
