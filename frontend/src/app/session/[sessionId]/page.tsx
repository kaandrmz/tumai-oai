"use client";
import { use } from "react";
import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
if (!supabaseUrl || !supabaseKey) {
  throw new Error("Missing Supabase environment variables");
}
const supabase = createClient(supabaseUrl, supabaseKey);

// Generate a random client ID and avatar
const clientId = Math.random().toString(36).substring(2, 15);

export default function SessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const channelId = `session-${sessionId}`;

  const [messages, setMessages] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [onlineAgents, setOnlineAgents] = useState<string[]>([]);

  useEffect(() => {
    // Subscribe to presence channel
    const channel = supabase.channel(channelId);

    channel
      .on("presence", { event: "sync" }, () => {
        const state = channel.presenceState<{ username: string }>();
        const presenceList: string[] = [];

        // Convert presence state to array of usernames
        Object.keys(state).forEach((key) => {
          const presences = state[key];
          // Extract username from each presence object
          presences.forEach((presence) => {
            presenceList.push(presence.username);
          });
        });

        // Remove duplicates if necessary (optional)
        const uniqueAgents = [...new Set(presenceList)];
        setOnlineAgents(uniqueAgents);
      })
      .subscribe(async (status) => {
        if (status === "SUBSCRIBED") {
          await channel.track({
            user_id: clientId,
            username: clientId,
            online_at: new Date().getTime(),
          });
          setIsConnected(true);
        }
      });

    channel
      .on("broadcast", { event: "message" }, (payload) => {
        // Assuming payload.payload is the message content (string)
        setMessages((prev) => [...prev, payload.payload as string]);
      })
      .subscribe(async (status) => {
        if (status === "SUBSCRIBED") {
          // Track presence
          await channel.track({
            user_id: clientId,
            username: clientId,
            online_at: new Date().getTime(),
          });
          setIsConnected(true);
        }
      });

    return () => {
      // Clean up subscription
      channel.unsubscribe();
    };
  }, [channelId]);

  return (
    <div className="container mx-auto py-10">
      <h1 className="text-2xl font-bold mb-4">Session Details</h1>
      <p>
        Displaying details for Session ID: <span className="font-mono bg-gray-100 px-2 py-1 rounded">{sessionId}</span>
      </p>
      <p>Online agents: {onlineAgents.join(", ")}</p>
      <p>Messages: {messages.map((msg) => String(msg)).join(", ")}</p>
      <p>Is connected: {isConnected ? "Yes" : "No"}</p>
    </div>
  );
}
