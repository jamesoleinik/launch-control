import React, { useEffect, useMemo, useState } from "react";
import {
  makeStyles,
  shorthands,
  tokens,
  Card,
  CardHeader,
  Text,
  Badge,
  Spinner,
  Divider,
  Title2,
  Title3,
  Subtitle2,
  Body1,
  Caption1,
  Tag,
} from "@fluentui/react-components";
import {
  CheckmarkCircleFilled,
  WarningFilled,
  ErrorCircleFilled,
  ClockFilled,
  CircleRegular,
  PersonRegular,
  CalendarLtrRegular,
  FlagRegular,
  BotRegular,
} from "@fluentui/react-icons";
import type { GeneratedComponentProps } from "./RuntimeTypes";

const useStyles = makeStyles({
  root: {
    display: "grid",
    gridTemplateColumns: "1fr 320px",
    gridTemplateRows: "auto auto 1fr",
    gridTemplateAreas: `
      "header header"
      "timeline rail"
      "kanban rail"
    `,
    height: "100%",
    minHeight: "100vh",
    columnGap: tokens.spacingHorizontalL,
    rowGap: tokens.spacingVerticalL,
    ...shorthands.padding(tokens.spacingVerticalL, tokens.spacingHorizontalXL),
    backgroundColor: tokens.colorNeutralBackground2,
    boxSizing: "border-box",
  },
  header: {
    gridArea: "header",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    ...shorthands.padding(tokens.spacingVerticalL, tokens.spacingHorizontalXL),
    backgroundColor: tokens.colorNeutralBackground1,
    ...shorthands.borderRadius(tokens.borderRadiusLarge),
    boxShadow: tokens.shadow4,
  },
  headerLeft: { display: "flex", flexDirection: "column", rowGap: tokens.spacingVerticalXS },
  headerRight: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    columnGap: tokens.spacingHorizontalL,
  },
  verdictPill: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
    rowGap: tokens.spacingVerticalXS,
  },
  kpiStrip: {
    display: "flex",
    flexDirection: "row",
    columnGap: tokens.spacingHorizontalXL,
  },
  kpi: { display: "flex", flexDirection: "column", alignItems: "flex-start" },
  kpiValue: { fontSize: tokens.fontSizeBase600, fontWeight: tokens.fontWeightSemibold },
  timelineCard: {
    gridArea: "timeline",
    ...shorthands.padding(tokens.spacingVerticalL),
    backgroundColor: tokens.colorNeutralBackground1,
    ...shorthands.borderRadius(tokens.borderRadiusLarge),
    boxShadow: tokens.shadow4,
  },
  timeline: {
    display: "flex",
    flexDirection: "row",
    columnGap: tokens.spacingHorizontalM,
    overflowX: "auto",
    paddingBottom: tokens.spacingVerticalS,
  },
  milestoneCard: {
    minWidth: "200px",
    ...shorthands.padding(tokens.spacingVerticalM, tokens.spacingHorizontalM),
    ...shorthands.borderRadius(tokens.borderRadiusMedium),
    ...shorthands.borderLeft("4px", "solid", tokens.colorNeutralStroke1),
    backgroundColor: tokens.colorNeutralBackground2,
    display: "flex",
    flexDirection: "column",
    rowGap: tokens.spacingVerticalXS,
  },
  msComplete: { borderLeftColor: tokens.colorPaletteGreenForeground1 },
  msInProgress: { borderLeftColor: tokens.colorBrandForeground1 },
  msAtRisk: { borderLeftColor: tokens.colorPaletteYellowForeground1 },
  msBlocked: { borderLeftColor: tokens.colorPaletteRedForeground1 },
  msNotStarted: { borderLeftColor: tokens.colorNeutralStroke1 },
  kanbanWrap: {
    gridArea: "kanban",
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    columnGap: tokens.spacingHorizontalM,
    minHeight: "400px",
  },
  column: {
    display: "flex",
    flexDirection: "column",
    rowGap: tokens.spacingVerticalS,
    ...shorthands.padding(tokens.spacingVerticalM),
    ...shorthands.borderRadius(tokens.borderRadiusLarge),
    backgroundColor: tokens.colorNeutralBackground1,
    boxShadow: tokens.shadow2,
    overflowY: "auto",
    maxHeight: "calc(100vh - 360px)",
  },
  columnHeader: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingBottom: tokens.spacingVerticalS,
  },
  taskCard: {
    ...shorthands.padding(tokens.spacingVerticalS, tokens.spacingHorizontalM),
    ...shorthands.borderRadius(tokens.borderRadiusMedium),
    backgroundColor: tokens.colorNeutralBackground3,
    display: "flex",
    flexDirection: "column",
    rowGap: tokens.spacingVerticalXS,
    ...shorthands.border("1px", "solid", tokens.colorNeutralStroke2),
  },
  taskMeta: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    columnGap: tokens.spacingHorizontalS,
    flexWrap: "wrap",
  },
  metaChip: {
    display: "inline-flex",
    flexDirection: "row",
    alignItems: "center",
    columnGap: tokens.spacingHorizontalXS,
    color: tokens.colorNeutralForeground3,
  },
  blockerBanner: {
    ...shorthands.padding(tokens.spacingVerticalXS, tokens.spacingHorizontalS),
    ...shorthands.borderRadius(tokens.borderRadiusSmall),
    backgroundColor: tokens.colorPaletteRedBackground2,
    color: tokens.colorPaletteRedForeground1,
    display: "flex",
    columnGap: tokens.spacingHorizontalXS,
    alignItems: "flex-start",
  },
  rail: {
    gridArea: "rail",
    display: "flex",
    flexDirection: "column",
    rowGap: tokens.spacingVerticalM,
    ...shorthands.padding(tokens.spacingVerticalL),
    backgroundColor: tokens.colorNeutralBackground1,
    ...shorthands.borderRadius(tokens.borderRadiusLarge),
    boxShadow: tokens.shadow4,
    overflowY: "auto",
    maxHeight: "calc(100vh - 100px)",
  },
  update: {
    display: "flex",
    flexDirection: "column",
    rowGap: tokens.spacingVerticalXXS,
    paddingBottom: tokens.spacingVerticalS,
    ...shorthands.borderBottom("1px", "solid", tokens.colorNeutralStroke2),
  },
  updateHead: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    columnGap: tokens.spacingHorizontalXS,
  },
  loading: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "60vh",
    rowGap: tokens.spacingVerticalM,
  },
});

type AnyRow = Record<string, any>;
type Verdict = "GO" | "NO-GO" | "AT-RISK";

const MILESTONE_STATUS: Record<number, string> = {
  10600010: "NotStarted",
  10600011: "InProgress",
  10600012: "Complete",
  10600013: "AtRisk",
  10600014: "Blocked",
};
const TASK_STATUS: Record<number, string> = {
  10600020: "NotStarted",
  10600021: "InProgress",
  10600022: "Done",
  10600023: "Blocked",
};
const KANBAN_ORDER: Array<{ key: string; label: string; statusCode: number }> = [
  { key: "NotStarted", label: "Not Started", statusCode: 10600020 },
  { key: "InProgress", label: "In Progress", statusCode: 10600021 },
  { key: "Blocked", label: "Blocked", statusCode: 10600023 },
  { key: "Done", label: "Done", statusCode: 10600022 },
];

const formatDate = (iso: string | undefined): string => {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

const App: React.FC<GeneratedComponentProps> = ({ dataApi }) => {
  const styles = useStyles();
  const [loading, setLoading] = useState(true);
  const [launch, setLaunch] = useState<AnyRow | null>(null);
  const [milestones, setMilestones] = useState<AnyRow[]>([]);
  const [tasks, setTasks] = useState<AnyRow[]>([]);
  const [updates, setUpdates] = useState<AnyRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const launchResult = await dataApi.queryTable("lc_launch", {
          select: ["lc_launchid", "lc_name", "lc_description", "lc_launchstatus", "lc_targetdate"],
          filter: "statecode eq 0",
          orderBy: "createdon desc",
          pageSize: 50,
        });
        const launches = (launchResult as any).rows as AnyRow[];
        const q3 =
          launches.find((r) => (r.lc_name || "").toLowerCase().includes("q3 widget")) ||
          launches[0];
        if (!q3) {
          if (!cancelled) {
            setError("No active launches found.");
            setLoading(false);
          }
          return;
        }
        const launchId = q3.lc_launchid as string;

        const [msRes, tkRes, upRes] = await Promise.all([
          dataApi.queryTable("lc_milestone", {
            select: [
              "lc_milestoneid",
              "lc_name",
              "lc_milestonestatus",
              "lc_duedate",
              "lc_sortorder",
              "_lc_launchid_value",
            ],
            filter: `_lc_launchid_value eq ${launchId} and statecode eq 0`,
            orderBy: "lc_sortorder asc",
            pageSize: 200,
          }),
          dataApi.queryTable("lc_task", {
            select: [
              "lc_taskid",
              "lc_title",
              "lc_description",
              "lc_taskstatus",
              "lc_isblocked",
              "lc_blockerreason",
              "lc_duedate",
              "_lc_milestoneid_value",
              "_lc_assignedtoid_value",
            ],
            filter: `statecode eq 0`,
            orderBy: "lc_duedate asc",
            pageSize: 500,
          }),
          dataApi.queryTable("lc_statusupdate", {
            select: [
              "lc_statusupdateid",
              "lc_title",
              "lc_body",
              "lc_updatedon",
              "_lc_launchid_value",
            ],
            filter: `_lc_launchid_value eq ${launchId} and statecode eq 0`,
            orderBy: "lc_updatedon desc",
            pageSize: 30,
          }),
        ]);

        if (cancelled) return;
        setLaunch(q3);
        setMilestones((msRes as any).rows as AnyRow[]);
        const allTasks = (tkRes as any).rows as AnyRow[];
        const msIds = new Set(((msRes as any).rows as AnyRow[]).map((m) => m.lc_milestoneid));
        setTasks(
          allTasks.filter((t) => {
            const raw = t._lc_milestoneid_value as string | undefined;
            if (!raw) return false;
            const id = raw.replace(/[{}]/g, "").toLowerCase();
            return Array.from(msIds).some((m) => (m as string).toLowerCase() === id);
          })
        );
        setUpdates((upRes as any).rows as AnyRow[]);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [dataApi]);

  const kpis = useMemo(() => {
    const total = milestones.length;
    const counts = { complete: 0, inprogress: 0, atrisk: 0, blocked: 0, notstarted: 0 };
    milestones.forEach((m) => {
      const key = MILESTONE_STATUS[m.lc_milestonestatus as number];
      if (key === "Complete") counts.complete++;
      else if (key === "InProgress") counts.inprogress++;
      else if (key === "AtRisk") counts.atrisk++;
      else if (key === "Blocked") counts.blocked++;
      else counts.notstarted++;
    });
    const score =
      total === 0
        ? 0
        : Math.round(((counts.complete + counts.inprogress * 0.5) / total) * 100);
    let verdict: Verdict = "GO";
    if (counts.blocked > 0) verdict = "NO-GO";
    else if (counts.atrisk > 0) verdict = "AT-RISK";
    const openTasks = tasks.filter((t) => TASK_STATUS[t.lc_taskstatus as number] !== "Done").length;
    const blockedTasks = tasks.filter(
      (t) => TASK_STATUS[t.lc_taskstatus as number] === "Blocked"
    ).length;
    return { total, counts, score, verdict, openTasks, blockedTasks };
  }, [milestones, tasks]);

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spinner size="large" label="Loading Launch Command Center..." />
      </div>
    );
  }

  if (error || !launch) {
    return (
      <div className={styles.loading}>
        <ErrorCircleFilled fontSize={48} primaryFill={tokens.colorPaletteRedForeground1} />
        <Title3>Unable to load launch data</Title3>
        <Body1>{error || "No launch found."}</Body1>
      </div>
    );
  }

  const verdictColor =
    kpis.verdict === "GO"
      ? tokens.colorPaletteGreenForeground1
      : kpis.verdict === "AT-RISK"
        ? tokens.colorPaletteYellowForeground1
        : tokens.colorPaletteRedForeground1;
  const verdictIcon =
    kpis.verdict === "GO" ? (
      <CheckmarkCircleFilled fontSize={36} primaryFill={verdictColor} />
    ) : kpis.verdict === "AT-RISK" ? (
      <WarningFilled fontSize={36} primaryFill={verdictColor} />
    ) : (
      <ErrorCircleFilled fontSize={36} primaryFill={verdictColor} />
    );

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Caption1>LAUNCH COMMAND CENTER</Caption1>
          <Title2>{launch.lc_name}</Title2>
          <Body1>
            Target{" "}
            {launch["lc_targetdate@OData.Community.Display.V1.FormattedValue"] ||
              formatDate(launch.lc_targetdate)}
            {" · "}
            {launch["lc_launchstatus@OData.Community.Display.V1.FormattedValue"] || ""}
          </Body1>
          <div className={styles.kpiStrip}>
            <div className={styles.kpi}>
              <Caption1>Milestones</Caption1>
              <Text className={styles.kpiValue}>
                {kpis.counts.complete}/{kpis.total}
              </Text>
            </div>
            <div className={styles.kpi}>
              <Caption1>Open Tasks</Caption1>
              <Text className={styles.kpiValue}>{kpis.openTasks}</Text>
            </div>
            <div className={styles.kpi}>
              <Caption1>Blocked</Caption1>
              <Text
                className={styles.kpiValue}
                style={{
                  color:
                    kpis.blockedTasks > 0
                      ? tokens.colorPaletteRedForeground1
                      : tokens.colorNeutralForeground1,
                }}
              >
                {kpis.blockedTasks}
              </Text>
            </div>
            <div className={styles.kpi}>
              <Caption1>Score</Caption1>
              <Text className={styles.kpiValue}>{kpis.score}</Text>
            </div>
          </div>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.verdictPill}>
            <Caption1>READINESS VERDICT</Caption1>
            <div style={{ display: "flex", alignItems: "center", columnGap: 8 }}>
              {verdictIcon}
              <Title2 style={{ color: verdictColor }}>{kpis.verdict}</Title2>
            </div>
          </div>
        </div>
      </div>

      <Card className={styles.timelineCard}>
        <CardHeader header={<Subtitle2>Milestones</Subtitle2>} />
        <div className={styles.timeline}>
          {milestones.length === 0 && <Body1>No milestones yet.</Body1>}
          {milestones.map((m) => {
            const key = MILESTONE_STATUS[m.lc_milestonestatus as number] || "NotStarted";
            const classMap: Record<string, string> = {
              Complete: styles.msComplete,
              InProgress: styles.msInProgress,
              AtRisk: styles.msAtRisk,
              Blocked: styles.msBlocked,
              NotStarted: styles.msNotStarted,
            };
            const labelMap: Record<string, "success" | "informative" | "warning" | "danger" | "subtle"> = {
              Complete: "success",
              InProgress: "informative",
              AtRisk: "warning",
              Blocked: "danger",
              NotStarted: "subtle",
            };
            return (
              <div key={m.lc_milestoneid} className={`${styles.milestoneCard} ${classMap[key]}`}>
                <Text weight="semibold">{m.lc_name}</Text>
                <div style={{ display: "flex", columnGap: 6, alignItems: "center" }}>
                  <CalendarLtrRegular />
                  <Caption1>
                    {m["lc_duedate@OData.Community.Display.V1.FormattedValue"] ||
                      formatDate(m.lc_duedate)}
                  </Caption1>
                </div>
                <Badge appearance="tint" color={labelMap[key]}>
                  {m["lc_milestonestatus@OData.Community.Display.V1.FormattedValue"] || key}
                </Badge>
              </div>
            );
          })}
        </div>
      </Card>

      <div className={styles.kanbanWrap}>
        {KANBAN_ORDER.map((col) => {
          const colTasks = tasks.filter((t) => t.lc_taskstatus === col.statusCode);
          return (
            <div key={col.key} className={styles.column}>
              <div className={styles.columnHeader}>
                <Subtitle2>{col.label}</Subtitle2>
                <Badge appearance="tint">{colTasks.length}</Badge>
              </div>
              {colTasks.length === 0 && <Caption1>—</Caption1>}
              {colTasks.map((t) => {
                const blocked = TASK_STATUS[t.lc_taskstatus as number] === "Blocked";
                return (
                  <div key={t.lc_taskid} className={styles.taskCard}>
                    <Text weight="semibold">{t.lc_title}</Text>
                    <div className={styles.taskMeta}>
                      {t.lc_milestoneidname && (
                        <Tag size="extra-small" icon={<FlagRegular />}>
                          {t.lc_milestoneidname}
                        </Tag>
                      )}
                      {t.lc_assignedtoidname && (
                        <span className={styles.metaChip}>
                          <PersonRegular />
                          <Caption1>{t.lc_assignedtoidname}</Caption1>
                        </span>
                      )}
                      {t.lc_duedate && (
                        <span className={styles.metaChip}>
                          <CalendarLtrRegular />
                          <Caption1>
                            {t["lc_duedate@OData.Community.Display.V1.FormattedValue"] ||
                              formatDate(t.lc_duedate)}
                          </Caption1>
                        </span>
                      )}
                    </div>
                    {blocked && t.lc_blockerreason && (
                      <div className={styles.blockerBanner}>
                        <ErrorCircleFilled />
                        <Caption1>{t.lc_blockerreason}</Caption1>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      <div className={styles.rail}>
        <div style={{ display: "flex", alignItems: "center", columnGap: 8 }}>
          <BotRegular />
          <Subtitle2>Agent Activity</Subtitle2>
        </div>
        <Divider />
        {updates.length === 0 && <Body1>No status updates yet.</Body1>}
        {updates.map((u) => (
          <div key={u.lc_statusupdateid} className={styles.update}>
            <div className={styles.updateHead}>
              <ClockFilled primaryFill={tokens.colorBrandForeground1} />
              <Caption1>
                {u["lc_updatedon@OData.Community.Display.V1.FormattedValue"] ||
                  formatDate(u.lc_updatedon)}
              </Caption1>
            </div>
            <Text weight="semibold">{u.lc_title}</Text>
            <Body1>{u.lc_body}</Body1>
          </div>
        ))}
      </div>
    </div>
  );
};

export default App;
