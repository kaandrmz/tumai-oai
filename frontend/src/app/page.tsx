"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Session } from "@/types";

const SessionTable = ({ title, sessions }: { title: string; sessions: Session[] }) => {
  if (sessions.length === 0) {
    return null; // Don't render table if no sessions
  }
  return (
    <div className="mb-8">
      <h2 className="text-xl font-semibold mb-3">{title}</h2>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Session ID</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sessions.map((session) => (
              <TableRow key={session.id}>
                <TableCell>
                  <Link href={`/session/${session.id}`} className="text-blue-600 hover:underline">
                    {session.id}
                  </Link>
                </TableCell>
                <TableCell>{session.status}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/fetch-sessions");
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      const data: Session[] = await response.json();
      // Sort sessions: active first, then by ID descending (newest first)
      const sortedData = (Array.isArray(data) ? data : []).sort((a, b) => {
        if (a.status === "active" && b.status !== "active") return -1;
        if (a.status !== "active" && b.status === "active") return 1;
        // Assuming session IDs are numeric strings, sort descending
        return parseInt(b.id, 10) - parseInt(a.id, 10);
      });
      setSessions(sortedData);
    } catch (e: unknown) {
      console.error("Failed to fetch sessions:", e);
      if (e instanceof Error) {
        setError(e.message || "Failed to load sessions.");
      } else {
        setError("An unknown error occurred.");
      }
      setSessions([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    const intervalId = setInterval(fetchSessions, 5000); // Refresh every 5 seconds

    return () => clearInterval(intervalId);
  }, [fetchSessions]);

  const activeSessions = sessions.filter((s) => s.status === "active");
  const finishedSessions = sessions.filter((s) => s.status !== "active"); // Includes finished, crashed, unknown etc.

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Session Dashboard</h1>
        <Button onClick={fetchSessions} disabled={isLoading}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {isLoading && sessions.length === 0 && <p>Loading sessions...</p>}
      {error && <p className="text-red-500 mb-4">Error: {error}</p>}
      {!isLoading && sessions.length === 0 && !error && <p>No sessions found.</p>}

      <SessionTable title="Active Sessions" sessions={activeSessions} />
      <SessionTable title="Finished / Other Sessions" sessions={finishedSessions} />
    </div>
  );
}
