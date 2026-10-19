import type { BaseLayoutProps } from "fumadocs-ui/layouts/shared";
import { appName, gitConfig } from "./shared";

export function NavTitle() {
  return (
    <span className="inline-flex items-center gap-2">
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        fill="none"
        stroke="var(--color-circuit)"
        className="size-5"
      >
        <path d="M17.66 6.34A8 8 0 1 0 20 12" strokeWidth={1.4} />
        <path d="M12 7.5a4.5 4.5 0 1 1-4.5 4.5" strokeWidth={2.6} />
        <circle
          cx={12}
          cy={12}
          r={1.4}
          fill="var(--color-circuit)"
          stroke="none"
        />
      </svg>
      <span className="font-display font-bold">{appName}</span>
      <span className="text-xs font-normal text-fd-muted-foreground">
        シュヴィ
      </span>
    </span>
  );
}

export function baseOptions(): BaseLayoutProps {
  return {
    nav: {
      // JSX supported
      title: <NavTitle />,
    },
    githubUrl: `https://github.com/${gitConfig.user}/${gitConfig.repo}`,
  };
}
