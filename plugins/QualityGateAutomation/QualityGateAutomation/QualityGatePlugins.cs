using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Microsoft.Crm.Sdk.Messages;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace QualityGateAutomation
{
    internal static class QualityGate
    {
        internal const string BpfEntity =
            "new_bpf_ae8e29d7071f4eec9ef2a881a1590d5c";
        internal const string BpfLaunchLookup = "bpf_lc_launchid";
        internal const string ProcessName = "Launch Approval";
        internal const string DraftStage = "Draft";
        internal const string QualityGateStage = "Quality Gate";
        internal const string ApprovalStage = "Launch Approval";
        internal const string AgentRole = "lc Quality Gate Agent";
        internal const string TaskPrefix = "Quality Gate::";

        internal const int ResultPassed = 106000000;
        internal const int ResultFailed = 106000001;
        internal const int ResultNeedsReview = 106000002;
        internal const int ResultError = 106000003;

        internal const int LaunchPending = 106000000;
        internal const int LaunchPassed = 106000001;
        internal const int LaunchFailed = 106000002;
        internal const int LaunchNeedsReview = 106000003;
        internal const int LaunchError = 106000004;

        internal static IOrganizationService SystemService(IServiceProvider services)
        {
            var factory = (IOrganizationServiceFactory)services.GetService(
                typeof(IOrganizationServiceFactory));
            return factory.CreateOrganizationService(null);
        }

        internal static Entity Target(IPluginExecutionContext context)
        {
            if (!context.InputParameters.Contains("Target")
                || !(context.InputParameters["Target"] is Entity))
            {
                throw new InvalidPluginExecutionException(
                    "The plug-in requires an entity Target.");
            }

            return (Entity)context.InputParameters["Target"];
        }

        internal static Guid ActiveProcessId(IOrganizationService service)
        {
            var query = new QueryExpression("workflow")
            {
                ColumnSet = new ColumnSet("workflowid"),
                TopCount = 2,
            };
            query.Criteria.AddCondition("name", ConditionOperator.Equal, ProcessName);
            query.Criteria.AddCondition("category", ConditionOperator.Equal, 4);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 1);
            var rows = service.RetrieveMultiple(query).Entities;
            if (rows.Count != 1)
            {
                throw new InvalidPluginExecutionException(
                    "Expected exactly one active Launch Approval BPF.");
            }

            return rows[0].Id;
        }

        internal static Guid StageId(
            IOrganizationService service,
            Guid processId,
            string stageName)
        {
            var query = new QueryExpression("processstage")
            {
                ColumnSet = new ColumnSet("processstageid"),
                TopCount = 2,
            };
            query.Criteria.AddCondition(
                "processid", ConditionOperator.Equal, processId);
            query.Criteria.AddCondition(
                "stagename", ConditionOperator.Equal, stageName);
            var rows = service.RetrieveMultiple(query).Entities;
            if (rows.Count != 1)
            {
                throw new InvalidPluginExecutionException(
                    "Expected exactly one BPF stage named " + stageName + ".");
            }

            return rows[0].Id;
        }

        internal static Entity ResolveAgent(IOrganizationService service)
        {
            var query = new QueryExpression("systemuser")
            {
                ColumnSet = new ColumnSet(
                    "systemuserid", "systemmanagedusertype", "isdisabled"),
                Distinct = true,
                TopCount = 2,
            };
            query.Criteria.AddCondition("isdisabled", ConditionOperator.Equal, false);
            query.Criteria.AddCondition(
                "systemmanagedusertype", ConditionOperator.Equal, 3);
            var userRoles = query.AddLink(
                "systemuserroles", "systemuserid", "systemuserid");
            var role = userRoles.AddLink("role", "roleid", "roleid");
            role.LinkCriteria.AddCondition(
                "name", ConditionOperator.Equal, AgentRole);

            var rows = service.RetrieveMultiple(query).Entities;
            if (rows.Count != 1)
            {
                throw new InvalidPluginExecutionException(
                    "Expected exactly one enabled Agentic User with role "
                    + AgentRole + ".");
            }

            return rows[0];
        }

        internal static bool HasAgentRole(
            IOrganizationService service,
            Guid userId)
        {
            var query = new QueryExpression("role")
            {
                ColumnSet = new ColumnSet("roleid"),
                TopCount = 1,
            };
            query.Criteria.AddCondition("name", ConditionOperator.Equal, AgentRole);
            var userRoles = query.AddLink("systemuserroles", "roleid", "roleid");
            userRoles.LinkCriteria.AddCondition(
                "systemuserid", ConditionOperator.Equal, userId);
            return service.RetrieveMultiple(query).Entities.Count == 1;
        }

        internal static void GrantLaunchAccess(
            IOrganizationService service,
            EntityReference launch,
            EntityReference agent)
        {
            GrantRecordAccess(
                service,
                launch,
                agent,
                AccessRights.ReadAccess | AccessRights.AppendToAccess);
            foreach (var record in ResearchRecords(service, launch.Id))
            {
                GrantRecordAccess(
                    service, record, agent, AccessRights.ReadAccess);
            }
        }

        internal static void RevokeLaunchAccess(
            IOrganizationService service,
            EntityReference launch,
            EntityReference agent)
        {
            foreach (var record in ResearchRecords(service, launch.Id))
            {
                if (IsOwnedBy(service, record, agent.Id))
                {
                    continue;
                }
                RevokeRecordAccess(service, record, agent);
            }
            RevokeRecordAccess(service, launch, agent);
        }

        private static bool IsOwnedBy(
            IOrganizationService service,
            EntityReference record,
            Guid userId)
        {
            var row = service.Retrieve(
                record.LogicalName,
                record.Id,
                new ColumnSet("ownerid"));
            return row.GetAttributeValue<EntityReference>("ownerid")?.Id
                == userId;
        }

        private static IEnumerable<EntityReference> ResearchRecords(
            IOrganizationService service,
            Guid launchId)
        {
            var entities = new[]
            {
                new[] { "lc_milestone", "lc_launchid" },
                new[] { "lc_task", "lc_launchid" },
                new[] { "lc_statusupdate", "lc_launchid" },
            };
            foreach (var definition in entities)
            {
                var query = new QueryExpression(definition[0])
                {
                    ColumnSet = new ColumnSet(false),
                };
                query.Criteria.AddCondition(
                    definition[1], ConditionOperator.Equal, launchId);
                foreach (var record in service.RetrieveMultiple(query).Entities)
                {
                    yield return record.ToEntityReference();
                }
            }
        }

        private static void GrantRecordAccess(
            IOrganizationService service,
            EntityReference target,
            EntityReference agent,
            AccessRights rights)
        {
            service.Execute(new GrantAccessRequest
            {
                Target = target,
                PrincipalAccess = new PrincipalAccess
                {
                    Principal = agent,
                    AccessMask = rights,
                },
            });
        }

        private static void RevokeRecordAccess(
            IOrganizationService service,
            EntityReference target,
            EntityReference agent)
        {
            service.Execute(new RevokeAccessRequest
            {
                Target = target,
                Revokee = agent,
            });
        }

        internal static string AssignmentKey(Guid launchId)
        {
            return TaskPrefix + launchId.ToString("D");
        }

        internal static string JsonDescription(Guid launchId, string launchName)
        {
            return "{\"launch_id\":\"" + launchId.ToString("D")
                + "\",\"launch_name\":\"" + JsonEscape(launchName)
                + "\",\"check\":\"playwright\"}";
        }

        private static string JsonEscape(string value)
        {
            if (value == null)
            {
                return string.Empty;
            }

            var output = new StringBuilder(value.Length + 8);
            foreach (var character in value)
            {
                switch (character)
                {
                    case '\\': output.Append("\\\\"); break;
                    case '"': output.Append("\\\""); break;
                    case '\r': output.Append("\\r"); break;
                    case '\n': output.Append("\\n"); break;
                    case '\t': output.Append("\\t"); break;
                    default:
                        if (character < 32)
                        {
                            output.Append("\\u");
                            output.Append(((int)character).ToString("x4"));
                        }
                        else
                        {
                            output.Append(character);
                        }
                        break;
                }
            }

            return output.ToString();
        }
    }

    public sealed class CreateQualityGateAssignmentPlugin : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            var context = (IPluginExecutionContext)serviceProvider.GetService(
                typeof(IPluginExecutionContext));
            var trace = (ITracingService)serviceProvider.GetService(
                typeof(ITracingService));
            if (context.Depth > 1
                || !string.Equals(
                    context.MessageName, "Update",
                    StringComparison.OrdinalIgnoreCase)
                || !string.Equals(
                    context.PrimaryEntityName, QualityGate.BpfEntity,
                    StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            var target = QualityGate.Target(context);
            var activeStage = target.GetAttributeValue<EntityReference>(
                "activestageid");
            if (activeStage == null)
            {
                return;
            }

            var service = QualityGate.SystemService(serviceProvider);
            var processId = QualityGate.ActiveProcessId(service);
            var draftStage = QualityGate.StageId(
                service, processId, QualityGate.DraftStage);
            var qualityGateStage = QualityGate.StageId(
                service, processId, QualityGate.QualityGateStage);
            if (activeStage.Id != qualityGateStage
                && activeStage.Id != draftStage)
            {
                return;
            }

            var instance = service.Retrieve(
                QualityGate.BpfEntity,
                target.Id,
                new ColumnSet(QualityGate.BpfLaunchLookup));
            var launchReference = instance.GetAttributeValue<EntityReference>(
                QualityGate.BpfLaunchLookup);
            if (launchReference == null)
            {
                throw new InvalidPluginExecutionException(
                    "The Launch Approval BPF instance has no Launch.");
            }

            var agent = QualityGate.ResolveAgent(service);
            if (activeStage.Id == draftStage)
            {
                QualityGate.RevokeLaunchAccess(
                    service, launchReference, agent.ToEntityReference());
                trace.Trace(
                    "Revoked Quality Gate access after returning launch {0} to Draft.",
                    launchReference.Id);
                return;
            }

            var assignmentKey = QualityGate.AssignmentKey(launchReference.Id);
            var resultQuery = new QueryExpression("lc_qualitygateresult")
            {
                ColumnSet = new ColumnSet("lc_qualitygateresultid"),
                TopCount = 1,
            };
            resultQuery.Criteria.AddCondition(
                "lc_assignmentkey", ConditionOperator.Equal, assignmentKey);
            if (service.RetrieveMultiple(resultQuery).Entities.Any())
            {
                throw new InvalidPluginExecutionException(
                    "A Quality Gate Result already exists. Reset the demo "
                    + "before re-entering Quality Gate.");
            }
            var existingQuery = new QueryExpression("task")
            {
                ColumnSet = new ColumnSet("activityid", "statecode"),
                TopCount = 1,
            };
            existingQuery.Criteria.AddCondition(
                "subject", ConditionOperator.Equal, assignmentKey);
            var existing = service.RetrieveMultiple(existingQuery).Entities
                .SingleOrDefault();
            if (existing != null)
            {
                if (existing.GetAttributeValue<OptionSetValue>("statecode")?.Value != 0)
                {
                    var reopened = new Entity("task", existing.Id);
                    reopened["statecode"] = new OptionSetValue(0);
                    reopened["statuscode"] = new OptionSetValue(2);
                    reopened["actualstart"] = null;
                    reopened["actualend"] = null;
                    reopened["percentcomplete"] = 0;
                    service.Update(reopened);
                }
                QualityGate.GrantLaunchAccess(
                    service, launchReference, agent.ToEntityReference());
                trace.Trace(
                    "Reopened assignment and restored Quality Gate access for {0}.",
                    launchReference.Id);
                return;
            }

            var launch = service.Retrieve(
                "lc_launch",
                launchReference.Id,
                new ColumnSet("lc_name"));
            var task = new Entity("task");
            task["subject"] = assignmentKey;
            task["description"] = QualityGate.JsonDescription(
                launchReference.Id,
                launch.GetAttributeValue<string>("lc_name") ?? "Launch");
            task["ownerid"] = agent.ToEntityReference();
            task["regardingobjectid"] = launchReference;
            task["prioritycode"] = new OptionSetValue(1);
            var taskId = service.Create(task);
            QualityGate.GrantLaunchAccess(
                service, launchReference, agent.ToEntityReference());
            trace.Trace(
                "Created Quality Gate assignment {0} and granted launch access {1}.",
                taskId,
                launchReference.Id);
        }
    }

    public sealed class ApplyQualityGateResultPlugin : IPlugin
    {
        public void Execute(IServiceProvider serviceProvider)
        {
            var context = (IPluginExecutionContext)serviceProvider.GetService(
                typeof(IPluginExecutionContext));
            var trace = (ITracingService)serviceProvider.GetService(
                typeof(ITracingService));
            // Dataverse MCP create_record performs the create from its server
            // plug-in, so the governed result handler runs at depth 2.
            if (context.Depth > 2
                || !string.Equals(
                    context.MessageName, "Create",
                    StringComparison.OrdinalIgnoreCase)
                || !string.Equals(
                    context.PrimaryEntityName, "lc_qualitygateresult",
                    StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            var target = QualityGate.Target(context);
            var service = QualityGate.SystemService(serviceProvider);
            var result = service.Retrieve(
                "lc_qualitygateresult",
                target.Id,
                new ColumnSet(
                    "lc_launch",
                    "lc_outcome",
                    "lc_score",
                    "lc_feedback",
                    "lc_evidence",
                    "lc_checkedon",
                    "lc_assignmentkey"));
            var launchReference = result.GetAttributeValue<EntityReference>(
                "lc_launch");
            var outcome = result.GetAttributeValue<OptionSetValue>("lc_outcome");
            var assignmentKey = result.GetAttributeValue<string>(
                "lc_assignmentkey");
            if (launchReference == null || outcome == null
                || string.IsNullOrWhiteSpace(assignmentKey))
            {
                throw new InvalidPluginExecutionException(
                    "Quality Gate Result requires Launch, Outcome, and Assignment Key.");
            }

            var expectedKey = QualityGate.AssignmentKey(launchReference.Id);
            if (!string.Equals(
                assignmentKey, expectedKey, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidPluginExecutionException(
                    "Assignment Key does not match the related Launch.");
            }

            var duplicateQuery = new QueryExpression("lc_qualitygateresult")
            {
                ColumnSet = new ColumnSet("lc_qualitygateresultid"),
                TopCount = 1,
            };
            duplicateQuery.Criteria.AddCondition(
                "lc_assignmentkey", ConditionOperator.Equal, expectedKey);
            duplicateQuery.Criteria.AddCondition(
                "lc_qualitygateresultid",
                ConditionOperator.NotEqual,
                result.Id);
            if (service.RetrieveMultiple(duplicateQuery).Entities.Any())
            {
                throw new InvalidPluginExecutionException(
                    "A Quality Gate Result already exists for this assignment.");
            }

            var taskQuery = new QueryExpression("task")
            {
                ColumnSet = new ColumnSet("activityid", "ownerid"),
                TopCount = 2,
            };
            taskQuery.Criteria.AddCondition(
                "subject", ConditionOperator.Equal, expectedKey);
            var tasks = service.RetrieveMultiple(taskQuery).Entities;
            if (tasks.Count != 1)
            {
                throw new InvalidPluginExecutionException(
                    "Expected exactly one Quality Gate assignment.");
            }

            var owner = tasks[0].GetAttributeValue<EntityReference>("ownerid");
            if (owner == null
                || !string.Equals(
                    owner.LogicalName, "systemuser",
                    StringComparison.OrdinalIgnoreCase)
                || owner.Id != context.InitiatingUserId)
            {
                throw new InvalidPluginExecutionException(
                    "Only the Agentic User that owns the assignment may submit its result.");
            }

            var agent = service.Retrieve(
                "systemuser",
                owner.Id,
                new ColumnSet("systemmanagedusertype", "isdisabled"));
            var managedType = agent.GetAttributeValue<OptionSetValue>(
                "systemmanagedusertype");
            if (agent.GetAttributeValue<bool>("isdisabled")
                || managedType == null
                || managedType.Value != 3
                || !QualityGate.HasAgentRole(service, owner.Id))
            {
                throw new InvalidPluginExecutionException(
                    "The assignment owner is not an enabled governed Agentic User.");
            }

            var launchStatus = MapLaunchStatus(outcome.Value);
            var launchUpdate = new Entity("lc_launch", launchReference.Id);
            launchUpdate["lc_qualitygatestatus"] =
                new OptionSetValue(launchStatus);
            Copy(result, launchUpdate, "lc_score", "lc_qualitygatescore");
            Copy(result, launchUpdate, "lc_feedback", "lc_qualitygatefeedback");
            Copy(result, launchUpdate, "lc_evidence", "lc_qualitygateevidence");
            Copy(result, launchUpdate, "lc_checkedon", "lc_qualitygatecheckedon");
            service.Update(launchUpdate);

            if (outcome.Value == QualityGate.ResultPassed)
            {
                AdvanceToApproval(service, launchReference.Id);
            }

            QualityGate.RevokeLaunchAccess(service, launchReference, owner);
            trace.Trace(
                "Applied Quality Gate result {0} and revoked launch access {1}.",
                result.Id,
                launchReference.Id);
        }

        private static void Copy(
            Entity source,
            Entity destination,
            string sourceName,
            string destinationName)
        {
            if (source.Attributes.Contains(sourceName))
            {
                destination[destinationName] = source[sourceName];
            }
        }

        private static int MapLaunchStatus(int outcome)
        {
            switch (outcome)
            {
                case QualityGate.ResultPassed:
                    return QualityGate.LaunchPassed;
                case QualityGate.ResultFailed:
                    return QualityGate.LaunchFailed;
                case QualityGate.ResultNeedsReview:
                    return QualityGate.LaunchNeedsReview;
                case QualityGate.ResultError:
                    return QualityGate.LaunchError;
                default:
                    throw new InvalidPluginExecutionException(
                        "Unsupported Quality Gate outcome.");
            }
        }

        private static void AdvanceToApproval(
            IOrganizationService service,
            Guid launchId)
        {
            var processId = QualityGate.ActiveProcessId(service);
            var qualityGateStage = QualityGate.StageId(
                service, processId, QualityGate.QualityGateStage);
            var approvalStage = QualityGate.StageId(
                service, processId, QualityGate.ApprovalStage);
            var query = new QueryExpression(QualityGate.BpfEntity)
            {
                ColumnSet = new ColumnSet("activestageid", "traversedpath"),
                TopCount = 2,
            };
            query.Criteria.AddCondition(
                QualityGate.BpfLaunchLookup,
                ConditionOperator.Equal,
                launchId);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            var rows = service.RetrieveMultiple(query).Entities;
            if (rows.Count != 1)
            {
                throw new InvalidPluginExecutionException(
                    "Expected exactly one active Launch Approval process instance.");
            }

            var instance = rows[0];
            var activeStage = instance.GetAttributeValue<EntityReference>(
                "activestageid");
            if (activeStage == null || activeStage.Id != qualityGateStage)
            {
                throw new InvalidPluginExecutionException(
                    "A Passed result may advance only from Quality Gate.");
            }

            var traversedPath = instance.GetAttributeValue<string>(
                "traversedpath") ?? string.Empty;
            var approval = approvalStage.ToString("D");
            var stages = traversedPath.Split(
                new[] { ',' },
                StringSplitOptions.RemoveEmptyEntries);
            if (!stages.Any(
                value => string.Equals(
                    value.Trim().Trim('{', '}'),
                    approval,
                    StringComparison.OrdinalIgnoreCase)))
            {
                traversedPath = string.IsNullOrWhiteSpace(traversedPath)
                    ? approval
                    : traversedPath + "," + approval;
            }

            var update = new Entity(QualityGate.BpfEntity, instance.Id);
            update["activestageid"] =
                new EntityReference("processstage", approvalStage);
            update["traversedpath"] = traversedPath;
            service.Update(update);
        }
    }
}
