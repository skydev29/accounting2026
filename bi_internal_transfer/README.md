# bi_internal_transfer — Internal Transfers

Odoo 19 Community · Category: Accounting

## Purpose

Provides a standalone Internal Transfer document that moves funds between
any combination of cash-register and bank journals, creates the corresponding
balanced journal entry automatically, and tracks the full lifecycle in a
simple three-state workflow.

## Supported Scenarios

- Cash to Bank: source journal type=cash, destination journal type=bank
- Bank to Cash: source journal type=bank, destination journal type=cash
- Bank to Bank: source journal type=bank, destination journal type=bank
- Cash to Cash: source journal type=cash, destination journal type=cash

## Workflow

- Draft: transfer created, editable
- Confirm: validates journals and amount, posts a balanced journal entry (CR source, DR destination)
- Reset to Draft: voids the journal entry, returns to editable state
- Cancel: voids the journal entry, sets state to Cancelled (kept for audit)

## Reference Numbering

References are auto-generated via ir.sequence with prefix INT/ and
5-digit padding, for example INT/00001.

## Security

- Account Manager: full CRUD access
- Account User: read and write (no create or delete)
- Internal User: read-only

## Installation

    odoo-bin -i bi_internal_transfer --stop-after-init --no-http
