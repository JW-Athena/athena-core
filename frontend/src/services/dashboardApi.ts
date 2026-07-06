import type { DashboardResponse } from "../types/dashboard";

const API_URL = "http://127.0.0.1:8000";

export async function getDashboardSummary(): Promise<DashboardResponse> {
  const response = await fetch(`${API_URL}/dashboard/summary`);

  if (!response.ok) {
    throw new Error("Dashboard summary request failed");
  }

  return await response.json();
}