type MetricCardProps = {
    title: string;
    value: string | number;
};

export function MetricCard({
    title,
    value,
}: MetricCardProps) {

    return (
        <div className="brief-item">

            <span>
                {title}
            </span>

            <strong>
                {value}
            </strong>

        </div>
    );

}