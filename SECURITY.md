# Security Policy

## Reporting a Vulnerability

Please do not open public GitHub issues for security-sensitive bugs.

Instead, report vulnerabilities privately by contacting the maintainer through GitHub security reporting if it is enabled for the repository, or by opening a private disclosure through the maintainer contact listed on GitHub.

When reporting, include:
- affected command or workflow
- reproduction steps
- expected vs actual behavior
- impact assessment
- any suggested mitigation

## Scope

Security reports are especially useful for issues involving:
- install and bootstrap scripts
- runtime/container control
- credential handling
- import/export flows
- agent-to-agent or user-directed delivery paths

## Disclosure Expectations

- We will try to acknowledge reports promptly.
- We may ask follow-up questions to reproduce and scope the issue.
- Please avoid public disclosure until a fix or mitigation is available.

## Supported Versions

Security fixes are currently evaluated on the latest tagged release and the latest `main` branch.