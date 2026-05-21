Internal Transfers
==================

Move funds between **any combination of cash registers and bank accounts**
with a single, dedicated document. A balanced journal entry is created and
posted automatically on confirmation.

Supported scenarios
-------------------

- Cash → Bank : deposit cash takings into a bank account
- Bank → Cash : withdraw cash for petty-cash use
- Bank → Bank : transfer between two bank accounts
- Cash → Cash : move petty cash between two registers

Key features
------------

- Auto-sequence references ``INT/XXXXX``
- Journal dropdowns filtered in real time by transfer type
- One-click ``Confirm`` creates and posts the accounting entry
- Full lifecycle: Draft → Posted → Reset to Draft / Cancel
- Chatter tracking and activity scheduling on every record
- Smart button to the linked journal entry
- Multi-currency and multi-company ready
- Three-tier security: Administrator / Accountant / Read-only

Accounting entry
----------------

A single balanced entry is posted in the source journal::

    CR  source-journal default account      (money leaves)
    DR  destination-journal default account (money arrives)

Technical
---------

- Model       : ``account.internal.transfer``
- Depends     : ``account``, ``mail``
- Inherits    : ``mail.thread``, ``mail.activity.mixin``
- License     : LGPL-3
- Odoo        : 19 Community & Enterprise
