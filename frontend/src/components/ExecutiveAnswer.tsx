import type { AthenaAnswer } from "../types/athena";

type Props = {
    answer: AthenaAnswer | null;
    intent: string;
};

export function ExecutiveAnswer({
    answer,
    intent,
}: Props) {

    if (!answer) {
        return (
            <div className="answer-panel">

                <p className="eyebrow">
                    EXECUTIVE ANSWER
                </p>

                <div className="empty-state">
                    <h3>ATHENA is ready.</h3>

                    <p>
                        Ask about products, tenders, warranty,
                        delivery, payment, risk or compliance.
                    </p>
                </div>

            </div>
        );
    }

    return (
        <div className="answer-panel">

            <p className="eyebrow">
                EXECUTIVE ANSWER
            </p>

            <div className="answer-card">

                {intent && (
                    <div className="intent-pill">
                        {intent}
                    </div>
                )}

                <h3>
                    {answer.direct_answer}
                </h3>

                <p className="summary">
                    {answer.executive_summary}
                </p>

                <div className="answer-grid">

                    <AnswerList
                        title="Supporting Points"
                        items={answer.supporting_points}
                    />

                    <AnswerList
                        title="Risks"
                        items={answer.risks_or_uncertainties}
                    />

                    <AnswerList
                        title="Actions"
                        items={answer.recommended_actions}
                    />

                </div>

                <div className="confidence">
                    Confidence
                    <strong>
                        {answer.confidence_score ?? 0}%
                    </strong>
                </div>

            </div>

        </div>
    );
}

function AnswerList({
    title,
    items,
}: {
    title: string;
    items?: string[];
}) {

    if (!items || items.length === 0) {
        return null;
    }

    return (
        <div className="section">

            <h4>
                {title}
            </h4>

            <ul>

                {items.map((item, index) => (

                    <li key={index}>
                        {item}
                    </li>

                ))}

            </ul>

        </div>
    );
}