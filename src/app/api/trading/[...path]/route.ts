import { NextRequest, NextResponse } from "next/server";

const rawUrl = process.env.TRADING_ENGINE_URL || "https://caught-dietary-trading-perception.trycloudflare.com";
const TRADING_ENGINE_URL = rawUrl.trim().replace(/\/+$/, "");

async function proxyRequest(
  request: NextRequest,
  paramsPromise: Promise<{ path: string[] }>,
  method: string
) {
  const { path } = await paramsPromise;
  const pathStr = path.join("/");

  const targetPath = `/api/trading/${pathStr}`;
  const targetUrl = `${TRADING_ENGINE_URL}${targetPath}`;

  try {
    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("connection");
    headers.set("bypass-tunnel-reminder", "true");

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
        detail: `Trading engine not running. Please start the Python backend first. Error: ${error instanceof Error ? error.message : "Unknown error"}`,
      },
      { status: 502 }
    );
  }
}

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
