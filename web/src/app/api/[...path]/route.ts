import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL =
  process.env.PIPELINER_API_BASE_URL ||
  process.env.NEXT_PUBLIC_PIPELINER_API_BASE_URL ||
  'http://127.0.0.1:8000';

async function forward(request: NextRequest, params: { path?: string[] }) {
  const path = params.path?.join('/') ?? '';
  const search = request.nextUrl.search || '';
  const targetUrl = `${API_BASE_URL}/api/${path}${search}`;
  const body =
    request.method === 'GET' || request.method === 'HEAD'
      ? undefined
      : await request.text();

  const response = await fetch(targetUrl, {
    method: request.method,
    headers: {
      'content-type': request.headers.get('content-type') || 'application/json',
    },
    body,
    cache: 'no-store',
  });

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: {
      'content-type': response.headers.get('content-type') || 'application/json',
    },
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  return forward(request, await context.params);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  return forward(request, await context.params);
}
export const maxDuration = 900;  
  
