import { NextResponse } from "next/server";

// Replace with the actual URL of your Python service
const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || "http://localhost:8000";
const SESSIONS_ENDPOINT = "/sessions";

export async function GET() {
  try {
    // const url = new URL(PYTHON_SERVICE_URL + SESSIONS_ENDPOINT);
    // const response = await fetch(url, {
    //   method: "GET",
    //   headers: {
    //     "Content-Type": "application/json",
    //   },
    //   cache: "no-store",
    // });

    // if (!response.ok) {
    //   console.error(`Error fetching sessions: ${response.status} ${response.statusText}`);
    //   const errorBody = await response.text();
    //   console.error(`Error body: ${errorBody}`);
    //   return NextResponse.json(
    //     { error: `Failed to fetch sessions from backend: ${response.statusText}` },
    //     { status: response.status }
    //   );
    // }

    // const sessions = await response.json();
    
    // mock for now
    const sessions = [
      { id: "1", status: "active" },
      { id: "2", status: "completed" },
      { id: "3", status: "failed" },
    ];

    return NextResponse.json(sessions);
  } catch (error) {
    console.error("An unexpected error occurred:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
