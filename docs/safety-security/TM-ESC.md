# Threat Model - ESC Project

> Document: TM-ESC.md

## Context
- Assets
- Entry points

## Threats (STRIDE)
- Spoofing
- Tampering
- Repudiation
- Information Disclosure
- Denial of Service
- Elevation of Privilege

## Attack Trees

## Controls & References
- Links to SecRS and SRTM

---

### TM-ESC-0001: MITM on management/configuration channel
- Description: Attacker attempts to intercept or impersonate management communications.
- Affected Assets: Configuration interface, credentials, firmware settings
- Controls: Mutual TLS 1.3 with client authentication; strict certificate validation
- References: [SecRS-ESC-M-0001-1]
