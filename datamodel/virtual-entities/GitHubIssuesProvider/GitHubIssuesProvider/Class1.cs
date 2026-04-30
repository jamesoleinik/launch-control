using System;
using System.Collections.Generic;
using System.Net;
using System.Runtime.Serialization.Json;
using System.IO;
using System.Text;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;
using Microsoft.Xrm.Sdk.Extensions;

namespace GitHubIssuesProvider
{
    /// <summary>
    /// Virtual entity data provider for GitHub Issues.
    /// Maps GitHub issues to Dataverse records so they appear alongside
    /// native launch tasks in the Launch Control dashboard.
    /// </summary>
    public class RetrieveMultiplePlugin : IPlugin
    {
        // GitHub repo to pull issues from (configurable via data source)
        private const string DefaultOwner = "jamesoleinik";
        private const string DefaultRepo = "launch-control";

        public void Execute(IServiceProvider serviceProvider)
        {
            var context = serviceProvider.Get<IPluginExecutionContext>();
            var tracingService = serviceProvider.Get<ITracingService>();

            try
            {
                tracingService.Trace("GitHubIssuesProvider: RetrieveMultiple started");

                var query = context.InputParameters["Query"];
                string entityName = null;

                if (query is QueryExpression qe)
                    entityName = qe.EntityName;
                else if (query is FetchExpression)
                    entityName = context.PrimaryEntityName;

                tracingService.Trace("Entity: {0}", entityName);

                // Fetch issues from GitHub API
                var issues = FetchGitHubIssues(DefaultOwner, DefaultRepo, tracingService);

                // Build the entity collection
                var collection = new EntityCollection();
                collection.EntityName = entityName;

                foreach (var issue in issues)
                {
                    var entity = new Entity(entityName);
                    entity.Id = DeterministicGuid(issue.Number);
                    entity[entityName + "id"] = entity.Id;
                    entity["lc_name"] = issue.Title;
                    entity["lc_description"] = issue.Body ?? "";
                    entity["lc_issuenumber"] = issue.Number;
                    entity["lc_state"] = issue.State;
                    entity["lc_url"] = issue.HtmlUrl;
                    entity["lc_assignee"] = issue.Assignee ?? "Unassigned";
                    entity["lc_createdat"] = issue.CreatedAt;
                    entity["lc_updatedat"] = issue.UpdatedAt;
                    entity["lc_labels"] = issue.Labels;

                    collection.Entities.Add(entity);
                }

                collection.TotalRecordCount = collection.Entities.Count;
                context.OutputParameters["BusinessEntityCollection"] = collection;

                tracingService.Trace("Returned {0} issues", collection.Entities.Count);
            }
            catch (Exception ex)
            {
                tracingService.Trace("Error: {0}", ex.ToString());
                throw new InvalidPluginExecutionException(
                    "Failed to retrieve GitHub issues: " + ex.Message, ex);
            }
        }

        /// <summary>
        /// Generate a deterministic GUID from the issue number so the same
        /// issue always maps to the same record ID.
        /// </summary>
        private static Guid DeterministicGuid(int issueNumber)
        {
            var bytes = new byte[16];
            var numBytes = BitConverter.GetBytes(issueNumber);
            // Prefix with a namespace to avoid collisions
            bytes[0] = 0xAB;
            bytes[1] = 0xCD;
            Array.Copy(numBytes, 0, bytes, 12, 4);
            return new Guid(bytes);
        }

        private static List<GitHubIssue> FetchGitHubIssues(
            string owner, string repo, ITracingService trace)
        {
            var url = string.Format(
                "https://api.github.com/repos/{0}/{1}/issues?state=all&per_page=50",
                owner, repo);

            trace.Trace("Fetching: {0}", url);

            var request = (HttpWebRequest)WebRequest.Create(url);
            request.UserAgent = "DataverseLaunchControl/1.0";
            request.Accept = "application/vnd.github+json";
            request.Timeout = 15000;

            var issues = new List<GitHubIssue>();

            using (var response = (HttpWebResponse)request.GetResponse())
            using (var stream = response.GetResponseStream())
            using (var reader = new StreamReader(stream, Encoding.UTF8))
            {
                var json = reader.ReadToEnd();
                // Simple JSON parsing without external dependencies
                issues = ParseIssuesJson(json);
            }

            trace.Trace("Fetched {0} issues from GitHub", issues.Count);
            return issues;
        }

        /// <summary>
        /// Minimal JSON parser for GitHub issues array.
        /// Uses basic string parsing to avoid external dependencies.
        /// </summary>
        private static List<GitHubIssue> ParseIssuesJson(string json)
        {
            var issues = new List<GitHubIssue>();
            var settings = new DataContractJsonSerializerSettings
            {
                DateTimeFormat = new System.Runtime.Serialization.DateTimeFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
            };
            var serializer = new DataContractJsonSerializer(typeof(GitHubIssueDto[]), settings);
            using (var ms = new MemoryStream(Encoding.UTF8.GetBytes(json)))
            {
                var dtos = (GitHubIssueDto[])serializer.ReadObject(ms);
                if (dtos != null)
                {
                    foreach (var dto in dtos)
                    {
                        // Skip pull requests (GitHub API returns them as issues too)
                        if (dto.pull_request != null) continue;

                        issues.Add(new GitHubIssue
                        {
                            Number = dto.number,
                            Title = dto.title ?? "",
                            Body = dto.body ?? "",
                            State = dto.state ?? "unknown",
                            HtmlUrl = dto.html_url ?? "",
                            Assignee = dto.assignee != null ? dto.assignee.login : "Unassigned",
                            CreatedAt = dto.created_at,
                            UpdatedAt = dto.updated_at,
                            Labels = dto.labels != null
                                ? string.Join(", ", Array.ConvertAll(dto.labels, l => l.name))
                                : ""
                        });
                    }
                }
            }
            return issues;
        }
    }

    /// <summary>
    /// Retrieve a single GitHub issue by its deterministic GUID.
    /// Used when Dataverse resolves a lookup column referencing lc_githubissue
    /// (e.g. lc_task.lc_GitHubIssueId), where the platform fetches one record
    /// at a time to render the lookup label and $expand payloads.
    /// </summary>
    public class RetrievePlugin : IPlugin
    {
        // Same constants as RetrieveMultiplePlugin so single-record retrieval
        // and bulk retrieval pull from the same repo.
        private const string DefaultOwner = "jamesoleinik";
        private const string DefaultRepo = "launch-control";

        public void Execute(IServiceProvider serviceProvider)
        {
            var context = serviceProvider.Get<IPluginExecutionContext>();
            var tracingService = serviceProvider.Get<ITracingService>();

            try
            {
                tracingService.Trace("GitHubIssuesProvider: Retrieve started");

                var target = (EntityReference)context.InputParameters["Target"];

                // Extract issue number from the deterministic GUID
                // (last 4 bytes of the GUID == issue number, see DeterministicGuid)
                var bytes = target.Id.ToByteArray();
                var issueNumber = BitConverter.ToInt32(bytes, 12);

                tracingService.Trace("Looking up issue #{0}", issueNumber);

                var entity = new Entity(target.LogicalName, target.Id);
                entity[target.LogicalName + "id"] = target.Id;

                // Fetch the real issue from GitHub so lookup labels show the actual
                // title and $expand returns full data instead of a placeholder.
                var issue = FetchSingleGitHubIssue(
                    DefaultOwner, DefaultRepo, issueNumber, tracingService);

                if (issue != null)
                {
                    entity["lc_name"] = issue.Title;
                    entity["lc_description"] = issue.Body ?? "";
                    entity["lc_issuenumber"] = issue.Number;
                    entity["lc_state"] = issue.State;
                    entity["lc_url"] = issue.HtmlUrl;
                    entity["lc_assignee"] = issue.Assignee ?? "Unassigned";
                    entity["lc_createdat"] = issue.CreatedAt;
                    entity["lc_updatedat"] = issue.UpdatedAt;
                    entity["lc_labels"] = issue.Labels;
                }
                else
                {
                    // Fallback: issue may have been deleted or repo unavailable.
                    // Return a minimal record so the lookup doesn't error out.
                    entity["lc_name"] = string.Format("GitHub Issue #{0} (unavailable)", issueNumber);
                    entity["lc_issuenumber"] = issueNumber;
                    entity["lc_state"] = "unknown";
                }

                context.OutputParameters["BusinessEntity"] = entity;
                tracingService.Trace("Retrieve complete for issue #{0}", issueNumber);
            }
            catch (Exception ex)
            {
                tracingService.Trace("Retrieve error: {0}", ex.ToString());
                throw new InvalidPluginExecutionException(
                    "Failed to retrieve GitHub issue: " + ex.Message, ex);
            }
        }

        /// <summary>
        /// Fetch a single GitHub issue by number via the GitHub REST API.
        /// Returns null if the issue can't be fetched (404, network error, etc.)
        /// so the caller can render a graceful fallback record.
        /// </summary>
        private static GitHubIssue FetchSingleGitHubIssue(
            string owner, string repo, int issueNumber, ITracingService trace)
        {
            var url = string.Format(
                "https://api.github.com/repos/{0}/{1}/issues/{2}",
                owner, repo, issueNumber);

            trace.Trace("Fetching single issue: {0}", url);

            try
            {
                var request = (HttpWebRequest)WebRequest.Create(url);
                request.UserAgent = "DataverseLaunchControl/1.0";
                request.Accept = "application/vnd.github+json";
                request.Timeout = 15000;

                using (var response = (HttpWebResponse)request.GetResponse())
                using (var stream = response.GetResponseStream())
                using (var reader = new StreamReader(stream, Encoding.UTF8))
                {
                    var json = reader.ReadToEnd();
                    var settings = new DataContractJsonSerializerSettings
                    {
                        DateTimeFormat = new System.Runtime.Serialization.DateTimeFormat(
                            "yyyy-MM-dd'T'HH:mm:ss'Z'")
                    };
                    var serializer = new DataContractJsonSerializer(
                        typeof(GitHubIssueDto), settings);
                    using (var ms = new MemoryStream(Encoding.UTF8.GetBytes(json)))
                    {
                        var dto = (GitHubIssueDto)serializer.ReadObject(ms);
                        if (dto == null) return null;
                        return new GitHubIssue
                        {
                            Number = dto.number,
                            Title = dto.title ?? "",
                            Body = dto.body ?? "",
                            State = dto.state ?? "unknown",
                            HtmlUrl = dto.html_url ?? "",
                            Assignee = dto.assignee != null ? dto.assignee.login : "Unassigned",
                            CreatedAt = dto.created_at,
                            UpdatedAt = dto.updated_at,
                            Labels = dto.labels != null
                                ? string.Join(", ", Array.ConvertAll(dto.labels, l => l.name))
                                : ""
                        };
                    }
                }
            }
            catch (Exception ex)
            {
                trace.Trace("Single fetch failed for #{0}: {1}", issueNumber, ex.Message);
                return null;
            }
        }
    }

    // DTO classes for JSON deserialization
    [System.Runtime.Serialization.DataContract]
    internal class GitHubIssueDto
    {
        [System.Runtime.Serialization.DataMember] public int number;
        [System.Runtime.Serialization.DataMember] public string title;
        [System.Runtime.Serialization.DataMember] public string body;
        [System.Runtime.Serialization.DataMember] public string state;
        [System.Runtime.Serialization.DataMember] public string html_url;
        [System.Runtime.Serialization.DataMember] public GitHubUserDto assignee;
        [System.Runtime.Serialization.DataMember] public DateTime created_at;
        [System.Runtime.Serialization.DataMember] public DateTime updated_at;
        [System.Runtime.Serialization.DataMember] public GitHubLabelDto[] labels;
        [System.Runtime.Serialization.DataMember] public object pull_request;
    }

    [System.Runtime.Serialization.DataContract]
    internal class GitHubUserDto
    {
        [System.Runtime.Serialization.DataMember] public string login;
    }

    [System.Runtime.Serialization.DataContract]
    internal class GitHubLabelDto
    {
        [System.Runtime.Serialization.DataMember] public string name;
    }

    internal class GitHubIssue
    {
        public int Number;
        public string Title;
        public string Body;
        public string State;
        public string HtmlUrl;
        public string Assignee;
        public DateTime CreatedAt;
        public DateTime UpdatedAt;
        public string Labels;
    }
}
