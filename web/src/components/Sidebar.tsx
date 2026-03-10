'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  PenTool,
  GitBranch,
  PlayCircle,
  AlertTriangle,
  Settings,
  LayoutDashboard
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Authoring', href: '/authoring', icon: PenTool },
  { name: 'Workflows', href: '/workflows', icon: GitBranch },
  { name: 'Runs', href: '/runs', icon: PlayCircle },
  { name: 'Attention Queue', href: '/attention', icon: AlertTriangle },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="hidden h-full w-72 flex-col border-r border-stone-200 bg-stone-950/95 px-4 py-5 text-white lg:flex">
      <div className="rounded-[2rem] border border-white/10 bg-white/5 px-5 py-5">
        <p className="text-xs uppercase tracking-[0.28em] text-stone-400">Pipeliner</p>
        <span className="mt-3 block text-2xl font-semibold tracking-tight">Workflow Studio</span>
        <p className="mt-3 text-sm leading-6 text-stone-300">
          Inspect workflow specs, author drafts, debug runs, and track resolved config.
        </p>
      </div>

      <div className="mt-6 flex flex-1 flex-col overflow-y-auto">
        <nav className="flex-1 space-y-2">
          {navigation.map((item) => (
            <Link
              key={item.name}
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
              {item.name}
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}
