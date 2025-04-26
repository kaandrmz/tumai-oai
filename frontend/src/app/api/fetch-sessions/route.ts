import { NextResponse } from "next/server";

const FASTAPI_URL = process.env.FASTAPI_URL;
if (!FASTAPI_URL) {
  console.error("FASTAPI_URL environment variable is not set.");
}
const SESSIONS_ENDPOINT = "/sessions";

export async function GET() {
  if (!FASTAPI_URL) {
    return NextResponse.json({ error: "Backend service URL not configured" }, { status: 500 });
  }

  try {
    const url = new URL(FASTAPI_URL + SESSIONS_ENDPOINT);
    console.log(`Fetching sessions from: ${url}`);
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      console.error(`Error fetching sessions: ${response.status} ${response.statusText}`);
      const errorBody = await response.text();
      console.error(`Error body: ${errorBody}`);
      return NextResponse.json(
        { error: `Failed to fetch sessions from backend: ${response.statusText}` },
        { status: response.status }
      );
    }

    const sessions = await response.json();
    console.log("Fetched sessions:", sessions);

    // // mock for now - REMOVED
    // const sessions = [
    //   { id: "1", status: "active" },
    //   { id: "2", status: "completed" },
    //   { id: "3", status: "failed" },
    // ];

    return NextResponse.json(sessions);
  } catch (error) {
    console.error("An unexpected error occurred while fetching sessions:", error);
    // Provide more context in the error response if possible
    const errorMessage = error instanceof Error ? error.message : "Internal Server Error";
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
