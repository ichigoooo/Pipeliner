import { WorkflowDetailClient } from './WorkflowDetailClient';

export default async function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ workflow_id: string }>;
}) {
  const { workflow_id: workflowId } = await params;
  return <WorkflowDetailClient workflowId={workflowId} />;
}
