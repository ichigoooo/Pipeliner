'use client';

import React, { useState } from 'react';
import { Edge, Node } from '@xyflow/react';
import { useTranslations } from 'next-intl';
import { TabList } from '@/components/ui/TabList';
import { InspectorPanel } from '@/components/ui/InspectorPanel';
import { WorkflowGraph } from '@/components/workflow/WorkflowGraph';
import { WorkflowSpecView } from '@/components/workflow/WorkflowSpecView';
import { WorkflowCard } from '@/lib/api';

interface WorkflowWorkspaceProps {
  spec: object;
  cards?: WorkflowCard[];
  nodes: Node[];
  edges: Edge[];
  lintWarnings: string[];
  lintErrors?: string[];
  inputEditor?: React.ReactNode;
}

export function WorkflowWorkspace({
  spec,
  cards = [],
  nodes,
  edges,
  lintWarnings,
  lintErrors = [],
  inputEditor,
}: WorkflowWorkspaceProps) {
  const t = useTranslations('workflow');
  const lintTab = t('lintTab', { count: lintWarnings.length + lintErrors.length });
  const [activeTab, setActiveTab] = useState(t('tabs.graph'));
  const [selectedNodeData, setSelectedNodeData] = useState<unknown>(null);
  const inputTab = inputEditor ? t('tabs.inputs') : null;
  const tabs = [
    t('tabs.graph'),
    t('tabs.cards'),
    ...(inputTab ? [inputTab] : []),
    t('tabs.spec'),
    lintTab,
  ];

  const handleNodeClick = (_event: React.MouseEvent, node: Node) => {
    setSelectedNodeData(node.data?.spec || node.data || null);
  };

  const handlePaneClick = () => {
    setSelectedNodeData(null);
  };

  return (
    <div className="flex h-full flex-col bg-white">
      <div className="px-4">
        <TabList tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      <div className="relative flex-1 overflow-hidden bg-stone-50">
        {activeTab === t('tabs.graph') && (
          <WorkflowGraph
            initialNodes={nodes}
            initialEdges={edges}
            onNodeClick={handleNodeClick}
            onPaneClick={handlePaneClick}
          />
        )}

        {activeTab === t('tabs.cards') && (
          <div className="grid h-full gap-4 overflow-auto p-4 xl:grid-cols-2">
            {cards.map((card) => (
              <button
                key={card.node_id}
                type="button"
                className="rounded-3xl border border-stone-200 bg-white p-5 text-left shadow-sm transition hover:border-amber-500 hover:shadow-md"
                onClick={() => setSelectedNodeData(card.raw)}
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-stone-500">
                      {card.node_id}
                    </p>
                    <h3 className="mt-2 text-lg font-semibold text-stone-900">{card.title}</h3>
                  </div>
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-900">
                    {card.archetype || 'workflow-node'}
                  </span>
                </div>
                <p className="text-sm leading-6 text-stone-600">{card.purpose}</p>
                <dl className="mt-4 grid gap-3 text-sm text-stone-700">
                  <div>
                    <dt className="font-medium text-stone-500">{t('card.dependsOn')}</dt>
                    <dd>{card.depends_on.length ? card.depends_on.join(', ') : t('card.rootNode')}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-stone-500">{t('card.executor')}</dt>
                    <dd>{card.executor_skill || '-'}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-stone-500">{t('card.validators')}</dt>
                    <dd>{card.validator_ids.filter(Boolean).join(', ') || '-'}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-stone-500">{t('card.doneMeans')}</dt>
                    <dd>{card.done_means || '-'}</dd>
                  </div>
                </dl>
              </button>
            ))}
          </div>
        )}

        {inputEditor && inputTab && activeTab === inputTab && (
          <div className="h-full overflow-auto p-4">
            {inputEditor}
          </div>
        )}

        {activeTab === t('tabs.spec') && <WorkflowSpecView spec={spec} />}

        {activeTab === lintTab && (
          <div className="grid h-full gap-6 overflow-auto p-4 lg:grid-cols-2">
            <section className="rounded-3xl border border-rose-200 bg-white p-5 shadow-sm">
              <h3 className="text-base font-semibold text-stone-900">{t('lint.blockingIssues')}</h3>
              <div className="mt-4 space-y-3">
                {lintErrors.length === 0 ? (
                  <p className="text-sm text-stone-500">{t('lint.noBlockingIssues')}</p>
                ) : (
                  lintErrors.map((message) => (
                    <div
                      key={message}
                      className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900"
                    >
                      {message}
                    </div>
                  ))
                )}
              </div>
            </section>
            <section className="rounded-3xl border border-amber-200 bg-white p-5 shadow-sm">
              <h3 className="text-base font-semibold text-stone-900">{t('lint.warnings')}</h3>
              <div className="mt-4 space-y-3">
                {lintWarnings.length === 0 ? (
                  <p className="text-sm text-stone-500">{t('lint.noWarnings')}</p>
                ) : (
                  lintWarnings.map((message) => (
                    <div
                      key={message}
                      className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                    >
                      {message}
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        )}
      </div>

      {selectedNodeData !== null && (
        <div className="absolute inset-y-0 right-0 z-10 border-l border-stone-200 shadow-lg">
          <InspectorPanel
            title={t('inspector.title')}
            data={selectedNodeData}
            onClose={() => setSelectedNodeData(null)}
          />
        </div>
      )}
    </div>
  );
}
