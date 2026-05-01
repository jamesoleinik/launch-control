using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace CalculateLaunchReadiness
{
    /// <summary>
    /// Custom action plugin: lc_CalculateLaunchReadiness
    ///
    /// Input: lc_LaunchName (string) - name of the launch to evaluate
    /// Output: lc_ReadinessScore (decimal) - 0-100 readiness score
    /// Output: lc_ReadinessSummary (string) - milestone-by-milestone summary
    /// Output: lc_Verdict (string) - "GO", "NO-GO", or "CONDITIONAL"
    ///
    /// Scores every milestone attached to the launch (no hard-coded gate names).
    /// Per-milestone weight (out of 100):
    ///   Complete=100, AtRisk=50, InProgress=60, NotStarted=20, Blocked=0.
    /// Final readiness = average across all milestones.
    /// Verdict:
    ///   NO-GO       if any milestone is Blocked
    ///   GO          if score >= 90 and no AtRisk
    ///   CONDITIONAL otherwise
    /// </summary>
    public class CalculateLaunchReadinessPlugin : IPlugin
    {
        // Milestone status codes (lc_milestonestatus choice)
        private const int NotStarted = 10600010;
        private const int InProgress = 10600011;
        private const int Complete   = 10600012;
        private const int AtRisk     = 10600013;
        private const int Blocked    = 10600014;

        public void Execute(IServiceProvider serviceProvider)
        {
            var context = (IPluginExecutionContext)serviceProvider.GetService(typeof(IPluginExecutionContext));
            var factory = (IOrganizationServiceFactory)serviceProvider.GetService(typeof(IOrganizationServiceFactory));
            var service = factory.CreateOrganizationService(context.UserId);
            var trace   = (ITracingService)serviceProvider.GetService(typeof(ITracingService));

            string launchName = context.InputParameters.Contains("lc_LaunchName")
                ? (string)context.InputParameters["lc_LaunchName"]
                : null;

            if (string.IsNullOrEmpty(launchName))
                throw new InvalidPluginExecutionException("lc_LaunchName is required.");

            trace.Trace("Evaluating readiness for: {0}", launchName);

            // Resolve launch by name
            var launchQuery = new QueryExpression("lc_launch")
            {
                ColumnSet = new ColumnSet("lc_launchid", "lc_name"),
                Criteria  = new FilterExpression()
            };
            launchQuery.Criteria.AddCondition("lc_name", ConditionOperator.Equal, launchName);
            var launches = service.RetrieveMultiple(launchQuery);

            if (launches.Entities.Count == 0)
                throw new InvalidPluginExecutionException("Launch not found: " + launchName);

            var launchId = launches.Entities[0].Id;

            // Pull every milestone for this launch
            var msQuery = new QueryExpression("lc_milestone")
            {
                ColumnSet = new ColumnSet("lc_name", "lc_milestonestatus"),
                Criteria  = new FilterExpression()
            };
            msQuery.Criteria.AddCondition("lc_launchid", ConditionOperator.Equal, launchId);
            msQuery.AddOrder("lc_sortorder", OrderType.Ascending);
            msQuery.AddOrder("lc_name",      OrderType.Ascending);
            var milestones = service.RetrieveMultiple(msQuery);

            int milestoneCount = milestones.Entities.Count;
            if (milestoneCount == 0)
            {
                context.OutputParameters["lc_ReadinessScore"]   = 0m;
                context.OutputParameters["lc_ReadinessSummary"] = "No milestones found for launch: " + launchName;
                context.OutputParameters["lc_Verdict"]          = "NO-GO";
                return;
            }

            int totalPoints = 0;
            bool anyBlocked = false;
            bool anyAtRisk  = false;
            var lines = new List<string>();

            foreach (var ms in milestones.Entities)
            {
                string name      = ms.GetAttributeValue<string>("lc_name") ?? "(unnamed)";
                var statusOpt    = ms.GetAttributeValue<OptionSetValue>("lc_milestonestatus");
                int statusCode   = statusOpt != null ? statusOpt.Value : NotStarted;

                int points;
                string label;
                switch (statusCode)
                {
                    case Complete:   points = 100; label = "COMPLETE";    break;
                    case InProgress: points = 60;  label = "IN PROGRESS"; break;
                    case AtRisk:     points = 50;  label = "AT RISK";     anyAtRisk  = true; break;
                    case Blocked:    points = 0;   label = "BLOCKED";     anyBlocked = true; break;
                    default:         points = 20;  label = "NOT STARTED"; break;
                }

                totalPoints += points;
                lines.Add(string.Format("- [{0,-12}] {1} ({2}/100)", label, name, points));
                trace.Trace("{0}: {1} ({2}/100)", name, label, points);
            }

            decimal score = Math.Round((decimal)totalPoints / milestoneCount, 1);

            string verdict;
            if (anyBlocked)        verdict = "NO-GO";
            else if (score >= 90m && !anyAtRisk) verdict = "GO";
            else                   verdict = "CONDITIONAL";

            string summary = string.Format("Launch: {0}\nMilestones evaluated: {1}\n\n", launchName, milestoneCount)
                           + string.Join("\n", lines)
                           + string.Format("\n\nReadiness Score: {0}/100\nVerdict: {1}", score, verdict);

            trace.Trace("Score: {0}/100, Verdict: {1}", score, verdict);

            context.OutputParameters["lc_ReadinessScore"]   = score;
            context.OutputParameters["lc_ReadinessSummary"] = summary;
            context.OutputParameters["lc_Verdict"]          = verdict;
        }
    }
}

