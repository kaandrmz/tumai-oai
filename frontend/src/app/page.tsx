"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import Image from "next/image";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const student_image = "/student.png";

type Teacher = {
  id: string;
  name: string;
  url: string;
  logo_url: string;
};

export default function Home() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [teachers, setTeachers] = useState<Teacher[]>([]);

  const fetchTeachers = useCallback(async () => {
    setIsLoading(true);
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
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTeachers();
    const intervalId = setInterval(fetchTeachers, 5000);

    return () => clearInterval(intervalId);
  }, [fetchTeachers]);

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <Button onClick={fetchTeachers} disabled={isLoading}>
          {isLoading ? "Refreshing..." : "Refresh"}
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
                        <DropdownMenuItem>
                          <Link href={`/session/${teacher.id}`}>Train {"->"}</Link>
                        </DropdownMenuItem>
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
