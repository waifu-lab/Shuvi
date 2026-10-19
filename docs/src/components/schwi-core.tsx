// 修比頭上那圈斷開的青色光環。

const CENTER = 260;

function polar(radius: number, angle: number) {
  return {
    x: Number((CENTER + radius * Math.cos(angle)).toFixed(2)),
    y: Number((CENTER + radius * Math.sin(angle)).toFixed(2)),
  };
}

// 以中心為圓心的一段圓弧，角度用度數，0 度在正右方、順時針
function arc(radius: number, from: number, to: number) {
  const start = polar(radius, (from * Math.PI) / 180);
  const end = polar(radius, (to * Math.PI) / 180);
  const large = to - from > 180 ? 1 : 0;
  return `M${start.x} ${start.y} A${radius} ${radius} 0 ${large} 1 ${end.x} ${end.y}`;
}

// 光環：幾圈斷開的環，粗細不一，各自用不同速度轉
const halo = {
  outer: [arc(200, -60, 150), arc(200, 172, 280)],
  band: [arc(162, 20, 135), arc(162, 160, 250), arc(162, 268, 330)],
  inner: [arc(88, -100, 120), arc(88, 140, 230)],
  notches: [arc(178, 0, 8), arc(178, 140, 146), arc(178, 255, 262)],
};

export function SchwiCore({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`relative aspect-square ${className ?? ""}`}
    >
      <svg
        viewBox="0 0 520 520"
        className="relative size-full"
        aria-hidden="true"
      >
        <defs>
          <filter
            id="schwi-halo-glow"
            x="-50%"
            y="-50%"
            width="200%"
            height="200%"
          >
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <g
          fill="none"
          stroke="var(--color-circuit)"
          filter="url(#schwi-halo-glow)"
        >
          <g className="origin-[260px_260px] motion-safe:animate-[spin_24s_linear_infinite]">
            {halo.outer.map((d) => (
              <path key={d} d={d} strokeWidth={4} />
            ))}
            {halo.notches.map((d) => (
              <path key={d} d={d} strokeWidth={12} />
            ))}
          </g>
          <g className="origin-[260px_260px] motion-safe:animate-[spin_16s_linear_infinite_reverse]">
            {halo.band.map((d) => (
              <path key={d} d={d} strokeWidth={20} strokeOpacity={0.85} />
            ))}
          </g>
          <circle
            cx={CENTER}
            cy={CENTER}
            r={124}
            strokeWidth={2.5}
            strokeOpacity={0.6}
          />
          <g className="origin-[260px_260px] motion-safe:animate-[spin_10s_linear_infinite]">
            {halo.inner.map((d) => (
              <path key={d} d={d} strokeWidth={10} />
            ))}
          </g>
          <circle
            cx={CENTER}
            cy={CENTER}
            r={14}
            fill="var(--color-circuit)"
            stroke="none"
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

      <div className="absolute right-[2%] bottom-[6%] rounded-md border border-[var(--color-circuit)]/50 bg-fd-background/70 px-2.5 py-1.5 font-mono text-[11px] leading-snug backdrop-blur-sm">
        <div style={{ color: "var(--color-circuit)" }}>Analyzing: heart</div>
      </div>
    </div>
  );
}
