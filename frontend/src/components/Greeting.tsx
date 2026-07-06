import { useEffect, useMemo, useState } from "react";

type GreetingProps = {
  pendingApprovals: number;
  overrideMessage?: string;
};

export function Greeting({ pendingApprovals, overrideMessage }: GreetingProps) {
  const [now, setNow] = useState(() => new Date());
  const [isFading, setIsFading] = useState(false);
  const hour = now.getHours();
  const period = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  const secondLine = useMemo(
    () =>
      overrideMessage ||
      (pendingApprovals > 0
        ? "Two executive approvals require your attention."
        : "How may I assist the company today?"),
    [overrideMessage, pendingApprovals],
  );
  const [displayedGreeting, setDisplayedGreeting] = useState(() => ({
    period,
    secondLine,
  }));

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (displayedGreeting.period === period && displayedGreeting.secondLine === secondLine) {
      return;
    }

    const fadeOutTimer = window.setTimeout(() => setIsFading(true), 1);
    const swapTimer = window.setTimeout(() => {
      setDisplayedGreeting({ period, secondLine });
      setIsFading(false);
    }, 260);

    return () => {
      window.clearTimeout(fadeOutTimer);
      window.clearTimeout(swapTimer);
    };
  }, [displayedGreeting, period, secondLine]);

  return (
    <div className={isFading ? "command-copy greeting-fading" : "command-copy"}>
      <p>{`Good ${displayedGreeting.period}, Wassim.`}</p>
      <h2>{displayedGreeting.secondLine}</h2>
    </div>
  );
}
