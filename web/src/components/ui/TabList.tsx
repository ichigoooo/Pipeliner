import React from 'react';

interface TabListProps {
    tabs: string[];
    activeTab: string;
    onTabChange: (tab: string) => void;
}

export function TabList({ tabs, activeTab, onTabChange }: TabListProps) {
  return (
    <div className="border-b border-stone-200">
      <nav className="-mb-px flex flex-wrap gap-6" aria-label="Tabs">
        {tabs.map((tab) => {
          const isActive = tab === activeTab;
          return (
            <button
              key={tab}
              onClick={() => onTabChange(tab)}
              className={`
                whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium transition
                ${
                  isActive
                    ? 'border-amber-500 text-stone-950'
                    : 'border-transparent text-stone-500 hover:border-stone-300 hover:text-stone-900'
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
