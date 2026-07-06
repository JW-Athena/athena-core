import type { AthenaPresenceState } from "./athenaPresenceState";

type AthenaEnvironmentProps = {
  state: AthenaPresenceState;
};

export function AthenaEnvironment({ state }: AthenaEnvironmentProps) {
  return (
    <div className={`athena-environment env-state-${state}`} aria-hidden="true">
      <div className="environment-grid" />
      <div className="environment-glow" />
      <div className="environment-particles" />
      <div className="environment-scan" />
      <div className="environment-wave" />
    </div>
  );
}
