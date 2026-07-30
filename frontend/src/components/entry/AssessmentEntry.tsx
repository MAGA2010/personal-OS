"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { usePrefersReducedMotion } from "@/components/news/usePrefersReducedMotion";
import { EntryChrome } from "./EntryChrome";
import styles from "./AssessmentEntry.module.css";

const CAMPUSES = [
  {
    id: "harvard",
    name: "哈佛大学",
    nameEn: "Harvard University",
    location: "Cambridge, Massachusetts",
    image: "/news/campus/harvard-yard.webp",
  },
  {
    id: "mit",
    name: "麻省理工学院",
    nameEn: "Massachusetts Institute of Technology",
    location: "Cambridge, Massachusetts",
    image: "/news/campus/mit-great-dome.webp",
  },
  {
    id: "stanford",
    name: "斯坦福大学",
    nameEn: "Stanford University",
    location: "Stanford, California",
    image: "/news/campus/stanford-main-quad.webp",
  },
] as const;

export function AssessmentEntry() {
  const [active, setActive] = useState(0);
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    if (reducedMotion) return;
    const interval = window.setInterval(() => {
      setActive((current) => (current + 1) % CAMPUSES.length);
    }, 6000);
    return () => window.clearInterval(interval);
  }, [reducedMotion]);

  const campus = CAMPUSES[active];

  return (
    <EntryChrome
      sectionLabel="AI SCHOOL ASSESSMENT"
      systemLabel="EDITORIAL FIELD / 03"
      tone="editorial"
      footer={
        <Link href="/assessment" className={styles.cta}>
          进入学校评估
          <ArrowRight size={16} strokeWidth={1.5} aria-hidden="true" />
        </Link>
      }
    >
      <section className={styles.stage} aria-labelledby="assessment-entry-title">
        <div className={styles.copy}>
          <p className={styles.kicker}>PATHOS · SCHOOL ASSESSMENT</p>
          <h1 id="assessment-entry-title">
            重新审视
            <br />
            <em>你的美国本科选校</em>
          </h1>
          <p className={styles.summary}>
            将学生画像与目标院校放在同一套可追溯数据边界中，整理下一步需要核实的问题。
          </p>
        </div>

        <div
          className={styles.carousel}
          data-reduced-motion={reducedMotion ? "true" : "false"}
          aria-label="已授权美国大学校园摄影"
        >
          {CAMPUSES.map((item, index) => (
            <div
              key={item.id}
              className={`${styles.slide} ${index === active ? styles.slideActive : ""}`}
              aria-hidden={index !== active}
            >
              <Image
                src={item.image}
                alt={`${item.name}校园`}
                fill
                priority={index === 0}
                sizes="(max-width: 720px) 94vw, (max-width: 1200px) 82vw, 1120px"
                className={styles.image}
              />
            </div>
          ))}
          <div className={styles.vignette} aria-hidden="true" />
          <div className={styles.scan} aria-hidden="true" />
          <div className={styles.glow} aria-hidden="true" />

          <div className={styles.badge}>
            <span aria-hidden="true" />
            LOCAL · LICENSED CAMPUS PHOTOGRAPHY
          </div>

          <div className={styles.counter} aria-label={`第 ${active + 1} 张，共 ${CAMPUSES.length} 张`}>
            <strong>{String(active + 1).padStart(2, "0")}</strong>
            <span>/</span>
            <small>{String(CAMPUSES.length).padStart(2, "0")}</small>
          </div>

          <div className={styles.meta}>
            <p>{campus.name}</p>
            <span>{campus.nameEn}</span>
            <span>{campus.location}</span>
          </div>

          <div className={styles.dots} aria-label="选择校园摄影">
            {CAMPUSES.map((item, index) => (
              <button
                key={item.id}
                type="button"
                aria-label={`显示${item.name}校园`}
                aria-pressed={index === active}
                onClick={() => setActive(index)}
                className={index === active ? styles.dotActive : styles.dot}
              />
            ))}
          </div>
        </div>
      </section>
    </EntryChrome>
  );
}
