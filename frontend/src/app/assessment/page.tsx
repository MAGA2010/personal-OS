"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ProductJourney } from "@/components/ProductJourney";
import { Sparkles, Save, GraduationCap, Target, Globe, Shield, TrendingUp, Users } from "lucide-react";

const STORAGE_KEY = "pathos_student_profile";

interface StudentProfile {
  nickname: string;
  grade: string;
  gpa: string;
  gpaScale: string;
  toefl: string;
  sat: string;
  targetMajor: string;
  targetDegree: string;
  budget: number;
  regions: string[];
  rankImp: number;
  safetyImp: number;
  employImp: number;
  communityImp: number;
  activities: string;
}

const DEFAULT_PROFILE: StudentProfile = {
  nickname: "", grade: "11", gpa: "", gpaScale: "4.0", toefl: "", sat: "",
  targetMajor: "", targetDegree: "bachelor", budget: 50,
  regions: [], rankImp: 3, safetyImp: 3, employImp: 3, communityImp: 3,
  activities: "",
};

const REGIONS = [
  { id: "northeast", label: "东北部 (NY/MA/PA)" },
  { id: "midwest", label: "中西部 (IL/MI/OH)" },
  { id: "south", label: "南部 (TX/FL/GA)" },
  { id: "west", label: "西部 (CA/WA/OR)" },
];

const LABELS_5 = ["不在乎", "较低", "中等", "重视", "非常重视"];

export default function AssessmentPage() {
  const [profile, setProfile] = useState<StudentProfile>(DEFAULT_PROFILE);
  const [saved, setSaved] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setProfile({ ...DEFAULT_PROFILE, ...JSON.parse(raw) });
    } catch {}
    setLoaded(true);
  }, []);

  const update = <K extends keyof StudentProfile>(key: K, value: StudentProfile[K]) => {
    setProfile((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleSave = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {}
  };

  const toggleRegion = (id: string) => {
    setProfile((prev) => ({
      ...prev,
      regions: prev.regions.includes(id)
        ? prev.regions.filter((r) => r !== id)
        : [...prev.regions, id],
    }));
    setSaved(false);
  };

  if (!loaded) return null;

  return (
    <div>
      <header className="border-b border-line bg-panel px-5 py-3">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-ink text-panel"><Sparkles size={18} /></div>
          <div>
            <h1 className="text-base font-semibold text-ink">学生画像</h1>
            <p className="text-xs text-ink/52">第 1 步：填写学生信息，生成个性化选校方案</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={handleSave} className="inline-flex items-center gap-1.5 rounded-md bg-ink px-3 py-1.5 text-xs font-medium text-panel transition-colors hover:bg-ink/90">
              <Save size={13} />{saved ? "已保存" : "保存画像"}
            </button>
            <Link href="/match" className="rounded-md border border-line/50 px-2.5 py-1.5 text-[11px] font-medium text-ink/60 transition-colors hover:bg-white hover:text-ink">智能匹配 →</Link>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 pt-4">
        <ProductJourney active="assessment" compact />
      </div>

      <main className="mx-auto max-w-4xl px-4 py-6">
        <form onSubmit={(e) => { e.preventDefault(); handleSave(); }} className="space-y-6">
          {/* 基本信息 */}
          <Section icon={<GraduationCap size={16} />} title="基本信息">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="称呼">
                <input type="text" value={profile.nickname} onChange={(e) => update("nickname", e.target.value)}
                  placeholder="如：小明" className="w-full rounded-md border border-line/60 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-cobalt/50" />
              </Field>
              <Field label="当前年级">
                <select value={profile.grade} onChange={(e) => update("grade", e.target.value)}
                  className="w-full rounded-md border border-line/60 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-cobalt/50">
                  <option value="9">初三 / Grade 9</option>
                  <option value="10">高一 / Grade 10</option>
                  <option value="11">高二 / Grade 11</option>
                  <option value="12">高三 / Grade 12</option>
                  <option value="freshman">大一 / Freshman</option>
                  <option value="sophomore">大二 / Sophomore</option>
                  <option value="junior">大三 / Junior</option>
                  <option value="senior">大四 / Senior</option>
                </select>
              </Field>
              <Field label="GPA">
                <input type="text" value={profile.gpa} onChange={(e) => update("gpa", e.target.value)}
                  placeholder="如：3.8" className="w-full rounded-md border border-line/60 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-cobalt/50" />
              </Field>
              <Field label="GPA 满分">
                <select value={profile.gpaScale} onChange={(e) => update("gpaScale", e.target.value)}
                  className="w-full rounded-md border border-line/60 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-cobalt/50">
                  <option value="4.0">4.0</option>
                  <option value="5.0">5.0</option>
                  <option value="100">100 分制</option>
                </select>
              </Field>
              <Field label="托福 / 雅思">
                <input type="text" value={profile.toefl} onChange={(e) => update("toefl", e.target.value)}
                  placeholder="如：105" className="w-full rounded-md border border-line/60 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-cobalt/50" />
              </Field>
              <Field label="SAT / ACT">
                <input type="text" value={profile.sat} onChange={(e) => update("sat", e.target.value)}
                  placeholder="如：1500" className="w-full rounded-md border border-line/60 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-cobalt/50" />
              </Field>
              <Field label="目标专业">
                <input type="text" value={profile.targetMajor} onChange={(e) => update("targetMajor", e.target.value)}
                  placeholder="如：计算机科学" className="w-full rounded-md border border-line/60 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-cobalt/50" />
              </Field>
              <Field label="目标学位">
                <select value={profile.targetDegree} onChange={(e) => update("targetDegree", e.target.value)}
                  className="w-full rounded-md border border-line/60 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-cobalt/50">
                  <option value="bachelor">本科 / Bachelor</option>
                  <option value="master">硕士 / Master</option>
                  <option value="phd">博士 / PhD</option>
                </select>
              </Field>
            </div>
          </Section>

          {/* 预算 */}
          <Section icon={<Target size={16} />} title="预算 (年预算 ￥万)">
            <input type="range" min={15} max={80} step={5} value={profile.budget}
              onChange={(e) => update("budget", Number(e.target.value))}
              className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-ink/10 accent-ink" />
            <div className="mt-1 flex justify-between text-xs text-ink/60">
              <span>￥15 万</span>
              <span className="font-semibold text-cobalt">￥{profile.budget} 万</span>
              <span>￥80 万</span>
            </div>
          </Section>

          {/* 地区偏好 */}
          <Section icon={<Globe size={16} />} title="地区偏好">
            <div className="flex flex-wrap gap-2">
              {REGIONS.map((r) => (
                <button key={r.id} type="button" onClick={() => toggleRegion(r.id)}
                  className={"rounded-md border px-2.5 py-1 text-xs font-medium transition-colors " +
                    (profile.regions.includes(r.id) ? "border-cobalt/40 bg-cobalt/10 text-cobalt" : "border-line/50 text-ink/50 hover:border-line")}
                >{r.label}</button>
              ))}
            </div>
          </Section>

          {/* 偏好权重 */}
          <Section icon={<Shield size={16} />} title="选校偏好权重">
            <p className="mb-3 text-xs text-ink/44">调整各项指标的重要程度，会直接影响智能匹配结果</p>
            <div className="grid gap-5 sm:grid-cols-2">
              <SliderField label="排名重视" value={profile.rankImp} onChange={(v) => update("rankImp", v)} />
              <SliderField label="安全要求" value={profile.safetyImp} onChange={(v) => update("safetyImp", v)} />
              <SliderField label="就业重视" value={profile.employImp} onChange={(v) => update("employImp", v)} />
              <SliderField label="华人社区" value={profile.communityImp} onChange={(v) => update("communityImp", v)} />
            </div>
          </Section>

          {/* 课外活动 */}
          <Section icon={<Globe size={16} />} title="课外活动">
            <textarea value={profile.activities} onChange={(e) => update("activities", e.target.value)}
              placeholder="如：学生会、辩论队、志愿者、科研项目等" rows={3}
              className="w-full resize-none rounded-md border border-line/60 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-cobalt/50" />
          </Section>

          {/* 保存 */}
          <div className="flex items-center justify-between rounded-xl border border-line/50 bg-white/90 p-4 shadow-sm">
            <div>
              <p className="text-sm font-semibold text-ink">保存后去智能匹配</p>
              <p className="text-xs text-ink/44">画像会被保存到本地，匹配页面会自动读取你的偏好</p>
            </div>
            <div className="flex items-center gap-3">
              <button type="submit" className="inline-flex items-center gap-2 rounded-lg bg-ink px-5 py-2.5 text-sm font-semibold text-panel transition hover:bg-ink/90">
                <Save size={15} />{saved ? "已保存 ✓" : "保存画像"}
              </button>
              <Link href="/match" className="inline-flex items-center gap-1 rounded-lg border border-line/50 px-4 py-2.5 text-sm font-medium text-ink/60 transition hover:bg-white hover:text-ink">
                匹配 →</Link>
            </div>
          </div>
        </form>
      </main>
    </div>
  );
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line/50 bg-white/90 p-4 shadow-sm">
      <div className="mb-4 flex items-center gap-2 border-b border-line/30 pb-3">
        <span className="text-cobalt">{icon}</span>
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-ink/56">{label}</label>
      {children}
    </div>
  );
}

function SliderField({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-ink/60">{label}</span>
        <span className="font-medium tabular-nums text-ink/80">{LABELS_5[value - 1]}</span>
      </div>
      <input type="range" min={1} max={5} step={1} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-ink/10 accent-ink" />
      <div className="mt-0.5 flex justify-between text-[9px] text-ink/30"><span>不在乎</span><span>非常重视</span></div>
    </div>
  );
}