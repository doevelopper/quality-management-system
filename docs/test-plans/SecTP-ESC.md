# Security Test Plan - ESC Project

> Document: SecTP-ESC.md

## Guidelines
- ID format: `SecTP-ESC-nnnn-v [SecRS-ESC-Type-nnnn-v]`

## Test Plans

### SecTP-ESC-0001-1 [SecRS-ESC-M-0001-1]
- Objective: Validate mutual TLS enforcement and certificate validation on management interfaces.
- Environment: ESC board, CA-signed certs, invalid/self-signed certs, packet capture.
- Test Cases:
	- 0001: Connect with invalid client certificate (expect failure).
	- 0002: Connect with revoked certificate (expect failure; CRL/OCSP checked if applicable).
	- 0003: Connect with valid certificate chain (expect success; protocol TLS 1.3 negotiated).
- Pass/Fail Criteria: Only valid client certificates accepted; TLS 1.3 enforced.
