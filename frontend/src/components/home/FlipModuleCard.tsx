"use client";

import Link from "next/link";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import styles from "@/app/home.module.css";

interface FlipModuleCardProps {
  index: string;
  eyebrow: string;
  title: string;
  description: string;
  reveal: string;
  href: string;
  icon: ReactNode;
}

export function FlipModuleCard({
  index,
  eyebrow,
  title,
  description,
  reveal,
  href,
  icon,
}: FlipModuleCardProps) {
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    if (!flipped) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setFlipped(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [flipped]);

  return (
    <article className={styles.moduleCard} data-flipped={flipped ? "true" : "false"}>
      <div className={`${styles.moduleCardInner} ${flipped ? styles.moduleCardFlipped : ""}`}>
        <button
          type="button"
          className={`${styles.moduleFace} ${styles.moduleFront}`}
          onClick={() => setFlipped(true)}
          aria-pressed={flipped}
          aria-label={`开启${title}章节卡片`}
          tabIndex={flipped ? -1 : 0}
        >
          <span className={styles.moduleMeta}>
            <span>{index}</span>
            <span>{eyebrow}</span>
          </span>
          <span className={styles.moduleIcon}>{icon}</span>
          <span className={styles.moduleTitle}>{title}</span>
          <span className={styles.moduleDescription}>{description}</span>
          <span className={styles.moduleLink}>
            点击开启 <ArrowUpRight aria-hidden="true" size={15} />
          </span>
        </button>

        <div className={`${styles.moduleFace} ${styles.moduleBack}`} aria-hidden={!flipped}>
          <span className={styles.moduleMeta}>
            <span>{index}</span>
            <span>UNLOCKED</span>
          </span>
          <span className={styles.moduleBackLabel}>PATHOS CHAPTER</span>
          <h3>{title}</h3>
          <p>{reveal}</p>
          <div className={styles.moduleBackActions}>
            <Link href={href} className={styles.moduleEnter} tabIndex={flipped ? 0 : -1}>
              进入章节 <ArrowUpRight aria-hidden="true" size={15} />
            </Link>
            <button
              type="button"
              className={styles.moduleReset}
              onClick={() => setFlipped(false)}
              tabIndex={flipped ? 0 : -1}
            >
              <ArrowLeft aria-hidden="true" size={14} /> 翻回正面
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}
