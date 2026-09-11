# Security Policy

## Supported version

The actively maintained version is the current `main` branch and the latest tagged release.

## Reporting a vulnerability

Please do not open a public issue for vulnerabilities involving authentication, authorization, secrets, webhook validation, user data, or third-party credentials.

Report the issue privately to the repository owner through GitHub's private security reporting features when available. Include:

- affected component and version/commit
- clear reproduction steps
- expected and actual behavior
- security impact
- any suggested mitigation

Do not include real credentials, access tokens, customer data, or production database contents in reports.

## Security-sensitive areas

Changes touching the following areas require extra review and tests:

- JWT authentication and role checks
- password hashing and account bootstrap
- WhatsApp webhook signature validation
- agent conversation ownership and assignment
- feedback/conversation ownership validation
- external CRM/order webhook destinations
- database migrations and data retention
- environment-variable and secret handling

## Deployment requirements

Production deployments should use TLS, a strong random `JWT_SECRET_KEY`, managed PostgreSQL with backups, private secret storage, restricted network access, webhook signature verification, and trusted HTTPS integration endpoints. Never deploy the placeholder values from `.env.example`.