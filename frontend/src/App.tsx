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
  createContractConversation,
  createDailyBriefingConversation,
  createMeetingConversation,
  createMissionConversation,
  createProcurementConversation,
  createReasoningConversation,
  createSupplierConversation,
  createTenderConversation,
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
  const missionIntent = detectMissionIntent(mission);
  const hasDraftMission = mission.trim().length > 0;
  const greetingMessage = missionIntent.hint ? missionIntent.greeting : missionIntent.greeting;
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
    if (!isExecuting) {
      return;
    }

    if (visibleSteps.length >= orchestrationSteps.length) {
      return;
    }

    const timer = window.setTimeout(() => {
      setVisibleSteps((steps) => [...steps, orchestrationSteps[steps.length]]);
    }, visibleSteps.length === 0 ? 220 : 760);

    return () => window.clearTimeout(timer);
  }, [isExecuting, orchestrationSteps, visibleSteps.length]);

  useEffect(() => {
    if (isExecuting) {
      return;
    }

    if (!missionResult && !reasoningResult && !tenderResult && !supplierResult && !contractResult && !procurementResult && !meetingResult && !briefingResult && !missionError) {
      return;
    }

    const conversation = missionError
      ? createErrorConversation(missionError)
      : briefingResult
        ? createDailyBriefingConversation(briefingResult)
      : meetingResult
        ? createMeetingConversation(meetingResult)
      : procurementResult
        ? createProcurementConversation(procurementResult)
      : contractResult
        ? createContractConversation(contractResult)
      : supplierResult
        ? createSupplierConversation(supplierResult)
      : tenderResult
        ? createTenderConversation(tenderResult)
      : reasoningResult
        ? createReasoningConversation(reasoningResult)
        : createMissionConversation(missionResult);
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
            setPresenceState(AthenaPresenceState.SUCCESS);
            setWorkspaceMemory(
              updateWorkspaceMemory({
                lastPresenceState: AthenaPresenceState.SUCCESS,
              }),
            );
          } else if (missionResult?.mission_status === "pending_approval") {
            setPresenceState(AthenaPresenceState.APPROVAL);
            setWorkspaceMemory(
              updateWorkspaceMemory({
                lastPresenceState: AthenaPresenceState.APPROVAL,
              }),
            );
          } else {
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

    setSubmittedMission(nextMission);
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
    setIsExecuting(true);

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
      setIsExecuting(false);
    }
  };

  const returnToListening = () => {
    setMission("");
    setSubmittedMission("");
    setVisibleSteps([]);
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

        <section
          className={isExecuting ? "command-timeline visible" : "command-timeline"}
          aria-live="polite"
        >
            <div className="command-timeline-header">
              <span>Executive thinking</span>
            </div>

            <ol>
              {visibleSteps.map((step, index) => (
                <li key={step} className={index === visibleSteps.length - 1 && isExecuting ? "active" : "complete"}>
                  <p>{step}</p>
                </li>
              ))}
            </ol>
          </section>
      </div>

      {activePath !== "/" && (
        <ChamberOverlay route={route} activePath={activePath} />
      )}

      <ExecutiveBriefDrawer
        open={briefOpen}
        result={missionResult}
        reasoningResult={reasoningResult}
        tenderResult={tenderResult}
        supplierResult={supplierResult}
        steps={visibleSteps}
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

function ExecutiveBriefDrawer({
  open,
  result,
  reasoningResult,
  tenderResult,
  supplierResult,
  steps,
  onClose,
}: {
  open: boolean;
  result: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
  supplierResult: SupplierExecutiveResponse | null;
  steps: string[];
  onClose: () => void;
}) {
  const executiveResponse = result?.executive_response;
  const evaluation = result?.mission_evaluation;
  const approvalRequest = result?.approval_request;

  return (
    <aside className={open ? "executive-brief-drawer open" : "executive-brief-drawer"} aria-hidden={!open}>
      <div className="brief-drawer-header">
        <div>
          <span>Executive Brief</span>
          <h3>
            {tenderResult
              ? "Tender Executive Brief"
              : supplierResult
                ? "Supplier Evidence"
                : reasoningResult
                  ? "Reasoning Evidence"
                  : "Mission Detail"}
          </h3>
        </div>
        <button type="button" onClick={onClose} aria-label="Close executive brief">
          Close
        </button>
      </div>

      {supplierResult ? (
        <div className="brief-drawer-body">
          <section>
            <span>Executive Summary</span>
            <p>{supplierResult.executive_summary || "No executive summary was returned."}</p>
            <p>{supplierResult.executive_reasoning || "No executive reasoning was returned."}</p>
          </section>

          <section>
            <span>Supplier Direction</span>
            <dl>
              <div>
                <dt>Decision</dt>
                <dd>{supplierResult.supplier_decision || "Review"}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{formatConfidence(supplierResult.confidence)}</dd>
              </div>
              <div>
                <dt>Risk Level</dt>
                <dd>{supplierResult.risk_level || "Unknown"}</dd>
              </div>
            </dl>
          </section>

          <section>
            <span>Key Strengths</span>
            <ol>
              {(supplierResult.key_strengths || []).map((strength) => (
                <li key={strength}>{strength}</li>
              ))}
            </ol>
          </section>

          <section>
            <span>Key Concerns</span>
            <ol>
              {(supplierResult.key_concerns || []).map((concern) => (
                <li key={concern}>{concern}</li>
              ))}
            </ol>
          </section>

          <section>
            <span>Recommended Actions</span>
            <ol>
              {(supplierResult.recommended_actions || []).map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ol>
          </section>
        </div>
      ) : tenderResult ? (
        <div className="brief-drawer-body">
          <section>
            <span>Executive Summary</span>
            <p>{tenderResult.executive_summary || "No executive summary was returned."}</p>
            <p>{tenderResult.executive_reasoning || "No executive reasoning was returned."}</p>
          </section>

          <section>
            <span>Bid Direction</span>
            <dl>
              <div>
                <dt>Decision</dt>
                <dd>{tenderResult.bid_decision || "Review"}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{formatConfidence(tenderResult.confidence)}</dd>
              </div>
              <div>
                <dt>Commercial Risk</dt>
                <dd>{tenderResult.commercial_risk || "Unknown"}</dd>
              </div>
              <div>
                <dt>Technical Risk</dt>
                <dd>{tenderResult.technical_risk || "Unknown"}</dd>
              </div>
            </dl>
          </section>

          <section>
            <span>Primary Blockers</span>
            <ol>
              {(tenderResult.key_blockers || []).map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ol>
          </section>

          <section>
            <span>Required Departments</span>
            <ol>
              {(tenderResult.required_departments || []).map((department) => (
                <li key={department}>{department}</li>
              ))}
            </ol>
          </section>

          <section>
            <span>Recommended Next Actions</span>
            <ol>
              {(tenderResult.recommended_next_actions || []).map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ol>
          </section>
        </div>
      ) : reasoningResult ? (
        <div className="brief-drawer-body">
          <section>
            <span>Executive Recommendation</span>
            <p>{reasoningResult.executive_recommendation || "No recommendation was returned."}</p>
            <p>{reasoningResult.executive_explanation || "No executive explanation was returned."}</p>
          </section>

          <section>
            <span>Key Findings</span>
            <ol>
              {(reasoningResult.key_findings || []).map((finding) => (
                <li key={finding}>{finding}</li>
              ))}
            </ol>
          </section>

          <section>
            <span>Evidence</span>
            <ol>
              {(reasoningResult.evidence || []).map((item, index) => (
                <li key={`${item.source || "evidence"}-${index}`}>
                  <strong>{item.source || "Evidence"}</strong>
                  <p>{item.summary || "No evidence summary was returned."}</p>
                </li>
              ))}
            </ol>
          </section>

          <section>
            <span>Technical Details</span>
            <dl>
              <div>
                <dt>Domain</dt>
                <dd>{reasoningResult.reasoning_domain || "Not returned"}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{formatConfidence(reasoningResult.confidence)}</dd>
              </div>
              <div>
                <dt>Executive Attention</dt>
                <dd>{formatBoolean(reasoningResult.requires_executive_attention)}</dd>
              </div>
            </dl>
          </section>
        </div>
      ) : result ? (
        <div className="brief-drawer-body">
          <section>
            <span>Current Backend Report</span>
            <p>{executiveResponse?.summary || "No executive summary was returned."}</p>
            <p>{executiveResponse?.recommended_next_action || "No recommended next action was returned."}</p>
          </section>

          <section>
            <span>Mission Evaluation</span>
            <dl>
              <div>
                <dt>Confidence</dt>
                <dd>{formatConfidence(evaluation?.confidence)}</dd>
              </div>
              <div>
                <dt>Decision Ready</dt>
                <dd>{formatBoolean(evaluation?.decision_ready)}</dd>
              </div>
              <div>
                <dt>Approval Required</dt>
                <dd>{formatBoolean(evaluation?.approval_required)}</dd>
              </div>
            </dl>
          </section>

          {approvalRequest && (
            <section>
              <span>Approval Detail</span>
              <dl>
                <div>
                  <dt>Approval ID</dt>
                  <dd>{approvalRequest.approval_id || "Not provided"}</dd>
                </div>
                <div>
                  <dt>Reason</dt>
                  <dd>{approvalRequest.reason || "No approval reason was returned."}</dd>
                </div>
                <div>
                  <dt>Required Action</dt>
                  <dd>{approvalRequest.required_action || "No required action was returned."}</dd>
                </div>
              </dl>
            </section>
          )}

          <section>
            <span>Timeline</span>
            <ol>
              {steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </section>

          <section>
            <span>Technical Details</span>
            <dl>
              <div>
                <dt>Status</dt>
                <dd>{result.mission_status || "Not returned"}</dd>
              </div>
              <div>
                <dt>Engine</dt>
                <dd>{result.engine || "Not returned"}</dd>
              </div>
            </dl>
          </section>
        </div>
      ) : (
        <p className="brief-empty">No executive brief is available yet.</p>
      )}
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

function cleanObjectiveText(value: string) {
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

function formatBoolean(value: boolean | undefined) {
  if (value === undefined) {
    return "Not returned";
  }

  return value ? "Yes" : "No";
}

function formatConfidence(value: number | undefined) {
  if (value === undefined) {
    return "Not returned";
  }

  return `${value}%`;
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
