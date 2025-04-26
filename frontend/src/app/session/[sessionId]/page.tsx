"use client";
import { use } from "react";
import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronsUpDownIcon } from "lucide-react";
import Image from "next/image";

const student_image = "/student.png";
const teacher_image = "/teacher.png";

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
if (!supabaseUrl || !supabaseKey) {
  throw new Error("Missing Supabase environment variables");
}
const supabase = createClient(supabaseUrl, supabaseKey);

const clientId = Math.random().toString(36).substring(2, 15);

type LogPayload = {
  event: string;
  role?: string;
  content?: string;
  [key: string]: unknown;
};

type ChatMessagePayload = {
  event: "chat_message";
  role: "user" | "teacher";
  content: string;
  [key: string]: unknown;
};

export default function SessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const channelId = `session-${sessionId}`;

  const [logMessages, setLogMessages] = useState<LogPayload[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessagePayload[]>([]);
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

    // Broadcast listener
    channel
      .on("broadcast", { event: "message" }, (message) => {
        const payload = message.payload as LogPayload;
        console.log("Received log:", payload);
        if (
          payload.event === "chat_message" &&
          payload.role &&
          payload.content &&
          (payload.role === "user" || payload.role === "teacher")
        ) {
          setChatMessages((prev) => [...prev, payload as ChatMessagePayload]);
        } else {
          setLogMessages((prev) => [...prev, payload]);
        }
      })
      .subscribe(async (status) => {
        if (status === "SUBSCRIBED") {
          await channel.track({
            user_id: clientId,
            username: `viewer-${clientId.substring(0, 5)}`,
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
      supabase.removeChannel(channel);
    };
  }, [channelId]);

  return (
    <div className="container mx-auto py-10 max-w-4xl">
      <h1 className="text-2xl font-bold mb-4">Session {sessionId} ({isConnected ? <span className="text-green-600">Connected</span> : <span className="text-red-600">Disconnected</span>})</h1>

      {/* --- Chat Area --- */}
      <div className="space-y-4 border rounded-lg p-4 h-dhv overflow-y-auto bg-slate-50">
        {chatMessages.length === 0 ? (
          <p className="text-gray-500 text-center pt-4">Waiting for messages...</p>
        ) : (
          chatMessages.map((msg, index) => (
            <div key={index} className={`flex items-end gap-2 ${msg.role === "user" ? "justify-start" : "justify-end"}`}>
              {msg.role === "user" && (
                <>
                  <Image src={student_image} alt="Student" width={32} height={32} className="rounded-full" />
                  <div className="bg-blue-100 text-blue-900 rounded-lg p-3 max-w-xs sm:max-w-md">
                    <p className="text-sm">{msg.content}</p>
                  </div>
                </>
              )}
              {msg.role === "teacher" && (
                <>
                  <div className="bg-green-100 text-green-900 rounded-lg p-3 max-w-xs sm:max-w-md">
                    <p className="text-sm">{msg.content}</p>
                  </div>
                  <Image src={teacher_image} alt="Teacher" width={32} height={32} className="rounded-full" />
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* --- Collapsible Event Log Section --- */}
      <Collapsible className="mt-8 border rounded-md bg-white shadow-sm">
        <CollapsibleTrigger className="flex justify-between items-center w-full px-4 py-3 text-left font-medium text-gray-700 hover:bg-gray-50 rounded-t-md">
          <h2 className="text-xl font-semibold">Detailed Event Log</h2>
          <ChevronsUpDownIcon className="h-5 w-5 text-gray-500" />
        </CollapsibleTrigger>
        <CollapsibleContent className="p-4 border-t">
          <div className="bg-gray-900 text-green-400 font-mono p-3 rounded-md overflow-x-auto text-xs max-h-96 overflow-y-auto">
            {logMessages.length === 0 && !isConnected ? (
              <p className="text-gray-400">Connecting...</p>
            ) : logMessages.length === 0 && isConnected ? (
              <p className="text-gray-400">No system logs received yet...</p>
            ) : (
              <pre>{JSON.stringify([...logMessages].reverse(), null, 2)}</pre>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
