================
Deferred Revenue
================

.. |badge1| image:: https://img.shields.io/badge/maturity-Production%2FStable-green.png
.. |badge2| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
.. |badge3| image:: https://img.shields.io/badge/Odoo-19.0-blueviolet

|badge1| |badge2| |badge3|

Manage deferred revenue (unearned income) and automate recognition in Odoo Accounting.

When a company receives payment before delivering a service or product (e.g. annual subscriptions,
advance rent), the income cannot be recognised immediately. This module automates the recognition
schedule so revenue is spread correctly over the earned period.

**Table of Contents**

.. contents::
   :local:

Features
--------

- **Reusable Templates** — Define journal, deferred revenue account, and recognition account once; apply to multiple records instantly.
- **Invoice Linking** — Attach a deferred revenue record to a specific customer invoice line for full traceability.
- **Automatic Monthly Schedule** — Confirm a record to generate recognition lines using calendar-day pro-rata proration for partial months.
- **Manual or Automated Posting** — Post recognition journal entries manually per line, or let the daily cron handle it automatically.
- **Real-Time Progress** — Recognised Amount and Remaining Amount update live as journal entries are posted.
- **Chatter & Audit Trail** — State changes and scheduled postings are logged with timestamps in the record's chatter.
- **Arabic Localisation** — Ships with Arabic (ar_001) translations.

Workflow
--------

1. *(Optional)* Create a **Template** under *Accounting → Deferred Revenue → Templates* with the default journal, deferred account, and recognition account.
2. Create a new **Deferred Revenue** record. Enter the total amount, start date, and end date.
3. Link it to a customer invoice line (optional but recommended for audit purposes).
4. Apply a template or configure the accounts manually.
5. Click **Confirm** — monthly recognition lines are generated automatically with pro-rata amounts.
6. A daily scheduled action posts lines whose date has arrived; alternatively post them manually.
7. Click **Close** when all revenue has been recognised.

Configuration
-------------

No additional configuration is required beyond a standard Odoo Accounting installation.

Installation
------------

This module depends on:

- ``account`` (Odoo Accounting)
- ``mail`` (Discuss / Chatter)

Both are standard Odoo modules included in every Odoo 19 instance.

Known Limitations
-----------------

- Recognition lines are split by calendar month. The amount for each month is proportional to the
  number of days in the service period that fall within that month.
- The last recognition line absorbs any rounding difference to ensure the total always matches
  exactly.

Bug Tracker
-----------

Bugs and feature requests can be submitted through your support channel or directly to the author.

Authors
-------

* muknon

Contributors
------------

* muknon

Maintainers
-----------

* muknon

This module is maintained by **muknon**.
