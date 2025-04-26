export interface Session {
  id: string;
  status: "active" | "completed" | "failed";
}