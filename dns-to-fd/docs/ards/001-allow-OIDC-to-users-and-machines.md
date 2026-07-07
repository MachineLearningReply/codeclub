# ADR 001: Allow both Machines and Users as callers

## Status
Accepted

## Context
The APIs must be callable by any Azure EntraID Principal (User or Application)

## Decision
We will use OIDC via EntraID to validate tokens

## Consequences
Strong authentication and authorization with additional administrative overhead