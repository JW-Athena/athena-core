export type DashboardSummary = {
  documents_processed: number;
  entities_stored: number;
  relationships: number;
  products_identified: number;
  open_risks: number;
  tenders_identified: number;
  primary_product: string;
};

export type DashboardResponse = {
  engine: string;
  status: string;
  summary: DashboardSummary;
};