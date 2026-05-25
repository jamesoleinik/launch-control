using System;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Extensions;

namespace GitHubIssuesProvider
{
    /// <summary>
    /// lc_taskstatus option set values (from the LaunchControl solution).
    /// Keeping them as constants avoids a metadata roundtrip on every Update.
    /// </summary>
    internal static class TaskStatus
    {
        public const int NotStarted = 10600301;
        public const int InProgress = 10600302;
        public const int Blocked    = 10600303;
        public const int Done       = 10600304;
    }

    /// <summary>
    /// Rule 1 — Pre-Update on lc_task: when lc_blockerreason is being SET to
    /// a non-empty value, force lc_taskstatus to Blocked in the same write.
    /// </summary>
    public class TaskBlockedRulePlugin : IPlugin
    {
        public void Execute(IServiceProvider sp)
        {
            var ctx = sp.Get<IPluginExecutionContext>();
            var trace = sp.Get<ITracingService>();

            if (!ctx.InputParameters.Contains("Target") ||
                !(ctx.InputParameters["Target"] is Entity target)) return;
            if (target.LogicalName != "lc_task") return;
            // Only act when the caller is touching lc_blockerreason
            if (!target.Contains("lc_blockerreason")) return;

            var reason = target["lc_blockerreason"] as string;
            if (string.IsNullOrWhiteSpace(reason)) return;

            target["lc_taskstatus"] = new OptionSetValue(TaskStatus.Blocked);
            trace.Trace("TaskBlockedRule: blockerreason set -> forcing status=Blocked");
        }
    }

    /// <summary>
    /// Rule 2 — Pre-Update on lc_task: when lc_blockerreason is being CLEARED
    /// on a task whose previous status was Blocked, revert status to
    /// InProgress (unless the caller is already setting status themselves).
    /// Requires PreImage "PreImage" with lc_taskstatus.
    /// </summary>
    public class TaskUnblockedRulePlugin : IPlugin
    {
        public void Execute(IServiceProvider sp)
        {
            var ctx = sp.Get<IPluginExecutionContext>();
            var trace = sp.Get<ITracingService>();

            if (!ctx.InputParameters.Contains("Target") ||
                !(ctx.InputParameters["Target"] is Entity target)) return;
            if (target.LogicalName != "lc_task") return;
            if (!target.Contains("lc_blockerreason")) return;

            var reason = target["lc_blockerreason"] as string;
            if (!string.IsNullOrWhiteSpace(reason)) return;

            Entity pre = null;
            if (ctx.PreEntityImages != null && ctx.PreEntityImages.Contains("PreImage"))
                pre = ctx.PreEntityImages["PreImage"];
            if (pre == null) return;

            var priorStatus = pre.GetAttributeValue<OptionSetValue>("lc_taskstatus");
            if (priorStatus == null || priorStatus.Value != TaskStatus.Blocked) return;

            // Caller may have set status themselves in this same write — respect that.
            if (target.Contains("lc_taskstatus")) return;

            target["lc_taskstatus"] = new OptionSetValue(TaskStatus.InProgress);
            trace.Trace("TaskUnblockedRule: blockerreason cleared on Blocked task -> status=InProgress");
        }
    }

    /// <summary>
    /// Rule 3 — Pre-Update on lc_task: refuse to mark a task Done while
    /// lc_blockerreason is still set. Throws InvalidPluginExecutionException
    /// so the platform aborts the transaction and the row is unchanged.
    /// Requires PreImage "PreImage" with lc_blockerreason.
    /// </summary>
    public class TaskCompletionGuardRulePlugin : IPlugin
    {
        public void Execute(IServiceProvider sp)
        {
            var ctx = sp.Get<IPluginExecutionContext>();
            var trace = sp.Get<ITracingService>();

            if (!ctx.InputParameters.Contains("Target") ||
                !(ctx.InputParameters["Target"] is Entity target)) return;
            if (target.LogicalName != "lc_task") return;
            if (!target.Contains("lc_taskstatus")) return;

            var newStatus = target.GetAttributeValue<OptionSetValue>("lc_taskstatus");
            if (newStatus == null || newStatus.Value != TaskStatus.Done) return;

            // Effective blockerreason = target value if caller is updating it,
            // otherwise PreImage value.
            string reason;
            if (target.Contains("lc_blockerreason"))
            {
                reason = target["lc_blockerreason"] as string;
            }
            else
            {
                Entity pre = null;
                if (ctx.PreEntityImages != null && ctx.PreEntityImages.Contains("PreImage"))
                    pre = ctx.PreEntityImages["PreImage"];
                reason = pre != null ? pre.GetAttributeValue<string>("lc_blockerreason") : null;
            }

            if (!string.IsNullOrWhiteSpace(reason))
            {
                trace.Trace("TaskCompletionGuardRule: blocking Done because blockerreason='{0}'", reason);
                throw new InvalidPluginExecutionException(
                    "Cannot mark task Done while a blocker reason is set. " +
                    "Clear lc_blockerreason first.");
            }
        }
    }
}
