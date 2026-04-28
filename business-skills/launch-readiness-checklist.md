# Launch Readiness Checklist

## Description
Use this skill to evaluate whether a product launch is ready for go/no-go. Walk through each gate in order and report the status of each one based on the current data in Dataverse.

## Instructions

You are evaluating launch readiness for a product launch. Check each gate below in order. For each gate, query the relevant milestone and task data in Dataverse and report whether the gate is passed, at risk, or blocked.

### Gate 1: Engineering Sign-off
- Check the "Engineering Sign-off" milestone status
- All engineering tasks must be in "Done" status
- Performance benchmarks must be completed
- **Pass criteria:** Milestone status is "Complete" and all tasks are "Done"

### Gate 2: QA Pass
- Check the "QA Pass" milestone status
- Integration tests, load tests, and security review must all be "Done"
- **Pass criteria:** Milestone status is "Complete" and all QA tasks are "Done"

### Gate 3: Marketing Approval
- Check the "Marketing Approval" milestone status
- Blog post, demo video, and VP messaging approval must all be complete
- If any marketing task is "Blocked", report the blocker reason
- **Pass criteria:** Milestone status is "Complete" and all marketing tasks are "Done"

### Gate 4: Legal Review
- Check the "Legal Review" milestone status
- Terms of service, privacy impact assessment, and license audit must be complete
- **Pass criteria:** Milestone status is "Complete" and all legal tasks are "Done"

### Final Verdict
- If ALL gates pass: "Launch is GO. All readiness gates passed."
- If any gate is blocked: "Launch is NO-GO. [Gate name] is blocked: [reason]."
- If any gate is at risk: "Launch is CONDITIONAL. [Gate name] is at risk: [details]. Recommend [action]."

### Output Format
For each gate, report:
```
Gate [N]: [Name]
  Status: [PASSED / AT RISK / BLOCKED]
  Details: [one-sentence summary]
```

Then provide the final verdict as a single sentence.
