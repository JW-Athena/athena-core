type StatCardProps = {
  label: string;
  value: string;
  detail: string;
  tone?: "default" | "gold";
};

export function StatCard({ label, value, detail, tone = "default" }: StatCardProps) {
  return (
    <article className={tone === "gold" ? "stat-card gold" : "stat-card"}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}
