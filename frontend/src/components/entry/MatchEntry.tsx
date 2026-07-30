import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { EntryChrome } from "./EntryChrome";
import styles from "./MatchEntry.module.css";

const WAVES = [
  "M0 180 C130 104 224 260 356 184 S584 116 716 192 S942 266 1074 182 S1300 104 1440 180",
  "M0 244 C122 318 236 160 364 246 S590 326 718 236 S950 154 1082 250 S1310 326 1440 244",
  "M0 308 C136 226 238 390 372 300 S606 222 734 312 S964 392 1096 298 S1318 226 1440 308",
  "M0 118 C118 174 236 54 354 124 S590 186 706 112 S946 50 1074 130 S1318 176 1440 118",
] as const;

export function MatchEntry() {
  return (
    <EntryChrome
      sectionLabel="AUTONOMOUS MATCH"
      systemLabel="WEIGHT FIELD / 02"
      tone="data"
      footer={
        <Link href="/match" className={styles.cta}>
          点击进入自主匹配
          <ArrowRight size={16} strokeWidth={1.5} aria-hidden="true" />
        </Link>
      }
    >
      <div className={styles.environment} aria-hidden="true">
        <div className={styles.grid} />
        <svg
          className={styles.waves}
          viewBox="0 0 1440 430"
          preserveAspectRatio="none"
        >
          <g className={styles.waveRunner}>
            {WAVES.map((path, index) => (
              <g key={path}>
                <path
                  d={path}
                  pathLength={1}
                  className={styles.wave}
                  style={{ animationDelay: `${index * 160}ms` }}
                />
                {[0.16, 0.38, 0.61, 0.82].map((offset) => (
                  <circle
                    key={offset}
                    cx={1440 * offset}
                    cy={118 + index * 62}
                    r={index % 2 === 0 ? 3 : 2.4}
                    className={styles.node}
                    style={{ animationDelay: `${800 + (index + offset) * 220}ms` }}
                  />
                ))}
              </g>
            ))}
          </g>
        </svg>
      </div>

      <section className={styles.stage} aria-labelledby="match-entry-title">
        <p className={styles.kicker}>DEFINE YOUR DIMENSIONS</p>
        <h1 id="match-entry-title">定义你的选校维度</h1>
        <p className={styles.summary}>
          自主设定个人偏好权重，建立清晰、可解释的院校匹配参考。
        </p>
        <dl className={styles.metrics}>
          <div>
            <dt>01</dt>
            <dd>预算适配</dd>
          </div>
          <div>
            <dt>02</dt>
            <dd>排名目标</dd>
          </div>
          <div>
            <dt>03</dt>
            <dd>录取友好</dd>
          </div>
        </dl>
      </section>
    </EntryChrome>
  );
}
