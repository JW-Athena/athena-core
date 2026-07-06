import type { AthenaPresenceState } from "./athenaPresenceState";
import { AthenaFaceAsset } from "./AthenaFaceAsset";

type AthenaPresenceEngineProps = {
  state: AthenaPresenceState;
};

export function AthenaPresenceEngine({ state }: AthenaPresenceEngineProps) {
  return (
    <div className={`athena-face athena-state-${state}`} aria-label={`ATHENA presence: ${state}`}>
      <div className="athena-face-ring outer" />
      <div className="athena-face-ring middle" />
      <div className="athena-face-ring inner" />
      <div className="athena-face-ring signal one" />
      <div className="athena-face-ring signal two" />
      <div className="athena-face-ring success-wave" />
      <span className="athena-scanline" />
      <AthenaFaceAsset state={state} />
      <div className="athena-face-axis horizontal" />
      <div className="athena-face-axis vertical" />
    </div>
  );
}
