// lc_CalculateLaunchReadinessFx — Power Fx Function (Functions in Dataverse, preview).
//
// Inputs : { LaunchName: Text }
// Outputs: { lc_ReadinessScore: Number, lc_Verdict: Text,
//            lc_ReadinessSummary: Text, lc_NotifiedAt: DateTime }
//
// Strategy:
//   1. Look up the launch by name.
//   2. Invoke the .NET-backed Custom API (lc_CalculateLaunchReadiness) for
//      the baseline score / verdict / summary. Reusing the plugin keeps the
//      milestone math in one place.
//   3. If lc_TeamsChannelId is set, post a readiness card to the launch's
//      Teams channel via the first-party MicrosoftTeams connector. The
//      platform's connection reference resolves auth + DLP.
//   4. Return the baseline contract plus a lc_NotifiedAt timestamp (Blank
//      if no channel was posted to).

With(
    {
        launch: LookUp(lc_launchs, lc_name = LaunchName)
    },
    If(
        IsBlank(launch),
        // Launch not found — graceful default; nothing to notify.
        {
            lc_ReadinessScore: 0,
            lc_Verdict: "NO-GO",
            lc_ReadinessSummary: "Launch '" & LaunchName & "' not found.",
            lc_NotifiedAt: Blank()
        },
        With(
            {
                // Reuse the .NET Custom API for the milestone math.
                baseline: Environment.lc_CalculateLaunchReadiness({
                    lc_LaunchName: LaunchName
                })
            },
            With(
                {
                    posted: If(
                        And(
                            !IsBlank(launch.lc_TeamsChannelId),
                            !IsBlank(launch.lc_TeamsTeamId)
                        ),
                        MicrosoftTeams.PostMessageToChannelV3(
                            launch.lc_TeamsTeamId,
                            launch.lc_TeamsChannelId,
                            {
                                contentType: "html",
                                content:
                                    "<b>" & launch.lc_name & " — " &
                                    baseline.lc_Verdict &
                                    " (" & baseline.lc_ReadinessScore & ")</b><br/>" &
                                    baseline.lc_ReadinessSummary
                            }
                        ),
                        Blank()
                    )
                },
                {
                    lc_ReadinessScore: baseline.lc_ReadinessScore,
                    lc_Verdict: baseline.lc_Verdict,
                    lc_ReadinessSummary: baseline.lc_ReadinessSummary,
                    lc_NotifiedAt: If(IsBlank(posted), Blank(), Now())
                }
            )
        )
    )
)
