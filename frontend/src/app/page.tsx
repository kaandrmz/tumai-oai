"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Session } from "@/types";

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
      setSessions(Array.isArray(data) ? data : []);
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
    const intervalId = setInterval(fetchSessions, 5000);

    return () => clearInterval(intervalId);
  }, [fetchSessions]);

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Sessions</h1>
        <Button onClick={fetchSessions} disabled={isLoading}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {error && <p className="text-red-500 mb-4">Error: {error}</p>}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Session ID</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && sessions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={2} className="text-center">
                  Loading sessions...
                </TableCell>
              </TableRow>
            ) : sessions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={2} className="text-center">
                  No sessions found.
                </TableCell>
              </TableRow>
            ) : (
              sessions.map((session) => (
                <TableRow key={session.id}>
                  <TableCell>
                    <Link href={`/session/${session.id}`} className="text-blue-600 hover:underline">
                      {session.id}
                    </Link>
                  </TableCell>
                  <TableCell>{session.status}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
