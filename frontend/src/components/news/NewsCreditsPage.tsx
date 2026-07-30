// Stage 7B-A.3.3 — public photography credits, generated from the
// same machine-readable record that is verified against local files.

import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import licenseData from "../../../docs/STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json";
import { NEWS_HERO_COLORS } from "./news-images";

export default function NewsCreditsPage() {
  return (
    <main
      data-testid="news-credits-page"
      className="mx-auto w-full max-w-5xl px-5 py-14 sm:px-8 md:py-20"
      style={{ color: NEWS_HERO_COLORS.text }}
    >
      <Link
        href="/news"
        data-testid="news-credits-back"
        className="inline-flex items-center gap-2 font-sans"
        style={{
          color: NEWS_HERO_COLORS.muted,
          fontSize: "11px",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
        }}
      >
        <ArrowLeft size={12} strokeWidth={1.5} aria-hidden="true" />
        返回留学资讯
      </Link>

      <h1
        className="mt-10 font-serif font-semibold"
        style={{
          color: NEWS_HERO_COLORS.title,
          fontSize: "clamp(32px, 6vw, 52px)",
          letterSpacing: "-0.01em",
        }}
      >
        校园摄影来源与授权
      </h1>
      <p
        className="mt-3 font-sans"
        style={{
          color: NEWS_HERO_COLORS.muted,
          fontSize: "11px",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
        }}
      >
        Campus Photography Credits
      </p>
      <p
        className="mt-6 max-w-2xl font-sans leading-relaxed"
        style={{ color: NEWS_HERO_COLORS.text, fontSize: "14px" }}
      >
        留学资讯入口使用的九张校园摄影均来自逐张核验的 Wikimedia
        Commons File 页面。PathOS 将原图等比例缩放并转换为 WebP；作者、
        原始页面、许可证和修改说明如下。
      </p>

      <div
        data-testid="news-credits-table"
        className="mt-10 grid gap-px overflow-hidden border sm:grid-cols-2"
        style={{
          borderColor: "rgba(146, 154, 146, 0.32)",
          backgroundColor: "rgba(146, 154, 146, 0.24)",
        }}
      >
        {licenseData.records.map((photo) => (
          <article
            key={photo.localFile}
            data-testid="news-credits-row"
            className="min-w-0 p-5"
            style={{ backgroundColor: NEWS_HERO_COLORS.bgSoft }}
          >
            <p
              className="font-sans"
              style={{
                color: NEWS_HERO_COLORS.muted,
                fontSize: "10px",
                letterSpacing: "0.16em",
              }}
            >
              {String(photo.id).padStart(2, "0")} / {photo.school}
            </p>
            <h2
              className="mt-3 font-serif text-xl"
              style={{ color: NEWS_HERO_COLORS.title }}
            >
              {photo.scene}
            </h2>
            <dl className="mt-5 grid gap-3 font-sans text-xs leading-relaxed">
              <div>
                <dt style={{ color: NEWS_HERO_COLORS.muted }}>摄影师</dt>
                <dd className="mt-1" style={{ color: NEWS_HERO_COLORS.text }}>
                  {photo.photographer}
                </dd>
              </div>
              <div>
                <dt style={{ color: NEWS_HERO_COLORS.muted }}>来源与许可证</dt>
                <dd className="mt-1 flex flex-wrap gap-x-4 gap-y-2">
                  <a
                    href={photo.sourcePage}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-1 underline"
                    style={{ color: NEWS_HERO_COLORS.accent }}
                  >
                    Wikimedia Commons File
                    <ExternalLink size={11} aria-hidden="true" />
                  </a>
                  <a
                    href={photo.licenseUrl}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="underline"
                    style={{ color: NEWS_HERO_COLORS.accent }}
                  >
                    {photo.licenseName}
                  </a>
                </dd>
              </div>
              <div>
                <dt style={{ color: NEWS_HERO_COLORS.muted }}>本地处理</dt>
                <dd className="mt-1" style={{ color: NEWS_HERO_COLORS.text }}>
                  {photo.cropDescription} {photo.colorAdjustment}
                </dd>
              </div>
            </dl>
            {photo.shareAlikeRequired ? (
              <p
                className="mt-4 font-sans"
                style={{
                  color: NEWS_HERO_COLORS.muted,
                  fontSize: "10px",
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                }}
              >
                ShareAlike applies
              </p>
            ) : null}
          </article>
        ))}
      </div>

      <div
        className="mt-12 p-4 font-sans"
        style={{
          border: `1px solid ${NEWS_HERO_COLORS.muted}`,
          color: NEWS_HERO_COLORS.muted,
          fontSize: "12px",
          lineHeight: 1.7,
        }}
      >
        <strong style={{ color: NEWS_HERO_COLORS.title }}>
          PathOS 不主张这些图片的版权。
        </strong>{" "}
        所有摄影版权与许可归各自作者及许可证约定；Public Domain 与 CC0
        作品也继续保留作者和来源。含 ShareAlike 条款的转换版本按相同或兼容
        许可证共享。
      </div>
    </main>
  );
}
