import { NextRequest, NextResponse } from "next/server";

const PYTHON_BACKEND_PORT = process.env.PYTHON_BACKEND_PORT || "8000";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, params, "POST");
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, params, "GET");
}

async function proxyRequest(
  request: NextRequest,
  paramsPromise: Promise<{ path: string[] }>,
  method: string
) {
  const { path } = await paramsPromise;
  const pathStr = path.join("/");

  // Forward to Python backend via XTransformPort
  const searchParams = new URLSearchParams(request.search);
  searchParams.set("XTransformPort", PYTHON_BACKEND_PORT);

  const targetPath = `/api/trading/${pathStr}`;
  const targetUrl = `http://localhost:${PYTHON_BACKEND_PORT}${targetPath}`;

  try {
    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("connection");

    const body = method !== "GET" ? await request.text() : undefined;

    const res = await fetch(targetUrl, {
      method,
      headers,
      body,
    });

    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    return NextResponse.json(
      {
        detail: `Python backend unavailable. Is the MT5 trading engine running? ${error instanceof Error ? error.message : "Unknown error"}`,
      },
      { status: 502 }
    );
  }
}

