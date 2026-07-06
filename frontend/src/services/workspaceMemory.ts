import { AthenaPresenceState, type AthenaPresenceState as AthenaPresenceStateValue } from "../components/athenaPresenceState";

const WORKSPACE_MEMORY_KEY = "athena.workspaceMemory";

export type WorkspaceMemory = {
  lastMission: string;
  lastRecommendation: string;
  lastApproval: string;
  lastGreeting: string;
  lastInteractionTime: string;
  lastPresenceState: AthenaPresenceStateValue;
};

const emptyMemory: WorkspaceMemory = {
  lastMission: "",
  lastRecommendation: "",
  lastApproval: "",
  lastGreeting: "",
  lastInteractionTime: "",
  lastPresenceState: AthenaPresenceState.BOOTING,
};

export function readWorkspaceMemory(): WorkspaceMemory | null {
  if (typeof window === "undefined") {
    return null;
  }

  const storedMemory = window.localStorage.getItem(WORKSPACE_MEMORY_KEY);
  if (!storedMemory) {
    return null;
  }

  try {
    const parsedMemory = JSON.parse(storedMemory) as Partial<WorkspaceMemory>;
    return {
      ...emptyMemory,
      ...parsedMemory,
      lastPresenceState: normalizePresenceState(parsedMemory.lastPresenceState),
    };
  } catch {
    return null;
  }
}

export function writeWorkspaceMemory(memory: WorkspaceMemory) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(WORKSPACE_MEMORY_KEY, JSON.stringify(memory));
}

export function updateWorkspaceMemory(patch: Partial<WorkspaceMemory>) {
  const currentMemory = readWorkspaceMemory() ?? emptyMemory;
  const nextMemory = {
    ...currentMemory,
    ...patch,
    lastInteractionTime: patch.lastInteractionTime ?? new Date().toISOString(),
  };

  writeWorkspaceMemory(nextMemory);
  return nextMemory;
}

export function clearWorkspaceMemory() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(WORKSPACE_MEMORY_KEY);
}

function normalizePresenceState(state: WorkspaceMemory["lastPresenceState"] | undefined) {
  const states = Object.values(AthenaPresenceState);
  return states.includes(state ?? AthenaPresenceState.BOOTING) ? state ?? AthenaPresenceState.BOOTING : AthenaPresenceState.BOOTING;
}
