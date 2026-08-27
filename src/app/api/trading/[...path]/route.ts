import { NextRequest, NextResponse } from "next/server";
import { ChildProcess, spawn } from "child_process";

const TRADING_ENGINE_PORT = process.env.TRADING_ENGINE_PORT || "8001";
let engineProcess: ChildProcess | null = null;
let engineReady = false;
let starting = false;
let startAttempts = 0;
const MAX_START_ATTEMPTS = 3;

function startEngine() {
  if (engineProcess || starting || startAttempts >= MAX_START_ATTEMPTS) return;
  starting = true;
  startAttempts++;

  console.log(`[TradingProxy] Starting Cloud Trading Engine (attempt ${startAttempts})...`);

  engineProcess = spawn(
    "python3",
    ["-m", "uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", TRADING_ENGINE_PORT],
    {
      cwd: "/home/z/my-project/mini-services/trading-engine",
      stdio: ["ignore", "pipe", "pipe"],
      detached: false,
    }
  );

  engineProcess.stdout?.on("data", (data: Buffer) => {
    const msg = data.toString().trim();
    if (msg) console.log(`[TradingEngine] ${msg}`);
    if (msg.includes("Application startup complete")) {
      engineReady = true;
      starting = false;
      startAttempts = 0; // Reset on successful start
    }
  });

  engineProcess.stderr?.on("data", (data: Buffer) => {
    const msg = data.toString().trim();
    if (msg) console.log(`[TradingEngine:ERR] ${msg}`);
  });

  engineProcess.on("exit", (code) => {
    console.log(`[TradingProxy] Engine exited with code ${code}`);
    engineProcess = null;
    engineReady = false;
    starting = false;
  });

  // Force ready after timeout
  setTimeout(() => {
    if (starting) {
      engineReady = true;
      starting = false;
    }
  }, 12000);
}

// Auto-start engine on module load
startEngine();

// Restart if engine dies (check every 20s)
setInterval(() => {
  if (!engineProcess && !starting && startAttempts < MAX_START_ATTEMPTS) {
    console.log("[TradingProxy] Engine died, restarting...");
    startEngine();
  }
}, 20000);

async function waitForEngine(maxWait = 15000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    if (engineReady) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  engineReady = true;
  return true;
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

async function proxyRequest(
  request: NextRequest,
  paramsPromise: Promise<{ path: string[] }>,
  method: string
) {
  const { path } = await paramsPromise;
  const pathStr = path.join("/");

  await waitForEngine();

  const targetPath = `/api/trading/${pathStr}`;
  const targetUrl = `http://127.0.0.1:${TRADING_ENGINE_PORT}${targetPath}`;

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
    if (!engineProcess && startAttempts < MAX_START_ATTEMPTS) {
      startAttempts = 0; // Allow retry
      startEngine();
    }
    return NextResponse.json(
      {
        detail: `Trading engine starting up... ${error instanceof Error ? error.message : "Unknown error"}`,
      },
      { status: 502 }
    );
  }
}
