import { useEffect, useState } from "react";

import { MetricCard } from "./MetricCard";
import { getDashboardSummary } from "../services/dashboardApi";
import type { DashboardSummary } from "../types/dashboard";

export function ExecutiveBrief() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    getDashboardSummary()
      .then((data) => setSummary(data.summary))
      .catch(() => setSummary(null));
  }, []);

  return (
    <section className="executive-brief">
      <p className="eyebrow">TODAY'S EXECUTIVE BRIEF</p>

      <h3>ATHENA has prepared your command overview.</h3>

      <div className="brief-grid">
        <MetricCard
          title="Documents Processed"
          value={summary?.documents_processed ?? "—"}
        />

        <MetricCard
          title="Products Identified"
          value={summary?.products_identified ?? "—"}
        />

        <MetricCard
          title="Open Risks"
          value={summary?.open_risks ?? "—"}
        />

        <MetricCard
          title="Primary Product"
          value={summary?.primary_product ?? "—"}
        />
      </div>
    </section>
  );
}