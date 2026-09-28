import type { ReactNode } from 'react';
type IconName = 'profile' | 'briefcase' | 'upload' | 'check' | 'arrow' | 'download' | 'lock' | 'close' | 'alert';
const paths: Record<IconName, ReactNode> = {
  profile: <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6"/><path d="M8 13h8M8 17h5"/></>,
  briefcase: <><rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12a23 23 0 0 0 18 0M12 11v4"/></>,
  upload: <path d="M12 16V4m-5 5 5-5 5 5M4 16v4h16v-4"/>,
  check: <path d="m5 12 4 4L19 6"/>, arrow: <path d="M4 12h16m-6-6 6 6-6 6"/>,
  download: <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/></>,
  close: <path d="m6 6 12 12M6 18 18 6"/>,
  alert: <><circle cx="12" cy="12" r="9"/><path d="M12 7v6m0 3v1"/></>,
};
export function Icon({ name, className = '' }: { name: IconName; className?: string }) {
  return <svg className={`icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
