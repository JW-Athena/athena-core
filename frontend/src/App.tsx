import { useEffect, useMemo, useState } from "react";
import "./App.css";

import { AppShell } from "./components/AppShell";
import { AthenaEnvironment } from "./components/AthenaEnvironment";
import { AthenaPresenceEngine } from "./components/AthenaPresenceEngine";
import { AthenaPresenceState } from "./components/athenaPresenceState";
import {
  executeExecutiveReasoning,
  executeMission,
  executeTenderExecutive,
  type ExecutiveMissionResponse,
  type ExecutiveReasoningResponse,
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
  createMissionConversation,
  createReasoningConversation,
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

const missionSteps = [
  "Mission accepted",
  "Planning objective",
  "Executing capabilities",
  "Evaluating outcome",
  "Learning from execution",
  "Checking approvals",
];

type ExecutionMode = "mission" | "reasoning" | "tender" | null;

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
  const [mission, setMission] = useState("");
  const [submittedMission, setSubmittedMission] = useState(() => workspaceMemory?.lastMission ?? "");
  const [isExecuting, setIsExecuting] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>(null);
  const [missionResult, setMissionResult] = useState<ExecutiveMissionResponse | null>(null);
  const [reasoningResult, setReasoningResult] = useState<ExecutiveReasoningResponse | null>(null);
  const [tenderResult, setTenderResult] = useState<TenderExecutiveResponse | null>(null);
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
  const missionIntent = detectMissionIntent(mission);
  const hasDraftMission = mission.trim().length > 0;
  const continuityGreeting = workspaceMemory?.lastMission ? buildContinuityGreeting(workspaceMemory) : "";
  const greetingMessage = missionIntent.hint ? missionIntent.greeting : continuityGreeting || missionIntent.greeting;
  const chamberLines = buildChamberLines({
    missionIntent,
    workspaceMemory,
    submittedMission,
    visibleProtocolLines,
    isExecuting,
    executionMode,
    missionError,
    greetingMessage,
  });

  useEffect(() => {
    if (!isExecuting) {
      return;
    }

    if (visibleSteps.length >= missionSteps.length) {
      return;
    }

    const timer = window.setTimeout(() => {
      setVisibleSteps((steps) => [...steps, missionSteps[steps.length]]);
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [isExecuting, visibleSteps.length]);

  useEffect(() => {
    if (!missionResult && !reasoningResult && !tenderResult && !missionError) {
      return;
    }

    const conversation = missionError
      ? createErrorConversation(missionError)
      : tenderResult
        ? createTenderConversation(tenderResult)
      : reasoningResult
        ? createReasoningConversation(reasoningResult)
        : createMissionConversation(missionResult);
    const lines = conversation.lines;

    if (protocolLines.length === 0) {
      setProtocolLines(lines);
      return;
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
          } else if (reasoningResult || tenderResult) {
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
    missionError,
    missionResult,
    protocolLines,
    reasoningResult,
    tenderResult,
    setPresenceState,
    visibleProtocolLines.length,
  ]);

  useEffect(() => {
    if (isExecuting || isSpeaking || submittedMission) {
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
  }, [hasDraftMission, isExecuting, isSpeaking, setPresenceState, submittedMission]);

  const handleExecuteMission = async () => {
    const nextMission = mission.trim();
    if (!nextMission) {
      return;
    }

    setSubmittedMission(nextMission);
    setVisibleSteps([missionSteps[0]]);
    setMissionResult(null);
    setReasoningResult(null);
    setTenderResult(null);
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
        lastPresenceState: AthenaPresenceState.THINKING,
      }),
    );
    setIsExecuting(true);

    try {
      if (looksLikeTenderBidQuestion(nextMission)) {
        setExecutionMode("tender");
        setVisibleSteps([]);
        const result = await executeTenderExecutive(nextMission);
        setTenderResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            lastRecommendation: result.bid_decision ? `Tender recommendation: ${result.bid_decision}` : "",
            lastApproval: result.key_blockers?.[0] || "",
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
            lastRecommendation: result.executive_recommendation || result.recommended_next_action || "",
            lastApproval: result.requires_executive_attention ? "This requires executive attention." : "",
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      } else {
        setExecutionMode("mission");
        const result = await executeMission(nextMission);
        const nextRecommendation =
          result.executive_response?.recommended_next_action ||
          result.executive_response?.summary ||
          "ATHENA completed the mission and prepared an executive recommendation.";
        const nextApproval =
          result.approval_request?.reason ||
          result.approval_request?.required_action ||
          (result.executive_response?.requires_approval ? "Executive approval is required." : "");

        setMissionResult(result);
        setWorkspaceMemory(
          updateWorkspaceMemory({
            lastMission: nextMission,
            lastRecommendation: nextRecommendation,
            lastApproval: nextApproval,
            lastGreeting: currentProtocolGreeting(),
            lastPresenceState: AthenaPresenceState.SPEAKING,
          }),
        );
      }
      setPresenceState(AthenaPresenceState.SPEAKING);
      setIsSpeaking(true);
    } catch (error) {
      const errorMessage = looksLikeExecutiveQuestion(nextMission) || looksLikeTenderBidQuestion(nextMission)
        ? "I cannot reach the Executive Brain right now."
        : error instanceof Error
          ? error.message
          : "ATHENA backend is not reachable.";
      setMissionError(errorMessage);
      setWorkspaceMemory(
        updateWorkspaceMemory({
          lastMission: nextMission,
          lastRecommendation: "",
          lastApproval: "",
          lastGreeting: currentProtocolGreeting(),
          lastPresenceState: AthenaPresenceState.ERROR,
        }),
      );
      setPresenceState(
        looksLikeExecutiveQuestion(nextMission) || looksLikeTenderBidQuestion(nextMission)
          ? AthenaPresenceState.ERROR
          : AthenaPresenceState.SPEAKING,
      );
      setIsSpeaking(true);
    } finally {
      if (looksLikeExecutiveQuestion(nextMission) || looksLikeTenderBidQuestion(nextMission)) {
        setVisibleSteps([]);
      } else {
        setVisibleSteps(missionSteps);
      }
      setIsExecuting(false);
    }
  };

  const returnToListening = () => {
    setMission("");
    setSubmittedMission("");
    setVisibleSteps([]);
    setMissionResult(null);
    setReasoningResult(null);
    setTenderResult(null);
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
    if (!workspaceMemory?.lastMission) {
      return;
    }

    setMission("");
    setSubmittedMission(workspaceMemory.lastMission);
    setProtocolLines(buildMemorySpeech(workspaceMemory));
    setVisibleProtocolLines(buildMemorySpeech(workspaceMemory));
    setShowProtocolOffer(false);
    setBriefOpen(false);
    setPresenceState(AthenaPresenceState.WAITING);
  };

  const startNewMission = () => {
    clearWorkspaceMemory();
    setWorkspaceMemory(null);
    setMission("");
    setSubmittedMission("");
    setMissionResult(null);
    setReasoningResult(null);
    setTenderResult(null);
    setMissionError("");
    setProtocolLines([]);
    setVisibleProtocolLines([]);
    setShowProtocolOffer(false);
    setVisibleSteps([]);
    setBriefOpen(false);
    setExecutionMode(null);
    setPresenceState(AthenaPresenceState.IDLE);
  };

  return (
    <section className={`executive-home env-state-${presenceState}`}>
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

        <form className={submittedMission ? "command-console compact" : "command-console"} onSubmit={(event) => event.preventDefault()}>
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
            placeholder="Tell me what you want to accomplish..."
          />
          {missionIntent.hint && <p className="mission-hint">Possible mission: {missionIntent.hint}</p>}
          <div className="chamber-actions">
            {workspaceMemory?.lastMission && !mission.trim() && (
              <button type="button" onClick={resumeLastMission}>
                Continue Previous Mission
              </button>
            )}
            <button type="button" onClick={startNewMission}>
              Start New Mission
            </button>
            {mission.trim() && (
              <button type="button" onClick={handleExecuteMission} disabled={isExecuting || isSpeaking}>
                {looksLikeExecutiveQuestion(mission) ? "Ask ATHENA" : "Execute Mission"}
              </button>
            )}
          </div>
        </form>

        {submittedMission && (
          <section className="conversation-exchange" aria-live="polite">
            {!isSpeaking && showProtocolOffer && visibleProtocolLines.length > 0 && (
              <div className="conversation-actions">
                <button type="button" onClick={() => setBriefOpen(true)}>
                  {tenderResult ? "View Executive Brief" : "YES"}
                </button>
                {!tenderResult && (
                  <button type="button" onClick={returnToListening}>
                    NOT NOW
                  </button>
                )}
              </div>
            )}
          </section>
        )}

        <section
          className={isExecuting && executionMode !== "reasoning" ? "command-timeline visible" : "command-timeline"}
          aria-live="polite"
        >
            <div className="command-timeline-header">
              <span>{isExecuting ? "Mission executing" : "Mission response received"}</span>
              <strong>{visibleSteps.length}/{missionSteps.length}</strong>
            </div>

            <ol>
              {visibleSteps.map((step, index) => (
                <li key={step} className={index === visibleSteps.length - 1 && isExecuting ? "active" : "complete"}>
                  <span />
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
  steps,
  onClose,
}: {
  open: boolean;
  result: ExecutiveMissionResponse | null;
  reasoningResult: ExecutiveReasoningResponse | null;
  tenderResult: TenderExecutiveResponse | null;
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
          <h3>{tenderResult ? "Tender Executive Brief" : reasoningResult ? "Reasoning Evidence" : "Mission Detail"}</h3>
        </div>
        <button type="button" onClick={onClose} aria-label="Close executive brief">
          Close
        </button>
      </div>

      {tenderResult ? (
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
  missionIntent,
  workspaceMemory,
  submittedMission,
  visibleProtocolLines,
  isExecuting,
  executionMode,
  missionError,
  greetingMessage,
}: {
  missionIntent: MissionIntent;
  workspaceMemory: WorkspaceMemory | null;
  submittedMission: string;
  visibleProtocolLines: ConversationProtocolLine[];
  isExecuting: boolean;
  executionMode: ExecutionMode;
  missionError: string;
  greetingMessage: string;
}) {
  if (missionError) {
    return [missionError];
  }

  if (isExecuting) {
    if (executionMode === "reasoning") {
      return ["ATHENA is reasoning..."];
    }

    return ["Mission accepted.", "I am evaluating the objective.", "I will return with a recommendation."];
  }

  if (submittedMission && visibleProtocolLines.length > 0) {
    return visibleProtocolLines.slice(-4).map((line) => line.text);
  }

  if (missionIntent.hint) {
    return [greetingMessage];
  }

  if (workspaceMemory?.lastMission) {
    const lines = [
      currentProtocolGreeting(),
      buildContinuityGreeting(workspaceMemory),
      workspaceMemory.lastRecommendation ? "My recommendation remains unchanged." : "I am holding the previous mission context.",
    ];

    if (workspaceMemory.lastApproval) {
      lines.push(workspaceMemory.lastApproval);
    } else if (workspaceMemory.lastRecommendation) {
      lines.push(workspaceMemory.lastRecommendation);
    }

    return lines.slice(0, 4);
  }

  return [buildCurrentGreeting(), "How may I assist the company today?"];
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

function buildContinuityGreeting(memory: WorkspaceMemory) {
  const sessionReference = getSessionReference(memory.lastInteractionTime);
  const missionReference = summarizeMission(memory.lastMission);

  return `${sessionReference} we completed ${missionReference}. Would you like to continue where we left off?`;
}

const buildCurrentGreeting = currentProtocolGreeting;

function getSessionReference(timestamp: string) {
  if (!timestamp) {
    return "In our previous session";
  }

  const interactionDate = new Date(timestamp);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  if (isSameLocalDay(interactionDate, yesterday)) {
    return "Yesterday";
  }

  if (isSameLocalDay(interactionDate, today)) {
    return "Earlier today";
  }

  return "In our previous session";
}

function isSameLocalDay(leftDate: Date, rightDate: Date) {
  return (
    leftDate.getFullYear() === rightDate.getFullYear() &&
    leftDate.getMonth() === rightDate.getMonth() &&
    leftDate.getDate() === rightDate.getDate()
  );
}

function summarizeMission(mission: string) {
  const normalizedMission = mission.toLowerCase();

  if (normalizedMission.includes("ministry of interior") || normalizedMission.includes("moi")) {
    return "the Ministry of Interior assessment";
  }

  if (normalizedMission.includes("tender")) {
    return "the tender assessment";
  }

  if (normalizedMission.includes("supplier")) {
    return "the supplier review";
  }

  if (normalizedMission.includes("contract")) {
    return "the contract review";
  }

  return "the last executive mission";
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

  if (normalizedMission.includes("contract")) {
    return {
      hint: "Contract Intelligence",
      greeting: "I can assist with contract intelligence.",
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

function looksLikeTenderBidQuestion(input: string) {
  const normalized = input.trim().toLowerCase();
  return /^(should)\b/.test(normalized) && /\b(icc|we)\b/.test(normalized) && /\bbid\b/.test(normalized);
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
