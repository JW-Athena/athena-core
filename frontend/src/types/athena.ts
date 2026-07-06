export type AthenaAnswer = {
  direct_answer?: string;
  executive_summary?: string;
  supporting_points?: string[];
  risks_or_uncertainties?: string[];
  recommended_actions?: string[];
  confidence_score?: number;
};

export type AthenaIntent = {
  question: string;
  intent: string;
};

export type AthenaResult = {
  question: string;
  answer: AthenaAnswer;
  intent: AthenaIntent;
};

export type AthenaResponse = {
  engine: string;
  name: string;
  status: string;
  result: AthenaResult;
};