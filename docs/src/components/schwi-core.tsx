// 機凱種（Ex-Machina）的核心：外圈是轉動的回路環，中間是一顆在跳的心。
// 修比一直想弄懂的就是「心」，agent loop 每跑一圈，就離答案近一點。

const CENTER = 260;

// 固定種子的亂數，伺服器和瀏覽器算出同一張圖，避免 hydration 不一致
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const random = mulberry32(207);

function polar(radius: number, angle: number) {
  return {
    x: Number((CENTER + radius * Math.cos(angle)).toFixed(2)),
    y: Number((CENTER + radius * Math.sin(angle)).toFixed(2)),
  };
}

// 外圈刻度：每 5 格一根長刻度
const ticks = Array.from({ length: 120 }, (_, i) => {
  const angle = (i / 120) * Math.PI * 2;
  const long = i % 5 === 0;
  const inner = polar(long ? 214 : 220, angle);
  const outer = polar(228, angle);
  return { id: i, x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y, long };
});

// 回路：從中間往外的折線，末端一個節點
const traces = Array.from({ length: 14 }, (_, i) => {
  const angle = (i / 14) * Math.PI * 2 + random() * 0.2;
  const bend = angle + (random() - 0.5) * 0.5;
  const start = polar(96, angle);
  const mid = polar(130 + random() * 20, angle);
  const end = polar(168 + random() * 26, bend);
  return {
    id: i,
    d: `M${start.x} ${start.y} L${mid.x} ${mid.y} L${end.x} ${end.y}`,
    end,
  };
});

// 心形，中心在 (0, 0)，寬約 2 個單位
const HEART =
  "M0 0.9 C-0.9 0.3 -1.1 -0.3 -0.8 -0.7 C-0.5 -1.05 -0.1 -0.9 0 -0.55 C0.1 -0.9 0.5 -1.05 0.8 -0.7 C1.1 -0.3 0.9 0.3 0 0.9 Z";

export function SchwiCore({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`relative aspect-square text-fd-primary ${className ?? ""}`}
    >
      <div className="absolute inset-[22%] rounded-full bg-fd-primary/20 blur-3xl" />
      <svg
        viewBox="0 0 520 520"
        className="relative size-full"
        aria-hidden="true"
      >
        <g className="origin-[260px_260px] motion-safe:animate-[spin_60s_linear_infinite]">
          {ticks.map((t) => (
            <line
              key={t.id}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke="currentColor"
              strokeOpacity={t.long ? 0.7 : 0.3}
              strokeWidth={t.long ? 1.5 : 1}
            />
          ))}
        </g>

        <circle
          cx={CENTER}
          cy={CENTER}
          r={200}
          fill="none"
          stroke="var(--color-circuit)"
          strokeOpacity={0.5}
          strokeDasharray="2 6"
        />

        <g className="origin-[260px_260px] motion-safe:animate-[spin_30s_linear_infinite_reverse]">
          <circle
            cx={CENTER}
            cy={CENTER}
            r={184}
            fill="none"
            stroke="currentColor"
            strokeOpacity={0.45}
            strokeWidth={2}
            strokeDasharray="90 30 12 30"
          />
        </g>

        <g
          stroke="var(--color-circuit)"
          fill="none"
          strokeWidth={1.2}
          strokeOpacity={0.7}
        >
          {traces.map((t) => (
            <path key={t.id} d={t.d} />
          ))}
        </g>
        <g fill="var(--color-circuit)">
          {traces.map((t) => (
            <circle key={t.id} cx={t.end.x} cy={t.end.y} r={3} />
          ))}
        </g>

        <g className="origin-[260px_260px] motion-safe:animate-[spin_12s_linear_infinite]">
          <circle
            cx={CENTER}
            cy={CENTER}
            r={100}
            fill="none"
            stroke="currentColor"
            strokeOpacity={0.8}
            strokeWidth={1.5}
            strokeDasharray="4 8"
          />
          <circle cx={CENTER + 100} cy={CENTER} r={6} fill="currentColor" />
        </g>

        <circle
          cx={CENTER}
          cy={CENTER}
          r={70}
          fill="currentColor"
          opacity={0.08}
        />
        <g transform={`translate(${CENTER} ${CENTER + 4}) scale(46)`}>
          <path
            d={HEART}
            fill="currentColor"
            className="origin-center motion-safe:animate-pulse"
          />
        </g>
      </svg>

      <div className="absolute top-[4%] left-[2%] rounded-md border border-fd-primary/40 bg-fd-background/70 px-2.5 py-1.5 font-mono leading-tight backdrop-blur-sm">
        <div className="text-[10px] text-fd-muted-foreground">
          Ex-Machina · Prüfer
        </div>
        <div className="text-base font-semibold text-fd-foreground">
          Üc207Pr4f57t9
        </div>
        <div className="text-[10px] text-fd-muted-foreground">
          シュヴィ · Schwi
        </div>
      </div>

      <div className="absolute right-[2%] bottom-[6%] rounded-md border border-[var(--color-circuit)]/50 bg-fd-background/70 px-2.5 py-1.5 font-mono text-[11px] leading-snug backdrop-blur-sm motion-safe:animate-[schwi-blink_4s_ease-in-out_infinite]">
        <div style={{ color: "var(--color-circuit)" }}>解析：心</div>
        <div className="text-fd-muted-foreground">status … learning</div>
      </div>
    </div>
  );
}
