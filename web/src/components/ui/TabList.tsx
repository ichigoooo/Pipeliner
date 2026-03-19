import React from 'react';

interface TabListProps {
    tabs: string[];
    activeTab: string;
    onTabChange: (tab: string) => void;
}

export function TabList({ tabs, activeTab, onTabChange }: TabListProps) {
  return (
    <div className="py-4">
      <nav
        className="inline-flex flex-wrap gap-2 rounded-[1.35rem] border border-stone-200/80 bg-[#f7f3ec] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]"
        aria-label="Tabs"
      >
        {tabs.map((tab) => {
          const isActive = tab === activeTab;
          return (
            <button
              key={tab}
              onClick={() => onTabChange(tab)}
              className={`
                whitespace-nowrap rounded-[1rem] px-3 py-2.5 text-sm font-medium transition duration-200
                ${
                  isActive
                    ? 'bg-white text-stone-950 shadow-[0_16px_28px_-20px_rgba(68,64,60,0.55)]'
                    : 'text-stone-500 hover:bg-white/70 hover:text-stone-900'
                }
              `}
              aria-current={isActive ? 'page' : undefined}
            >
              {tab}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
