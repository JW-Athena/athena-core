type PageHeaderProps = {
  eyebrow: string;
  title: string;
  summary: string;
};

export function PageHeader({ eyebrow, title, summary }: PageHeaderProps) {
  return (
    <div className="page-header">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
      <p>{summary}</p>
    </div>
  );
}
