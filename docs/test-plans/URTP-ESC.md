# User Requirements Test Plan - ESC Project

> Document: URTP-ESC.md

## Guidelines
- ID format: `URTP-ESC-nnnn-v [URS-ESC-Type-nnnn-v]`

## Test Plans

### URTP-ESC-0001-1 [URS-ESC-M-0001-1]
- Objective: Validate that configuration and telemetry use authenticated and encrypted channels.
- Environment: Test bench with ESC dev board, host PC, network proxy/sniffer.
- Test Cases:
	- 0001: Attempt connection without client certificate (expect failure).
	- 0002: Valid mTLS connection and telemetry exchange (expect success; packets encrypted).
- Pass/Fail Criteria: Unauthorized connections rejected; authorized connection succeeds; traffic is encrypted.
