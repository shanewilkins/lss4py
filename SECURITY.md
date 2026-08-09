# Security Policy

## Supported versions

Before 1.0, security fixes are provided for the latest released version of LSS4PY.
Users should reproduce a report against the latest release or the current default
branch when practical. After 1.0, this section will be updated with an explicit
supported-version policy.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Report it privately
using either:

- [GitHub private vulnerability reporting](https://github.com/shanewilkins/lss4py/security/advisories/new); or
- email to [shane@wilkinsadvisors.com](mailto:shane@wilkinsadvisors.com) with
  `LSS4PY security` in the subject.

Include the affected version or commit, impact, reproduction steps or a minimal
example, and any known mitigations. Remove credentials, production data, personal
information, and other secrets from the report.

The maintainer will acknowledge the report as soon as practical, assess severity
and affected versions, coordinate a fix and release, and credit the reporter if
requested. Please allow reasonable time for remediation before public disclosure.

Ordinary numerical disagreements, documentation errors, and feature requests may
be reported through the public issue tracker. Report them privately when they could
enable code execution, unauthorized access or disclosure, dependency compromise,
denial of service, or intentional manipulation of analytical results.

## Scope

This policy covers LSS4PY source code, published packages, command-line behavior,
and project-controlled release infrastructure. Vulnerabilities in a third-party
dependency should also be reported to that dependency's maintainers; please notify
LSS4PY privately when the project is affected.
