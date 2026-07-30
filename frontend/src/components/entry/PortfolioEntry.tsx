import Link from "next/link";
import { ArrowRight, Bot } from "lucide-react";
import { EntryChrome } from "./EntryChrome";
import styles from "./PortfolioEntry.module.css";

export function PortfolioEntry() {
  return (
    <EntryChrome
      sectionLabel="AI PORTFOLIO REVIEW"
      systemLabel="STRUCTURE MODEL / 04"
      tone="ai"
      footer={
        <Link href="/portfolio" className={styles.cta}>
          <Bot size={17} strokeWidth={1.5} aria-hidden="true" />
          进入 AI 清单分析
          <ArrowRight size={16} strokeWidth={1.5} aria-hidden="true" />
        </Link>
      }
    >
      <div className={styles.environment} aria-hidden="true">
        <div className={styles.grid} />
        <div className={styles.horizon} />
        <div className={styles.orbitOne} />
        <div className={styles.orbitTwo} />
      </div>

      <section className={styles.stage} aria-labelledby="portfolio-entry-title">
        <div className={styles.copy}>
          <p>AI PORTFOLIO REVIEW / STRUCTURE MODEL</p>
          <h1 id="portfolio-entry-title">让 AI 审视你的选校结构</h1>
          <span>识别冲刺、匹配与保底结构中的风险与下一步行动</span>
        </div>

        <div className={styles.robot} role="img" aria-label="缓慢扫描的抽象 AI 机器人">
          <div className={styles.shoulders} aria-hidden="true" />
          <div className={styles.neck} aria-hidden="true" />
          <div className={styles.head} aria-hidden="true">
            <span className={styles.templeLeft} />
            <span className={styles.templeRight} />
            <span className={styles.facePlate} />
            <span className={styles.eyeLeft} />
            <span className={styles.eyeRight} />
            <span className={styles.mouth} />
          </div>
          <div className={styles.scanBeam} aria-hidden="true" />
        </div>

        <dl className={styles.structure}>
          <div>
            <dt>REACH</dt>
            <dd>冲刺</dd>
          </div>
          <div>
            <dt>TARGET</dt>
            <dd>匹配</dd>
          </div>
          <div>
            <dt>SAFETY</dt>
            <dd>保底</dd>
          </div>
        </dl>
      </section>
    </EntryChrome>
  );
}
