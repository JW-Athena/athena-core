import { useEffect, useState } from "react";

import { AthenaPresenceState, type AthenaPresenceState as AthenaPresenceStateValue } from "./athenaPresenceState";

type AthenaPresenceController = {
  presenceState: AthenaPresenceStateValue;
  setPresenceState: (state: AthenaPresenceStateValue) => void;
};

export function useAthenaPresenceEngine(
  initialState: AthenaPresenceStateValue = AthenaPresenceState.BOOTING,
): AthenaPresenceController {
  const [presenceState, setPresenceState] = useState<AthenaPresenceStateValue>(initialState);

  useEffect(() => {
    if (presenceState !== AthenaPresenceState.BOOTING) {
      return;
    }

    const timer = window.setTimeout(() => setPresenceState(AthenaPresenceState.IDLE), 1800);
    return () => window.clearTimeout(timer);
  }, [presenceState]);

  useEffect(() => {
    if (presenceState !== AthenaPresenceState.SUCCESS && presenceState !== AthenaPresenceState.ERROR) {
      return;
    }

    const timer = window.setTimeout(() => setPresenceState(AthenaPresenceState.IDLE), 1800);
    return () => window.clearTimeout(timer);
  }, [presenceState]);

  return { presenceState, setPresenceState };
}
