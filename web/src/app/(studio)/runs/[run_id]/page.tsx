import { RunDetailClient } from './RunDetailClient';

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ run_id: string }>;
}) {
  const { run_id: runId } = await params;
  return <RunDetailClient runId={runId} />;
}
