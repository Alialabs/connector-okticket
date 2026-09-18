# Integration Test Plan: Odoo ↔ OkTicket

## Objective

Validate every feature of the OkTicket connector against a real OkTicket API,
starting from an empty database, and verify data consistency, correct analytic
distribution, correct taxes, document reception and status propagation.

## Scope

Modules covered:

| Module | Area |
|---|---|
| `okticket_connector` | backend, transport, expense import, logs, expense wizard |
| `okticket_connector_user_synchronization` | employees ↔ OkTicket users |
| `okticket_connector_product_synchronization` | categories → products, invoice/rebillable versions |
| `okticket_connector_cost_center` | analytic accounts ↔ cost centers |
| `okticket_connector_hr_expense_sheet` | expense sheet export, status workflow |
| `okticket_connector_hr_expense_sheet_grouping` | grouping methods and time intervals |
| `okticket_hr_timesheet_cost_center` | cost center creation from timesheet projects |
| `okticket_hr_expense_reporting` | expense / expense sheet QWeb reports |

## Conventions

- **ID**: `INT-<phase><nn>`. Phases run in order: a phase depends on the ones before it.
- **Status**: `PASS` / `FAIL` / `PENDING` / `N/A`. Record the date and the environment.
- **Verification**: every case states how to check the result — UI, connector log
  (*Connectors → OkTicket → Logs*) or SQL. SQL snippets are in the Appendix.
- **Reference environment**: database `okticket-multicompany`, backend against
  `api.okticket.es` (company `31965`, demo credentials). A second backend
  (company `62544`) exists for the multi-company phase.

### Mapping to the previous plan

| Previous | Now |
|---|---|
| INT-001 | INT-201 |
| INT-002 | INT-301 |
| INT-003 | INT-401 |
| INT-004 | INT-501 |
| INT-005 | INT-701 |
| INT-006 | INT-801 |
| INT-007 | INT-504 |
| INT-008 | INT-601 |
| INT-009 | INT-514 |
| INT-010 | INT-905 |
| INT-011 | INT-1101 |

---

## Phase 0 — Clean start

### INT-001 — Install from an empty database
- **Preconditions:** empty database, `repos.yaml` pointing at the connector branch.
- **Steps:**
  1. Install in order: `okticket_connector`, `okticket_connector_user_synchronization`,
     `okticket_connector_product_synchronization`, `okticket_connector_cost_center`,
     `okticket_connector_hr_expense_sheet`, `okticket_connector_hr_expense_sheet_grouping`.
  2. Optionally `okticket_hr_timesheet_cost_center` and `okticket_hr_expense_reporting`.
  3. Review the install log.
- **Expected:** no errors. The three scheduled actions (*Import Expenses*,
  *Product Synchronization*, *User Synchronization*) exist and are **inactive**.

### INT-002 — Minimum Odoo data (Spanish environment)
- **Context:** OkTicket is a Spanish product and reports Spanish VAT rates, so the
  environment has to be Spanish or the tax cases cannot pass.
- **Steps:**
  1. Set **Spain** as the country of every company under test.
  2. Install the **Spanish chart of accounts** (`l10n_es`) and apply the template
     to each company — `es_pymes` (PGCE PYMES) is what the reference environment
     uses; `es_full` works too.
  3. Check that purchase taxes exist for **0 %, 4 %, 10 % and 21 %** — they ship
     with the Spanish chart.
  4. Create at least one employee with `work_email`, and configure the expense
     journal.
- **Expected:** prerequisites in place. Without them phases 3 and 5 fail for
  configuration reasons, not connector reasons — and in particular INT-507 falls
  back to the product's tax for every expense, which reads like a connector defect
  but is not.
- **Verification:**
  ```sql
  SELECT c.id, c.name, co.code AS country, c.chart_template
  FROM res_company c
  JOIN res_partner p ON p.id = c.partner_id
  LEFT JOIN res_country co ON co.id = p.country_id ORDER BY c.id;
  ```

---

## Phase 1 — Configuration and connection

### INT-101 — Company OkTicket id
- **Steps:** set `okticket_company_id` on the company (*OkTicket Conf.* tab).
- **Expected:** value stored. Without it **every expense is discarded** for a
  missing `company_id`.

### INT-102 — Create the backend
- **Steps:** *Connectors → OkTicket → Backend → New*. Fill in Location,
  HTTP connection url, Base url, Image Base url, Oauth path, Operations path,
  User, Pass, Grant type, Oauth client id, Oauth secret, Scope, HTTPS, Version.
- **Expected:** record saved, company linked, `Okticket Company Id` shown.

### INT-103 — Authentication test
- **Steps:** press *Authentication test*.
- **Expected:** success message.
- **Known defect:** success is reported through a `UserError`, so the dialog title
  reads "Invalid operation". Cosmetic only.

### INT-104 — Invalid credentials
- **Steps:** change the password to a wrong one, press *Authentication test*, restore.
- **Expected:** explicit credentials error (401). Not a hang and not silence.

### INT-105 — Wrong host
- **Steps:** point `HTTP connection url` at an unresolvable host, test, restore.
- **Expected:** clear connection error, no worker left hanging.

---

## Phase 2 — Employees

### INT-201 — Import OkTicket users
- **Steps:** run *User Synchronization From OkTicket* manually.
- **Expected:** employees created/linked, one `okticket.hr.employee` binding per
  user, `okticket_user_id` populated, no errors in the log.

### INT-202 — Match an existing employee by email
- **Preconditions:** an Odoo employee whose `work_email` matches an OkTicket user.
- **Expected:** the existing employee is bound. **No duplicate is created.**

### INT-203 — Non-matching email
- **Steps:** sync a user whose email does not exist in Odoo.
- **Expected:** a new employee is created. Re-running does not duplicate it.

### INT-204 — Employee created in Odoo → OkTicket
- **Steps:** create an employee with `work_email`.
- **Expected:** the create listener triggers synchronisation.

### INT-205 — Company without a backend
- **Steps:** create an employee in a company that has no OkTicket backend.
- **Expected:** skipped with a warning, no traceback.

### INT-206 — Employee roles
- **Steps:** review the imported users against their OkTicket role
  (3 employee, 2 company admin, 6 team leader, 5 inactive).
- **Expected:** inactive users (role 5) do not break the import.

---

## Phase 3 — Categories → Products

### INT-301 — Import root categories
- **Steps:** run *Product Synchronization From OkTicket* manually.
- **Expected:** the 7 fixed categories (Otros, Restauración, Aparcamiento, Peaje,
  Transporte, Alojamiento, Gasolina) exist as products with
  `can_be_expensed = True` and `okticket_type_prod_id = 0`.

### INT-302 — Subcategories and company-specific categories
- **Expected:** children and company categories are imported too (Bus, VTC,
  Alquiler vehículo, Taxi, Tren, Avión, Otros Transportes, and any company ones).
- **Note:** this is the case that fails when the `company` header is sent on
  `/categories`; the API then returns only the 7 global roots.
- **Reference result:** 18 categories on company 31965.

### INT-303 — Invoice product versions
- **Expected:** each base product has its `-Invoiceable` version with
  `okticket_type_prod_id = 1`, linked through `invoice_prod_id`.

### INT-304 — Rebillable product versions
- **Expected:** `-Rebillable` versions created and linked through `rebillable_prod_id`.

### INT-305 — Company of the company-dependent links ⚠ critical
- **Steps:** check `ir_property` for `invoice_prod_id` / `rebillable_prod_id`.
- **Expected:** written under **the backend's company**, not the scheduler user's.
- **Why it matters:** both fields are `company_dependent`. If the sync runs without
  the company context the links land under another company, the expense importer
  looks them up under the backend's company, finds nothing, and **every invoice
  expense is silently discarded**.

### INT-306 — Accounting configuration of the products
- **Steps:** set the expense account and taxes on the synced products.
- **Expected:** imported expenses inherit the right account. The account comes
  from Odoo's product configuration, not from the connector.

### INT-307 — Re-run the product sync
- **Expected:** no duplicate products, bindings unchanged, `-Invoiceable` /
  `-Rebillable` versions reused rather than recreated.

---

## Phase 4 — Cost centers

### INT-401 — Project → cost center
- **Preconditions:** `create_cost_center_automatically` enabled on the company.
- **Steps:** create a project with an analytic account.
- **Expected:** the cost center appears in OkTicket and the binding is created.

### INT-402 — Duplicate control
- **Steps:** create an analytic account whose name already exists as a cost center.
- **Expected:** the confirmation wizard appears. Selecting several analytic accounts
  at once raises `ValidationError` asking to process them one at a time.

### INT-403 — Confirm a duplicate
- **Steps:** in the wizard tick *Confirm Duplicate* and continue.
- **Expected:** the duplicated cost center is created. Leaving the box unticked
  raises a `ValidationError` explaining the choice.

### INT-404 — Rename the analytic account
- **Expected:** the new name propagates to OkTicket.

### INT-405 — Archive / unarchive
- **Expected:** the cost center active state changes in OkTicket.

### INT-406 — Delete the analytic account
- **Expected:** the cost center and the binding are removed.

### INT-407 — Company without a backend
- **Expected:** the operation is skipped with a warning, no exception.

### INT-408 — Cost center from a timesheet project
- **Preconditions:** `okticket_hr_timesheet_cost_center` installed.
- **Expected:** the create listener also fires for timesheet projects.

### INT-409 — Global vs per-user cost centers
- **Steps:** review the `global` flag of the created cost centers.
- **Expected:** a non-global cost center has to be assigned to users before they
  can charge expenses to it.

---

## Phase 5 — Expense import

### INT-501 — Full import
- **Steps:** run *Import Expenses From OkTicket* manually.
- **Expected:** the number imported equals `meta.total` returned by the API for the
  filter `accounted=false&statuses=0,1,2`. One binding per expense, no orphans.
- **Reference result:** 44/44 on company 31965.

### INT-502 — Pagination beyond the first page
- **Preconditions:** more expenses than `per_page` (20 by default).
- **Expected:** every page is fetched **and the search filter is preserved on all
  of them**.
- **Trap:** `links.next` arrives as a bare `?page=2` and drops the search
  parameters; they must be re-appended or pages 2+ come back unfiltered.

### INT-503 — Ticket (`type_id = 0`)
- **Expected:** product resolved by `okticket_type_prod_id = 0` + `category_id`.

### INT-504 — Invoice (`type_id = 1`) ⚠ critical
- **Expected:** resolves the `-Invoiceable` product and sets `is_invoice = True`.
  None discarded for a missing `product_id`.
- **Reference result:** 7 imported. Zero before the INT-305 fix.

### INT-505 — Mileage (`type_id = 2`)
- **Expected:** imported; `category_id` is always 0; `distance` and `unit_price`
  present.
- **Open question:** mileage should normally carry no VAT. Confirm the expected
  tax with the customer — on the demo company all 9 received the product's 21 %.

### INT-506 — Per diem (`type_id = 4`) ⚠ not implemented
- **Context:** the data model documents type 4 (Dieta) with the diet type in
  `category_id`, but the connector only special-cases 0 and 1 and **no product
  carries `okticket_type_prod_id = 4`**.
- **Expected:** either imported, or skipped with an explicit warning. Verify the
  current behaviour and decide.

### INT-507 — Receipt taxes, single rate
- **Expected:** the rate OkTicket reports in `taxes` is applied, for **every**
  expense type.
- **Trap:** OkTicket sends an entry for every rate it knows and zeroes the base of
  the unused ones — e.g. `[{p:0,b:0},{p:4,b:0},{p:10,b:0},{p:21,b:14.88}]`. Only
  entries with `b > 0` describe the receipt.
- **Reference result:** 27 of 44 matched the receipt (17 of them at 10 %, which
  previously received the product's 21 %).

### INT-508 — Receipt taxes, rate missing in Odoo
- **Steps:** archive the Odoo purchase tax for a rate OkTicket reports.
- **Expected:** falls back to the product's supplier taxes.

### INT-509 — Multi-rate receipt
- **Preconditions:** an expense with more than one base, e.g. 10 % + 4 %.
- **Expected:** warning in the connector log and the product's taxes kept, because
  `hr.expense` holds a single taxable base.
- **Reference result:** 2 expenses on the demo company.

### INT-510 — Tax inclusion
- **Expected:** `total_amount` is the gross figure and Odoo extracts the base
  (`hr.expense` computes taxes with `force_price_include`). Check
  `untaxed_amount` + `tax_amount` = `total_amount`.

### INT-511 — Cost center and analytic distribution
- **Preconditions:** INT-401, and expenses carrying `cost_center_id`.
- **Expected:** `analytic_account_id` set, `analytic_distribution` 100 %, and
  `sale_order_id` filled when the analytic account has a related sale order.

### INT-512 — Ledger account
- **Expected:** the project's default account wins; otherwise the product's
  expense account.

### INT-513 — Payment method and mode
- **Expected:** `payment_method` mapped (efectivo, tarjeta, tarjeta-gas, cheque,
  transferencia, paypal, na). `payment_mode` = `own_account` for cash, and driven
  by `custom_fields.refundable` (`payed` → `company_account`).

### INT-514 — Missing optional fields
- **Steps:** import a set that includes expenses without `comments`, `status_id`,
  `type_id` or `company_id`.
- **Expected:** no `KeyError`, and no record dropped for a missing optional field.

### INT-515 — Missing required fields
- **Steps:** import an expense whose employee is not synced, or whose category has
  no product.
- **Expected:** **that** expense is skipped with a warning; the rest continue.

### INT-516 — Missing amount
- **Expected:** skipped with a warning. **No 0.00 expense reaches accounting.**

### INT-517 — Rebillable expense
- **Preconditions:** an expense with `custom_fields.refacturable = 1`.
- **Expected:** resolves the `-Rebillable` product version.

### INT-518 — Date filter
- **Steps:** untick *Ignore "Import Expenses since"* and set a date.
- **Expected:** only expenses updated after it are fetched (`updated_after`), and
  **existing drafts are not deleted**.

### INT-519 — Destructive pre-delete ⚠ risk
- **Steps:** tick *Ignore "Import Expenses since"* and import.
- **Expected:** draft expenses carrying `okticket_expense_id` are deleted and
  re-imported. Verify that if the import then fails the transaction rolls back and
  **nothing is lost**.

### INT-520 — Reviewed only
- **Steps:** tick *Import Only Reviewed Expenses*.
- **Expected:** only expenses carrying `review` are imported.

### INT-521 — Expense deleted in OkTicket ⚠ known defect
- **Preconditions:** an expense with `deleted_at` set.
- **Expected:** the deletion is reflected in Odoo.
- **Current behaviour:** calls `delete_expense_synchro()`, which **does not
  exist** → `AttributeError` caught per expense. Needs implementing.

### INT-522 — Foreign currency ⚠ not implemented
- **Preconditions:** a company with multi-currency enabled and an expense whose
  `currency` is not EUR (`rate`, `rate_amount` present).
- **Expected:** the original currency and rate are reflected in Odoo.
- **Current behaviour:** the connector **never reads** `currency`, `rate` or
  `rate_amount`, and never assigns `currency_id`, so it falls back to the company
  currency: the amount in the receipt's currency is booked as if it were euros.
- **Reproducible case** (demo company 31965, 1 of 1329 expenses):
  `678fd2098edf9996de0ef9f6`, 2025-01-04. The API sends `amount=59.82 currency=USD
  rate=1.031349 rate_amount=61.7 rate_datetime=2025-01-03 rate_source='Fixer Api'`
  and `taxes=[{b: 54.38, p: 10}]` -- the tax base is in the receipt's currency too.
  Odoo stores 59.82 EUR instead of the 61.70 EUR the API already computed (1.88 EUR
  short, 3.05 %), and the VAT follows: base 54.38 / tax 5.44 where it should be
  56.09 / 5.61. INT-510 still passes because the three figures agree with each other.
- **Note for the fix:** the five fields are already requested -- they are in
  `EXPENSE_LIST_FIELDS` -- so no change to the request is needed. Setting
  `currency_id` alone is not enough: with no `res.currency.rate` loaded Odoo converts
  at 1.0 and the amount stays wrong. Either write `total_amount_currency =
  rate_amount` and scale the tax base by `rate` (a few lines in the `amount` mapper),
  or set `currency_id` and create the day's `res.currency.rate` from `rate` -- mind
  the direction, OkTicket sends EUR per USD (1.031349) and Odoo stores the inverse
  (0.96961).
- **Deferred** to a later iteration on 2026-09-09, to keep it out of the release
  carrying the 403 / 500 / report-deletion defences.

### INT-523 — Validation group (`department_id`)
- **Expected:** decide whether the OkTicket validation group has to reach Odoo.
- **Current behaviour:** `department_id` is not read at all.

---

## Phase 6 — Receipt and document reception

### INT-601 — PDF into the expense chatter
- **Preconditions:** an expense whose OkTicket record exposes `signed_pdf_url`
  (typically invoices forwarded to the robot).
- **Steps:** import, open the expense form, inspect the chatter.
- **Expected:** a chatter message *"OkTicket PDF document imported"* with the PDF
  attached as `<ticket_num>.pdf`, and the PDF renders in the attachment preview.
- **Reference result:** 5 PDFs on the demo company.

### INT-602 — PDF idempotency
- **Steps:** run the import twice.
- **Expected:** the attachment is **not** duplicated (matched by filename).

### INT-603 — Expense without `signed_pdf_url`
- **Expected:** no attachment, no warning noise, import unaffected.
- **Note:** the field is not in the published data model (v1.5) but the API does
  return it — 13 of 62 records on the demo company. Confirm with OkTicket that it
  is a supported field before relying on it.

### INT-604 — Unreachable or expired PDF URL
- **Steps:** point `signed_pdf_url` at an unreachable host (or let a pre-signed URL
  expire).
- **Expected:** warning logged, the expense still imports, and **the rest of the
  import is unaffected** (the download runs outside the expense savepoint and has
  a timeout).

### INT-605 — JPG preview into `okticket_img`
- **Expected:** `remote_uri` is downloaded into `okticket_img` and shown on the
  expense form.

### INT-606 — Unreachable image host
- **Steps:** make `Image Base url` unresolvable.
- **Expected:** warning logged and the import completes. It must **not** hang, and
  an HTML error page must **not** be stored as if it were the receipt image.

### INT-607 — Robot flow end to end
- **Steps:** send an invoice PDF to the OkTicket robot mailbox, let OkTicket
  process it, then import.
- **Expected:** the expense arrives as `type_id = 1`, resolves its `-Invoiceable`
  product, and the PDF ends up in the chatter. This is the customer-facing case
  behind the "PDFs cannot be used" complaint.

### INT-608 — Attachment as the expense main document
- **Expected:** review whether the imported PDF should become
  `message_main_attachment_id` so it shows in the expense preview pane.

---

## Phase 7 — Expense sheet grouping

Repeat the import for each combination of `expense_sheet_grouping_method` ×
`expense_sheet_grouping_time` configured on the company.

### INT-701 — `analytic` grouping
- **Expected:** grouped by employee + payment mode + cost center. Name pattern
  `Employee | COST CENTER | Mode`. Expenses without a cost center group under
  "NO COST CENTER".

### INT-702 — `standard` grouping
- **Expected:** grouped by employee + payment mode (Odoo standard).

### INT-703 — `single_expense` grouping
- **Expected:** **one sheet per expense** (the expense name is part of the
  grouping key).

### INT-704 — `no_grouping`
- **Expected:** no sheet is created; expenses stay unassigned.

### INT-705 — `monthly` interval
- **Expected:** name prefixed `MOnn YYYY`, and `init_date` / `end_date` covering
  the month.

### INT-706 — `biweekly` interval
- **Expected:** name prefixed `BI d-d Month YYYY`, split on the company's
  `month_day_limit`.

### INT-707 — `weekly` interval
- **Expected:** name prefixed `WKnn YYYY`, Monday–Sunday range.

### INT-708 — Sheet export to OkTicket
- **Expected:** `POST /api/reports` with `name`, `user_id`, `company_id`; binding
  created; expenses attached with `PATCH /api/expenses/{id}` carrying `report_id`.

### INT-709 — Duplicated sheet name ⚠ critical
- **Preconditions:** a sheet whose name already exists in OkTicket.
- **Expected:** 422 logged as a warning, the exporter retries with a suffixed name
  (` | 1`, ` | 2`, …) and the sheet is created. **The import must not abort.**
- **Why it matters:** a single conflicting name used to propagate and roll the
  whole import back — the observed effect was zero expenses imported.
- **Reference result:** 19 conflicts, all resolved, 44 expenses kept.

### INT-710 — Name exhaustion
- **Steps:** force more than 20 conflicting names.
- **Expected:** falls back to a timestamped name; the failure path is logged rather
  than silent.

### INT-711 — Employee without `okticket_user_id`
- **Expected:** the sheet is not synced and a warning is logged.

### INT-712 — Sheet becomes empty
- **Steps:** remove every expense from a sheet.
- **Expected:** the sheet is deleted (`check_empty_sheet`).

### INT-713 — Expense in OkTicket but not in Odoo
- **Expected:** it is detached from the sheet (`report_id: ""`).

### INT-714 — One bad sheet does not stop the batch
- **Steps:** force a failure on one sheet (e.g. unreachable API mid-run).
- **Expected:** that sheet is logged as an error, the remaining sheets and every
  imported expense survive.

---

## Phase 8 — Expense sheet status workflow

For each transition check the OkTicket report status **and** the `accounted` flag
of the expenses.

### INT-801 — Submit to manager
- **Expected:** OkTicket action 347; expenses set to `accounted = true`.

### INT-802 — Approve
- **Expected:** action 349.

### INT-803 — Post journal entries
- **Expected:** action 351, plus 353 when `payment_mode = company_account`.

### INT-804 — Register payment
- **Expected:** action 353.

### INT-805 — Refuse
- **Expected:** action 350 from submitted, 352 from approved; expenses set back to
  `accounted = false`.

### INT-806 — Reset to draft
- **Expected:** action 348 from submitted, 354 from refused. From approved, the
  connector forces 352 then 354.

### INT-807 — Invalid transition ⚠ divergence risk
- **Context:** the documented OkTicket statuses are 0–5, but
  `_STATUS_TRANSITIONS` uses 0, 3, 5, **34, 35, 36**. Statuses 1, 2 and 4 have
  **no transition defined**.
- **Expected:** review against the customer's actual workflow. Today an
  undefined transition only logs a warning and Odoo/OkTicket diverge silently.

### INT-808 — Delete the sheet
- **Expected:** the report is deleted in OkTicket and the binding removed.

### INT-809 — Delete a non-draft expense
- **Expected:** `UserError` — deleting expenses outside draft is not allowed.

### INT-810 — Expense wizard: accounted state
- **Steps:** select expenses, run the OkTicket expense wizard, set the accounted flag.
- **Expected:** `accounted` is pushed to OkTicket for each selected expense.

### INT-811 — Expense wizard: default account
- **Steps:** run *assign default expense account* on a selection.
- **Expected:** `account_id` is taken from the product's expense account.

---

## Phase 9 — Multi-company

### INT-901 — Two backends, two companies
- **Preconditions:** two companies, each with its `okticket_company_id` and an
  active backend.
- **Expected:** each backend imports **only** its own expenses; neither writes
  records into the other company.

### INT-902 — Isolation of company-dependent links
- **Expected:** `invoice_prod_id` / `rebillable_prod_id` have one entry per company
  in `ir_property`.

### INT-903 — Shared API credentials ⚠ residual risk
- **Context:** with both backends using the same API user, `/categories` without
  the `company` header returns the global categories **plus those of the
  authenticated company**.
- **Expected:** backend B must not adopt company A's categories.

### INT-904 — Product binding per backend
- **Expected:** the second backend does not rebind to itself the product templates
  already bound to the first.

### INT-905 — Same user, employee in both companies
- **Preconditions:** the same OkTicket user exists as an employee in both companies.
- **Expected:** each expense takes the employee of its own company; no
  "Incompatible companies" error. When the employee only exists in the parent
  company the lookup falls back to it instead of dropping the expense.

### INT-906 — Token revocation ⚠ risk
- **Context:** refreshing a token **revokes the previous one**.
- **Expected:** with two backends sharing credentials, one refreshing must not
  break the other's in-flight import.

### INT-907 — Cost centers per company
- **Expected:** a cost center is created against the company of its analytic
  account, not the active company in the session.

---

## Phase 10 — Resilience and error handling

### INT-1001 — Token expiry (401)
- **Steps:** force expiry mid-import (the token lasts 30 minutes).
- **Expected:** automatic re-login and the import continues. Bounded retries; the
  token endpoint itself is never retried.

### INT-1002 — Rate limit (429)
- **Steps:** exceed the documented per-minute call limit (`X-RateLimit-*`).
- **Expected:** the connector waits (honouring `Retry-After` when present) and
  retries. No silent data loss.

### INT-1003 — Server error (500)
- **Expected:** visible error in the connector log. Never swallowed.

### INT-1004 — Validation error (422)
- **Expected:** readable message combining `message` and `errors`, e.g.
  *"El valor ya está en uso (name: El valor ya está en uso.)"*.

### INT-1005 — Not found (404)
- **Expected:** logged as a warning and operations continue.

### INT-1006 — Successful delete (204)
- **Expected:** recorded as **success**, not as an error.

### INT-1007 — Network down
- **Steps:** stop the `proxy_okticket` container mid-import.
- **Expected:** clear error, no Odoo worker left hanging (connections have timeouts).

### INT-1008 — Per-record isolation
- **Expected:** a single bad expense or sheet never aborts the whole batch.

### INT-1009 — Search methods with no match
- **Steps:** search by a non-existent `okticket_expense_id`, `okticket_user_id`,
  `okticket_cost_center_id`, `okticket_expense_sheet_id` and category id.
- **Expected:** empty result. **No `IndexError: pop from empty list`** — a custom
  `search=` method must return a well-formed domain leaf, never an empty domain.

### INT-1010 — Connector log completeness
- **Steps:** review *Connectors → OkTicket → Logs* after a full run.
- **Expected:** every API call logged with status; warnings and errors carry an
  actionable message.

---

## Phase 11 — Idempotency and re-runs

### INT-1101 — Full clean-database run
- **Steps:** from a freshly reset database run the three scheduled actions in order
  (Users → Products → Expenses) entirely through the UI.
- **Expected:** users, products (including invoice and rebillable versions),
  tickets, mileage and invoices all import with no errors, and PDFs reach the chatter.

### INT-1102 — Two consecutive runs
- **Expected:** same totals, no duplicates (`hr.expense` count equals binding
  count), no repeated PDF attachments.

### INT-1103 — Expense left without a binding
- **Steps:** delete a binding while keeping the expense, then re-import.
- **Expected:** decide the intended behaviour. Detection is only by
  `(backend_id, external_id)`, so an orphaned expense can be re-created as a
  duplicate.

### INT-1104 — Modify in OkTicket and re-import
- **Expected:** the existing expense is updated, not duplicated.

### INT-1105 — Re-import after a partial failure
- **Steps:** interrupt an import (stop the API mid-run), then re-run.
- **Expected:** converges to the correct state with no duplicates.

---

## Phase 12 — Reports

### INT-1201 — Expense report
- **Preconditions:** `okticket_hr_expense_reporting` installed.
- **Expected:** the expense QWeb report prints with the OkTicket data.

### INT-1202 — Expense sheet report
- **Expected:** the expense sheet report prints, including the attached receipts.

---

## Phase 13 — Regression suite

Quick checks that must stay green after any change. Each maps to a defect found
and fixed.

| ID | Check | Case |
|---|---|---|
| INT-1301 | Product sync writes under the backend's company | INT-305 |
| INT-1302 | `type_id = 1` invoices are imported | INT-504 |
| INT-1303 | A duplicated sheet name does not abort the batch | INT-709 |
| INT-1304 | Pages 2+ keep the search filter | INT-502 |
| INT-1305 | Receipt tax applied for `type_id = 0` too | INT-507 |
| INT-1306 | `search=` methods never raise `IndexError` | INT-1009 |
| INT-1307 | PDF download runs outside the expense savepoint | INT-604 |
| INT-1308 | OkTicket comments reach `description` | INT-514 |
| INT-1309 | 204 is logged as success | INT-1006 |
| INT-1310 | 401 triggers a real re-login | INT-1001 |
| INT-1311 | 429 backs off and retries | INT-1002 |
| INT-1312 | Image download has a timeout | INT-606 |

---

## Appendix A — Verification queries

```sql
-- Totals after a full run
SELECT (SELECT count(*) FROM hr_expense)                  AS expenses,
       (SELECT count(*) FROM okticket_hr_expense)          AS expense_bindings,
       (SELECT count(*) FROM hr_expense_sheet)             AS sheets,
       (SELECT count(*) FROM okticket_hr_expense_sheet)    AS sheet_bindings,
       (SELECT count(*) FROM hr_expense WHERE is_invoice)  AS invoices,
       (SELECT count(*) FROM okticket_hr_employee)         AS employee_bindings,
       (SELECT count(*) FROM okticket_product_template)    AS product_bindings;

-- Log summary (0 errors expected)
SELECT type, count(*) FROM log_event GROUP BY type ORDER BY 1;

-- Warning detail
SELECT type, left(regexp_replace(content, '\s+', ' ', 'g'), 140), count(*)
FROM log_event WHERE type <> 'success' GROUP BY 1, 2 ORDER BY 3 DESC;

-- INT-305: which company holds the company-dependent links
SELECT f.name AS field, p.company_id, count(*)
FROM ir_property p JOIN ir_model_fields f ON f.id = p.fields_id
WHERE f.name IN ('invoice_prod_id', 'rebillable_prod_id')
GROUP BY 1, 2 ORDER BY 1, 2;

-- INT-507/509: reported tax vs applied tax
WITH d AS (
  SELECT e.id,
         (e.okticket_response::json->>'type_id')::int AS type_id,
         e.okticket_response::json->'taxes'           AS oktk_taxes,
         (SELECT string_agg(t.amount::numeric(5,2)::text, '+' ORDER BY t.amount)
            FROM expense_tax r JOIN account_tax t ON t.id = r.tax_id
           WHERE r.expense_id = e.id)                 AS odoo_tax
    FROM hr_expense e WHERE e.okticket_response <> ''
)
SELECT type_id,
       coalesce((SELECT string_agg((x->>'p'), '+' ORDER BY (x->>'p')::numeric)
                   FROM json_array_elements(oktk_taxes) x
                  WHERE (x->>'b')::numeric > 0), '(no base)') AS okticket_rates,
       odoo_tax, count(*)
FROM d GROUP BY 1, 2, 3 ORDER BY 1, 4 DESC;

-- INT-601: PDFs and chatter messages
SELECT (SELECT count(*) FROM ir_attachment
         WHERE res_model = 'hr.expense' AND mimetype = 'application/pdf') AS pdfs,
       (SELECT count(*) FROM mail_message
         WHERE model = 'hr.expense' AND body ILIKE '%PDF%')               AS pdf_messages;

-- INT-701..707: sheets, their OkTicket report and expense count
SELECT left(s.name, 60) AS sheet, b.external_id AS okticket_report,
       s.state, count(e.id) AS expenses
FROM hr_expense_sheet s
LEFT JOIN okticket_hr_expense_sheet b ON b.odoo_id = s.id
LEFT JOIN hr_expense e ON e.sheet_id = s.id
GROUP BY 1, 2, 3 ORDER BY 4 DESC;

-- Orphans: expenses with no sheet / no binding
SELECT (SELECT count(*) FROM hr_expense WHERE sheet_id IS NULL) AS without_sheet,
       (SELECT count(*) FROM hr_expense e
         WHERE NOT EXISTS (SELECT 1 FROM okticket_hr_expense b
                            WHERE b.odoo_id = e.id))            AS without_binding;

-- INT-302: imported categories, including subcategories
SELECT b.external_id, t.name->>'en_US' AS product, t.okticket_type_prod_id
FROM okticket_product_template b JOIN product_template t ON t.id = b.odoo_id
ORDER BY b.external_id::int;
```

## Appendix B — Reset between runs

Deleting expense data so a phase can be replayed. Reconciliations and journal
entries have to go first, and products are kept because other records reference
them.

```sql
BEGIN;
CREATE TEMP TABLE _mv AS SELECT DISTINCT move_id FROM account_move_line WHERE expense_id IS NOT NULL;
CREATE TEMP TABLE _ml AS SELECT id FROM account_move_line WHERE move_id IN (SELECT move_id FROM _mv);
DELETE FROM account_partial_reconcile
 WHERE credit_move_id IN (SELECT id FROM _ml) OR debit_move_id IN (SELECT id FROM _ml);
DELETE FROM account_full_reconcile WHERE id IN (
  SELECT full_reconcile_id FROM account_move_line
   WHERE id IN (SELECT id FROM _ml) AND full_reconcile_id IS NOT NULL);
DELETE FROM account_move_line WHERE move_id IN (SELECT move_id FROM _mv);
DELETE FROM account_move      WHERE id      IN (SELECT move_id FROM _mv);

DELETE FROM ir_attachment WHERE res_model = 'hr.expense';
DELETE FROM mail_message  WHERE model     = 'hr.expense';
DELETE FROM hr_expense;
DELETE FROM hr_expense_sheet;
DELETE FROM okticket_hr_expense;
DELETE FROM okticket_hr_expense_sheet;

-- Only when replaying phase 3: forces the company-dependent links to be rewritten
DELETE FROM okticket_product_template;
DELETE FROM ir_property WHERE fields_id IN (
  SELECT id FROM ir_model_fields WHERE name IN ('invoice_prod_id', 'rebillable_prod_id'));

DELETE FROM okticket_hr_employee;
DELETE FROM log_event;
UPDATE okticket_backend SET import_expenses_since = NULL;
COMMIT;
```

## Appendix C — Probing the API directly

Useful to tell a connector defect from an API behaviour. Run inside the Odoo
container with `odoo shell -d <db> --no-http`.

```python
backend = env['okticket.backend'].search([('active', '=', True)], limit=1)
with backend.work_on('okticket.backend') as work:
    adapter = work.component(usage='backend.adapter')
adapter._auth()
api = adapter.okticket_api

# Categories with and without the company header (INT-302)
api.find('/categories', https=backend.https, company_in_header=True)
api.find('/categories', https=backend.https, company_in_header=False)

# Raw expenses payload: links / meta / taxes / signed_pdf_url (INT-502, INT-507, INT-603)
url = api.get_full_path('/expenses')
header = {'Authorization': api.token_type + ' ' + api.access_token,
          'Accept': 'application/json', 'company': api.okticket_company_id}
raw = api.general_request(url, 'GET', {}, headers=header, only_data=False,
                          params={'accounted': 'false', 'statuses': '0,1,2'},
                          https=backend.https)
payload = raw['result']
sorted(payload)                 # data / links / meta / status
payload['meta']                 # current_page, last_page, per_page, total
payload['data'][0]['taxes']     # [{'p': rate, 'b': base}, ...]
```

## Appendix D — Coverage status

Last full run: **2026-09-18**, database `okticket-16-cierre2`, `api.okticket.es`
(production), both backends active — 31965 and 62544, `analytic` grouping with no
interval. 1120 expenses imported, reconciled against the API with nothing missing
(`in_api_not_in_odoo = 0`). Connector at `4cb67e3`, modules `16.0.1.4.0` /
`16.0.1.1.0` / `16.0.1.0.3`.

Run as: the skill's automated battery (install, prerequisites, backends, the three
synchronisations, `checks.sql` and `gap_check`), then the phases the battery cannot
assert, driven by hand on the same database, then the module's own unit tests.

| Phase | Cases | Exercised | Result |
|---|---|---|---|
| 0 Clean start | 2 | 2 | verde |
| 1 Configuration | 5 | 5 | verde |
| 2 Employees | 6 | 4 | verde; roles no se replican |
| 3 Categories/products | 7 | 7 | verde |
| 4 Cost centers | 9 | 9 | 8 verde, INT-403b falla |
| 5 Expense import | 23 | 16 | 13 verde, 3 fallan |
| 6 Documents | 8 | 5 | verde |
| 7 Grouping | 14 | 9 | verde |
| 8 Status workflow | 11 | 8 | verde |
| 9 Multi-company | 7 | 7 | verde |
| 10 Resilience | 10 | 7 | verde |
| 11 Idempotency | 5 | 2 | verde |
| 12 Reports | 2 | 2 | verde |
| **Total** | **121** | **83** | **79 verde, 4 fallan** |

Unit tests: 17, all green, on the same database.

### Lo que falla

- **INT-507** — 907 gastos de tipo único, 27 no coinciden. Ninguno lleva un impuesto
  equivocado: los 27 entran **sin impuesto y con aviso** porque su recibo declara un
  tipo que la normativa no admite para esa categoría (22 transportes al 21 %, un peaje
  al 10 %, un repostaje al 0 %, un aparcamiento al 5 %) o porque la categoría *Otros* no
  declara criterio (2). Son datos generados a propósito con errores.
- **INT-517** — 8 de 37 gastos refacturables no resuelven la versión *-Rebillable*: 7 son
  facturas, cuya versión refacturable no se crea, y uno es kilometraje. Defecto conocido.
- **INT-522** — divisa extranjera: un gasto en USD se contabiliza en euros. Sin implementar.
- **INT-403b** — confirmar la creación de un centro de coste duplicado ya no es posible:
  OkTicket responde 422 «El valor ya está en uso». El asistente quedó obsoleto frente a
  la API.

### Lo que no se ejercita aquí

INT-204/205/206 (alta de empleado hacia OkTicket), INT-506 (dietas, no hay en el
dataset), INT-508, INT-518/519/520 (filtros de importación), INT-521 (borrado en
OkTicket), INT-604/606/607/608 (fallos de descarga y flujo del robot), INT-709/710/711/
713/714 (conflictos de nombre de hoja), INT-807/808/810/811, INT-1002/1003 (el 429 y el
500 no se fuerzan a voluntad), INT-1103/1104/1105 y la fase 13.

Varias de ellas sí se validaron el 17 y el 18 de septiembre sobre otras bases
(`okticket-16-bateria` y el recorrido end to end por navegador en `okticket-16-e2e`),
donde además se comprobó la instalación y la configuración completas desde la interfaz.

### Defectos corregidos en esta versión

- El flujo de estados de la hoja no llegaba a OkTicket: las redefiniciones traían los
  nombres de método de 17.0 y en 16.0 no las llamaba nadie.
- Borrar dos proyectos a la vez levantaba *Expected singleton* y no borraba nada.
- Al modelo de mapeo de impuestos le faltaba la regla multicompañía.
- El IVA ya no se inventa: un recibo sin desglose, con varios tipos, con un tipo que su
  categoría no admite o con un tipo que el plan no tiene entra **sin impuesto** y con el
  motivo en el log, en lugar de quedarse con el impuesto por defecto del producto.
