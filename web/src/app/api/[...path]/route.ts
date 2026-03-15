import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL =
  process.env.PIPELINER_API_BASE_URL ||
  process.env.NEXT_PUBLIC_PIPELINER_API_BASE_URL ||
  'http://127.0.0.1:8000';

async function readRequestBody(request: NextRequest): Promise<BodyInit | undefined> {
  if (request.method === 'GET' || request.method === 'HEAD') {
    return undefined;
  }

  const contentType = request.headers.get('content-type') || '';
  if (contentType.includes('multipart/form-data')) {
    return request.formData();
  }
  if (contentType.includes('application/octet-stream')) {
    return request.arrayBuffer();
  }
  return request.text();
}

async function forward(request: NextRequest, params: { path?: string[] }) {
  const path = params.path?.join('/') || '';
  const search = request.nextUrl.search || '';
  const targetUrl = `${API_BASE_URL}/api/${path}${search}`;
  const contentType = request.headers.get('content-type');
  const accept = request.headers.get('accept');
  const headers = new Headers();
  const body = await readRequestBody(request);

  if (contentType && !contentType.includes('multipart/form-data')) {
    headers.set('content-type', contentType);
  }
  if (accept) {
    headers.set('accept', accept);
  }

  const response = await fetch(targetUrl, {
    method: request.method,
    headers,
    body,
    cache: 'no-store',
  });

  const responseHeaders = new Headers(response.headers);
  if (!responseHeaders.get('content-type')) {
    responseHeaders.set('content-type', 'application/json');
  }
  if (!responseHeaders.get('cache-control')) {
    responseHeaders.set('cache-control', 'no-store');
  }
  if (!response.body) {
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: responseHeaders,
    });
  }
  return new NextResponse(response.body, {
    status: response.status,
    headers: responseHeaders,
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
