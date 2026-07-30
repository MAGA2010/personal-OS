import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { EntryChrome } from "./EntryChrome";
import styles from "./MapEntry.module.css";

export function MapEntry() {
  return (
    <EntryChrome
      sectionLabel="ORBITAL DATA SERIES"
      systemLabel="MAP ENVIRONMENT / 01"
      tone="space"
      footer={
        <Link href="/map" className={styles.cta}>
          <span>
            <strong>进入地图</strong>
            <small>ENTER MAP SYSTEM</small>
          </span>
          <ArrowRight size={18} strokeWidth={1.5} aria-hidden="true" />
        </Link>
      }
    >
      <div className={styles.environment} aria-hidden="true">
        <Image
          src="/entry/pathos-earth-from-orbit.jpg"
          alt=""
          fill
          priority
          sizes="100vw"
          className={styles.earth}
        />
        <div className={styles.wash} />
        <div className={styles.scan} />
      </div>

      <section className={styles.stage} aria-labelledby="map-entry-title">
        <aside className={`${styles.stat} ${styles.statLeft}`}>
          <span>01</span>
          <strong>4 项州级区域指标</strong>
          <small>VERIFIED METRICS</small>
        </aside>

        <div className={styles.title}>
          <p>EXPLORE THE</p>
          <span className={styles.rule} aria-hidden="true" />
          <h1 id="map-entry-title">MAP</h1>
          <span className={styles.rule} aria-hidden="true" />
          <p className={styles.subtitle}>交互式美国大学择校地图</p>
        </div>

        <aside className={`${styles.stat} ${styles.statRight}`}>
          <span>02</span>
          <strong>51 个州级辖区</strong>
          <small>REGIONAL NETWORK</small>
        </aside>
      </section>

      <p className={styles.credit}>
        NASA · S131-E-006087
        <span>EARTH OBSERVATION · 2010</span>
      </p>
    </EntryChrome>
  );
}
