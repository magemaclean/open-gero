import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Svg({ size = 18, children, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      {children}
    </svg>
  );
}

export const IconLogo = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <circle cx="12" cy="12" r="3.2" fill="currentColor" />
    <circle cx="5" cy="7" r="1.6" fill="currentColor" />
    <circle cx="19" cy="8" r="1.6" fill="currentColor" />
    <circle cx="7" cy="18" r="1.6" fill="currentColor" />
    <path d="M8.2 8.2 10 10.4M15.8 9.2 13.8 10.6M8.4 16.2 10.6 13.8" stroke="currentColor" strokeWidth="1.6" />
  </svg>
);

export const IconLibrary = (p: IconProps) => (
  <Svg {...p}><rect x="4" y="4" width="16" height="16" rx="3" /><path d="M8 8h8M8 12h8M8 16h5" /></Svg>
);
export const IconDraw = (p: IconProps) => (
  <Svg {...p}><path d="M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17v3z" /><path d="M13.5 6.5l3 3" /></Svg>
);
export const IconSearch = (p: IconProps) => (
  <Svg {...p}><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4 4" /></Svg>
);
export const IconJobs = (p: IconProps) => (
  <Svg {...p}><path d="M4 8h16v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8z" /><path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><path d="M4 12h16" /></Svg>
);
export const IconFlask = (p: IconProps) => (
  <Svg {...p}><path d="M9 3h6M10 3v6L5.4 18.2A2.2 2.2 0 0 0 7.3 21h9.4a2.2 2.2 0 0 0 1.9-2.8L14 9V3" /><path d="M8 14h8" /></Svg>
);
export const IconTarget = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="1.2" fill="currentColor" /></Svg>
);
export const IconAdmin = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="8" r="3.2" /><path d="M5 19.2a7 7 0 0 1 14 0" /></Svg>
);
export const IconSun = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="4" /><path d="M12 3v2M12 19v2M4.2 4.2l1.5 1.5M18.3 18.3l1.5 1.5M3 12h2M19 12h2M4.2 19.8l1.5-1.5M18.3 5.7l1.5-1.5" /></Svg>
);
export const IconMoon = (p: IconProps) => (
  <Svg {...p}><path d="M16 13.2A6.2 6.2 0 1 1 10.8 8 4.8 4.8 0 0 0 16 13.2z" /></Svg>
);
export const IconLogout = (p: IconProps) => (
  <Svg {...p}><path d="M10 7V5a2 2 0 0 1 2-2h7v18h-7a2 2 0 0 1-2-2v-2" /><path d="M4 12h11M12 9l3 3-3 3" /></Svg>
);
export const IconUpload = (p: IconProps) => (
  <Svg {...p}><path d="M12 16V5M8 8l4-4 4 4" /><path d="M5 19h14" /></Svg>
);
export const IconDownload = (p: IconProps) => (
  <Svg {...p}><path d="M12 5v11M8 12l4 4 4-4" /><path d="M5 19h14" /></Svg>
);
export const IconPlus = (p: IconProps) => (
  <Svg {...p}><path d="M12 5v14M5 12h14" /></Svg>
);
export const IconClose = (p: IconProps) => (
  <Svg {...p}><path d="M6 6l12 12M18 6 6 18" /></Svg>
);
export const IconSpark = (p: IconProps) => (
  <Svg {...p}><path d="M12 3l1.4 5.2L18 9.5l-4.6 2.1L12 17l-1.4-5.4L6 9.5l4.6-1.3z" /></Svg>
);
export const IconMenu = (p: IconProps) => (
  <Svg {...p}><path d="M5 7h14M5 12h14M5 17h10" /></Svg>
);
export const IconProjects = (p: IconProps) => (
  <Svg {...p}><rect x="4" y="4" width="7" height="7" rx="1.6" /><rect x="13" y="4" width="7" height="7" rx="1.6" /><rect x="4" y="13" width="7" height="7" rx="1.6" /><rect x="13" y="13" width="7" height="7" rx="1.6" /></Svg>
);
