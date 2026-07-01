import json
import os
from typing import Dict

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class ResponseEngine:
    """
    Response Engine

    Creates the final executive answer from verified evidence.
    It uses full document text, not just summaries.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if OpenAI and self.api_key else None

    def respond(self, verified_package: Dict) -> Dict:
        if not self.client:
            return self._fallback_response(verified_package)

        return self._ai_response(verified_package)

    def _ai_response(self, verified_package: Dict) -> Dict:
        reasoning_package = verified_package.get("reasoning_package", {})
        question = reasoning_package.get("question", "")
        evidence = reasoning_package.get("evidence", [])
        warnings = verified_package.get("warnings", [])

        evidence_blocks = []

        for index, item in enumerate(evidence, start=1):
            full_text = item.get("full_text", "")
            evidence_blocks.append(
                f"""
SOURCE {index}
Document ID: {item.get("document_id")}
Filename: {item.get("filename")}
Document Type: {item.get("document_type")}
Summary:
{item.get("summary")}

Full Document Text:
{full_text[:7000]}
"""
            )

        prompt = f"""
You are ATHENA Core Response Engine.

Answer the user's question using ONLY the provided full source text.

Critical rules:
- Do not invent information.
- Do not confuse payment terms with warranty terms.
- Do not confuse warranty terms with delivery terms.
- Do not confuse delivery terms with payment terms.
- If the document says "Payment Terms: 30 days after delivery and acceptance", that is payment timing, NOT warranty timing.
- If the document says "5 year warranty against manufacturing defects", that means warranty is 5 years.
- If information is unclear, say it is unclear.
- Follow verification warnings strictly.
- Answer like an executive assistant to company management.
- Return ONLY valid JSON.

Verification warnings:
{warnings}

Required JSON format:
{{
  "direct_answer": "",
  "executive_summary": "",
  "supporting_points": [],
  "risks_or_uncertainties": [],
  "recommended_actions": [],
  "confidence_score": 0
}}

Question:
{question}

Sources:
{"".join(evidence_blocks)}
"""

        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You answer executive business questions using verified source evidence only. Accuracy is more important than confidence.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            answer = json.loads(raw)
        except Exception:
            answer = {
                "direct_answer": raw,
                "executive_summary": raw,
                "supporting_points": [],
                "risks_or_uncertainties": ["AI response was not valid JSON"],
                "recommended_actions": ["Review answer manually"],
                "confidence_score": 50,
            }

        return {
            "status": "success",
            "answer": answer,
        }

    def _fallback_response(self, verified_package: Dict) -> Dict:
        reasoning_package = verified_package.get("reasoning_package", {})
        evidence = reasoning_package.get("evidence", [])

        if not evidence:
            return {
                "status": "no_evidence",
                "answer": {
                    "direct_answer": "No relevant evidence found.",
                    "executive_summary": "",
                    "supporting_points": [],
                    "risks_or_uncertainties": ["No knowledge source matched the question"],
                    "recommended_actions": [],
                    "confidence_score": 0,
                },
            }

        best = evidence[0]

        return {
            "status": "fallback",
            "answer": {
                "direct_answer": best.get("summary") or "Relevant evidence found.",
                "executive_summary": best.get("summary") or "",
                "supporting_points": [f"Best source: {best.get('filename')}"],
                "risks_or_uncertainties": ["OpenAI is not available"],
                "recommended_actions": ["Review source manually"],
                "confidence_score": 40,
            },
        }