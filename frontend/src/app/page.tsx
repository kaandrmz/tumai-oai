"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import Image from "next/image";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

const student_image = "/student.png";

type Task = {
  id: string;
  title: string;
  description: string;
};

type Teacher = {
  id: string;
  name: string;
  url: string;
  logo_url: string;
  tasks: Task[];
};

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [teachers, setTeachers] = useState<Teacher[]>([]);

  const router = useRouter();

  const fetchTeachers = useCallback(async () => {
    setError(null);
    try {
      const response = await fetch("/api/fetch-teachers");
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      const data: Teacher[] = await response.json();
      console.log("Fetched teachers:", data);
      setTeachers(data);
    } catch (e: unknown) {
      console.error("Failed to fetch teachers:", e);
      if (e instanceof Error) {
        setError(e.message || "Failed to load teachers.");
      } else {
        setError("An unknown error occurred.");
      }
    } finally {
      console.log("Fetching teachers completed.");
    }
  }, []);

  const startSession = useCallback(
    async (teacher: Teacher, task: Task) => {
      setIsLoading(true);
      setError(null);

      // Generate a new session ID on the client side
      const newSessionId = Math.floor(Math.random() * (99999 - 10000 + 1)) + 10000;
      console.log(`Requesting to start training with session ID: ${newSessionId}`);

      try {
        // Call the new /api/start-training endpoint
        const response = await fetch("/api/start-training", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            teacherId: teacher.id,
            // Ensure taskId is parsed to a number if it comes as a string
            taskId: parseInt(task.id, 10),
            sessionId: newSessionId,
          }),
        });

        const responseBody = await response.json(); // Always try to parse JSON

        if (!response.ok) {
          // Use the error message from the backend if available
          throw new Error(responseBody.error || `HTTP error! status: ${response.status}`);
        }

        console.log("Training session started successfully (backend response):", responseBody);

        // Redirect to the session page using the ID we generated
        // add a two second delay
        setTimeout(() => {
          router.push(`/session/${newSessionId}`);
        }, 2000);
      } catch (e: unknown) {
        console.error("Failed to start training session:", e);
        if (e instanceof Error) {
          setError(e.message || "Failed to start training session.");
        } else {
          setError("An unknown error occurred while starting the session.");
        }
      } finally {
        setIsLoading(false);
      }
    },
    [router]
  ); // Added router to dependency array

  useEffect(() => {
    fetchTeachers();
    const intervalId = setInterval(fetchTeachers, 5000);

    return () => clearInterval(intervalId);
  }, [fetchTeachers]);

  const handleTaskClick = (teacher: Teacher, task: Task) => {
    startSession(teacher, task);
  };

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <Button onClick={fetchTeachers} disabled={isLoading}>
          {isLoading ? (
            <div className="flex items-center gap-2">
              <span>Loading...</span>
              <Loader2 className="animate-spin" />
            </div>
          ) : (
            "Refresh"
          )}
        </Button>
      </div>
      <div className="flex flex-row items-center mb-6">
        <div className="flex w-1/2 flex-col items-center">
          <Image src={student_image} alt="Student" width={480} height={480} />
          <p>Student</p>
        </div>
        <div className="flex w-1/2 flex-col items-center">
          {isLoading && teachers.length === 0 && <p>Loading Training Agents...</p>}
          {error && <p className="text-red-500 mb-4">Error: {error}</p>}
          {!isLoading && teachers.length === 0 && !error && <p>No Training Agents Found.</p>}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Start</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {teachers.map((teacher) => (
                <TableRow key={teacher.id}>
                  <TableCell>
                    <div className="flex flex-row items-center gap-2">
                      {teacher.name}
                      <Image src={teacher.logo_url} alt={teacher.name} width={48} height={48} />
                    </div>
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button>Train {"->"}</Button>
                      </DropdownMenuTrigger>

                      <DropdownMenuContent>
                        {teacher.tasks.map((task) => (
                          <DropdownMenuItem key={task.id}>
                            <Button variant="link" onClick={() => handleTaskClick(teacher, task)}>
                              {task.title}
                            </Button>
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
