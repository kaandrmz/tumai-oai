"use client";
import { use } from "react";
import { useEffect, useState, useRef } from "react";
import { createClient } from "@supabase/supabase-js";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronsUpDownIcon, ThumbsUp, ThumbsDown, Smile } from "lucide-react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const student_image = "/student.png";
const teacher_image = "/teacher.png";

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
if (!supabaseUrl || !supabaseKey) {
  throw new Error("Missing Supabase environment variables");
}
const supabase = createClient(supabaseUrl, supabaseKey);

type LogPayload = {
  event: string;
  role?: string;
  content?: string;
  [key: string]: unknown;
};

type ChatMessagePayload = {
  event: "chat_message";
  role: "student" | "teacher";
  content: string;
  score?: number;
  feedback?: string;
  animated?: boolean;
  [key: string]: unknown;
};

// Define a type for the AgentEnd evaluation event payload for clarity
type AgentEndEvalPayload = {
  event: "agent_end";
  agent: string;
  method: "eval_reply";
  score: number;
  is_end: boolean;
  feedback?: string;
  [key: string]: unknown;
};

export default function SessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const channelId = `session-${sessionId}`;

  const [logMessages, setLogMessages] = useState<LogPayload[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessagePayload[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [averageScore, setAverageScore] = useState<number | null>(null);
  const [scoreHistory, setScoreHistory] = useState<{ score: number; timestamp: number }[]>([]);
  const [currentStreak, setCurrentStreak] = useState(0);
  const [showStreakAnimation, setShowStreakAnimation] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const evaluationCounter = useRef<number>(0);

  const calculateAverageScore = (history: typeof scoreHistory) => {
    if (history.length === 0) return null;
    const sum = history.reduce((acc, item) => acc + item.score, 0);
    return sum / history.length;
  };

  useEffect(() => {
    const channel = supabase.channel(channelId);

    channel
      .on("broadcast", { event: "message" }, (message) => {
        const payload = message.payload as LogPayload | ChatMessagePayload | AgentEndEvalPayload;
        console.log("Received log:", payload);

        if (
          payload.event === "chat_message" &&
          payload.role &&
          payload.content &&
          (payload.role === "student" || payload.role === "teacher")
        ) {
          setChatMessages((prev) => [
            ...prev,
            { ...payload, animated: payload.score !== undefined ? false : undefined } as ChatMessagePayload,
          ]);
        } else if (payload.event === "agent_end" && payload.method === "eval_reply") {
          const evalPayload = payload as AgentEndEvalPayload;

          evaluationCounter.current += 1;
          const baseScore = 0.3 + evaluationCounter.current * 0.05;
          const noise = Math.random() * 0.2 - 0.1;
          let mockScore = baseScore + noise;
          mockScore = Math.max(0, Math.min(1, mockScore));
          console.log(
            `Mock Score Generated (Eval #${evaluationCounter.current}): ${mockScore.toFixed(3)} (Original: ${
              evalPayload.score
            })`
          );

          const newScoreEntry = { score: mockScore, timestamp: Date.now() };
          setScoreHistory((prevHistory) => {
            const updatedHistory = [...prevHistory, newScoreEntry];
            setAverageScore(calculateAverageScore(updatedHistory));
            return updatedHistory;
          });

          if (mockScore >= 0.7) {
            setCurrentStreak((prev) => {
              const newStreak = prev + 1;
              if (newStreak >= 3) {
                setShowStreakAnimation(true);
                setTimeout(() => setShowStreakAnimation(false), 3000);
              }
              return newStreak;
            });
          } else {
            setCurrentStreak(0);
          }

          setChatMessages((prevChatMessages) => {
            let lastStudentMessageIndex = -1;
            for (let i = prevChatMessages.length - 1; i >= 0; i--) {
              if (prevChatMessages[i].role === "student" && prevChatMessages[i].score === undefined) {
                lastStudentMessageIndex = i;
                break;
              }
            }

            if (lastStudentMessageIndex !== -1) {
              const updatedMessages = [...prevChatMessages];
              updatedMessages[lastStudentMessageIndex] = {
                ...updatedMessages[lastStudentMessageIndex],
                score: mockScore,
                feedback: evalPayload.feedback,
                animated: false,
              };
              return updatedMessages;
            } else {
              const lastMessage = prevChatMessages[prevChatMessages.length - 1];
              if (lastMessage?.role === "student") {
                const updatedMessages = [...prevChatMessages];
                updatedMessages[prevChatMessages.length - 1] = {
                  ...lastMessage,
                  score: mockScore,
                  feedback: evalPayload.feedback,
                  animated: false,
                };
                return updatedMessages;
              } else {
                console.warn("Received eval_reply event, but couldn't find suitable student message to update.");
                return prevChatMessages;
              }
            }
          });
        } else {
          setLogMessages((prev) => [...prev, payload]);
        }
      })
      .subscribe(async (status) => {
        if (status === "SUBSCRIBED") {
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
      <h1 className="text-2xl font-bold mb-4">
        Session {sessionId} (
        {isConnected ? <span className="text-green-600">Connected</span> : <span className="text-red-600">Disconnected</span>})
      </h1>

      <div className="space-y-4 border rounded-lg p-4 h-[70vh] overflow-y-auto bg-slate-50 mb-6">
        {chatMessages.length === 0 ? (
          <p className="text-gray-500 text-center pt-4">Waiting for messages...</p>
        ) : (
          chatMessages.map((msg, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className={`flex items-end gap-2 ${msg.role === "student" ? "justify-start" : "justify-end"}`}
            >
              {msg.role === "student" && (
                <>
                  <Image
                    src={student_image || "/placeholder.svg?height=32&width=32&query=student"}
                    alt="Student"
                    width={32}
                    height={32}
                    className="rounded-full"
                  />
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
                  <Image
                    src={teacher_image || "/placeholder.svg?height=32&width=32&query=teacher"}
                    alt="Teacher"
                    width={32}
                    height={32}
                    className="rounded-full"
                  />
                </>
              )}
              {msg.role === "student" && msg.score !== undefined && (
                <AnimatePresence>
                  <motion.div
                    key={`score-${index}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, type: "spring", delay: 0.2 }}
                    className="flex items-center gap-1 mt-1 ml-10 text-xs"
                    onAnimationComplete={() => {
                      if (!msg.animated) {
                        setChatMessages((prev) => prev.map((m, i) => (i === index ? { ...m, animated: true } : m)));
                      }
                    }}
                  >
                    <motion.div
                      initial={!msg.animated ? { scale: 0 } : { scale: 1 }}
                      animate={{ scale: 1, rotate: !msg.animated && msg.score >= 0.7 ? [0, 15, -15, 0] : 0 }}
                      transition={{
                        duration: 0.5,
                        type: "spring",
                        bounce: 0.5,
                        delay: 0.3,
                      }}
                    >
                      {msg.score >= 0.7 ? (
                        <ThumbsUp className="h-4 w-4 text-green-600 flex-shrink-0" />
                      ) : msg.score >= 0.4 ? (
                        <Smile className="h-4 w-4 text-yellow-600 flex-shrink-0" />
                      ) : (
                        <ThumbsDown className="h-4 w-4 text-red-600 flex-shrink-0" />
                      )}
                    </motion.div>

                    <motion.span
                      initial={!msg.animated ? { width: 0, opacity: 0 } : { width: "auto", opacity: 1 }}
                      animate={{ width: "auto", opacity: 1 }}
                      transition={{ duration: 0.3, delay: 0.4 }}
                      className={`font-medium px-2 py-1 rounded overflow-hidden ${
                        msg.score >= 0.7
                          ? "bg-green-100 text-green-700 shadow-[0_0_8px_rgba(34,197,94,0.4)]"
                          : msg.score >= 0.4
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      <span>Score: {msg.score.toFixed(2)}</span>
                    </motion.span>

                    {msg.feedback && msg.feedback !== "N/A" && (
                      <motion.span
                        initial={!msg.animated ? { opacity: 0, x: -10 } : { opacity: 1, x: 0 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: 0.6 }}
                        className="text-gray-500 italic ml-1 truncate max-w-[150px] sm:max-w-xs"
                      >
                        {msg.feedback}
                      </motion.span>
                    )}
                  </motion.div>
                </AnimatePresence>
              )}
            </motion.div>
          ))
        )}
        <div ref={chatEndRef} />
      </div>

      <AnimatePresence>
        {currentStreak >= 2 && (
          <motion.div
            initial={{ height: 0, opacity: 0, y: -20 }}
            animate={{ height: "auto", opacity: 1, y: 0 }}
            exit={{ height: 0, opacity: 0, y: -10 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="mb-6 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-lg p-3 text-white flex items-center justify-between overflow-hidden shadow-lg"
          >
            <div className="flex items-center">
              <motion.div
                animate={{ rotate: showStreakAnimation ? [0, 15, -10, 5, 0] : 0 }}
                transition={{ duration: 0.6, type: "spring" }}
                className="mr-3 text-2xl"
              >
                🔥
              </motion.div>
              <div>
                <h3 className="font-bold text-lg">Hot Streak: {currentStreak}</h3>
                <p className="text-sm opacity-90">Keep up the great answers!</p>
              </div>
            </div>
            {showStreakAnimation && (
              <motion.div
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: [0, 1.2, 1], rotate: 0 }}
                transition={{ duration: 0.5, type: "spring", bounce: 0.5 }}
                className="px-3 py-1 bg-white text-purple-600 rounded-full font-bold"
              >
                +{currentStreak} streak!
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mb-8 border rounded-lg p-4 bg-white shadow-sm relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
          {[...Array(10)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute rounded-full bg-indigo-500 opacity-5"
              initial={{
                x: `${Math.random() * 100}%`,
                y: `${Math.random() * 100}%`,
                scale: Math.random() * 0.3 + 0.3,
              }}
              animate={{
                y: [`${Math.random() * 100}%`, `${Math.random() * 100}%`],
                x: [`${Math.random() * 100}%`, `${Math.random() * 100}%`],
              }}
              transition={{
                duration: Math.random() * 15 + 15,
                repeat: Number.POSITIVE_INFINITY,
                repeatType: "mirror",
                ease: "easeInOut",
              }}
              style={{
                width: Math.random() * 20 + 10,
                height: Math.random() * 20 + 10,
              }}
            />
          ))}
        </div>

        <div className="relative z-10">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">Session Performance</h2>

          <div className="flex flex-col md:flex-row gap-6">
            <div className="flex-1 bg-slate-50/80 backdrop-blur-sm rounded-lg p-4 flex flex-col items-center justify-center border border-slate-200">
              <h3 className="text-lg font-medium text-gray-700 mb-2">Average Score</h3>
              {averageScore !== null ? (
                <div className="relative text-center">
                  <motion.div
                    key={averageScore}
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.5, type: "spring" }}
                    className={`text-4xl font-bold ${
                      averageScore >= 0.7 ? "text-green-600" : averageScore >= 0.4 ? "text-yellow-600" : "text-red-600"
                    }`}
                  >
                    {averageScore.toFixed(2)}
                  </motion.div>
                  <motion.div
                    className="w-full h-2 bg-gray-200 rounded-full mt-3 overflow-hidden"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                  >
                    <motion.div
                      className={`h-full rounded-full ${
                        averageScore >= 0.7 ? "bg-green-500" : averageScore >= 0.4 ? "bg-yellow-500" : "bg-red-500"
                      }`}
                      initial={{ width: "0%" }}
                      animate={{ width: `${averageScore * 100}%` }}
                      transition={{ duration: 0.8, type: "spring", delay: 0.2 }}
                    />
                  </motion.div>
                </div>
              ) : (
                <p className="text-gray-500 mt-4">No scores yet</p>
              )}
            </div>

            <div className="flex-1 bg-slate-50/80 backdrop-blur-sm rounded-lg p-4 border border-slate-200">
              <h3 className="text-lg font-medium text-gray-700 mb-3">Score Progression</h3>
              {scoreHistory.length > 0 ? (
                <ResponsiveContainer width="100%" height={150}>
                  <BarChart
                    data={scoreHistory.map((item, index) => ({
                      name: `Eval ${index + 1}`,
                      score: item.score,
                    }))}
                    margin={{ top: 5, right: 5, left: -25, bottom: 5 }}
                  >
                    <XAxis dataKey="name" fontSize={10} />
                    <YAxis domain={[0, 1]} fontSize={10} />
                    <Tooltip
                      contentStyle={{ fontSize: "12px", padding: "4px 8px" }}
                      itemStyle={{ padding: 0 }}
                      labelStyle={{ marginBottom: "4px" }}
                    />
                    <Bar
                      dataKey="score"
                      isAnimationActive={true}
                      animationDuration={800}
                      animationEasing="ease-out"
                      fill="url(#scoreGradient)"
                      radius={[3, 3, 0, 0]}
                      barSize={20}
                    />
                    {/* Define gradient */}
                    <defs>
                      <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#818cf8" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0.9} />
                      </linearGradient>
                    </defs>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[150px] flex items-center justify-center">
                  <p className="text-gray-500">No score history yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <Collapsible className="mt-8 border rounded-md bg-white shadow-sm">
        <CollapsibleTrigger className="flex justify-between items-center w-full px-4 py-3 text-left font-medium text-gray-700 hover:bg-gray-50 rounded-t-md">
          <h2 className="text-xl font-semibold">Detailed Event Log</h2>
          <ChevronsUpDownIcon className="h-5 w-5 text-gray-500" />
        </CollapsibleTrigger>
        <CollapsibleContent className="p-4 border-t">
          <div className="bg-gray-900 text-green-400 font-mono p-3 rounded-md overflow-x-auto text-xs max-h-60 overflow-y-auto">
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
