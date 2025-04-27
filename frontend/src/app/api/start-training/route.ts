import { createClient } from "@supabase/supabase-js";
import { NextResponse, type NextRequest } from "next/server";

// Ensure Supabase client is initialized (consider moving to a shared config/client file)
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY; // Use service role key for server-side operations

if (!supabaseUrl || !supabaseKey) {
  console.error("Missing Supabase environment variables for start-training API");
  // Avoid throwing error at module level, handle in request
}

const supabase = createClient(supabaseUrl ?? "", supabaseKey ?? "");

// Ensure FastAPI URL is configured
const FASTAPI_URL = process.env.FASTAPI_URL;
if (!FASTAPI_URL) {
  console.error("FASTAPI_URL environment variable is not set.");
  // Avoid throwing error at module level, handle in request
}
const RUN_TRAINING_ENDPOINT = "/run_training";

// Define the expected request body structure
interface StartTrainingRequestBody {
  teacherId: string; // Assuming teacherId corresponds to the UUID in your Supabase table
  taskId: number;
  sessionId: number;
}

export async function POST(request: NextRequest) {
  // Check required environment variables at request time
  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.json({ error: "Supabase configuration missing" }, { status: 500 });
  }
  if (!FASTAPI_URL) {
    return NextResponse.json({ error: "Backend service URL not configured" }, { status: 500 });
  }

  let requestBody: StartTrainingRequestBody;
  try {
    requestBody = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  const { teacherId, taskId, sessionId } = requestBody;

  // Validate input
  if (!teacherId || !taskId || !sessionId) {
    return NextResponse.json({ error: "Missing required fields: teacherId, taskId, sessionId" }, { status: 400 });
  }

  try {
    // 1. Fetch teacher URL from Supabase using teacherId
    const { data: teacherData, error: supabaseError } = await supabase
      .from("teacher")
      .select("url")
      .eq("id", teacherId)
      .single(); // Expect only one teacher for the ID

    if (supabaseError) {
      console.error("Supabase error fetching teacher:", supabaseError);
      return NextResponse.json({ error: `Failed to fetch teacher details: ${supabaseError.message}` }, { status: 500 });
    }

    if (!teacherData || !teacherData.url) {
      return NextResponse.json({ error: `Teacher with ID ${teacherId} not found or has no URL` }, { status: 404 });
    }

    let teacherUrl = teacherData.url;

    // 2. Call the backend /run_training endpoint
    if (teacherUrl.endsWith("/") && RUN_TRAINING_ENDPOINT.startsWith("/")) {
      teacherUrl = teacherUrl.slice(0, -1);
    }
    const backendUrl = new URL(teacherUrl + RUN_TRAINING_ENDPOINT);
    console.log(`Calling backend training endpoint: ${backendUrl}`);

    const backendResponse = await fetch(backendUrl.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        task_id: taskId,
        session_id: sessionId,
        teacher_url: teacherUrl,
        max_turns: 4
      }),
    });

    // Forward the backend response (both success and error)
    const backendResponseBody = await backendResponse.json();

    if (!backendResponse.ok) {
      console.error(
        `Backend training endpoint error: ${backendResponse.status} ${backendResponse.statusText}`,
        backendResponseBody
      );
      // Forward the backend's error message and status if possible
      return NextResponse.json(
        { error: backendResponseBody.detail || backendResponseBody.message || "Backend training request failed" },
        { status: backendResponse.status }
      );
    }

    console.log("Backend training response:", backendResponseBody);
    return NextResponse.json(backendResponseBody, { status: backendResponse.status });
  } catch (error) {
    console.error("An unexpected error occurred in start-training API:", error);
    const errorMessage = error instanceof Error ? error.message : "Internal Server Error";
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
