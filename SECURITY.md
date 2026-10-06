# Security Policy

Tinlance Agent OS is a security-sensitive agent control-plane project. Please report suspected vulnerabilities privately.

## Reporting

Preferred path: use GitHub's **private vulnerability reporting / Security Advisories** for this repository when available.

If private reporting is not enabled, contact the maintainer privately through the GitHub account **@LloydCoder** and do not open a public issue.

Do not include secrets, credentials, customer data, or unnecessary personal information in a report.

## What to include

Provide:

- affected version or commit;
- affected file or component;
- vulnerability class or suspected impact;
- reproducible steps or proof of concept;
- expected versus observed behavior;
- relevant logs with secrets removed;
- suggested mitigation, if known.

## Response expectations

- **Acknowledgement:** within 3 business days.
- **Initial triage:** within 7 business days.
- **Severity and remediation plan:** communicated after reproduction and impact assessment.
- **Disclosure:** coordinated with the reporter after a fix or mitigation is available.

These are target service levels, not a guarantee of a particular fix date.

## Scope

Examples of security-sensitive areas include:

- Agent Platform authority boundary;
- tenant/workspace isolation;
- memory classification and trust handling;
- local daemon access;
- filesystem/process execution;
- connector and remote-agent boundaries;
- release/update verification;
- CI/CD workflows and supply-chain controls;
- secrets or credential handling.

## Out of scope

Please do not report:

- unsupported deployment configurations without a security impact;
- vulnerabilities in third-party dependencies without evidence of impact to this project;
- general feature requests;
- public documentation mistakes without a security consequence.

## Coordinated disclosure

Please allow the maintainer reasonable time to reproduce, develop, test, and release a fix before public disclosure. GitHub Security Advisories can be used to coordinate a private fix and later publish the advisory.

## Security architecture

Agent OS intentionally does not authorize consequential actions. Agent Platform remains authoritative for identity, authorization, policy, approvals, budgets, governed execution, sandbox/tool authority, and authoritative evidence.

See [security/threat-model.md](security/threat-model.md) and [docs/SECURITY-CONTROLS.md](docs/SECURITY-CONTROLS.md).
