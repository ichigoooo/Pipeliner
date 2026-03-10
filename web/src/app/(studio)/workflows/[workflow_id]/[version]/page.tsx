import { WorkflowVersionClient } from './WorkflowVersionClient';

export default async function WorkflowVersionPage({
  params,
}: {
  params: Promise<{ workflow_id: string; version: string }>;
}) {
  const { workflow_id: workflowId, version } = await params;
  return <WorkflowVersionClient workflowId={workflowId} version={version} />;
}
