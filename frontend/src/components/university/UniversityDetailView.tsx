"use client";

// UniversityDetailView — the visible shell for /university/[id]. Lifted
// out of `page.tsx` so that route file can stay a server component
// (because `output: export` requires `generateStaticParams`).

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, GraduationCap, MapPin } from "lucide-react";
import { useDataSource } from "@/services/data-source-provider";
import { useStatusDictionary, useUniversityDetail } from "@/hooks/use-data-source";
import { UniversityProfilePanel } from "@/components/university/UniversityProfilePanel";
import {
  DataLoadingState,
  DataEmptyState,
  PreviewErrorState,
  PreviewWarningBanner,
} from "@/components/shared/data-states";

export function UniversityDetailView() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";
  const source = useDataSource();
  const detail = useUniversityDetail(source, id);
  const dict = useStatusDictionary(source);
  const router = useRouter();

  if (detail.state.status === "loading") {
    return (
      <main className="mx-auto max-w-4xl px-4 py-12" aria-busy="true">
        <DataLoadingState message="正在加载学校档案…" />
      </main>
    );
  }

  if (detail.state.status === "error") {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16">
        <PreviewErrorState
          code={detail.state.code}
          onRetry={() => detail.reload()}
        />
        <Link
          href="/map"
          className="mt-6 inline-block rounded-lg bg-cobalt px-4 py-1.5 text-sm text-white"
        >
          返回地图
        </Link>
      </main>
    );
  }

  if (detail.state.status === "ready" && detail.state.data == null) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16">
        <DataEmptyState
          title="未找到该学校"
          description={
            <>
              编号 <span className="font-mono">{id}</span> 当前不在数据集中。
            </>
          }
          action={
            <Link
              href="/map"
              className="rounded-md border border-line/60 bg-panel px-2.5 py-1 text-xs font-medium text-ink/70 hover:border-cobalt/40 hover:text-cobalt"
            >
              返回地图
            </Link>
          }
        />
      </main>
    );
  }

  if (detail.state.status !== "ready" || !detail.state.data) {
    return null;
  }

  const d = detail.state.data;
  const dictionary = dict.state.status === "ready" ? dict.state.data : undefined;

  return (
    <main className="mx-auto max-w-6xl px-4 pb-16 pt-6 lg:max-w-7xl">
      <nav className="mb-4 flex items-center justify-between gap-2 text-sm text-ink/60">
        <Link
          href="/map"
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 hover:bg-ink/8"
        >
          <ArrowLeft size={14} aria-hidden="true" />
          <span>返回地图</span>
        </Link>
        <button
          type="button"
          onClick={() => router.back()}
          className="rounded-md px-2 py-1 text-[11px] text-ink/44 hover:bg-ink/8"
        >
          返回上一页
        </button>
      </nav>

      <header className="rounded-xl border border-line bg-panel px-6 py-5">
        <p className="text-[10px] uppercase tracking-wide text-ink/44">
          <GraduationCap size={11} className="mr-1 inline" aria-hidden="true" />
          学校详情
          <span className="ml-1.5 text-ink/32" lang="en">
            University Detail
          </span>
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-ink">{d.chineseName}</h1>
        <p className="mt-0.5 text-sm text-ink/60" lang="en">
          {d.name}
        </p>
        <p className="mt-2 flex items-center gap-1 text-[12px] text-ink/52">
          <MapPin size={11} aria-hidden="true" />
          {d.city}, {d.state}, {d.country}
          {d.rankingBand && (
            <span className="ml-3 inline-flex items-center rounded-full bg-ink/8 px-2 py-0.5 text-[10px] font-medium text-ink/64">
              {d.rankingBand}
            </span>
          )}
        </p>
        {d.previewOnly && (
          <div className="mt-3">
            <PreviewWarningBanner detail="当前展示字段来自约束预览集;后端生产接口上线后将自动切换为完整档案。" />
          </div>
        )}
      </header>

      <UniversityProfilePanel detail={d} statusDictionary={dictionary} />
    </main>
  );
}
