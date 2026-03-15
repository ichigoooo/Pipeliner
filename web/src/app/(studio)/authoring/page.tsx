import { Suspense } from 'react';
import { AuthoringStudio } from '@/components/authoring/AuthoringStudio';

export default function AuthoringPage() {
  return (
    <Suspense fallback={null}>
      <AuthoringStudio />
    </Suspense>
  );
}
