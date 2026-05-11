# Security

This repository is an example/demo project for the **Launch Control** LinkedIn series. It is not a Microsoft-supported product. The code is provided as-is for educational purposes.

## Reporting a security issue

If you believe you've found a security vulnerability in any code or configuration in this repository, please **do not file a public GitHub issue**.

Instead, report it privately:

- **Email:** open a private security advisory via [GitHub's Security tab](https://github.com/jamesoleinik/launch-control/security/advisories/new), or
- **DM:** reach out via LinkedIn to [@james-oleinik](https://www.linkedin.com/in/james-oleinik/)

I'll acknowledge receipt within a few business days and work with you on a fix and disclosure timeline.

## Scope

In-scope:
- Hardcoded secrets, credentials, or environment-specific identifiers in committed code
- Authentication/authorization mistakes in the sample agents or scripts
- Insecure defaults that could mislead someone copying patterns from this repo

Out-of-scope:
- Issues in upstream Microsoft products (Dataverse, Power Platform, Copilot Studio, etc.) — please report those via [MSRC](https://msrc.microsoft.com/).
- Issues in third-party packages — report to those package maintainers.

## Sensitive data

This repository should never contain real tenant IDs, environment GUIDs, organization URLs, user emails, internal SharePoint links, or API keys. If you spot any, please report it.
