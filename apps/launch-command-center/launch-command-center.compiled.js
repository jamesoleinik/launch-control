var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
import React, { useEffect, useMemo, useState } from "react";
import { makeStyles, shorthands, tokens, Card, CardHeader, Text, Badge, Spinner, Divider, Title2, Title3, Subtitle2, Body1, Caption1, Tag, } from "@fluentui/react-components";
import { CheckmarkCircleFilled, WarningFilled, ErrorCircleFilled, ClockFilled, PersonRegular, CalendarLtrRegular, FlagRegular, BotRegular, } from "@fluentui/react-icons";
var useStyles = makeStyles({
    root: __assign(__assign({ display: "grid", gridTemplateColumns: "1fr 320px", gridTemplateRows: "auto auto 1fr", gridTemplateAreas: "\n      \"header header\"\n      \"timeline rail\"\n      \"kanban rail\"\n    ", height: "100%", minHeight: "100vh", columnGap: tokens.spacingHorizontalL, rowGap: tokens.spacingVerticalL }, shorthands.padding(tokens.spacingVerticalL, tokens.spacingHorizontalXL)), { backgroundColor: tokens.colorNeutralBackground2, boxSizing: "border-box" }),
    header: __assign(__assign(__assign(__assign({ gridArea: "header", display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "space-between" }, shorthands.padding(tokens.spacingVerticalL, tokens.spacingHorizontalXL)), { backgroundColor: tokens.colorNeutralBackground1 }), shorthands.borderRadius(tokens.borderRadiusLarge)), { boxShadow: tokens.shadow4 }),
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
    timelineCard: __assign(__assign(__assign(__assign({ gridArea: "timeline" }, shorthands.padding(tokens.spacingVerticalL)), { backgroundColor: tokens.colorNeutralBackground1 }), shorthands.borderRadius(tokens.borderRadiusLarge)), { boxShadow: tokens.shadow4 }),
    timeline: {
        display: "flex",
        flexDirection: "row",
        columnGap: tokens.spacingHorizontalM,
        overflowX: "auto",
        paddingBottom: tokens.spacingVerticalS,
    },
    milestoneCard: __assign(__assign(__assign(__assign({ minWidth: "200px" }, shorthands.padding(tokens.spacingVerticalM, tokens.spacingHorizontalM)), shorthands.borderRadius(tokens.borderRadiusMedium)), shorthands.borderLeft("4px", "solid", tokens.colorNeutralStroke1)), { backgroundColor: tokens.colorNeutralBackground2, display: "flex", flexDirection: "column", rowGap: tokens.spacingVerticalXS }),
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
    column: __assign(__assign(__assign({ display: "flex", flexDirection: "column", rowGap: tokens.spacingVerticalS }, shorthands.padding(tokens.spacingVerticalM)), shorthands.borderRadius(tokens.borderRadiusLarge)), { backgroundColor: tokens.colorNeutralBackground1, boxShadow: tokens.shadow2, overflowY: "auto", maxHeight: "calc(100vh - 360px)" }),
    columnHeader: {
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        paddingBottom: tokens.spacingVerticalS,
    },
    taskCard: __assign(__assign(__assign(__assign({}, shorthands.padding(tokens.spacingVerticalS, tokens.spacingHorizontalM)), shorthands.borderRadius(tokens.borderRadiusMedium)), { backgroundColor: tokens.colorNeutralBackground3, display: "flex", flexDirection: "column", rowGap: tokens.spacingVerticalXS }), shorthands.border("1px", "solid", tokens.colorNeutralStroke2)),
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
    blockerBanner: __assign(__assign(__assign({}, shorthands.padding(tokens.spacingVerticalXS, tokens.spacingHorizontalS)), shorthands.borderRadius(tokens.borderRadiusSmall)), { backgroundColor: tokens.colorPaletteRedBackground2, color: tokens.colorPaletteRedForeground1, display: "flex", columnGap: tokens.spacingHorizontalXS, alignItems: "flex-start" }),
    rail: __assign(__assign(__assign(__assign({ gridArea: "rail", display: "flex", flexDirection: "column", rowGap: tokens.spacingVerticalM }, shorthands.padding(tokens.spacingVerticalL)), { backgroundColor: tokens.colorNeutralBackground1 }), shorthands.borderRadius(tokens.borderRadiusLarge)), { boxShadow: tokens.shadow4, overflowY: "auto", maxHeight: "calc(100vh - 100px)" }),
    update: __assign({ display: "flex", flexDirection: "column", rowGap: tokens.spacingVerticalXXS, paddingBottom: tokens.spacingVerticalS }, shorthands.borderBottom("1px", "solid", tokens.colorNeutralStroke2)),
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
var MILESTONE_STATUS = {
    10600010: "NotStarted",
    10600011: "InProgress",
    10600012: "Complete",
    10600013: "AtRisk",
    10600014: "Blocked",
};
var TASK_STATUS = {
    10600020: "NotStarted",
    10600021: "InProgress",
    10600022: "Done",
    10600023: "Blocked",
};
var KANBAN_ORDER = [
    { key: "NotStarted", label: "Not Started", statusCode: 10600020 },
    { key: "InProgress", label: "In Progress", statusCode: 10600021 },
    { key: "Blocked", label: "Blocked", statusCode: 10600023 },
    { key: "Done", label: "Done", statusCode: 10600022 },
];
var formatDate = function (iso) {
    if (!iso)
        return "";
    var d = new Date(iso);
    if (isNaN(d.getTime()))
        return "";
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};
var App = function (_a) {
    var dataApi = _a.dataApi;
    var styles = useStyles();
    var _b = useState(true), loading = _b[0], setLoading = _b[1];
    var _c = useState(null), launch = _c[0], setLaunch = _c[1];
    var _d = useState([]), milestones = _d[0], setMilestones = _d[1];
    var _e = useState([]), tasks = _e[0], setTasks = _e[1];
    var _f = useState([]), updates = _f[0], setUpdates = _f[1];
    var _g = useState(null), error = _g[0], setError = _g[1];
    useEffect(function () {
        var cancelled = false;
        (function () { return __awaiter(void 0, void 0, void 0, function () {
            var launchResult, launches, q3, launchId, _a, msRes, tkRes, upRes, allTasks, msIds_1, e_1;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _b.trys.push([0, 3, 4, 5]);
                        setLoading(true);
                        return [4 /*yield*/, dataApi.queryTable("lc_launch", {
                                select: ["lc_launchid", "lc_name", "lc_description", "lc_launchstatus", "lc_targetdate"],
                                filter: "statecode eq 0",
                                orderBy: "createdon desc",
                                pageSize: 50,
                            })];
                    case 1:
                        launchResult = _b.sent();
                        launches = launchResult.rows;
                        q3 = launches.find(function (r) { return (r.lc_name || "").toLowerCase().includes("q3 widget"); }) ||
                            launches[0];
                        if (!q3) {
                            if (!cancelled) {
                                setError("No active launches found.");
                                setLoading(false);
                            }
                            return [2 /*return*/];
                        }
                        launchId = q3.lc_launchid;
                        return [4 /*yield*/, Promise.all([
                                dataApi.queryTable("lc_milestone", {
                                    select: [
                                        "lc_milestoneid",
                                        "lc_name",
                                        "lc_milestonestatus",
                                        "lc_duedate",
                                        "lc_sortorder",
                                        "_lc_launchid_value",
                                    ],
                                    filter: "_lc_launchid_value eq ".concat(launchId, " and statecode eq 0"),
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
                                    filter: "statecode eq 0",
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
                                    filter: "_lc_launchid_value eq ".concat(launchId, " and statecode eq 0"),
                                    orderBy: "lc_updatedon desc",
                                    pageSize: 30,
                                }),
                            ])];
                    case 2:
                        _a = _b.sent(), msRes = _a[0], tkRes = _a[1], upRes = _a[2];
                        if (cancelled)
                            return [2 /*return*/];
                        setLaunch(q3);
                        setMilestones(msRes.rows);
                        allTasks = tkRes.rows;
                        msIds_1 = new Set(msRes.rows.map(function (m) { return m.lc_milestoneid; }));
                        setTasks(allTasks.filter(function (t) {
                            var raw = t._lc_milestoneid_value;
                            if (!raw)
                                return false;
                            var id = raw.replace(/[{}]/g, "").toLowerCase();
                            return Array.from(msIds_1).some(function (m) { return m.toLowerCase() === id; });
                        }));
                        setUpdates(upRes.rows);
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _b.sent();
                        if (!cancelled)
                            setError((e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || String(e_1));
                        return [3 /*break*/, 5];
                    case 4:
                        if (!cancelled)
                            setLoading(false);
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        }); })();
        return function () {
            cancelled = true;
        };
    }, [dataApi]);
    var kpis = useMemo(function () {
        var total = milestones.length;
        var counts = { complete: 0, inprogress: 0, atrisk: 0, blocked: 0, notstarted: 0 };
        milestones.forEach(function (m) {
            var key = MILESTONE_STATUS[m.lc_milestonestatus];
            if (key === "Complete")
                counts.complete++;
            else if (key === "InProgress")
                counts.inprogress++;
            else if (key === "AtRisk")
                counts.atrisk++;
            else if (key === "Blocked")
                counts.blocked++;
            else
                counts.notstarted++;
        });
        var score = total === 0
            ? 0
            : Math.round(((counts.complete + counts.inprogress * 0.5) / total) * 100);
        var verdict = "GO";
        if (counts.blocked > 0)
            verdict = "NO-GO";
        else if (counts.atrisk > 0)
            verdict = "AT-RISK";
        var openTasks = tasks.filter(function (t) { return TASK_STATUS[t.lc_taskstatus] !== "Done"; }).length;
        var blockedTasks = tasks.filter(function (t) { return TASK_STATUS[t.lc_taskstatus] === "Blocked"; }).length;
        return { total: total, counts: counts, score: score, verdict: verdict, openTasks: openTasks, blockedTasks: blockedTasks };
    }, [milestones, tasks]);
    if (loading) {
        return (React.createElement("div", { className: styles.loading },
            React.createElement(Spinner, { size: "large", label: "Loading Launch Command Center..." })));
    }
    if (error || !launch) {
        return (React.createElement("div", { className: styles.loading },
            React.createElement(ErrorCircleFilled, { fontSize: 48, primaryFill: tokens.colorPaletteRedForeground1 }),
            React.createElement(Title3, null, "Unable to load launch data"),
            React.createElement(Body1, null, error || "No launch found.")));
    }
    var verdictColor = kpis.verdict === "GO"
        ? tokens.colorPaletteGreenForeground1
        : kpis.verdict === "AT-RISK"
            ? tokens.colorPaletteYellowForeground1
            : tokens.colorPaletteRedForeground1;
    var verdictIcon = kpis.verdict === "GO" ? (React.createElement(CheckmarkCircleFilled, { fontSize: 36, primaryFill: verdictColor })) : kpis.verdict === "AT-RISK" ? (React.createElement(WarningFilled, { fontSize: 36, primaryFill: verdictColor })) : (React.createElement(ErrorCircleFilled, { fontSize: 36, primaryFill: verdictColor }));
    return (React.createElement("div", { className: styles.root },
        React.createElement("div", { className: styles.header },
            React.createElement("div", { className: styles.headerLeft },
                React.createElement(Caption1, null, "LAUNCH COMMAND CENTER"),
                React.createElement(Title2, null, launch.lc_name),
                React.createElement(Body1, null,
                    "Target",
                    " ",
                    launch["lc_targetdate@OData.Community.Display.V1.FormattedValue"] ||
                        formatDate(launch.lc_targetdate),
                    " · ",
                    launch["lc_launchstatus@OData.Community.Display.V1.FormattedValue"] || ""),
                React.createElement("div", { className: styles.kpiStrip },
                    React.createElement("div", { className: styles.kpi },
                        React.createElement(Caption1, null, "Milestones"),
                        React.createElement(Text, { className: styles.kpiValue },
                            kpis.counts.complete,
                            "/",
                            kpis.total)),
                    React.createElement("div", { className: styles.kpi },
                        React.createElement(Caption1, null, "Open Tasks"),
                        React.createElement(Text, { className: styles.kpiValue }, kpis.openTasks)),
                    React.createElement("div", { className: styles.kpi },
                        React.createElement(Caption1, null, "Blocked"),
                        React.createElement(Text, { className: styles.kpiValue, style: {
                                color: kpis.blockedTasks > 0
                                    ? tokens.colorPaletteRedForeground1
                                    : tokens.colorNeutralForeground1,
                            } }, kpis.blockedTasks)),
                    React.createElement("div", { className: styles.kpi },
                        React.createElement(Caption1, null, "Score"),
                        React.createElement(Text, { className: styles.kpiValue }, kpis.score)))),
            React.createElement("div", { className: styles.headerRight },
                React.createElement("div", { className: styles.verdictPill },
                    React.createElement(Caption1, null, "READINESS VERDICT"),
                    React.createElement("div", { style: { display: "flex", alignItems: "center", columnGap: 8 } },
                        verdictIcon,
                        React.createElement(Title2, { style: { color: verdictColor } }, kpis.verdict))))),
        React.createElement(Card, { className: styles.timelineCard },
            React.createElement(CardHeader, { header: React.createElement(Subtitle2, null, "Milestones") }),
            React.createElement("div", { className: styles.timeline },
                milestones.length === 0 && React.createElement(Body1, null, "No milestones yet."),
                milestones.map(function (m) {
                    var key = MILESTONE_STATUS[m.lc_milestonestatus] || "NotStarted";
                    var classMap = {
                        Complete: styles.msComplete,
                        InProgress: styles.msInProgress,
                        AtRisk: styles.msAtRisk,
                        Blocked: styles.msBlocked,
                        NotStarted: styles.msNotStarted,
                    };
                    var labelMap = {
                        Complete: "success",
                        InProgress: "informative",
                        AtRisk: "warning",
                        Blocked: "danger",
                        NotStarted: "subtle",
                    };
                    return (React.createElement("div", { key: m.lc_milestoneid, className: "".concat(styles.milestoneCard, " ").concat(classMap[key]) },
                        React.createElement(Text, { weight: "semibold" }, m.lc_name),
                        React.createElement("div", { style: { display: "flex", columnGap: 6, alignItems: "center" } },
                            React.createElement(CalendarLtrRegular, null),
                            React.createElement(Caption1, null, m["lc_duedate@OData.Community.Display.V1.FormattedValue"] ||
                                formatDate(m.lc_duedate))),
                        React.createElement(Badge, { appearance: "tint", color: labelMap[key] }, m["lc_milestonestatus@OData.Community.Display.V1.FormattedValue"] || key)));
                }))),
        React.createElement("div", { className: styles.kanbanWrap }, KANBAN_ORDER.map(function (col) {
            var colTasks = tasks.filter(function (t) { return t.lc_taskstatus === col.statusCode; });
            return (React.createElement("div", { key: col.key, className: styles.column },
                React.createElement("div", { className: styles.columnHeader },
                    React.createElement(Subtitle2, null, col.label),
                    React.createElement(Badge, { appearance: "tint" }, colTasks.length)),
                colTasks.length === 0 && React.createElement(Caption1, null, "\u2014"),
                colTasks.map(function (t) {
                    var blocked = TASK_STATUS[t.lc_taskstatus] === "Blocked";
                    return (React.createElement("div", { key: t.lc_taskid, className: styles.taskCard },
                        React.createElement(Text, { weight: "semibold" }, t.lc_title),
                        React.createElement("div", { className: styles.taskMeta },
                            t.lc_milestoneidname && (React.createElement(Tag, { size: "extra-small", icon: React.createElement(FlagRegular, null) }, t.lc_milestoneidname)),
                            t.lc_assignedtoidname && (React.createElement("span", { className: styles.metaChip },
                                React.createElement(PersonRegular, null),
                                React.createElement(Caption1, null, t.lc_assignedtoidname))),
                            t.lc_duedate && (React.createElement("span", { className: styles.metaChip },
                                React.createElement(CalendarLtrRegular, null),
                                React.createElement(Caption1, null, t["lc_duedate@OData.Community.Display.V1.FormattedValue"] ||
                                    formatDate(t.lc_duedate))))),
                        blocked && t.lc_blockerreason && (React.createElement("div", { className: styles.blockerBanner },
                            React.createElement(ErrorCircleFilled, null),
                            React.createElement(Caption1, null, t.lc_blockerreason)))));
                })));
        })),
        React.createElement("div", { className: styles.rail },
            React.createElement("div", { style: { display: "flex", alignItems: "center", columnGap: 8 } },
                React.createElement(BotRegular, null),
                React.createElement(Subtitle2, null, "Agent Activity")),
            React.createElement(Divider, null),
            updates.length === 0 && React.createElement(Body1, null, "No status updates yet."),
            updates.map(function (u) { return (React.createElement("div", { key: u.lc_statusupdateid, className: styles.update },
                React.createElement("div", { className: styles.updateHead },
                    React.createElement(ClockFilled, { primaryFill: tokens.colorBrandForeground1 }),
                    React.createElement(Caption1, null, u["lc_updatedon@OData.Community.Display.V1.FormattedValue"] ||
                        formatDate(u.lc_updatedon))),
                React.createElement(Text, { weight: "semibold" }, u.lc_title),
                React.createElement(Body1, null, u.lc_body))); }))));
};
export default App;
