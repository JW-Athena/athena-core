import type {
  ContractExecutiveResponse,
  DailyBriefingExecutiveResponse,
  ExecutiveMissionResponse,
  ExecutiveReasoningResponse,
  MeetingExecutiveResponse,
  ProcurementExecutiveResponse,
  SupplierExecutiveResponse,
  TenderExecutiveResponse,
} from "./athenaApi";

export type ConversationProtocolLine = {
  stage: "recognition" | "context" | "decision" | "reason" | "offer";
  text: string;
};

export type ConversationProtocolResult = {
  lines: ConversationProtocolLine[];
  offer: string;
};

const greetings = {
  morning: ["Good morning, Wassim.", "Welcome back, Wassim."],
  afternoon: ["Good afternoon, Wassim.", "Welcome back, Wassim."],
  evening: ["Good evening, Wassim.", "Welcome back, Wassim."],
};

const contextLines = {
  mission: "I've completed my assessment.",
  reasoning: "I've reviewed the available evidence.",
  error: "I cannot complete the assessment from here.",
};

const offers = [
  "Would you like to understand my reasoning?",
  "Would you like me to explain?",
  "Would you like to review the evidence?",
];

export function createMissionConversation(result: ExecutiveMissionResponse | null): ConversationProtocolResult {
  const requiresApproval =
    result?.mission_status === "pending_approval" ||
    Boolean(result?.executive_response?.requires_approval) ||
    Boolean(result?.mission_evaluation?.approval_required);
  const recommendation = result?.executive_response?.recommended_next_action || result?.executive_response?.summary || "";
  const summary = result?.executive_response?.summary || "";
  const approvalReason = result?.approval_request?.reason || result?.approval_request?.required_action || "";
  const decision = requiresApproval
    ? "Further clarification is required."
    : normalizeDecision(recommendation, "I recommend executive review before proceeding.");
  const reason = normalizeReason(
    approvalReason || summary,
    requiresApproval
      ? "The mission requires executive approval before ATHENA can continue."
      : "The available assessment supports the recommended next action.",
  );

  return createConversation({
    context: contextLines.mission,
    decision,
    reason,
    offer: offers[0],
  });
}

export function createReasoningConversation(result: ExecutiveReasoningResponse): ConversationProtocolResult {
  const decision = normalizeDecision(
    result.executive_recommendation || "",
    "Further clarification is required.",
  );
  const reason = normalizeReason(
    result.key_findings?.[0] || result.executive_explanation || "",
    "The available evidence is not sufficient for a stronger decision.",
  );

  return createConversation({
    context: "I've finished evaluating this decision.",
    decision,
    reason,
    offer: offers[2],
  });
}

export function createTenderConversation(result: TenderExecutiveResponse): ConversationProtocolResult {
  const decision = tenderDecisionLine(result.bid_decision);
  const reason = normalizeReason(
    result.key_blockers?.[0] || result.executive_reasoning || result.executive_summary || "",
    "The tender requires further executive review before ICC commits.",
  );

  return createConversation({
    context: "I've completed my tender assessment.",
    decision,
    reason,
    offer: "Would you like me to present the executive briefing?",
  });
}

export function createSupplierConversation(result: SupplierExecutiveResponse): ConversationProtocolResult {
  const decision = supplierDecisionLine(result.supplier_decision);
  const reason = normalizeReason(
    result.key_concerns?.[0] || result.key_strengths?.[0] || result.executive_reasoning || result.executive_summary || "",
    "The supplier evidence requires further procurement review.",
  );

  return createConversation({
    context: "I've completed my supplier assessment.",
    decision,
    reason,
    offer: "Would you like me to review supplier evidence?",
  });
}

export function createContractConversation(result: ContractExecutiveResponse): ConversationProtocolResult {
  const decision = executiveDecisionLine(result.contract_decision, "REVIEW");
  const reason = normalizeReason(
    result.key_risks?.[0] || result.missing_information?.[0] || result.executive_reasoning || result.executive_summary || "",
    "The contract requires further executive review before commitment.",
  );

  return createConversation({
    context: "I've completed my contract assessment.",
    decision: `My recommendation is ${decision}.`,
    reason,
    offer: "Would you like me to review the contract reasoning?",
  });
}

export function createProcurementConversation(result: ProcurementExecutiveResponse): ConversationProtocolResult {
  const decision = executiveDecisionLine(result.procurement_decision, "REVIEW");
  const reason = normalizeReason(
    result.executive_reasoning || result.recommended_actions?.[0] || result.executive_summary || "",
    "The procurement evidence requires further review before commitment.",
  );

  return createConversation({
    context: "I've completed my procurement assessment.",
    decision: `My recommendation is ${decision}.`,
    reason,
    offer: "Would you like me to review the procurement reasoning?",
  });
}

export function createMeetingConversation(result: MeetingExecutiveResponse): ConversationProtocolResult {
  const reason = normalizeReason(
    result.risks_to_raise?.[0] || result.key_talking_points?.[0] || result.executive_summary || "",
    "The meeting should stay focused on decision, owner, and next action.",
  );

  return createConversation({
    context: "I've prepared the meeting.",
    decision: normalizeDecision(result.recommended_position || result.meeting_objective || "", "I recommend entering with a clear decision position."),
    reason,
    offer: "Would you like me to walk through the agenda?",
  });
}

export function createDailyBriefingConversation(result: DailyBriefingExecutiveResponse): ConversationProtocolResult {
  const reason = normalizeReason(
    result.risks?.[0] || result.executive_summary || "",
    "The current operating picture supports a focused executive day.",
  );

  return createConversation({
    context: result.greeting || "Good morning, Wassim.",
    decision: normalizeDecision(result.recommended_focus || result.priorities?.[0] || "", "I recommend setting one executive priority for today."),
    reason,
    offer: "Would you like me to expand the briefing?",
  });
}

export function createCompletionConversation(): ConversationProtocolResult {
  return {
    offer: "View Executive Brief",
    lines: [
      { stage: "context", text: "I've completed the assessment." },
      { stage: "offer", text: "The executive briefing is ready." },
    ],
  };
}

export function createErrorConversation(message: string): ConversationProtocolResult {
  return createConversation({
    context: contextLines.error,
    decision: "Further clarification is required.",
    reason: normalizeReason(message, "I cannot reach the Executive Brain right now."),
    offer: offers[1],
  });
}

export function protocolDelayForNextLine(nextLine: ConversationProtocolLine | undefined) {
  if (!nextLine) {
    return 650;
  }

  if (nextLine.stage === "offer") {
    return 1700;
  }

  return 1050;
}

export function currentProtocolGreeting() {
  const hour = new Date().getHours();
  const period = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  return greetings[period][0];
}

function createConversation({
  context,
  decision,
  reason,
  offer,
}: {
  context: string;
  decision: string;
  reason: string;
  offer: string;
}): ConversationProtocolResult {
  return {
    offer,
    lines: [
      { stage: "recognition", text: currentProtocolGreeting() },
      { stage: "context", text: ensureSentence(context) },
      { stage: "decision", text: ensureSentence(decision) },
      { stage: "reason", text: ensureSentence(reason) },
      { stage: "offer", text: ensureSentence(offer) },
    ],
  };
}

function normalizeDecision(value: string, fallback: string) {
  const clean = firstSentence(value);
  if (!clean) {
    return fallback;
  }

  if (/^(i recommend|i do not recommend|further clarification is required)/i.test(clean)) {
    return clean;
  }

  return `I recommend ${clean.charAt(0).toLowerCase()}${clean.slice(1)}`;
}

function tenderDecisionLine(decision: string | undefined) {
  const normalized = String(decision || "").toLowerCase();
  if (normalized === "bid") {
    return "My recommendation is BID.";
  }
  if (normalized === "no bid") {
    return "My recommendation is DO NOT BID.";
  }
  return "My recommendation is REVIEW FURTHER.";
}

function supplierDecisionLine(decision: string | undefined) {
  const normalized = String(decision || "").toLowerCase();
  if (normalized === "continue") {
    return "My recommendation is CONTINUE.";
  }
  if (normalized === "replace") {
    return "My recommendation is REPLACE.";
  }
  if (normalized === "monitor") {
    return "My recommendation is MONITOR.";
  }
  return "My recommendation is REVIEW.";
}

function executiveDecisionLine(decision: string | undefined, fallback: string) {
  return String(decision || fallback).toUpperCase();
}

function normalizeReason(value: string, fallback: string) {
  return firstSentence(value) || fallback;
}

function firstSentence(value: string) {
  const clean = String(value || "").replace(/\s+/g, " ").trim();
  if (!clean) {
    return "";
  }

  const match = clean.match(/.*?[.!?](\s|$)/);
  return (match ? match[0] : clean).trim();
}

function ensureSentence(value: string) {
  const clean = String(value || "").trim();
  if (!clean) {
    return "";
  }

  return /[.!?]$/.test(clean) ? clean : `${clean}.`;
}
