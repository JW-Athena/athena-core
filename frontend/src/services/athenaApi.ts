import type { AthenaResponse } from "../types/athena";

const API_URL = "http://127.0.0.1:8000";
const DEFAULT_MISSION_PATH = "D:\\JW\\athena-core\\backend\\sample_tender.txt";

export type MissionStatus = "pending_approval" | "completed" | string;

export type ExecutiveMissionResponse = {
  engine?: string;
  status?: string;
  mission?: string;
  mission_status?: MissionStatus;
  executive_response?: {
    summary?: string;
    recommended_next_action?: string;
    requires_approval?: boolean;
  };
  mission_evaluation?: {
    confidence?: number;
    decision_ready?: boolean;
    approval_required?: boolean;
  };
  approval_request?: {
    approval_id?: string;
    reason?: string;
    required_action?: string;
  } | null;
};

export type ExecutiveReasoningResponse = {
  engine?: string;
  status?: string;
  question?: string;
  reasoning_domain?: string;
  evidence?: Array<{
    source?: string;
    summary?: string;
    data?: unknown;
  }>;
  key_findings?: string[];
  executive_recommendation?: string;
  executive_explanation?: string;
  confidence?: number;
  recommended_next_action?: string;
  requires_executive_attention?: boolean;
};

export type TenderExecutiveResponse = {
  engine?: string;
  status?: string;
  question?: string;
  path?: string;
  executive_summary?: string;
  bid_decision?: "Bid" | "No Bid" | "Review" | string;
  confidence?: number;
  commercial_risk?: string;
  technical_risk?: string;
  key_blockers?: string[];
  required_departments?: string[];
  recommended_next_actions?: string[];
  executive_reasoning?: string;
  executive_brief?: Record<string, unknown>;
};

export async function askAthena(
  question: string
): Promise<AthenaResponse> {
  const formData = new FormData();

  formData.append("question", question);
  formData.append("limit", "5");

  const response = await fetch(
    `${API_URL}/engine/009/answer`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error("ATHENA backend is unavailable.");
  }

  return await response.json();
}

export async function executeMission(mission: string): Promise<ExecutiveMissionResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}/athena/brain/execute-mission`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        mission,
        path: DEFAULT_MISSION_PATH,
      }),
    });
  } catch {
    throw new Error("ATHENA backend is not reachable.");
  }

  if (!response.ok) {
    throw new Error("ATHENA backend is not reachable.");
  }

  return await response.json();
}

export async function executeExecutiveReasoning(question: string): Promise<ExecutiveReasoningResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}/athena/reasoning/executive`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
      }),
    });
  } catch {
    throw new Error("I cannot reach the Executive Brain right now.");
  }

  if (!response.ok) {
    throw new Error("I cannot reach the Executive Brain right now.");
  }

  return await response.json();
}

export async function executeTenderExecutive(question: string): Promise<TenderExecutiveResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}/athena/executive/tender`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        path: DEFAULT_MISSION_PATH,
      }),
    });
  } catch {
    throw new Error("I cannot reach the Executive Brain right now.");
  }

  if (!response.ok) {
    throw new Error("I cannot reach the Executive Brain right now.");
  }

  return await response.json();
}
