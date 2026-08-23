const FORMATTED = "@OData.Community.Display.V1.FormattedValue";

export interface LaunchRecord {
    lc_name?: string;
    lc_launchstatus?: number;
    lc_priority?: number;
    lc_targetdate?: string;
    lc_releasewindow?: string;
    lc_risksummary?: string;
    lc_qualitygatestatus?: number;
    lc_qualitygatescore?: number;
    lc_qualitygatefeedback?: string;
    lc_qualitygatecheckedon?: string;
    [key: string]: unknown;
}

export interface MilestoneRecord {
    lc_milestoneid: string;
    lc_name?: string;
    lc_milestonestatus?: number;
    lc_duedate?: string;
    [key: string]: unknown;
}

export interface TaskRecord {
    lc_taskid: string;
    lc_title?: string;
    lc_taskstatus?: number;
    lc_priority?: number;
    lc_isblocked?: boolean;
    lc_blockerreason?: string;
    lc_duedate?: string;
    [key: string]: unknown;
}

export interface StatusUpdateRecord {
    lc_statusupdateid: string;
    lc_title?: string;
    lc_summary?: string;
    lc_health?: number;
    lc_postedat?: string;
    [key: string]: unknown;
}

export interface DashboardData {
    launch: LaunchRecord;
    milestones: MilestoneRecord[];
    tasks: TaskRecord[];
    statusUpdates: StatusUpdateRecord[];
    blockedTasks: TaskRecord[];
    overdueTasks: TaskRecord[];
    overdueMilestones: MilestoneRecord[];
    milestoneCounts: Record<string, number>;
    liveScore: number;
}

export function formatted(
    row: Record<string, unknown>,
    field: string,
    fallback = "Unknown"
): string {
    const value = row[field + FORMATTED];
    return typeof value === "string" && value ? value : fallback;
}

export async function loadDashboardData(
    webAPI: ComponentFramework.WebApi,
    launchId: string
): Promise<DashboardData> {
    const filter = `_lc_launchid_value eq ${launchId}`;
    const [launch, milestonesResult, tasksResult, updatesResult] = await Promise.all([
        webAPI.retrieveRecord(
            "lc_launch",
            launchId,
            "?$select=lc_name,lc_launchstatus,lc_priority,lc_targetdate,"
            + "lc_releasewindow,lc_risksummary,lc_qualitygatestatus,"
            + "lc_qualitygatescore,lc_qualitygatefeedback,lc_qualitygatecheckedon"
        ),
        webAPI.retrieveMultipleRecords(
            "lc_milestone",
            "?$select=lc_milestoneid,lc_name,lc_milestonestatus,lc_duedate"
            + `&$filter=${filter}&$orderby=lc_duedate asc`
        ),
        webAPI.retrieveMultipleRecords(
            "lc_task",
            "?$select=lc_taskid,lc_title,lc_taskstatus,lc_priority,"
            + "lc_isblocked,lc_blockerreason,lc_duedate"
            + `&$filter=${filter}&$orderby=lc_duedate asc`
        ),
        webAPI.retrieveMultipleRecords(
            "lc_statusupdate",
            "?$select=lc_statusupdateid,lc_title,lc_summary,lc_health,lc_postedat"
            + `&$filter=${filter}&$orderby=lc_postedat desc&$top=5`
        ),
    ]);

    const milestones = milestonesResult.entities as MilestoneRecord[];
    const tasks = tasksResult.entities as TaskRecord[];
    const statusUpdates = updatesResult.entities as StatusUpdateRecord[];
    const now = Date.now();
    const blockedTasks = tasks.filter((task) => task.lc_isblocked === true);
    const overdueTasks = tasks.filter((task) =>
        isOverdue(task.lc_duedate, now)
        && formatted(task, "lc_taskstatus") !== "Done"
    );
    const overdueMilestones = milestones.filter((milestone) =>
        isOverdue(milestone.lc_duedate, now)
        && formatted(milestone, "lc_milestonestatus") !== "Done"
    );
    const milestoneCounts = milestones.reduce<Record<string, number>>(
        (counts, milestone) => {
            const status = formatted(milestone, "lc_milestonestatus");
            counts[status] = (counts[status] ?? 0) + 1;
            return counts;
        },
        {}
    );
    const launchRecord = launch as LaunchRecord;

    return {
        launch: launchRecord,
        milestones,
        tasks,
        statusUpdates,
        blockedTasks,
        overdueTasks,
        overdueMilestones,
        milestoneCounts,
        liveScore: calculateLiveScore(
            launchRecord,
            milestoneCounts,
            blockedTasks.length,
            overdueTasks.length,
            overdueMilestones.length,
            statusUpdates[0]
        ),
    };
}

function isOverdue(value: string | undefined, now: number): boolean {
    if (!value) {
        return false;
    }
    const date = Date.parse(value);
    return !Number.isNaN(date) && date < now;
}

function calculateLiveScore(
    launch: LaunchRecord,
    milestoneCounts: Record<string, number>,
    blockedTasks: number,
    overdueTasks: number,
    overdueMilestones: number,
    latestStatus?: StatusUpdateRecord
): number {
    let penalty = 0;
    const risk = (launch.lc_risksummary ?? "").toLowerCase();
    penalty += risk.startsWith("high") ? 10 : risk.startsWith("medium") ? 5 : 0;
    penalty += (milestoneCounts.Blocked ?? 0) * 12;
    penalty += (milestoneCounts.AtRisk ?? 0) * 7;
    penalty += Math.min(12, overdueMilestones * 4);
    penalty += Math.min(32, blockedTasks * 8);
    penalty += Math.min(12, overdueTasks * 2);
    const health = latestStatus
        ? formatted(latestStatus, "lc_health")
        : "Unknown";
    penalty += health === "Red" ? 20 : health === "Yellow" ? 5 : 0;
    if (!latestStatus) {
        penalty += 5;
    }
    return Math.max(0, 100 - penalty);
}
