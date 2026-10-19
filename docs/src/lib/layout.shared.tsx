import type { BaseLayoutProps } from "fumadocs-ui/layouts/shared";
import { appName, gitConfig } from "./shared";

export function NavTitle() {
  return (
    <span className="inline-flex items-center gap-2">
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        className="size-5 text-fd-primary"
      >
        <path
          d="M12 20.5 4.2 12.9a4.6 4.6 0 0 1 6.5-6.5l1.3 1.3 1.3-1.3a4.6 4.6 0 0 1 6.5 6.5Z"
          fill="currentColor"
          opacity={0.2}
        />
        <path
          d="M12 20.5 4.2 12.9a4.6 4.6 0 0 1 6.5-6.5l1.3 1.3 1.3-1.3a4.6 4.6 0 0 1 6.5 6.5Z"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.6}
          strokeLinejoin="round"
        />
        <path
          d="M7.5 12h3l1-2 1.5 4 1-2h2.5"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.4}
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
