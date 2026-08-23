import {
    Badge,
    Button,
    Spinner,
} from "@fluentui/react-components";
import * as React from "react";

import {
    DashboardData,
    formatted,
    TaskRecord,
} from "./data";

export interface LaunchReadinessDashboardProps {
    data?: DashboardData;
    error?: string;
    launchName: string;
    loading: boolean;
    onRefresh: () => void;
}

type BadgeColor = "brand" | "danger" | "important" | "informative"
    | "severe" | "subtle" | "success" | "warning";
type DashboardTab = "overview" | "quality" | "risks";

export const LaunchReadinessDashboard: React.FC<LaunchReadinessDashboardProps> = ({
    data,
    error,
    launchName,
    loading,
    onRefresh,
}) => {
    const [activeTab, setActiveTab] = React.useState<DashboardTab>("overview");

    if (!data && loading) {
        return (
            <div className="lc-readiness lc-readiness-state">
                <Spinner label="Loading launch readiness signals" />
            </div>
        );
    }
    if (!data && error) {
        return (
            <div className="lc-readiness lc-readiness-state lc-readiness-error">
                <Icon tone="danger">!</Icon>
                <div>
                    <strong>Readiness dashboard unavailable</strong>
                    <p>{error}</p>
                </div>
                <Button appearance="secondary" onClick={onRefresh}>
                    Retry
                </Button>
            </div>
        );
    }
    if (!data) {
        return (
            <div className="lc-readiness lc-readiness-state">
                Save this Launch to load readiness signals.
            </div>
        );
    }

    const gateStatus = formatted(data.launch, "lc_qualitygatestatus", "Pending");
    const latestStatus = data.statusUpdates[0];
    const health = latestStatus
        ? formatted(latestStatus, "lc_health")
        : "No signal";
    const officialScore = data.launch.lc_qualitygatescore;
    const hasAgentVerdict = officialScore !== undefined
        && officialScore !== null
        && gateStatus !== "Pending";

    return (
        <section className="lc-readiness" aria-label={`${launchName} readiness dashboard`}>
            <nav className="lc-readiness-tabs" aria-label="Launch readiness views">
                <DashboardTabButton
                    active={activeTab === "overview"}
                    label="Overview"
                    onClick={() => setActiveTab("overview")}
                />
                <DashboardTabButton
                    active={activeTab === "risks"}
                    label="Risks"
                    onClick={() => setActiveTab("risks")}
                />
                <DashboardTabButton
                    active={activeTab === "quality"}
                    label="Quality"
                    onClick={() => setActiveTab("quality")}
                />
            </nav>

            {activeTab === "overview" && (
                <OverviewView
                    data={data}
                    gateStatus={gateStatus}
                    health={health}
                    hasAgentVerdict={hasAgentVerdict}
                />
            )}
            {activeTab === "risks" && <RisksView data={data} />}
            {activeTab === "quality" && (
                <QualityView
                    data={data}
                    gateStatus={gateStatus}
                    hasAgentVerdict={hasAgentVerdict}
                    officialScore={officialScore}
                />
            )}
        </section>
    );
};

const DashboardTabButton: React.FC<{
    active: boolean;
    label: string;
    onClick: () => void;
}> = ({ active, label, onClick }) => (
    <button
        className={`lc-readiness-tab${active ? " lc-readiness-tab-active" : ""}`}
        type="button"
        onClick={onClick}
        aria-selected={active}
        role="tab"
    >
        {label}
    </button>
);

const OverviewView: React.FC<{
    data: DashboardData;
    gateStatus: string;
    health: string;
    hasAgentVerdict: boolean;
}> = ({ data, gateStatus, health, hasAgentVerdict }) => {
    const latestStatus = data.statusUpdates[0];
    const topBlocker = data.blockedTasks[0];
    const topMilestone = data.milestones.find(
        (milestone) => ["Blocked", "AtRisk"].includes(
            formatted(milestone, "lc_milestonestatus")
        )
    );
    return (
        <>
            <div className="lc-readiness-context">
                <Badge appearance="filled" color={badgeColor(gateStatus)}>
                    Quality Gate: {gateStatus}
                </Badge>
                <span>
                    {hasAgentVerdict
                        ? "Agent-reviewed launch state"
                        : "Owner-reported state. Agent review has not run yet."}
                </span>
            </div>
            <div className="lc-readiness-kpis">
                <Kpi
                    label="Milestones"
                    value={data.milestones.length}
                    detail={`${data.milestoneCounts.Blocked ?? 0} blocked`}
                    tone={(data.milestoneCounts.Blocked ?? 0) > 0 ? "danger" : "neutral"}
                />
                <Kpi
                    label="Active blockers"
                    value={data.blockedTasks.length}
                    detail={data.blockedTasks.length ? "Action required" : "None"}
                    tone={data.blockedTasks.length ? "danger" : "success"}
                />
                <Kpi
                    label="Overdue work"
                    value={data.overdueTasks.length + data.overdueMilestones.length}
                    detail={`${data.overdueTasks.length} tasks`}
                    tone={data.overdueTasks.length + data.overdueMilestones.length ? "warning" : "success"}
                />
                <Kpi
                    label="Reported health"
                    value={health}
                    detail={latestStatus?.lc_postedat ? formatDate(latestStatus.lc_postedat) : "No update"}
                    tone={health === "Red" ? "danger" : health === "Yellow" ? "warning" : "success"}
                />
            </div>
            <article className="lc-readiness-panel lc-readiness-focus">
                <PanelTitle icon={<Icon>!</Icon>} title="What needs attention" />
                {topBlocker && (
                    <TaskRisk task={topBlocker} />
                )}
                {!topBlocker && topMilestone && (
                    <SignalRow
                        title={topMilestone.lc_name ?? "Unnamed milestone"}
                        status={formatted(topMilestone, "lc_milestonestatus")}
                        detail={topMilestone.lc_duedate
                            ? `Due ${formatDate(topMilestone.lc_duedate)}`
                            : "Milestone needs review"}
                    />
                )}
                {!topBlocker && !topMilestone && (
                    <EmptySignal text="No critical blockers or milestone risks." />
                )}
                {latestStatus && (
                    <div className="lc-readiness-status-summary">
                        <Badge appearance="filled" color={badgeColor(health)}>
                            {health}
                        </Badge>
                        <p>{latestStatus.lc_summary ?? "No status narrative was provided."}</p>
                    </div>
                )}
            </article>
        </>
    );
};

const RisksView: React.FC<{ data: DashboardData }> = ({ data }) => (
    <div className="lc-readiness-tab-content">
        <article className="lc-readiness-panel">
            <PanelTitle icon={<Icon tone="danger">!</Icon>} title="Priority risks" />
            <div className="lc-readiness-list">
                {data.blockedTasks.slice(0, 3).map((task) => (
                    <TaskRisk key={task.lc_taskid} task={task} />
                ))}
                {data.overdueTasks.slice(0, 3).map((task) => (
                    <SignalRow
                        key={task.lc_taskid}
                        title={task.lc_title ?? "Unnamed task"}
                        status="Overdue"
                        detail={task.lc_duedate ? `Due ${formatDate(task.lc_duedate)}` : "Past due"}
                    />
                ))}
                {!data.blockedTasks.length && !data.overdueTasks.length && (
                    <EmptySignal text="No active blockers or overdue tasks." />
                )}
            </div>
            <div className="lc-readiness-risk-summary">
                <strong>Launch risk summary</strong>
                <p>{data.launch.lc_risksummary ?? "No launch-level risk summary is available."}</p>
            </div>
        </article>
    </div>
);

const QualityView: React.FC<{
    data: DashboardData;
    gateStatus: string;
    hasAgentVerdict: boolean;
    officialScore?: number;
}> = ({ data, gateStatus, hasAgentVerdict, officialScore }) => (
    <div className="lc-readiness-tab-content">
        {hasAgentVerdict && officialScore !== undefined && officialScore !== null ? (
            <>
                <div className="lc-readiness-quality-hero">
                    <div className={`lc-readiness-quality-score ${scoreClass(officialScore)}`}>
                        {officialScore}
                    </div>
                    <div>
                        <Badge appearance="filled" color={badgeColor(gateStatus)}>
                            {gateStatus}
                        </Badge>
                        <p>
                            {data.launch.lc_qualitygatefeedback
                                ?? "The agent completed its review without narrative feedback."}
                        </p>
                        {data.launch.lc_qualitygatecheckedon && (
                            <small>
                                Checked {formatDateTime(data.launch.lc_qualitygatecheckedon)}
                            </small>
                        )}
                    </div>
                </div>
                <div className="lc-readiness-quality-evidence">
                    <span>{data.milestones.length} milestones reviewed</span>
                    <span>{data.tasks.length} tasks reviewed</span>
                    <span>{data.statusUpdates.length} status updates reviewed</span>
                </div>
            </>
        ) : (
            <div className="lc-readiness-quality-pending">
                <Icon>AI</Icon>
                <div>
                    <strong>Awaiting Quality Gate review</strong>
                    <p>
                        No agent verdict or score is available yet. Advance the
                        launch to Quality Gate to trigger the assigned review.
                    </p>
                </div>
            </div>
        )}
    </div>
);

const Kpi: React.FC<{
    detail: string;
    label: string;
    tone: "danger" | "neutral" | "success" | "warning";
    value: number | string;
}> = ({ detail, label, tone, value }) => (
    <div className={`lc-readiness-kpi lc-tone-${tone}`}>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
    </div>
);

const PanelTitle: React.FC<{ icon: React.ReactElement; title: string }> = ({
    icon,
    title,
}) => (
    <h3 className="lc-readiness-panel-title">
        {icon}
        {title}
    </h3>
);

const SignalRow: React.FC<{
    detail: string;
    status: string;
    title: string;
}> = ({ detail, status, title }) => (
    <div className="lc-readiness-row">
        <div>
            <strong>{title}</strong>
            <small>{detail}</small>
        </div>
        <Badge appearance="tint" color={badgeColor(status)}>{status}</Badge>
    </div>
);

const TaskRisk: React.FC<{ task: TaskRecord }> = ({ task }) => (
    <div className="lc-readiness-risk">
        <Icon tone="danger">!</Icon>
        <div>
            <strong>{task.lc_title ?? "Unnamed task"}</strong>
            <small>{task.lc_blockerreason ?? "Active blocker flagged"}</small>
        </div>
    </div>
);

const EmptySignal: React.FC<{ text: string }> = ({ text }) => (
    <div className="lc-readiness-empty">
        <Icon tone="success">OK</Icon>
        {text}
    </div>
);

const Icon: React.FC<{
    children: React.ReactNode;
    tone?: "danger" | "success";
}> = ({ children, tone }) => (
    <span className={`lc-readiness-icon${tone ? ` lc-icon-${tone}` : ""}`}>
        {children}
    </span>
);

function badgeColor(value: string): BadgeColor {
    switch (value.toLowerCase().replace(/\s/g, "")) {
        case "passed":
        case "done":
        case "green":
        case "ontrack":
            return "success";
        case "failed":
        case "blocked":
        case "red":
        case "error":
            return "danger";
        case "needsreview":
        case "atrisk":
        case "yellow":
        case "delayed":
            return "warning";
        case "pending":
        case "planned":
            return "informative";
        default:
            return "subtle";
    }
}

function scoreClass(score: number): string {
    return score >= 85 ? "lc-score-good" : score >= 60 ? "lc-score-warning" : "lc-score-danger";
}

function formatDate(value: string): string {
    return new Intl.DateTimeFormat(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
    }).format(new Date(value));
}

function formatDateTime(value: string): string {
    return new Intl.DateTimeFormat(undefined, {
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        month: "short",
    }).format(new Date(value));
}
