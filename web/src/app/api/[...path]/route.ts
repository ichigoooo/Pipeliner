import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL =
  process.env.PIPELINER_API_BASE_URL ||
  process.env.NEXT_PUBLIC_PIPELINER_API_BASE_URL ||
  'http://127.0.0.1:8000';
const DEFAULT_HEADERS_TIMEOUT_MS = 30 * 60 * 1000;
const DEFAULT_BODY_TIMEOUT_MS = 30 * 60 * 1000;

const parseTimeoutMs = (value: string | undefined, fallback: number) => {
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
};

const headersTimeoutMs = parseTimeoutMs(
  process.env.PIPELINER_API_HEADERS_TIMEOUT_MS,
  DEFAULT_HEADERS_TIMEOUT_MS
);
const bodyTimeoutMs = parseTimeoutMs(
  process.env.PIPELINER_API_BODY_TIMEOUT_MS,
  DEFAULT_BODY_TIMEOUT_MS
);

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

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
      cache: 'no-store',
      signal: AbortSignal.timeout(Math.max(headersTimeoutMs, bodyTimeoutMs)),
    });
  } catch (error) {
    const detail =
      error instanceof Error
        ? `无法连接后端服务 ${targetUrl}: ${error.message}`
        : `无法连接后端服务 ${targetUrl}`;
    return NextResponse.json(
      {
        detail,
      },
      {
        status: 502,
        headers: {
          'cache-control': 'no-store',
        },
      }
    );
  }

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

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  return forward(request, await context.params);
}

export const maxDuration = 1800;
