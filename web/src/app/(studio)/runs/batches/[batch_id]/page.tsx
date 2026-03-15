import { BatchRunDetailClient } from './BatchRunDetailClient';

export default async function BatchRunDetailPage({
  params,
}: {
  params: Promise<{ batch_id: string }>;
}) {
  const { batch_id: batchId } = await params;
  return <BatchRunDetailClient batchId={batchId} />;
}
