'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import {
  PenTool,
  GitBranch,
  PlayCircle,
  AlertTriangle,
  Settings,
  LayoutDashboard
} from 'lucide-react';

const navigation = [
  { key: 'dashboard', href: '/', icon: LayoutDashboard },
  { key: 'authoring', href: '/authoring', icon: PenTool },
  { key: 'workflows', href: '/workflows', icon: GitBranch },
  { key: 'runs', href: '/runs', icon: PlayCircle },
  { key: 'attention', href: '/attention', icon: AlertTriangle },
  { key: 'settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const t = useTranslations('sidebar');
  const pathname = usePathname();

  return (
    <div className="hidden h-full w-72 flex-col border-r border-stone-200 bg-stone-950/95 px-4 py-5 text-white lg:flex">
      <div className="rounded-[2rem] border border-white/10 bg-white/5 px-5 py-5">
        <p className="text-xs uppercase tracking-[0.28em] text-stone-400">{t('title')}</p>
        <span className="mt-3 block text-2xl font-semibold tracking-tight">{t('subtitle')}</span>
        <p className="mt-3 text-sm leading-6 text-stone-300">
          {t('description')}
        </p>
      </div>

      <div className="mt-6 flex flex-1 flex-col overflow-y-auto">
        <nav className="flex-1 space-y-2">
          {navigation.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              className={`group flex items-center rounded-2xl px-4 py-3 text-sm font-medium transition ${
                pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
                  ? 'bg-amber-300 text-stone-950'
                  : 'text-stone-300 hover:bg-white/8 hover:text-white'
              }`}
            >
              <item.icon
                className={`mr-3 h-5 w-5 shrink-0 ${
                  pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
                    ? 'text-stone-950'
                    : 'text-stone-500 group-hover:text-white'
                }`}
                aria-hidden="true"
              />
              {t(`nav.${item.key}`)}
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}
