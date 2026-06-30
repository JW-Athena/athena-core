import os
import json

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class AthenaAI:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

    def executive_extract(self, text):
        prompt = f"""
You are Athena.

Read the following business document and extract executive information.

Return ONLY valid JSON.

Required JSON format:
{{
    "document_type": "",
    "customer": "",
    "supplier": "",
    "document_number": "",
    "document_date": "",
    "currency": "",
    "delivery_time": "",
    "payment_terms": "",
    "estimated_value": "",
    "executive_summary": ""
}}

Document:
{text[:12000]}
"""

        response = self.client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return json.loads(response.choices[0].message.content)