using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Microsoft.Xrm.Sdk.Extensions;

namespace CalculateLaunchReadiness
{
    /// <summary>
    /// Custom action plugin: lc_CalculateLaunchReadiness
    /// 
    /// Input: lc_LaunchName (string) - name of the launch to evaluate
    /// Output: lc_ReadinessScore (int) - 0-100 readiness score
    /// Output: lc_ReadinessSummary (string) - human-readable gate-by-gate summary
    /// Output: lc_Verdict (string) - "GO", "NO-GO", or "CONDITIONAL"
    /// 
    /// Evaluates all 4 gates: Engineering, QA, Marketing, Legal.
    /// Each gate is worth 25 points. Blocked gates score 0, at-risk score 12.
    /// </summary>
    public class CalculateLaunchReadinessPlugin : IPlugin
    {
        private static readonly string[] GateNames = {
            "Engineering Sign-off", "QA Pass", "Marketing Approval", "Legal Review"
        };

        // Milestone status codes
        private const int NotStarted = 10600010;
        private const int InProgress = 10600011;
        private const int Complete = 10600012;
        private const int AtRisk = 10600013;
        private const int Blocked = 10600014;

        // Task status codes
        private const int TaskDone = 10600022;
        private const int TaskBlocked = 10600023;

        public void Execute(IServiceProvider serviceProvider)
        {
            var context = serviceProvider.Get<IPluginExecutionContext>();
            var service = serviceProvider.Get<IOrganizationService>();
            var trace = serviceProvider.Get<ITracingService>();

            // Get input parameter
            string launchName = context.InputParameters.Contains("lc_LaunchName")
                ? (string)context.InputParameters["lc_LaunchName"]
                : null;

            if (string.IsNullOrEmpty(launchName))
                throw new InvalidPluginExecutionException("lc_LaunchName is required.");

            trace.Trace("Evaluating readiness for: {0}", launchName);

            // Find the launch
            var launchQuery = new QueryExpression("lc_launch")
            {
                ColumnSet = new ColumnSet("lc_launchid", "lc_name"),
                Criteria = new FilterExpression()
            };
            launchQuery.Criteria.AddCondition("lc_name", ConditionOperator.Equal, launchName);
            var launches = service.RetrieveMultiple(launchQuery);

            if (launches.Entities.Count == 0)
                throw new InvalidPluginExecutionException("Launch not found: " + launchName);

            var launchId = launches.Entities[0].Id;

            // Get milestones for this launch
            var msQuery = new QueryExpression("lc_milestone")
            {
                ColumnSet = new ColumnSet("lc_name", "lc_milestonestatus", "lc_milestoneid"),
                Criteria = new FilterExpression()
            };
            msQuery.Criteria.AddCondition("lc_launchid", ConditionOperator.Equal, launchId);
            var milestones = service.RetrieveMultiple(msQuery);

            // Get all tasks for this launch's milestones
            var taskQuery = new QueryExpression("lc_task")
            {
                ColumnSet = new ColumnSet("lc_title", "lc_taskstatus", "lc_isblocked",
                                          "lc_blockerreason", "lc_milestoneid"),
            };
            var milestoneIds = milestones.Entities
                .Select(m => m.Id.ToString())
                .ToArray();

            // Score each gate
            int totalScore = 0;
            var summaryLines = new List<string>();
            string verdict;

            bool anyBlocked = false;
            bool anyAtRisk = false;

            foreach (var gateName in GateNames)
            {
                var milestone = milestones.Entities
                    .FirstOrDefault(m => m.GetAttributeValue<string>("lc_name") == gateName);

                if (milestone == null)
                {
                    summaryLines.Add(string.Format(
                        "Gate: {0} | Status: NOT FOUND | Score: 0/25", gateName));
                    continue;
                }

                var msStatus = milestone.GetAttributeValue<OptionSetValue>("lc_milestonestatus");
                int statusCode = msStatus != null ? msStatus.Value : NotStarted;

                int gateScore;
                string statusLabel;

                switch (statusCode)
                {
                    case Complete:
                        gateScore = 25;
                        statusLabel = "PASSED";
                        break;
                    case AtRisk:
                        gateScore = 12;
                        statusLabel = "AT RISK";
                        anyAtRisk = true;
                        break;
                    case Blocked:
                        gateScore = 0;
                        statusLabel = "BLOCKED";
                        anyBlocked = true;
                        break;
                    case InProgress:
                        gateScore = 15;
                        statusLabel = "IN PROGRESS";
                        break;
                    default:
                        gateScore = 5;
                        statusLabel = "NOT STARTED";
                        break;
                }

                totalScore += gateScore;
                summaryLines.Add(string.Format(
                    "Gate: {0} | Status: {1} | Score: {2}/25",
                    gateName, statusLabel, gateScore));

                trace.Trace("{0}: {1} ({2}/25)", gateName, statusLabel, gateScore);
            }

            // Determine verdict
            if (anyBlocked)
                verdict = "NO-GO";
            else if (anyAtRisk)
                verdict = "CONDITIONAL";
            else if (totalScore == 100)
                verdict = "GO";
            else
                verdict = "CONDITIONAL";

            string summary = string.Join("\n", summaryLines)
                + string.Format("\n\nOverall Score: {0}/100 | Verdict: {1}", totalScore, verdict);

            trace.Trace("Score: {0}/100, Verdict: {1}", totalScore, verdict);

            // Set output parameters
            context.OutputParameters["lc_ReadinessScore"] = totalScore;
            context.OutputParameters["lc_ReadinessSummary"] = summary;
            context.OutputParameters["lc_Verdict"] = verdict;
        }
    }
}
