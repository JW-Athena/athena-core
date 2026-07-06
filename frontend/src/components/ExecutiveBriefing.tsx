import { useEffect, useMemo, useState } from "react";

type ExecutiveBriefingProps = {
  active: boolean;
  pendingApprovals: number;
  activeMissions: number;
  criticalAlerts: number;
  onSpeakingChange?: (speaking: boolean) => void;
};

export function ExecutiveBriefing({
  active,
  pendingApprovals,
  activeMissions,
  criticalAlerts,
  onSpeakingChange,
}: ExecutiveBriefingProps) {
  const [visibleLines, setVisibleLines] = useState<string[]>([]);
  const lines = useMemo(
    () => buildBriefingLines({ pendingApprovals, activeMissions, criticalAlerts }),
    [activeMissions, criticalAlerts, pendingApprovals],
  );

  useEffect(() => {
    if (!active) {
      const timer = window.setTimeout(() => onSpeakingChange?.(false), 1);
      return () => window.clearTimeout(timer);
    }

    const speakingTimer = window.setTimeout(() => {
      onSpeakingChange?.(visibleLines.length < lines.length);
    }, 1);

    if (visibleLines.length >= lines.length) {
      return () => window.clearTimeout(speakingTimer);
    }

    const lineTimer = window.setTimeout(
      () => {
        setVisibleLines((currentLines) => {
          const nextLine = lines[currentLines.length];
          return nextLine ? [...currentLines, nextLine] : currentLines;
        });
      },
      visibleLines.length === 0 ? 600 : 1200,
    );

    return () => {
      window.clearTimeout(speakingTimer);
      window.clearTimeout(lineTimer);
    };
  }, [active, lines, onSpeakingChange, visibleLines.length]);

  useEffect(() => {
    if (active || visibleLines.length === 0) {
      return;
    }

    const timer = window.setTimeout(
      () => {
        setVisibleLines([]);
      },
      720,
    );

    return () => window.clearTimeout(timer);
  }, [active, visibleLines.length]);

  return (
    <section className={active ? "executive-briefing active" : "executive-briefing"} aria-live="polite">
      <span>ATHENA</span>
      <div>
        {visibleLines.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>
    </section>
  );
}

function buildBriefingLines({
  pendingApprovals,
  activeMissions,
  criticalAlerts,
}: {
  pendingApprovals: number;
  activeMissions: number;
  criticalAlerts: number;
}) {
  const lines = ["Good morning, Wassim."];

  if (criticalAlerts > 0) {
    lines.push(`${criticalAlerts} critical operational alerts require your attention.`);
  }

  lines.push("All systems are operating normally.");

  if (pendingApprovals > 0) {
    lines.push(`${pendingApprovals === 2 ? "Two" : pendingApprovals} executive approvals require your attention.`);
  }

  if (criticalAlerts === 0) {
    lines.push("No critical operational alerts detected.");
  }

  if (activeMissions === 0) {
    lines.push("No active executive missions are currently running.");
  }

  lines.push("How may I assist the company today?");

  return lines;
}
