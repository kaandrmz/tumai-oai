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

// Generate a random client ID
const clientId = Math.random().toString(36).substring(2, 15);

// Define a type for the log messages we expect from the backend
type LogPayload = {
  event: string;
  [key: string]: unknown; // Use unknown instead of any
};

export default function SessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const channelId = `session-${sessionId}`;

  // State to hold structured log messages
  const [logMessages, setLogMessages] = useState<LogPayload[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [onlineAgents, setOnlineAgents] = useState<string[]>([]);

  useEffect(() => {
    const channel = supabase.channel(channelId);

    // Presence logic
    channel.on("presence", { event: "sync" }, () => {
      const state = channel.presenceState<{ username: string }>();
      const presenceList: string[] = [];

      Object.keys(state).forEach((key) => {
        const presences = state[key];
        presences.forEach((presence) => {
          presenceList.push(presence.username);
        });
      });

      const uniqueAgents = [...new Set(presenceList)];
      setOnlineAgents(uniqueAgents);
    });
    // We only need one subscribe call
    // .subscribe(async (status) => { /* ... */ });

    // Broadcast listener for logs
    channel
      .on("broadcast", { event: "message" }, (message) => {
        console.log("Received log:", message.payload); // Log for debugging
        setLogMessages((prev) => [...prev, message.payload as LogPayload]);
      })
      .subscribe(async (status) => {
        if (status === "SUBSCRIBED") {
          // Track presence when subscription is successful
          await channel.track({
            user_id: clientId,
            username: `viewer-${clientId.substring(0, 5)}`, // More descriptive username
            online_at: new Date().getTime(),
          });
          setIsConnected(true);
          console.log(`Subscribed to channel: ${channelId}`);
        } else {
          setIsConnected(false);
          console.log(`Subscription status: ${status}`);
        }
      });

    return () => {
      console.log(`Unsubscribing from channel: ${channelId}`);
      // Ensure presence is untracked on unmount/unsubscribe
      supabase.removeChannel(channel);
    };
  }, [channelId]); // Dependency array ensures effect runs when sessionId changes

  return (
    <div className="container mx-auto py-10">
      <h1 className="text-2xl font-bold mb-4">Session Details</h1>
      <p>
        Session ID: <span className="font-mono bg-gray-100 px-2 py-1 rounded">{sessionId}</span>
      </p>
      <p>
        Status:{" "}
        {isConnected ? <span className="text-green-600">Connected</span> : <span className="text-red-600">Disconnected</span>}
      </p>
      <p>Online participants: {onlineAgents.join(", ") || "None"}</p>
      <h2 className="text-xl font-semibold mt-6 mb-2">Event Log:</h2>
      <div className="bg-gray-800 text-green-400 font-mono p-4 rounded-md overflow-x-auto h-96">
        {logMessages.length === 0 ? (
          <p>Waiting for logs...</p>
        ) : (
          logMessages.map((msg, index) => (
            // Using pre for formatting, ensuring unique key
            <pre
              key={`${index}-${msg.event || "log"}`}
              className="whitespace-pre-wrap break-words mb-2 border-b border-gray-700 pb-1"
            >
              {JSON.stringify(msg, null, 2)}
            </pre>
          ))
        )}
      </div>
    </div>
  );
}
