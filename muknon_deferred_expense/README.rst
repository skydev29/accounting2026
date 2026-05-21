================
Deferred Expenses
================

.. |badge1| image:: https://img.shields.io/badge/maturity-Production%2FStable-green.png
.. |badge2| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
.. |badge3| image:: https://img.shields.io/badge/Odoo-19.0-blueviolet

|badge1| |badge2| |badge3|

Manage prepaid and deferred expenses with automatic amortisation schedules in Odoo Accounting.

When a company pays an expense upfront (e.g. annual insurance, prepaid rent, software licences),
the cost must be spread over the benefit period rather than recognised all at once.
This module automates that process end-to-end.

**Table of Contents**

.. contents::
   :local:

Features
--------

- **Reusable Templates** — Define journal, prepaid account, and expense account once; reuse across records.
- **Automatic Schedule Generation** — Confirm a record to instantly generate monthly recognition lines with pro-rata day-count proration for partial first/last months.
- **Invoice Linking** — Optionally attach a deferred expense directly to a vendor bill line for traceability.
- **Analytic Distribution** — Full support for analytic accounts on every recognition journal entry.
- **Daily Cron Automation** — A scheduled action posts due recognition entries automatically; no manual work needed.
- **Real-Time Tracking** — Recognised Amount and Remaining Amount are computed live from posted journal entries.
- **Chatter & Activity Log** — All state changes and automated postings are recorded in the chatter with full audit trail.
- **Arabic Localisation** — Ships with Arabic (ar_001) translations.

Workflow
--------

1. *(Optional)* Create a **Template** under *Accounting → Deferred Expenses → Templates* with the default journal and accounts.
2. Create a new **Deferred Expense** record, enter the total amount, start date, and end date.
3. Apply a template or set the journal/accounts manually.
4. Click **Confirm** — recognition lines are generated automatically.
5. Lines are posted daily by the cron job, or you can post them manually line by line.
6. Once all lines are posted, click **Close** to archive the record.

Configuration
-------------

No additional configuration is required beyond a standard Odoo Accounting installation.

To use analytic distribution, ensure the **Analytic Accounting** module (``analytic``) is installed
(it is a required dependency of this module).

Installation
------------

This module depends on:

- ``account`` (Odoo Accounting)
- ``analytic`` (Analytic Accounting)
- ``mail`` (Discuss / Chatter)

All three are standard Odoo modules included in every Odoo 19 instance.

Known Limitations
-----------------

- Recognition lines are generated in calendar months. Sub-monthly periods within a single month
  are treated as one line.
- Deleting a deferred expense record is only allowed while it is in **Draft** state.

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
