import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!supabaseUrl || !supabaseKey) {
  throw new Error("Missing Supabase environment variables");
}
const supabase = createClient(supabaseUrl, supabaseKey);

export async function GET() {
  const { data, error } = await supabase.from("teacher").select("*");
  if (error) {
    console.error("Error fetching teachers:", error);
    return NextResponse.json({ error: "Failed to fetch teachers" }, { status: 500 });
  }
  return NextResponse.json(data);
}
