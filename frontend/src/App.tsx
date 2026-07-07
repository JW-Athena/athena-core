import { useEffect, useMemo, useState } from "react";
import "./App.css";

import { AppShell } from "./components/AppShell";
import { AthenaEnvironment } from "./components/AthenaEnvironment";
import { AthenaPresenceEngine } from "./components/AthenaPresenceEngine";
import { AthenaPresenceState } from "./components/athenaPresenceState";
import {
  executeContractExecutive,
  executeDailyBriefingExecutive,
  executeExecutiveReasoning,
  fetchAthenaEvents,
  type AthenaEvent,
  executeMeetingExecutive,
  executeProcurementExecutive,
  executeSupplierExecutive,
  executeTenderExecutive,
  type ContractExecutiveResponse,
  type DailyBriefingExecutiveResponse,
  type ExecutiveMissionResponse,
  type ExecutiveReasoningResponse,
  type MeetingExecutiveResponse,
  type ProcurementExecutiveResponse,
  type SupplierExecutiveResponse,
  type TenderExecutiveResponse,
} from "./services/athenaApi";
import {
  clearWorkspaceMemory,
  readWorkspaceMemory,
  updateWorkspaceMemory,
  type WorkspaceMemory,
} from "./services/workspaceMemory";
import {
  createErrorConversation,
  createCompletionConversation,
  currentProtocolGreeting,
  protocolDelayForNextLine,
  type ConversationProtocolLine,
} from "./services/conversationProtocol";
import { useAthenaPresenceEngine } from "./components/useAthenaPresenceEngine";

type WorkspaceRoute = {
  path: string;
  label: string;
  title: string;
  eyebrow: string;
};

const routes: WorkspaceRoute[] = [
  { path: "/", label: "The Chamber", title: "The Chamber", eyebrow: "ATHENA Chamber" },
  { path: "/missions", label: "Missions", title: "Mission Console", eyebrow: "Mission Control" },
  { path: "/approvals", label: "Approvals", title: "Approvals", eyebrow: "Executive Governance" },
  { path: "/operations", label: "Operations Center", title: "Operations Center", eyebrow: "Operational Command" },
  { path: "/knowledge", label: "Knowledge", title: "Knowledge", eyebrow: "Institutional Memory" },
  { path: "/organization", label: "Organization", title: "Organization", eyebrow: "Enterprise Context" },
  {
    path: "/strategic-objectives",
    label: "Strategic Objectives",
    title: "Strategic Objectives",
    eyebrow: "Executive Direction",
  },
  { path: "/settings", label: "Settings", title: "Settings", eyebrow: "System Controls" },
];

const defaultOrchestrationSteps = [
  "Executive objective received...",
  "Mission scope is being defined...",
  "Relevant executive capabilities are being aligned...",
  "Organizational knowledge is being consulted...",
  "Strategic impact is being evaluated...",
  "Executive recommendation is being prepared...",
  "Final briefing is being assembled...",
];

type ExecutionMode = "mission" | "reasoning" | "tender" | "supplier" | "contract" | "procurement" | "meeting" | "briefing" | null;
type MissionState =
  | "Mission Created"
  | "Mission Accepted"
  | "Executive Brain Activated"
  | "Departments Mobilized"
  | "Knowledge Expansion"
  | "Executive Consolidation"
  | "Executive Recommendation"
  | "Mission Complete";
type DepartmentPresence = {
  name: string;
  status: "Waiting" | "Working" | "Completed";
};

type MissionIntent = {
  hint: string;
  greeting: string;
};

function App() {
  const [currentPath, setCurrentPath] = useState(() => normalizePath(window.location.pathname));

  useEffect(() => {
    const onPopState = () => setCurrentPath(normalizePath(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const currentRoute = useMemo(
    () => routes.find((route) => route.path === currentPath) ?? routes[0],
    [currentPath],
  );

  const navigate = (path: string) => {
    const nextPath = normalizePath(path);
    window.history.pushState({}, "", nextPath);
    setCurrentPath(nextPath);
  };

  return (
    <AppShell
      routes={routes}
      currentPath={currentRoute.path}
      onNavigate={navigate}
      title={currentRoute.title}
      hideHeader={currentRoute.path === "/"}
    >
      <Chamber route={currentRoute} activePath={currentRoute.path} />
    </AppShell>
  );
}

function Chamber({ route, activePath }: { route: WorkspaceRoute; activePath: string }) {
  const [workspaceMemory, setWorkspaceMemory] = useState<WorkspaceMemory | null>(() => readWorkspaceMemory());
  const [arrivalRestState] = useState(() => (workspaceMemory ? AthenaPresenceState.WAITING : AthenaPresenceState.IDLE));
  const [arrivalExecutiveLine] = useState(() => chooseArrivalExecutiveLine(workspaceMemory));
  const hasCompletedObjectiveMemory = Boolean(
    cleanObjectiveText(workspaceMemory?.lastObjectiveText || workspaceMemory?.lastMission || "") &&
    (workspaceMemory?.lastObjectiveResponseReceived || workspaceMemory?.lastRecommendation),
  );
  const [arrivalComplete, setArrivalComplete] = useState(false);
  const [arrivalLines, setArrivalLines] = useState<string[]>([]);
  const [mission, setMission] = useState("");
  const [submittedMission, setSubmittedMission] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>(null);
  const [missionResult, setMissionResult] = useState<ExecutiveMissionResponse | null>(null);
  const [reasoningResult, setReasoningResult] = useState<ExecutiveReasoningResponse | null>(null);
  const [tenderResult, setTenderResult] = useState<TenderExecutiveResponse | null>(null);
  const [supplierResult, setSupplierResult] = useState<SupplierExecutiveResponse | null>(null);
  const [contractResult, setContractResult] = useState<ContractExecutiveResponse | null>(null);
  const [procurementResult, setProcurementResult] = useState<ProcurementExecutiveResponse | null>(null);
  const [meetingResult, setMeetingResult] = useState<MeetingExecutiveResponse | null>(null);
  const [briefingResult, setBriefingResult] = useState<DailyBriefingExecutiveResponse | null>(null);
  const [missionError, setMissionError] = useState("");
  const [protocolLines, setProtocolLines] = useState<ConversationProtocolLine[]>(() => buildMemorySpeech(workspaceMemory));
  const [visibleProtocolLines, setVisibleProtocolLines] = useState<ConversationProtocolLine[]>(() =>
    buildMemorySpeech(workspaceMemory),
  );
  const [showProtocolOffer, setShowProtocolOffer] = useState(false);
  const [briefOpen, setBriefOpen] = useState(false);
  const { presenceState, setPresenceState } = useAthenaPresenceEngine(
    workspaceMemory ? AthenaPresenceState.WAITING : AthenaPresenceState.BOOTING,
  );
  const [visibleSteps, setVisibleSteps] = useState<string[]>([]);
  const [orchestrationSteps, setOrchestrationSteps] = useState<string[]>(defaultOrchestrationSteps);
  const [missionStartedAt, setMissionStartedAt] = useState("");
  const [eventBaselineIds, setEventBaselineIds] = useState<string[]>([]);
  const [eventTimelineActive, setEventTimelineActive] = useState(false);
  const [missionState, setMissionState] = useState<MissionState>("Mission Created");
  const [departmentPresence, setDepartmentPresence] = useState<DepartmentPresence[]>([]);
  const missionIntent = detectMissionIntent(mission);
  const hasDraftMission = mission.trim().length > 0;
  const greetingMessage = missionIntent.hint ? missionIntent.greeting : missionIntent.greeting;
  const hasExecutiveResponse = Boolean(
    missionResult ||
    reasoningResult ||
    tenderResult ||
    supplierResult ||
    contractResult ||
    procurementResult ||
    meetingResult ||
    briefingResult,
  );
  const showExecutiveWorkspace = Boolean(
    submittedMission &&
    !missionError &&
    (isExecuting || hasExecutiveResponse || visibleSteps.length > 0),
  );
  const chamberLines = buildChamberLines({
    arrivalComplete,
    arrivalLines,
    missionIntent,
    submittedMission,
    visibleProtocolLines,
    isExecuting,
    missionError,
    greetingMessage,
  });

  useEffect(() => {
    setPresenceState(AthenaPresenceState.SPEAKING);

    const firstLineTimer = window.setTimeout(() => {
      setArrivalLines([arrivalGreeting()]);
    }, 720);
    const secondLineTimer = window.setTimeout(() => {
      setArrivalLines([arrivalGreeting(), arrivalExecutiveLine]);
    }, 1420);
    const completeTimer = window.setTimeout(() => {
      setArrivalComplete(true);
      setPresenceState(arrivalRestState);
    }, 2600);

    return () => {
      window.clearTimeout(firstLineTimer);
      window.clearTimeout(secondLineTimer);
      window.clearTimeout(completeTimer);
    };
  }, [arrivalExecutiveLine, arrivalRestState, setPresenceState]);

  useEffect(() => {
    if (!isExecuting || eventTimelineActive) {
      return;
    }

    if (visibleSteps.length >= orchestrationSteps.length) {
      return;
    }

    const timer = window.setTimeout(() => {
      setVisibleSteps((steps) => [...steps, orchestrationSteps[steps.length]]);
    }, visibleSteps.length === 0 ? 220 : 760);

    return () => window.clearTimeout(timer);
  }, [eventTimelineActive, isExecuting, orchestrationSteps, visibleSteps.length]);

  useEffect(() => {
    if (!isExecuting || !missionStartedAt) {
      return;
    }

    let cancelled = false;

    const readEvents = async () => {
      try {
        const result = await fetchAthenaEvents(80);
        if (cancelled) {
          return;
        }

        const events = currentExecutiveEvents(result.events || [], eventBaselineIds, missionStartedAt);
        const lines = executiveEventLines(events);
        if (lines.length > 0) {
          setEventTimelineActive(true);
          setVisibleSteps(lines);
        }
        setMissionState(deriveMissionState(events, hasExecutiveResponse));
        setDepartmentPresence(executiveDepartmentPresence(events));
      } catch {
        if (!cancelled) {
          setEventTimelineActive(false);
        }
      }
    };

    void readEvents();
    const timer = window.setInterval(() => {
      void readEvents();
    }, 700);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [eventBaselineIds, hasExecutiveResponse, isExecuting, missionStartedAt]);

  useEffect(() => {
    if (isExecuting) {
      return;
    }

    if (!missionResult && !reasoningResult && !tenderResult && !supplierResult && !contractResult && !procurementResult && !meetingResult && !briefingResult && !missionError) {
      return;
    }

    const conversation = missionError ? createErrorConversation(missionError) : createCompletionConversation();
    const lines = conversation.lines;

    if (protocolLines.length === 0) {
      const timer = window.setTimeout(() => {
        setProtocolLines(lines);
      }, visibleSteps.length > 0 ? 760 : 0);
      return () => window.clearTimeout(timer);
    }

    if (visibleProtocolLines.length >= protocolLines.length) {
      const timer = window.setTimeout(() => {
        if (isSpeaking) {
          setIsSpeaking(false);
          setShowProtocolOffer(true);
          if (missionError) {
            setPresenceState(AthenaPresenceState.ERROR);
            setWorkspaceMemory(
              updateWorkspaceMemory({
                lastPresenceState: AthenaPresenceState.ERROR,
              }),
            );
          } else if (reasoningResult || tenderResult || supplierResult || contractResult || procurementResult || meetingResult || briefingResult) {
            setMissionState("Mission Complete");
            setPresenceState(AthenaPresenceState.SUCCESS);
            setWorkspaceMemory(
              updateWorkspaceMemory({
                lastPresenceState: AthenaPresenceState.SUCCESS,
              }),
            );
          } else if (missionResult?.mission_status === "pending_approval") {
            setMissionState("Mission Complete");
            setPresenceState(AthenaPresenceState.APPROVAL);
            setWorkspaceMemory(
              updateWorkspaceMemory({
                lastPresenceState: AthenaPresenceState.APPROVAL,
              }),
            );
          } else {
            setMissionState("Mission Complete");
            setPresenceState(AthenaPresenceState.SUCCESS);
            setWorkspaceMemory(
              updateWorkspaceMemory({
                lastPresenceState: AthenaPresenceState.SUCCESS,
              }),
            );
          }
        }
      }, 650);

      return () => window.clearTimeout(timer);
    }

    const nextLine = protocolLines[visibleProtocolLines.length];
    const timer = window.setTimeout(
      () => {
        setVisibleProtocolLines((currentLines) => [...currentLines, protocolLines[currentLines.length]]);
      },
      visibleProtocolLines.length === 0 ? 450 : protocolDelayForNextLine(nextLine),
    );

    return () => window.clearTimeout(timer);
  }, [
    isSpeaking,
    isExecuting,
    missionError,
    missionResult,
    briefingResult,
    contractResult,
    meetingResult,
    protocolLines,
    procurementResult,
    reasoningResult,
    supplierResult,
    tenderResult,
    setPresenceState,
    visibleSteps.length,
    visibleProtocolLines.length,
  ]);

  useEffect(() => {
    if (isExecuting || isSpeaking || submittedMission) {
      return;
    }

    if (!arrivalComplete) {
      return;
    }

    if (!hasDraftMission) {
      setPresenceState(AthenaPresenceState.IDLE);
      return;
    }

    const timer = window.setTimeout(() => {
      setPresenceState(AthenaPresenceState.UNDERSTANDING);
    }, 260);

    return () => window.clearTimeout(timer);
  }, [arrivalComplete, hasDraftMission, isExecuting, isSpeaking, setPresenceState, submittedMission]);

  const handleExecuteMission = async () => {
    const nextMission = mission.trim();
    if (!nextMission) {
      return;
    }

    const executionStartedAt = new Date().toISOString();
    setSubmittedMission(nextMission);
    setMissionStartedAt(executionStartedAt);
    setEventBaselineIds([]);
    setEventTimelineActive(false);
    setMissionState("Mission Accepted");
    setDepartmentPresence([]);
    setOrchestrationSteps(buildOrchestrationSteps(nextMission));
    setVisibleSteps([]);
    setMissionResult(null);
    setReasoningResult(null);
    setTenderResult(null);
    setSupplierResult(null);
    setContractResult(null);
    setProcurementResult(null);
    setMeetingResult(null);
    setBriefingResult(null);
    setMissionError("");
    setProtocolLines([]);
    setVisibleProtocolLines([]);
    setShowProtocolOffer(false);
    setBriefOpen(false);
    setIsSpeaking(false);
    setPresenceState(AthenaPresenceState.THINKING);
    setWorkspaceMemory(
      updateWorkspaceMemory({
        lastMission: nextMission,
        lastObjectiveText: nextMission,
        lastObjectiveTimestamp: new Date().toISOString(),
        lastObjectiveResponseReceived: false,
        lastObjectiveStatus: "assessment in progress",
        lastPresenceState: AthenaPresenceState.THINKING,
      }),
    );

    const baselineIds = await readAthenaEventBaseline();
    setEventBaselineIds(baselineIds);
    setIsExecuting(true);
    let responseReceived = false;

    try {
      if (looksLikeContractQuestion(nextMission)) {
        setExecutionMode("contract");
        setVisibleSteps([]);
        const result = await executeContractExecutive(nextMission);
        setContractResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            ...completedObjectiveMemory(nextMission),
            lastRecommendation: result.contract_decision ? `Contract recommendation: ${result.contract_decision}` : "",
            lastApproval: result.key_risks?.[0] || result.missing_information?.[0] || "",
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      } else if (looksLikeProcurementQuestion(nextMission)) {
        setExecutionMode("procurement");
        setVisibleSteps([]);
        const supplierName = extractSupplierName(nextMission);
        const result = await executeProcurementExecutive(nextMission, supplierName);
        setProcurementResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            ...completedObjectiveMemory(nextMission),
            lastRecommendation: result.procurement_decision ? `Procurement recommendation: ${result.procurement_decision}` : "",
            lastApproval: result.recommended_actions?.[0] || "",
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      } else if (looksLikeMeetingQuestion(nextMission)) {
        setExecutionMode("meeting");
        setVisibleSteps([]);
        const result = await executeMeetingExecutive(nextMission);
        setMeetingResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            ...completedObjectiveMemory(nextMission),
            lastRecommendation: result.recommended_position || result.meeting_objective || "",
            lastApproval: result.risks_to_raise?.[0] || "",
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      } else if (looksLikeDailyBriefingQuestion(nextMission)) {
        setExecutionMode("briefing");
        setVisibleSteps([]);
        const result = await executeDailyBriefingExecutive();
        setBriefingResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            ...completedObjectiveMemory(nextMission),
            lastRecommendation: result.recommended_focus || result.priorities?.[0] || "",
            lastApproval: result.risks?.[0] || "",
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      } else if (looksLikeTenderBidQuestion(nextMission)) {
        setExecutionMode("tender");
        setVisibleSteps([]);
        const result = await executeTenderExecutive(nextMission);
        setTenderResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            ...completedObjectiveMemory(nextMission),
            lastRecommendation: result.bid_decision ? `Tender recommendation: ${result.bid_decision}` : "",
            lastApproval: result.key_blockers?.[0] || "",
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      } else if (looksLikeSupplierQuestion(nextMission)) {
        const supplierName = extractSupplierName(nextMission);
        setExecutionMode("supplier");
        setVisibleSteps([]);
        const result = await executeSupplierExecutive(nextMission, supplierName);
        setSupplierResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            ...completedObjectiveMemory(nextMission),
            lastRecommendation: result.supplier_decision ? `Supplier recommendation: ${result.supplier_decision}` : "",
            lastApproval: result.key_concerns?.[0] || "",
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      } else if (looksLikeExecutiveQuestion(nextMission)) {
        setExecutionMode("reasoning");
        setVisibleSteps([]);
        const result = await executeExecutiveReasoning(nextMission);
        setReasoningResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            ...completedObjectiveMemory(nextMission),
            lastRecommendation: result.executive_recommendation || result.recommended_next_action || "",
            lastApproval: result.requires_executive_attention ? "This requires executive attention." : "",
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      } else {
        setExecutionMode("reasoning");
        setVisibleSteps([]);
        const result = await executeExecutiveReasoning(nextMission);
        setReasoningResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            ...completedObjectiveMemory(nextMission),
            lastRecommendation: result.executive_recommendation || result.recommended_next_action || "",
            lastApproval: result.requires_executive_attention ? "This requires executive attention." : "",
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      }
      setPresenceState(AthenaPresenceState.SPEAKING);
      setMissionState("Executive Recommendation");
      responseReceived = true;
      setIsSpeaking(true);
    } catch (error) {
      const errorMessage =
        looksLikeExecutiveSkillQuestion(nextMission)
        ? "I cannot reach the Executive Brain right now."
        : error instanceof Error
          ? error.message
          : "ATHENA cannot complete the assessment right now.";
      setMissionError(errorMessage);
      setWorkspaceMemory(
        updateWorkspaceMemory({
          lastMission: nextMission,
          lastObjectiveText: nextMission,
          lastObjectiveTimestamp: new Date().toISOString(),
          lastObjectiveResponseReceived: false,
          lastObjectiveStatus: "assessment paused",
          lastRecommendation: "",
          lastApproval: "",
          lastGreeting: currentProtocolGreeting(),
          lastPresenceState: AthenaPresenceState.ERROR,
        }),
      );
      setPresenceState(
        looksLikeExecutiveSkillQuestion(nextMission)
          ? AthenaPresenceState.ERROR
          : AthenaPresenceState.SPEAKING,
      );
      setIsSpeaking(true);
    } finally {
      try {
        const result = await fetchAthenaEvents(80);
        const events = currentExecutiveEvents(result.events || [], baselineIds, executionStartedAt);
        const lines = executiveEventLines(events);
        if (lines.length > 0) {
          setEventTimelineActive(true);
          setVisibleSteps(lines);
        }
        setMissionState(deriveMissionState(events, responseReceived));
        setDepartmentPresence(executiveDepartmentPresence(events));
      } catch {
        // Keep the current fallback or previously received event timeline.
      }
      setIsExecuting(false);
    }
  };

  const returnToListening = () => {
    setMission("");
    setSubmittedMission("");
    setVisibleSteps([]);
    setMissionStartedAt("");
    setEventBaselineIds([]);
    setEventTimelineActive(false);
    setMissionState("Mission Created");
    setDepartmentPresence([]);
    setOrchestrationSteps(defaultOrchestrationSteps);
    setMissionResult(null);
    setReasoningResult(null);
    setTenderResult(null);
    setSupplierResult(null);
    setContractResult(null);
    setProcurementResult(null);
    setMeetingResult(null);
    setBriefingResult(null);
    setMissionError("");
    setProtocolLines([]);
    setVisibleProtocolLines([]);
    setShowProtocolOffer(false);
    setBriefOpen(false);
    setIsExecuting(false);
    setIsSpeaking(false);
    setExecutionMode(null);
    setPresenceState(AthenaPresenceState.LISTENING);
  };

  const resumeLastMission = () => {
    const lastObjective = cleanObjectiveText(workspaceMemory?.lastObjectiveText || workspaceMemory?.lastMission || "");
    if (!lastObjective) {
      return;
    }

    setMission(lastObjective);
    setSubmittedMission("");
    setProtocolLines([]);
    setVisibleProtocolLines([]);
    setShowProtocolOffer(false);
    setBriefOpen(false);
    setPresenceState(AthenaPresenceState.LISTENING);
  };

  const startNewMission = () => {
    clearWorkspaceMemory();
    setWorkspaceMemory(null);
    setMission("");
    setSubmittedMission("");
    setMissionResult(null);
    setReasoningResult(null);
    setTenderResult(null);
    setSupplierResult(null);
    setContractResult(null);
    setProcurementResult(null);
    setMeetingResult(null);
    setBriefingResult(null);
    setMissionError("");
    setProtocolLines([]);
    setVisibleProtocolLines([]);
    setShowProtocolOffer(false);
    setVisibleSteps([]);
    setMissionStartedAt("");
    setEventBaselineIds([]);
    setEventTimelineActive(false);
    setMissionState("Mission Created");
    setDepartmentPresence([]);
    setOrchestrationSteps(defaultOrchestrationSteps);
    setBriefOpen(false);
    setExecutionMode(null);
    setPresenceState(AthenaPresenceState.IDLE);
  };

  return (
    <section
      className={`executive-home env-state-${presenceState}${arrivalComplete ? " arrival-ready" : " arrival-active"}`}
      data-execution-mode={executionMode || "idle"}
    >
      <AthenaEnvironment state={presenceState} />

      <div className="command-stage">
        <div className="athena-identity">
          <span>ATHENA</span>
          <p>Central Executive Intelligence</p>
        </div>

        <AthenaPresenceEngine state={presenceState} />

        <section className="chamber-subtitles" aria-live="polite">
          {chamberLines.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </section>

        <form className={`${submittedMission ? "command-console compact" : "command-console"}${arrivalComplete ? "" : " arrival-hidden"}`} onSubmit={(event) => event.preventDefault()}>
          <label htmlFor="executive-mission">Executive mission</label>
          <textarea
            id="executive-mission"
            value={mission}
            onChange={(event) => {
              setMission(event.target.value);
              if (event.target.value.trim()) {
                setWorkspaceMemory(
                  updateWorkspaceMemory({
                    lastPresenceState: AthenaPresenceState.LISTENING,
                  }),
                );
              }
              if (!isExecuting && !isSpeaking && !submittedMission) {
                setPresenceState(AthenaPresenceState.LISTENING);
              }
            }}
            onFocus={() => {
              if (!isExecuting) {
                setPresenceState(hasDraftMission ? AthenaPresenceState.UNDERSTANDING : AthenaPresenceState.LISTENING);
              }
            }}
            onBlur={() => {
              if (!isExecuting && !isSpeaking && !submittedMission) {
                setPresenceState(AthenaPresenceState.IDLE);
              }
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void handleExecuteMission();
              }
            }}
            placeholder="Define the next objective..."
          />
          {missionIntent.hint && <p className="mission-hint">Possible mission: {missionIntent.hint}</p>}
          <div className="chamber-actions">
            {hasCompletedObjectiveMemory && !mission.trim() && (
              <button type="button" onClick={resumeLastMission}>
                Continue from last objective
              </button>
            )}
            <button type="button" onClick={startNewMission}>
              Start New Mission
            </button>
            {mission.trim() && (
              <button type="button" onClick={handleExecuteMission} disabled={isExecuting || isSpeaking}>
                Present Objective
              </button>
            )}
          </div>
        </form>

        {submittedMission && (
          <section className="conversation-exchange" aria-live="polite">
            {!isSpeaking && showProtocolOffer && visibleProtocolLines.length > 0 && (
              <div className="conversation-actions">
                <button type="button" onClick={() => setBriefOpen(true)}>
                {tenderResult ? "View Executive Brief" : supplierResult ? "View Supplier Evidence" : "YES"}
                </button>
                {!tenderResult && !supplierResult && (
                  <button type="button" onClick={returnToListening}>
                    NOT NOW
                  </button>
                )}
              </div>
            )}
          </section>
        )}

        <ExecutiveWorkspacePanel
          visible={showExecutiveWorkspace}
          mission={submittedMission}
          timelineSteps={eventTimelineActive ? visibleSteps : []}
          missionState={missionState}
          departmentPresence={departmentPresence}
          hasExecutiveResponse={hasExecutiveResponse}
          missionResult={missionResult}
          reasoningResult={reasoningResult}
          tenderResult={tenderResult}
          supplierResult={supplierResult}
          contractResult={contractResult}
          procurementResult={procurementResult}
          meetingResult={meetingResult}
          briefingResult={briefingResult}
        />

      </div>

      {activePath !== "/" && (
        <ChamberOverlay route={route} activePath={activePath} />
      )}

        <ExecutiveBriefDrawer
          open={briefOpen}
          mission={submittedMission}
          missionState={missionState}
          hasExecutiveResponse={hasExecutiveResponse}
          missionResult={missionResult}
          reasoningResult={reasoningResult}
          tenderResult={tenderResult}
          supplierResult={supplierResult}
          contractResult={contractResult}
          procurementResult={procurementResult}
          meetingResult={meetingResult}
          briefingResult={briefingResult}
          timelineSteps={visibleSteps}
          departmentPresence={departmentPresence}
          onClose={() => setBriefOpen(false)}
        />
    </section>
  );
}

function ChamberOverlay({ route, activePath }: { route: WorkspaceRoute; activePath: string }) {
  const overlay = getChamberOverlay(route, activePath);

  return (
    <aside className="chamber-overlay" aria-label={`${route.title} context`}>
      <span>{route.eyebrow}</span>
      <h2>{route.title}</h2>
      <p>{overlay.summary}</p>

      <div className="chamber-overlay-list">
        {overlay.items.map((item) => (
          <section key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.detail}</p>
          </section>
        ))}
      </div>
    </aside>
  );
}

function ExecutiveWorkspacePanel({
  visible,
  mission,
  timelineSteps,
  missionState,
  departmentPresence,
  hasExecutiveResponse,
  missionResult,
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
}: {
  visible: boolean;
  mission: string;
  timelineSteps: string[];
  missionState: MissionState;
  departmentPresence: DepartmentPresence[];
  hasExecutiveResponse: boolean;
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  if (!visible) {
    return null;
  }

  const briefing = buildExecutiveWorkspaceBrief({
    mission,
    missionState,
    hasExecutiveResponse,
    missionResult,
    reasoningResult,
    tenderResult,
    supplierResult,
    contractResult,
    procurementResult,
    meetingResult,
    briefingResult,
  });
  const flowSteps = buildLiveMissionFlow(timelineSteps, missionState, hasExecutiveResponse);
  const coordinatedDepartments = buildDepartmentCoordination({
    mission,
    departmentPresence,
    tenderResult,
    supplierResult,
    contractResult,
    procurementResult,
    meetingResult,
    briefingResult,
  });
  const showPresence = coordinatedDepartments.length > 0 && missionStateRank(missionState) >= missionStateRank("Mission Accepted");
  const showAssessment = Boolean(briefing.assessment) && missionStateRank(missionState) >= missionStateRank("Executive Recommendation");
  const showRecommendation = Boolean(briefing.recommendation) && missionStateRank(missionState) >= missionStateRank("Executive Recommendation");
  const showIntelligence = briefing.details.length > 0 && missionStateRank(missionState) >= missionStateRank("Executive Consolidation");
  const showRisks = (briefing.risks.length > 0 || briefing.missingInformation.length > 0) && missionStateRank(missionState) >= missionStateRank("Executive Consolidation");

  return (
    <section className="executive-workspace-panel" aria-label="Executive workspace">
      <div className="executive-workspace-section mission">
        <span>Mission</span>
        <h2>{briefing.title}</h2>
        <dl>
          <div>
            <dt>Type</dt>
            <dd>{briefing.type}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{briefing.status}</dd>
          </div>
        </dl>
      </div>

      <div className="executive-workspace-section timeline live-flow">
        <span>Live Mission Flow</span>
        <ol>
          {flowSteps.map((step) => (
            <li key={step.label} className={`flow-${step.status}`}>{step.label}</li>
          ))}
        </ol>
      </div>

      {showPresence && (
        <div className="executive-workspace-section presence">
          <span>Executive Presence</span>
          <ul>
            {coordinatedDepartments.map((department) => (
              <li key={department.name}>
                <strong>{department.name}</strong>
                <span>{department.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {showAssessment && (
        <div className="executive-workspace-section assessment">
          <span>Executive Assessment</span>
          <p>{briefing.assessment}</p>
        </div>
      )}

      {showRecommendation && (
        <div className="executive-workspace-section action">
          <span>Next Executive Action</span>
          <p>{briefing.recommendation}</p>
        </div>
      )}

      {showIntelligence && (
        <div className="executive-workspace-section details">
          <span>Mission Intelligence</span>
          <dl>
            {briefing.details.map((detail) => (
              <div key={detail.label}>
                <dt>{detail.label}</dt>
                <dd>{detail.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {showRisks && briefing.risks.length > 0 && (
        <div className="executive-workspace-section compact-list">
          <span>Risks</span>
          <ul>
            {briefing.risks.map((risk) => (
              <li key={risk}>{risk}</li>
            ))}
          </ul>
        </div>
      )}

      {showRisks && briefing.missingInformation.length > 0 && (
        <div className="executive-workspace-section compact-list">
          <span>Missing Information</span>
          <ul>
            {briefing.missingInformation.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function buildExecutiveWorkspaceBrief({
  mission,
  missionState,
  hasExecutiveResponse,
  missionResult,
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
}: {
  mission: string;
  missionState: MissionState;
  hasExecutiveResponse: boolean;
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  return {
    title: conciseMissionTitle(mission),
    type: executiveWorkspaceType({
      mission,
      missionResult,
      reasoningResult,
      tenderResult,
      supplierResult,
      contractResult,
      procurementResult,
      meetingResult,
      briefingResult,
    }),
    status: hasExecutiveResponse ? executiveWorkspaceStatus({ missionResult }) : missionState,
    assessment: executiveWorkspaceAssessment({
      hasExecutiveResponse,
      missionResult,
      reasoningResult,
      tenderResult,
      supplierResult,
      contractResult,
      procurementResult,
      meetingResult,
      briefingResult,
    }),
    recommendation: executiveWorkspaceRecommendation({
      hasExecutiveResponse,
      missionResult,
      reasoningResult,
      tenderResult,
      supplierResult,
      contractResult,
      procurementResult,
      meetingResult,
      briefingResult,
    }),
    details: executiveWorkspaceDetails({
      missionResult,
      reasoningResult,
      tenderResult,
      supplierResult,
      contractResult,
      procurementResult,
      meetingResult,
      briefingResult,
    }),
    risks: executiveWorkspaceRisks({
      reasoningResult,
      tenderResult,
      supplierResult,
      contractResult,
      procurementResult,
      meetingResult,
      briefingResult,
    }),
    missingInformation: executiveWorkspaceMissingInformation({
      contractResult,
    }),
  };
}

function ExecutiveBriefDrawer({
  open,
  mission,
  missionState,
  hasExecutiveResponse,
  missionResult,
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
  timelineSteps,
  departmentPresence,
  onClose,
}: {
  open: boolean;
  mission: string;
  missionState: MissionState;
  hasExecutiveResponse: boolean;
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
  timelineSteps: string[];
  departmentPresence: DepartmentPresence[];
  onClose: () => void;
}) {
  const briefing = buildExecutiveWorkspaceBrief({
    mission,
    missionState,
    hasExecutiveResponse,
    missionResult,
    reasoningResult,
    tenderResult,
    supplierResult,
    contractResult,
    procurementResult,
    meetingResult,
    briefingResult,
  });
  const flowSteps = buildLiveMissionFlow(timelineSteps, missionState, hasExecutiveResponse);
  const coordinatedDepartments = buildDepartmentCoordination({
    mission,
    departmentPresence,
    tenderResult,
    supplierResult,
    contractResult,
    procurementResult,
    meetingResult,
    briefingResult,
  });

  return (
    <aside className={open ? "executive-brief-drawer open" : "executive-brief-drawer"} aria-hidden={!open}>
      <div className="brief-drawer-header">
        <div>
          <span>Executive Brief</span>
          <h3>{briefing.title}</h3>
        </div>
        <button type="button" onClick={onClose} aria-label="Close executive brief">
          Close
        </button>
      </div>

      <div className="brief-drawer-body">
        <section>
          <span>Mission</span>
          <dl>
            <div>
              <dt>Type</dt>
              <dd>{briefing.type}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{briefing.status}</dd>
            </div>
          </dl>
        </section>

        {briefing.assessment && (
          <section>
            <span>Executive Assessment</span>
            <p>{briefing.assessment}</p>
          </section>
        )}

        {briefing.recommendation && (
          <section>
            <span>Next Executive Action</span>
            <p>{briefing.recommendation}</p>
          </section>
        )}

        {briefing.details.length > 0 && (
          <section>
            <span>Mission Intelligence</span>
            <dl>
              {briefing.details.map((detail) => (
                <div key={detail.label}>
                  <dt>{detail.label}</dt>
                  <dd>{detail.value}</dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        {coordinatedDepartments.length > 0 && (
          <section>
            <span>Department Coordination</span>
            <ol>
              {coordinatedDepartments.map((department) => (
                <li key={department.name}>{department.name} - {department.status}</li>
              ))}
            </ol>
          </section>
        )}

        <section>
          <span>Mission Lifecycle</span>
          <ol>
            {flowSteps.map((step) => (
              <li key={step.label}>{step.label}</li>
            ))}
          </ol>
        </section>

        {briefing.risks.length > 0 && (
          <section>
            <span>Strategic Risks</span>
            <ol>
              {briefing.risks.map((risk) => (
                <li key={risk}>{risk}</li>
              ))}
            </ol>
          </section>
        )}

        {briefing.missingInformation.length > 0 && (
          <section>
            <span>Missing Information</span>
            <ol>
              {briefing.missingInformation.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </aside>
  );
}

function buildChamberLines({
  arrivalComplete,
  arrivalLines,
  missionIntent,
  submittedMission,
  visibleProtocolLines,
  isExecuting,
  missionError,
  greetingMessage,
}: {
  arrivalComplete: boolean;
  arrivalLines: string[];
  missionIntent: MissionIntent;
  submittedMission: string;
  visibleProtocolLines: ConversationProtocolLine[];
  isExecuting: boolean;
  missionError: string;
  greetingMessage: string;
}) {
  if (!arrivalComplete) {
    return arrivalLines;
  }

  if (missionError) {
    return [missionError];
  }

  if (isExecuting) {
    return [];
  }

  if (submittedMission && visibleProtocolLines.length > 0) {
    return visibleProtocolLines.slice(-4).map((line) => line.text);
  }

  if (missionIntent.hint) {
    return [greetingMessage];
  }

  return [];
}

function buildMemorySpeech(memory: WorkspaceMemory | null): ConversationProtocolLine[] {
  if (!memory?.lastMission) {
    return [];
  }

  const lines: ConversationProtocolLine[] = [
    { stage: "recognition", text: "Welcome back, Wassim." },
    { stage: "context", text: "This is where we left off." },
  ];

  if (memory.lastRecommendation) {
    lines.push({ stage: "decision", text: memory.lastRecommendation });
  }

  if (memory.lastApproval) {
    lines.push({ stage: "reason", text: memory.lastApproval });
  }

  return lines;
}

function arrivalGreeting() {
  const hour = new Date().getHours();

  if (hour < 12) {
    return "Good morning, Wassim.";
  }

  if (hour < 18) {
    return "Good afternoon, Wassim.";
  }

  return "Good evening, Wassim.";
}

function chooseArrivalExecutiveLine(memory: WorkspaceMemory | null) {
  if (!memory) {
    return "The organization is operating normally.";
  }

  const hasPreviousObjective = Boolean(cleanObjectiveText(memory.lastObjectiveText || memory.lastMission));

  if (hasPreviousObjective && (memory.lastObjectiveResponseReceived || memory.lastRecommendation)) {
    return "Your last executive assessment was completed.";
  }

  if (hasPreviousObjective) {
    return "We paused with an executive objective still in progress.";
  }

  return "The organization is operating normally.";
}

function completedObjectiveMemory(objective: string): Partial<WorkspaceMemory> {
  return {
    lastObjectiveText: objective,
    lastObjectiveTimestamp: new Date().toISOString(),
    lastObjectiveResponseReceived: true,
    lastObjectiveStatus: "assessment completed",
  };
}

function cleanObjectiveText(value: unknown) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function buildOrchestrationSteps(objective: string) {
  const normalized = objective.toLowerCase();
  const capabilitySteps: string[] = [];

  if (/\b(tender|bid|proposal)\b/.test(normalized)) {
    capabilitySteps.push(
      "Tender Executive is reviewing submission requirements...",
      "Procurement implications are being assessed...",
    );
  } else if (/\b(supplier|vendor)\b/.test(normalized)) {
    capabilitySteps.push(
      "Supplier Executive is assessing vendor context...",
      "Commercial risk is being reviewed...",
    );
  } else if (/\b(contract|agreement)\b/.test(normalized)) {
    capabilitySteps.push(
      "Contract Executive is reviewing obligations...",
      "Risk exposure is being evaluated...",
    );
  } else if (/\b(meeting|minutes)\b/.test(normalized)) {
    capabilitySteps.push(
      "Meeting Executive is extracting decisions and actions...",
      "Follow-up accountability is being organized...",
    );
  } else if (/\b(daily|briefing|today)\b/.test(normalized)) {
    capabilitySteps.push(
      "Daily Briefing Executive is preparing the executive overview...",
      "Priority signals are being ranked...",
    );
  }

  if (!capabilitySteps.length) {
    return defaultOrchestrationSteps;
  }

  return [
    defaultOrchestrationSteps[0],
    defaultOrchestrationSteps[1],
    ...capabilitySteps,
    defaultOrchestrationSteps[4],
    defaultOrchestrationSteps[5],
    defaultOrchestrationSteps[6],
  ];
}

async function readAthenaEventBaseline() {
  try {
    const result = await fetchAthenaEvents(80);
    return (result.events || []).map(athenaEventIdentity);
  } catch {
    return [];
  }
}

function currentExecutiveEvents(events: AthenaEvent[], baselineIds: string[], startedAt: string) {
  const baseline = new Set(baselineIds);
  const recentFloor = Date.now() - 5 * 60 * 1000;
  const isUsableEvent = (event: AthenaEvent) => isExecutiveEvent(event) && isRecentEnoughEvent(event, startedAt, recentFloor);

  if (baseline.size > 0) {
    const newEvents = events.filter(
      (event) => !baseline.has(athenaEventIdentity(event)) && isExecutiveEvent(event) && isRecentEnoughEvent(event, startedAt, recentFloor),
    );
    return newEvents.length > 0 ? newEvents : events.filter(isUsableEvent);
  }

  const started = parseAthenaTimestamp(startedAt);
  return events.filter((event) => {
    const eventTime = parseAthenaTimestamp(event.timestamp);
    return isExecutiveEvent(event) && (Number.isNaN(started) || Number.isNaN(eventTime) || eventTime >= started - 750);
  });
}

function executiveEventLines(events: AthenaEvent[]) {
  const lines: string[] = [];
  const seen = new Set<string>();

  for (const event of events) {
    const line = executiveEventLine(event);
    if (line && !seen.has(line)) {
      seen.add(line);
      lines.push(line);
    }
  }

  return lines.slice(0, 7);
}

function athenaEventIdentity(event: AthenaEvent) {
  return String(event.id || `${event.timestamp || ""}:${event.event_type || ""}:${event.source || ""}`);
}

function parseAthenaTimestamp(value: unknown) {
  const timestamp = String(value || "");
  if (!timestamp) {
    return Number.NaN;
  }

  const hasTimezone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(timestamp);
  return Date.parse(hasTimezone ? timestamp : `${timestamp}Z`);
}

function isRecentEnoughEvent(event: AthenaEvent, startedAt: string, recentFloor: number) {
  const eventTime = parseAthenaTimestamp(event.timestamp);
  const started = parseAthenaTimestamp(startedAt);
  if (Number.isNaN(eventTime)) {
    return true;
  }

  if (!Number.isNaN(started) && eventTime >= started - 750) {
    return true;
  }

  return eventTime >= recentFloor;
}

function isExecutiveEvent(event: AthenaEvent) {
  const eventType = String(event.event_type || "");
  const source = String(event.source || "");
  return /Executive|Mission|Capability|Brain|Planning|Execution|Organization|Operations|Knowledge|Reasoning|Approval|Tender|Supplier|Contract|Procurement|Meeting|Briefing/i.test(
    `${eventType} ${source}`,
  );
}

function executiveEventLine(event: AthenaEvent) {
  const eventType = String(event.event_type || "");
  const payload = event.payload || {};
  const result = String(payload.result || "");

  if (result === "failed" || eventType.includes("Failed")) {
    return "Executive assessment requires attention...";
  }

  const eventLines: Record<string, string> = {
    ContractExecutiveStarted: "Contract Executive engaged...",
    ContractExecutiveCompleted: "Contract recommendation delivered...",
    ProcurementExecutiveStarted: "Procurement Executive engaged...",
    ProcurementExecutiveCompleted: "Procurement recommendation delivered...",
    MeetingExecutiveStarted: "Meeting Executive engaged...",
    MeetingExecutiveCompleted: "Meeting preparation completed...",
    DailyBriefingGenerated: "Executive briefing generated...",
    BrainObjectiveExecutionStarted: "Executive Brain engaged...",
    BrainObjectiveExecutionCompleted: "Executive Brain consolidated the assessment...",
    ExecutiveExecutionPlanBuilt: "Executive capabilities aligned...",
    AdaptivePlanningStarted: "Mission scope is being defined...",
    AdaptivePlanningCompleted: "Mission plan established...",
    CapabilityExecutionStarted: capabilityEventLine(event),
    CapabilityExecutionCompleted: capabilityEventCompletedLine(event),
    ExecutionEvaluationCompleted: "Executive readiness evaluated...",
    ExecutionLearned: "Institutional learning updated...",
    MissionObjectiveStarted: "Mission objective activated...",
    MissionObjectiveCompleted: "Mission objective completed...",
    MissionDependencyLevelStarted: "Departments are coordinating the next objective...",
    MissionDependencyLevelCompleted: "Department coordination completed...",
    MissionParallelExecutionCompleted: "Executive workstreams consolidated...",
    TenderExecutiveStarted: "Tender Executive engaged...",
    TenderExecutiveCompleted: "Tender recommendation delivered...",
    SupplierExecutiveStarted: "Supplier Executive engaged...",
    SupplierExecutiveCompleted: "Supplier recommendation delivered...",
    ExecutiveReasoningStarted: "Executive reasoning engaged...",
    ExecutiveReasoningCompleted: "Executive recommendation delivered...",
    OrganizationImpactAnalyzed: "Strategic impact evaluated...",
    OperationsOverviewRequested: "Operations context consulted...",
    ReasoningChainGenerated: "Business dependencies reviewed...",
    MissionExecutionStarted: "Mission execution initiated...",
    MissionExecutionCompleted: "Mission execution completed...",
    MissionApprovalRequired: "Executive approval requirement identified...",
    MissionApproved: "Executive approval recorded...",
    MissionRejected: "Executive decision recorded...",
  };

  return eventLines[eventType] || "";
}

function capabilityEventLine(event: AthenaEvent) {
  const capability = String(event.payload?.capability || "");
  if (/risk/i.test(capability)) {
    return "Risk exposure is being evaluated...";
  }
  if (/decision|brief/i.test(capability)) {
    return "Executive recommendation is being prepared...";
  }
  if (/action/i.test(capability)) {
    return "Required next action is being organized...";
  }
  if (/obligation|extraction|file/i.test(capability)) {
    return "Organizational knowledge is being consulted...";
  }
  return "Executive capability engaged...";
}

function capabilityEventCompletedLine(event: AthenaEvent) {
  const capability = String(event.payload?.capability || "");
  if (/risk/i.test(capability)) {
    return "Risk assessment completed...";
  }
  if (/decision|brief/i.test(capability)) {
    return "Executive recommendation prepared...";
  }
  if (/action/i.test(capability)) {
    return "Required next action prepared...";
  }
  return "";
}

function deriveMissionState(events: AthenaEvent[], hasExecutiveResponse: boolean): MissionState {
  if (hasExecutiveResponse || hasEvent(events, /MissionExecutionCompleted|ExecutiveReasoningCompleted|ContractExecutiveCompleted|ProcurementExecutiveCompleted|MeetingExecutiveCompleted|TenderExecutiveCompleted|SupplierExecutiveCompleted|DailyBriefingGenerated|BrainObjectiveExecutionCompleted/)) {
    return hasExecutiveResponse ? "Mission Complete" : "Executive Recommendation";
  }

  if (hasEvent(events, /ExecutionEvaluationCompleted|MissionParallelExecutionCompleted|MissionDependencyLevelCompleted|OrganizationImpactAnalyzed/)) {
    return "Executive Consolidation";
  }

  if (hasEvent(events, /Knowledge|ReasoningChain|OperationsOverview/)) {
    return "Knowledge Expansion";
  }

  if (hasEvent(events, /CapabilityExecution|TenderExecutiveStarted|SupplierExecutiveStarted|ContractExecutiveStarted|ProcurementExecutiveStarted|MeetingExecutiveStarted|ReasoningChainGenerated|Knowledge/)) {
    return "Departments Mobilized";
  }

  if (hasEvent(events, /MissionExecutionStarted|BrainObjectiveExecutionStarted|ExecutiveReasoningStarted|AdaptivePlanning/)) {
    return "Executive Brain Activated";
  }

  if (events.length > 0) {
    return "Mission Accepted";
  }

  return "Mission Created";
}

function hasEvent(events: AthenaEvent[], pattern: RegExp) {
  return events.some((event) => pattern.test(String(event.event_type || "")));
}

function executiveDepartmentPresence(events: AthenaEvent[]) {
  const departments: DepartmentPresence[] = [];
  const indexByName = new Map<string, number>();

  for (const event of events) {
    for (const department of departmentsForEvent(event)) {
      const key = department.name.toLowerCase();
      const existingIndex = indexByName.get(key);
      if (existingIndex === undefined) {
        indexByName.set(key, departments.length);
        departments.push(department);
      } else {
        departments[existingIndex] = {
          ...departments[existingIndex],
          status: moreAdvancedDepartmentStatus(departments[existingIndex].status, department.status),
        };
      }
    }
  }

  return departments.slice(0, 7);
}

function buildDepartmentCoordination({
  mission,
  departmentPresence,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
}: {
  mission: string;
  departmentPresence: DepartmentPresence[];
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  const departments = new Map<string, DepartmentPresence["status"]>();
  const add = (name: string, status: DepartmentPresence["status"] = "Waiting") => {
    const current = departments.get(name);
    departments.set(name, current ? moreAdvancedDepartmentStatus(current, status) : status);
  };

  add("Executive Brain", "Working");
  add("Reasoning Engine", "Waiting");

  for (const department of expectedDepartmentsForMission({
    mission,
    tenderResult,
    supplierResult,
    contractResult,
    procurementResult,
    meetingResult,
    briefingResult,
  })) {
    add(department);
  }

  for (const department of departmentPresence) {
    add(department.name, department.status);
  }

  return Array.from(departments.entries())
    .map(([name, status]) => ({ name, status }))
    .slice(0, 9);
}

function expectedDepartmentsForMission({
  mission,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
}: {
  mission: string;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  const expected = new Set<string>(["Organization Model", "Operations Center"]);
  const normalized = mission.toLowerCase();

  if (/\b(tender|bid|proposal)\b/.test(normalized) || tenderResult) {
    expected.add("Tender Executive");
    expected.add("Procurement Executive");
  }
  if (/\b(supplier|vendor)\b/.test(normalized) || supplierResult) {
    expected.add("Supplier Executive");
  }
  if (/\b(contract|agreement|terms)\b/.test(normalized) || contractResult) {
    expected.add("Contract Executive");
  }
  if (/\b(procure|procurement|purchase|buy|source)\b/.test(normalized) || procurementResult) {
    expected.add("Procurement Executive");
    expected.add("Supplier Executive");
  }
  if (/\b(meeting|minutes|agenda)\b/.test(normalized) || meetingResult) {
    expected.add("Meeting Executive");
  }
  if (/\b(daily|briefing|today|focus)\b/.test(normalized) || briefingResult) {
    expected.add("Daily Briefing Executive");
  }

  return Array.from(expected);
}

function departmentsForEvent(event: AthenaEvent) {
  const eventType = String(event.event_type || "");
  const source = String(event.source || "");
  const capability = String(event.payload?.capability || "");
  const departments: DepartmentPresence[] = [];
  const status = departmentStatusForEvent(event);

  if (/TenderExecutive/.test(eventType)) departments.push({ name: "Tender Executive", status });
  if (/SupplierExecutive/.test(eventType)) departments.push({ name: "Supplier Executive", status });
  if (/ContractExecutive/.test(eventType)) departments.push({ name: "Contract Executive", status });
  if (/ProcurementExecutive/.test(eventType)) departments.push({ name: "Procurement Executive", status });
  if (/MeetingExecutive/.test(eventType)) departments.push({ name: "Meeting Executive", status });
  if (/DailyBriefing/.test(eventType)) departments.push({ name: "Daily Briefing Executive", status });
  if (/ExecutiveReasoning|BrainObjective|CapabilityExecution|ExecutiveExecution|ExecutionEvaluation/.test(eventType) || /executive_brain/.test(source)) departments.push({ name: "Reasoning Engine", status: /Completed|Evaluation|Learned/.test(eventType) ? "Completed" : status });
  if (/OrganizationImpact/.test(eventType) || /organization/.test(source)) departments.push({ name: "Organization Model", status: "Completed" });
  if (/Knowledge|ReasoningChain/.test(eventType) || /knowledge_graph|reasoning_graph/.test(source)) departments.push({ name: /ReasoningChain|reasoning_graph/.test(`${eventType} ${source}`) ? "Reasoning Graph" : "Knowledge Graph", status: "Completed" });
  if (/OperationsOverview/.test(eventType) || /operations/.test(source)) departments.push({ name: "Operations Center", status: "Completed" });
  if (/Mission/.test(eventType) || /mission_controller|mission_context/.test(source)) departments.push({ name: "Mission Runtime", status });
  if (/approval/i.test(eventType) || /approval/.test(source)) departments.push({ name: "Approval Workflow", status: /Required/.test(eventType) ? "Working" : status });
  if (/supplier/i.test(capability)) departments.push({ name: "Supplier Executive", status });
  if (/risk|obligation|extraction|decision|action|file/i.test(capability)) departments.push({ name: "Executive Brain", status });

  return departments;
}

function departmentStatusForEvent(event: AthenaEvent): DepartmentPresence["status"] {
  const eventType = String(event.event_type || "");
  const result = String(event.payload?.result || "");

  if (/Completed|Generated|Approved|Rejected/.test(eventType) || result === "success") {
    return "Completed";
  }
  return "Working";
}

function moreAdvancedDepartmentStatus(
  current: DepartmentPresence["status"],
  next: DepartmentPresence["status"],
) {
  const order: DepartmentPresence["status"][] = ["Waiting", "Working", "Completed"];
  return order.indexOf(next) > order.indexOf(current) ? next : current;
}

function buildLiveMissionFlow(timelineSteps: string[], missionState: MissionState, hasExecutiveResponse: boolean) {
  const joinedSteps = timelineSteps.join(" ").toLowerCase();
  const completeRank = hasExecutiveResponse ? missionStateRank("Mission Complete") : missionStateRank(missionState);
  const flow = [
    {
      label: "Mission created",
      rank: missionStateRank("Mission Created"),
      matched: /objective received|mission execution|mission initiated|mission objective/i.test(joinedSteps),
    },
    {
      label: "Mission accepted",
      rank: missionStateRank("Mission Accepted"),
      matched: timelineSteps.length > 0,
    },
    {
      label: "Executive Brain activated",
      rank: missionStateRank("Executive Brain Activated"),
      matched: /brain engaged|reasoning|scope|plan/i.test(joinedSteps),
    },
    {
      label: "Departments mobilized",
      rank: missionStateRank("Departments Mobilized"),
      matched: /department|executive engaged|capability|tender|supplier|contract|procurement|meeting|briefing/i.test(joinedSteps),
    },
    {
      label: "Knowledge expansion",
      rank: missionStateRank("Knowledge Expansion"),
      matched: /knowledge|dependencies|operations|context/i.test(joinedSteps),
    },
    {
      label: "Executive consolidation",
      rank: missionStateRank("Executive Consolidation"),
      matched: /impact|operations|knowledge|dependencies|readiness|consolidated/i.test(joinedSteps),
    },
    {
      label: "Executive recommendation",
      rank: missionStateRank("Executive Recommendation"),
      matched: /recommendation|briefing|action prepared|delivered/i.test(joinedSteps),
    },
    {
      label: "Mission complete",
      rank: missionStateRank("Mission Complete"),
      matched: /completed|complete|delivered/i.test(joinedSteps) || hasExecutiveResponse,
    },
  ];

  return flow.map((step) => ({
    label: step.label,
    status: step.rank < completeRank || step.matched ? "complete" : step.rank === completeRank ? "active" : "pending",
  }));
}

function missionStateRank(state: MissionState) {
  const ranks: Record<MissionState, number> = {
    "Mission Created": 1,
    "Mission Accepted": 2,
    "Executive Brain Activated": 3,
    "Departments Mobilized": 4,
    "Knowledge Expansion": 5,
    "Executive Consolidation": 6,
    "Executive Recommendation": 7,
    "Mission Complete": 8,
  };

  return ranks[state];
}

function conciseMissionTitle(mission: string) {
  const cleanMission = cleanObjectiveText(mission);
  if (!cleanMission) {
    return "Executive Objective";
  }

  return cleanMission.length > 72 ? `${cleanMission.slice(0, 69).trim()}...` : cleanMission;
}

function executiveWorkspaceType({
  mission,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
}: {
  mission: string;
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  if (tenderResult) {
    return "Tender Executive";
  }
  if (supplierResult) {
    return "Supplier Executive";
  }
  if (contractResult) {
    return "Contract Executive";
  }
  if (procurementResult) {
    return "Procurement Executive";
  }
  if (meetingResult) {
    return "Meeting Executive";
  }
  if (briefingResult) {
    return "Daily Briefing";
  }

  const normalized = mission.toLowerCase();
  if (/\b(tender|bid|proposal)\b/.test(normalized)) {
    return "Tender Executive";
  }
  if (/\b(supplier|vendor)\b/.test(normalized)) {
    return "Supplier Executive";
  }
  if (/\b(contract|agreement)\b/.test(normalized)) {
    return "Contract Executive";
  }
  if (/\b(procure|procurement|purchase|buy|source)\b/.test(normalized)) {
    return "Procurement Executive";
  }
  if (/\b(meeting|minutes|agenda)\b/.test(normalized)) {
    return "Meeting Executive";
  }
  if (/\b(daily|briefing|today|focus)\b/.test(normalized)) {
    return "Daily Briefing";
  }
  return "Executive Reasoning";
}

function executiveWorkspaceAssessment({
  hasExecutiveResponse,
  missionResult,
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
}: {
  hasExecutiveResponse: boolean;
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  if (!hasExecutiveResponse) {
    return "";
  }

  return firstExecutiveSentence(
    contractResult?.executive_summary ||
    procurementResult?.executive_summary ||
    meetingResult?.executive_summary ||
    briefingResult?.executive_summary ||
    supplierResult?.executive_summary ||
    tenderResult?.executive_summary ||
    reasoningResult?.executive_explanation ||
    reasoningResult?.executive_recommendation ||
    missionResult?.executive_response?.summary ||
    "",
  );
}

function executiveWorkspaceRecommendation({
  hasExecutiveResponse,
  missionResult,
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
}: {
  hasExecutiveResponse: boolean;
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  if (!hasExecutiveResponse) {
    return "";
  }

  return firstExecutiveSentence(
    contractResult?.recommended_actions?.[0] ||
    procurementResult?.recommended_actions?.[0] ||
    meetingResult?.recommended_position ||
    briefingResult?.recommended_focus ||
    supplierResult?.recommended_actions?.[0] ||
    tenderResult?.recommended_next_actions?.[0] ||
    reasoningResult?.recommended_next_action ||
    reasoningResult?.executive_recommendation ||
    missionResult?.executive_response?.recommended_next_action ||
    "",
  );
}

function executiveWorkspaceDetails({
  missionResult,
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
}: {
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  const details: Array<{ label: string; value: string }> = [];
  const priority = executiveWorkspacePriority({
    missionResult,
    reasoningResult,
    tenderResult,
    supplierResult,
    contractResult,
    procurementResult,
  });
  const readiness = executiveWorkspaceReadiness({
    missionResult,
    reasoningResult,
    tenderResult,
    supplierResult,
    contractResult,
    procurementResult,
  });
  const requiredNextAction = firstExecutiveSentence(
    missionResult?.approval_request?.required_action ||
    contractResult?.recommended_actions?.[0] ||
    procurementResult?.recommended_actions?.[0] ||
    tenderResult?.recommended_next_actions?.[0] ||
    supplierResult?.recommended_actions?.[0] ||
    meetingResult?.questions_to_ask?.[0] ||
    meetingResult?.documents_to_prepare?.[0] ||
    briefingResult?.priorities?.[0] ||
    "",
  );
  const confidence = executiveWorkspaceConfidence({
    missionResult,
    reasoningResult,
    tenderResult,
    supplierResult,
    contractResult,
    procurementResult,
  });
  const approvalRequired = executiveWorkspaceApprovalRequired({ missionResult, reasoningResult });
  const missingInformation = executiveWorkspaceMissingInformation({ contractResult });
  const risks = executiveWorkspaceRisks({
    reasoningResult,
    tenderResult,
    supplierResult,
    contractResult,
    procurementResult,
    meetingResult,
    briefingResult,
  });
  const dependencies = executiveWorkspaceDependencies({
    tenderResult,
    procurementResult,
    briefingResult,
  });

  if (priority) {
    details.push({ label: "Priority", value: priority });
  }
  if (confidence) {
    details.push({ label: "Confidence", value: confidence });
  }
  if (approvalRequired) {
    details.push({ label: "Approval Required", value: approvalRequired });
  }
  if (missingInformation.length > 0) {
    details.push({ label: "Missing Information", value: `${missingInformation.length} item${missingInformation.length === 1 ? "" : "s"}` });
  }
  if (risks.length > 0) {
    details.push({ label: "Strategic Risks", value: `${risks.length} identified` });
  }
  if (dependencies) {
    details.push({ label: "Dependencies", value: dependencies });
  }
  if (requiredNextAction) {
    details.push({ label: "Required Next Action", value: requiredNextAction });
  }
  if (readiness) {
    details.push({ label: "Readiness", value: readiness });
  }

  return details;
}

function executiveWorkspaceConfidence({
  missionResult,
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
}: {
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
}) {
  const confidence =
    contractResult?.confidence ??
    procurementResult?.confidence ??
    supplierResult?.confidence ??
    tenderResult?.confidence ??
    reasoningResult?.confidence ??
    missionResult?.mission_evaluation?.confidence;

  return confidence !== undefined ? `${confidence}%` : "";
}

function executiveWorkspaceApprovalRequired({
  missionResult,
  reasoningResult,
}: {
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
}) {
  if (missionResult?.mission_evaluation?.approval_required !== undefined) {
    return missionResult.mission_evaluation.approval_required ? "Yes" : "No";
  }
  if (missionResult?.approval_request) {
    return "Yes";
  }
  if (reasoningResult?.requires_executive_attention !== undefined) {
    return reasoningResult.requires_executive_attention ? "Yes" : "No";
  }
  return "";
}

function executiveWorkspaceDependencies({
  tenderResult,
  procurementResult,
  briefingResult,
}: {
  tenderResult: TenderExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  const dependencies = uniqueExecutiveItems(
    tenderResult?.required_departments,
    procurementResult?.required_departments,
    (briefingResult?.pending_approvals || []).map((item) => readableUnknownItem(item)),
    (briefingResult?.active_missions || []).map((item) => readableUnknownItem(item)),
  );

  return dependencies.length > 0 ? dependencies.slice(0, 3).join(", ") : "";
}

function executiveWorkspacePriority({
  missionResult,
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
}: {
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
}) {
  if (missionResult?.mission_evaluation?.approval_required || missionResult?.approval_request) {
    return "Approval Required";
  }
  if (reasoningResult?.requires_executive_attention) {
    return "Executive Attention";
  }
  if (contractResult?.risk_level && ["High", "Critical"].includes(contractResult.risk_level)) {
    return `${contractResult.risk_level} Risk`;
  }
  if (supplierResult?.risk_level && ["High", "Critical"].includes(supplierResult.risk_level)) {
    return `${supplierResult.risk_level} Supplier Risk`;
  }
  if (procurementResult?.procurement_decision && ["Hold", "Reject", "Review"].includes(procurementResult.procurement_decision)) {
    return `${procurementResult.procurement_decision} Required`;
  }
  if (tenderResult?.bid_decision === "Review") {
    return "Executive Review";
  }
  return "";
}

function executiveWorkspaceReadiness({
  missionResult,
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
}: {
  missionResult: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
}) {
  if (missionResult?.mission_evaluation?.decision_ready !== undefined) {
    return missionResult.mission_evaluation.decision_ready ? "Decision Ready" : "Decision Not Ready";
  }

  const confidence =
    contractResult?.confidence ??
    procurementResult?.confidence ??
    supplierResult?.confidence ??
    tenderResult?.confidence ??
    reasoningResult?.confidence ??
    missionResult?.mission_evaluation?.confidence;

  return confidence !== undefined ? `Confidence ${confidence}%` : "";
}

function executiveWorkspaceRisks({
  reasoningResult,
  tenderResult,
  supplierResult,
  contractResult,
  procurementResult,
  meetingResult,
  briefingResult,
}: {
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  contractResult: ContractExecutiveResponse | null;
  procurementResult: ProcurementExecutiveResponse | null;
  meetingResult: MeetingExecutiveResponse | null;
  briefingResult: DailyBriefingExecutiveResponse | null;
}) {
  return uniqueExecutiveItems(
    contractResult?.key_risks,
    supplierResult?.key_concerns,
    tenderResult?.key_blockers,
    meetingResult?.risks_to_raise,
    briefingResult?.risks,
    riskLabelsFromProcurement(procurementResult),
    riskFindingsFromReasoning(reasoningResult),
  ).slice(0, 4);
}

function executiveWorkspaceMissingInformation({
  contractResult,
}: {
  contractResult: ContractExecutiveResponse | null;
}) {
  return uniqueExecutiveItems(
    contractResult?.missing_information,
  ).slice(0, 4);
}

function executiveWorkspaceStatus({ missionResult }: { missionResult: ExecutiveMissionResponse | null }) {
  if (missionResult?.mission_status === "pending_approval") {
    return "Pending Approval";
  }

  if (missionResult?.mission_status) {
    return titleCaseStatus(missionResult.mission_status);
  }

  return "Assessment Complete";
}

function riskLabelsFromProcurement(result: ProcurementExecutiveResponse | null) {
  if (!result) {
    return [];
  }

  return [result.supplier_risk, result.commercial_risk]
    .filter((value) => value && value !== "Low" && value !== "Unknown")
    .map((value) => `${value} procurement exposure.`) as string[];
}

function riskFindingsFromReasoning(result: ExecutiveReasoningResponse | null) {
  return (result?.key_findings || []).filter((finding) =>
    /\b(risk|limited|pending|no |missing|attention)\b/i.test(finding),
  );
}

function uniqueExecutiveItems(...groups: Array<string[] | undefined>) {
  const values: string[] = [];
  const seen = new Set<string>();

  for (const group of groups) {
    for (const item of group || []) {
      const cleanItem = firstExecutiveSentence(item);
      const key = cleanItem.toLowerCase();
      if (cleanItem && !seen.has(key)) {
        values.push(cleanItem);
        seen.add(key);
      }
    }
  }

  return values;
}

function readableUnknownItem(item: unknown) {
  if (!item) {
    return "";
  }

  if (typeof item === "string") {
    return item;
  }

  if (typeof item === "object") {
    const record = item as Record<string, unknown>;
    return cleanObjectiveText(
      record.title ||
      record.mission ||
      record.objective ||
      record.name ||
      record.status ||
      "",
    );
  }

  return String(item);
}

function firstExecutiveSentence(value: unknown) {
  const cleanValue = cleanObjectiveText(value);
  if (!cleanValue) {
    return "";
  }

  const match = cleanValue.match(/.*?[.!?](\s|$)/);
  return (match ? match[0] : cleanValue).trim();
}

function titleCaseStatus(value: string) {
  return String(value || "")
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1).toLowerCase()}`)
    .join(" ");
}

function detectMissionIntent(mission: string): MissionIntent {
  const normalizedMission = mission.toLowerCase();

  if (normalizedMission.includes("tender")) {
    return {
      hint: "Tender Analysis",
      greeting: "I believe you're preparing to evaluate a tender.",
    };
  }

  if (normalizedMission.includes("supplier")) {
    return {
      hint: "Supplier Review",
      greeting: "It appears you're reviewing a supplier.",
    };
  }

  if (looksLikeContractQuestion(mission)) {
    return {
      hint: "Contract Intelligence",
      greeting: "I can assist with contract intelligence.",
    };
  }

  if (looksLikeProcurementQuestion(mission)) {
    return {
      hint: "Procurement Review",
      greeting: "I can assist with procurement review.",
    };
  }

  if (looksLikeMeetingQuestion(mission)) {
    return {
      hint: "Meeting Preparation",
      greeting: "I can prepare the meeting position.",
    };
  }

  if (looksLikeDailyBriefingQuestion(mission)) {
    return {
      hint: "Daily Briefing",
      greeting: "I can prepare today's executive briefing.",
    };
  }

  if (normalizedMission.includes("portfolio")) {
    return {
      hint: "Portfolio Intelligence",
      greeting: "I can assist with portfolio intelligence.",
    };
  }

  return {
    hint: "",
    greeting: "How may I assist the company today?",
  };
}

function looksLikeExecutiveQuestion(input: string) {
  return /^(should|what|why|how|can|is|are)\b/i.test(input.trim());
}

function looksLikeContractQuestion(input: string) {
  const normalized = input.trim().toLowerCase();
  return /\b(contract|agreement|terms)\b/.test(normalized);
}

function looksLikeProcurementQuestion(input: string) {
  const normalized = input.trim().toLowerCase();
  return /\b(procure|procurement|purchase|buy|source)\b/.test(normalized);
}

function looksLikeMeetingQuestion(input: string) {
  const normalized = input.trim().toLowerCase();
  return /\b(meeting|agenda)\b/.test(normalized) || /\bprepare me\b/.test(normalized);
}

function looksLikeDailyBriefingQuestion(input: string) {
  const normalized = input.trim().toLowerCase();
  return /\b(briefing|morning|today|focus)\b/.test(normalized);
}

function looksLikeTenderBidQuestion(input: string) {
  const normalized = input.trim().toLowerCase();
  return /\b(bid|tender)\b/.test(normalized);
}

function looksLikeSupplierContinueQuestion(input: string) {
  const normalized = input.trim().toLowerCase();
  return (
    /^should\b/.test(normalized) &&
    /\b(we|icc)\b/.test(normalized) &&
    /\bcontinue\b/.test(normalized) &&
    /\b(supplier|working with|with)\b/.test(normalized)
  );
}

function looksLikeSupplierQuestion(input: string) {
  return /\bsupplier\b/i.test(input) || looksLikeSupplierContinueQuestion(input);
}

function looksLikeExecutiveSkillQuestion(input: string) {
  return (
    looksLikeContractQuestion(input) ||
    looksLikeProcurementQuestion(input) ||
    looksLikeMeetingQuestion(input) ||
    looksLikeDailyBriefingQuestion(input) ||
    looksLikeTenderBidQuestion(input) ||
    looksLikeSupplierQuestion(input) ||
    looksLikeExecutiveQuestion(input) ||
    input.trim().length > 0
  );
}

function extractSupplierName(input: string) {
  const cleanedWords = input
    .trim()
    .split(/\s+/)
    .map((word) => word.replace(/[.,:;!?()[\]{}]/g, ""))
    .filter(Boolean);
  const ignored = new Set(["Should", "should", "We", "we", "ICC", "icc", "Continue", "continue", "Working", "working", "With", "with", "Supplier", "supplier"]);

  for (let index = cleanedWords.length - 1; index >= 0; index -= 1) {
    const word = cleanedWords[index];
    if (!ignored.has(word)) {
      return word;
    }
  }

  return "";
}

function getChamberOverlay(route: WorkspaceRoute, activePath: string) {
  if (activePath === "/missions") {
    return {
      summary: "Mission context remains available while ATHENA stays central.",
      items: [
        { label: "Current Channel", value: "Executive Mission", detail: "Use the chamber input below ATHENA to direct execution." },
        { label: "Execution", value: "Connected", detail: "Mission execution continues through the existing backend integration." },
      ],
    };
  }

  if (activePath === "/operations") {
    return {
      summary: "Operational signals are present as chamber context, not a separate dashboard.",
      items: [
        { label: "System Status", value: "Optimal", detail: "Runtime posture is stable." },
        { label: "Active Missions", value: "0", detail: "No active executive missions are currently running." },
        { label: "Critical Alerts", value: "0", detail: "No critical operational alerts detected." },
      ],
    };
  }

  if (activePath === "/approvals") {
    return {
      summary: "Approvals remain near ATHENA so decisions stay conversational.",
      items: [
        { label: "Pending", value: "2", detail: "Two executive approvals require your attention." },
        { label: "Decision Mode", value: "Guarded", detail: "ATHENA will request confirmation before continuing approval-gated work." },
      ],
    };
  }

  if (activePath === "/knowledge") {
    return {
      summary: "Institutional memory is available as chamber context.",
      items: [
        { label: "Knowledge State", value: "Ready", detail: "ATHENA can reference organizational intelligence during missions." },
        { label: "Learning", value: "Enabled", detail: "Mission outcomes remain available to the learning layer." },
      ],
    };
  }

  if (activePath === "/organization") {
    return {
      summary: "Organization context frames ATHENA's executive reasoning.",
      items: [
        { label: "Enterprise Context", value: "Loaded", detail: "Company structure remains available for mission interpretation." },
        { label: "Governance", value: "Active", detail: "Executive constraints remain in force." },
      ],
    };
  }

  if (activePath === "/strategic-objectives") {
    return {
      summary: "Strategic objectives guide ATHENA without pulling focus from the chamber.",
      items: [
        { label: "Strategic Layer", value: "Ready", detail: "Mission recommendations can be evaluated against executive direction." },
        { label: "Priority Mode", value: "Executive", detail: "ATHENA keeps decisions aligned to company objectives." },
      ],
    };
  }

  return {
    summary: `${route.title} is available as chamber context while ATHENA remains present.`,
    items: [
      { label: "Context", value: "Available", detail: "This workspace section now opens around ATHENA." },
      { label: "Presence", value: "Persistent", detail: "The chamber remains active across navigation." },
    ],
  };
}

function normalizePath(path: string) {
  const clean = path.replace(/\/+$/, "") || "/";
  return routes.some((route) => route.path === clean) ? clean : "/";
}

export default App;
