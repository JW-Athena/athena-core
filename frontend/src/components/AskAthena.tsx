import { useState } from "react";

import { askAthena } from "../services/athenaApi";
import type { AthenaAnswer } from "../types/athena";

import { ExecutiveAnswer } from "./ExecutiveAnswer";

export function AskAthena() {

    const [question, setQuestion] = useState("Tell me about Tactical Boots");

    const [answer, setAnswer] = useState<AthenaAnswer | null>(null);

    const [intent, setIntent] = useState("");

    const [loading, setLoading] = useState(false);

    async function handleAsk() {

        setLoading(true);

        try {

            const response = await askAthena(question);

            setAnswer(response.result.answer);

            setIntent(response.result.intent.intent);

        }
        catch {

            setAnswer({
                direct_answer: "ATHENA backend is unavailable.",
                executive_summary: "Unable to contact backend.",
                supporting_points: [],
                risks_or_uncertainties: [],
                recommended_actions: [],
                confidence_score: 0,
            });

            setIntent("");

        }

        setLoading(false);

    }

    return (

        <>

            <section className="hero">

                <p className="eyebrow">
                    ASK ATHENA
                </p>

                <h3>
                    What decision do you need today?
                </h3>

                <div className="ask-box">

                    <input
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter") {
                                handleAsk();
                            }
                        }}
                    />

                    <button
                        onClick={handleAsk}
                        disabled={loading}
                    >
                        {loading ? "Thinking..." : "Ask"}
                    </button>

                </div>

            </section>

            <ExecutiveAnswer
                answer={answer}
                intent={intent}
            />

        </>

    );

}