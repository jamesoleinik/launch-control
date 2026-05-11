// ---------------- Type Definitions which can be imported from ./RuntimeTypes -------------------------
export interface TableRegistrations extends BaseTableRegistrations {
    "lc_launch": lc_launch,
    "lc_milestone": lc_milestone,
    "lc_statusupdate": lc_statusupdate,
    "lc_task": lc_task,
}
export interface EnumRegistrations extends BaseEnumRegistrations {
    "lc_launch-lc_launchstatus": lc_launch_lc_launchstatus,
    "lc_launch-statecode": lc_launch_statecode,
    "lc_launch-statuscode": lc_launch_statuscode,
    "lc_milestone-lc_milestonestatus": lc_milestone_lc_milestonestatus,
    "lc_milestone-statecode": lc_milestone_statecode,
    "lc_milestone-statuscode": lc_milestone_statuscode,
    "lc_statusupdate-statecode": lc_statusupdate_statecode,
    "lc_statusupdate-statuscode": lc_statusupdate_statuscode,
    "lc_task-lc_isblocked": lc_task_lc_isblocked,
    "lc_task-lc_taskstatus": lc_task_lc_taskstatus,
    "lc_task-statecode": lc_task_statecode,
    "lc_task-statuscode": lc_task_statuscode,
}
export type lc_launch = TableRow<{
    // Primary Key Column
    readonly lc_launchid: string,
    readonly cr88d_risksummary: string,
    readonly cr88d_risksummary_promptcolumndetails: string,
    readonly cr88d_risksummary_promptcolumnstatus: number,
    readonly createdbyname: string,
    readonly createdbyyominame: string,
    readonly createdonbehalfbyname: string,
    readonly createdonbehalfbyyominame: string,
    lc_description: string,
    // Foreign Key Column
    readonly _lc_importrunid_value: `/lc_importrun(${string})`,
    readonly lc_importrunidname: string,
    lc_launchstatus: lc_launch_lc_launchstatus,
    lc_name: string,
    lc_targetdate: Date,
    readonly modifiedbyname: string,
    readonly modifiedbyyominame: string,
    readonly modifiedonbehalfbyname: string,
    readonly modifiedonbehalfbyyominame: string,
    readonly owningbusinessunitname: string,
    statecode: lc_launch_statecode,
    statuscode: lc_launch_statuscode,
}>

export type lc_milestone = TableRow<{
    // Primary Key Column
    readonly lc_milestoneid: string,
    readonly createdbyname: string,
    readonly createdbyyominame: string,
    readonly createdonbehalfbyname: string,
    readonly createdonbehalfbyyominame: string,
    lc_duedate: Date,
    // Foreign Key Column
    readonly _lc_importrunid_value: `/lc_importrun(${string})`,
    readonly lc_importrunidname: string,
    // Foreign Key Column
    _lc_launchid_value: `/lc_launch(${string})`,
    readonly lc_launchidname: string,
    lc_milestonestatus: lc_milestone_lc_milestonestatus,
    lc_name: string,
    lc_sortorder: number,
    lc_stagingsource: string,
    readonly modifiedbyname: string,
    readonly modifiedbyyominame: string,
    readonly modifiedonbehalfbyname: string,
    readonly modifiedonbehalfbyyominame: string,
    readonly owningbusinessunitname: string,
    statecode: lc_milestone_statecode,
    statuscode: lc_milestone_statuscode,
}>

export type lc_statusupdate = TableRow<{
    // Primary Key Column
    readonly lc_statusupdateid: string,
    readonly createdbyname: string,
    readonly createdbyyominame: string,
    readonly createdonbehalfbyname: string,
    readonly createdonbehalfbyyominame: string,
    lc_body: string,
    // Foreign Key Column
    readonly _lc_importrunid_value: `/lc_importrun(${string})`,
    readonly lc_importrunidname: string,
    // Foreign Key Column
    _lc_launchid_value: `/lc_launch(${string})`,
    readonly lc_launchidname: string,
    lc_title: string,
    lc_updatedon: Date,
    readonly modifiedbyname: string,
    readonly modifiedbyyominame: string,
    readonly modifiedonbehalfbyname: string,
    readonly modifiedonbehalfbyyominame: string,
    readonly owningbusinessunitname: string,
    statecode: lc_statusupdate_statecode,
    statuscode: lc_statusupdate_statuscode,
}>

export type lc_task = TableRow<{
    // Primary Key Column
    readonly lc_taskid: string,
    readonly createdbyname: string,
    readonly createdbyyominame: string,
    readonly createdonbehalfbyname: string,
    readonly createdonbehalfbyyominame: string,
    // Foreign Key Column
    readonly _lc_assignedtoid_value: `/lc_teammember(${string})`,
    readonly lc_assignedtoidname: string,
    lc_blockerreason: string,
    lc_description: string,
    lc_duedate: Date,
    // Foreign Key Column
    readonly _lc_githubissueid_value: `/lc_githubissue(${string})`,
    readonly lc_githubissueidname: string,
    // Foreign Key Column
    readonly _lc_importrunid_value: `/lc_importrun(${string})`,
    readonly lc_importrunidname: string,
    lc_isblocked: lc_task_lc_isblocked,
    // Foreign Key Column
    _lc_milestoneid_value: `/lc_milestone(${string})`,
    readonly lc_milestoneidname: string,
    lc_stagingsource: string,
    lc_taskstatus: lc_task_lc_taskstatus,
    lc_title: string,
    readonly modifiedbyname: string,
    readonly modifiedbyyominame: string,
    readonly modifiedonbehalfbyname: string,
    readonly modifiedonbehalfbyyominame: string,
    readonly owningbusinessunitname: string,
    statecode: lc_task_statecode,
    statuscode: lc_task_statuscode,
}>

const enum lc_launch_lc_launchstatus {
"Planning" = 10600001,
"InProgress" = 10600002,
"ReadyForLaunch" = 10600003,
"Launched" = 10600004,
"OnHold" = 10600005,
}
const enum lc_launch_statecode {
"Active" = 0,
"Inactive" = 1,
}
const enum lc_launch_statuscode {
"Active" = 1,
"Inactive" = 2,
}
const enum lc_milestone_lc_milestonestatus {
"NotStarted" = 10600010,
"InProgress" = 10600011,
"Complete" = 10600012,
"AtRisk" = 10600013,
"Blocked" = 10600014,
}
const enum lc_milestone_statecode {
"Active" = 0,
"Inactive" = 1,
}
const enum lc_milestone_statuscode {
"Active" = 1,
"Inactive" = 2,
}
const enum lc_statusupdate_statecode {
"Active" = 0,
"Inactive" = 1,
}
const enum lc_statusupdate_statuscode {
"Active" = 1,
"Inactive" = 2,
}
const enum lc_task_lc_isblocked {
"False" = 0,
"True" = 1,
}
const enum lc_task_lc_taskstatus {
"NotStarted" = 10600020,
"InProgress" = 10600021,
"Done" = 10600022,
"Blocked" = 10600023,
}
const enum lc_task_statecode {
"Active" = 0,
"Inactive" = 1,
}
const enum lc_task_statuscode {
"Active" = 1,
"Inactive" = 2,
}

export interface UxAgentDataApi extends BaseUxAgentDataApi<TableRegistrations, EnumRegistrations> {}

export interface GeneratedComponentProps {
    dataApi: UxAgentDataApi;
}

