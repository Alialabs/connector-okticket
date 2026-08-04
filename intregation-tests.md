# **Integration Test Plan: Odoo - Okticket**

## **Objective**
Validate the synchronization and integration between Odoo and Okticket, ensuring data consistency, correct analytical distribution of expenses, and accurate status updates.

---

## **Test Cases**

### **1. Synchronize Odoo Employees with Okticket Users**
- **Test ID:** INT-001
- **Description:** Ensure that employees in Odoo are correctly synchronized as users in Okticket.
- **Preconditions:** At least one employee must exist in Odoo with an email matching Okticket.
- **Steps:**
  1. Trigger the synchronization process manually.
  2. Check if all users in Okticket exist in Odoo (created and updated)
  3. Verify employee bindings.
- **Expected Result:** Users from Okticket should appear in Odoo as employees with the correct details.

---

### **2. Synchronize Products**
- **Test ID:** INT-002
- **Description:** Ensure that categories in Okticket are correctly synchronized as Products with Odoo.
- **Preconditions:** Categories must be defined in Okticket
- **Steps:**
  1. Run the product synchronization process.
  2. Validate that products exist in Odoo.
  3. Check if products has been created in odoo.
- **Expected Result:** All categories in Okticket should be available in Odoo as Products with the correct data.

---

### **3. Create a Project in Odoo and Sync it as an Analytic Account in Okticket**
- **Test ID:** INT-003
- **Description:** Ensure that when a project is created in Odoo, the corresponding analytic account is created in Okticket as a cost center.
- **Preconditions:**Create Costs Center Automatically must be enabled in Company. Projects must have a company assigned selecting a client
- **Steps:**
  1. Create a new project in Odoo and assign company.
  2. Verify that an analytic account is automatically created in Odoo for the project.
  3. Check if the analytic account is synchronized with Okticket as a cost center.
  4. Validate that the cost center in Okticket reflects the correct project name and details.
- **Expected Result:** A new cost center is created in Okticket corresponding to the Odoo project’s analytic account.

---

### **4. Obtain Expenses from Okticket and Validate Data**
- **Test ID:** INT-004
- **Description:** Ensure that expenses from Okticket are retrieved and validated before being recorded in Odoo.
- **Preconditions:** Users have recorded expenses in Okticket.
- **Steps:**
  1. Trigger the expense retrieval process from Okticket.
  2. Validate that the data structure (amount, date, category, user) is correct.
  3. Check if analytical accounts and analytic distribution rules apply correctly.
- **Expected Result:** Expenses should be imported into Odoo with correct values and assigned to the correct analytical accounts.

---

### **5. Create Expense Sheets with Grouping Methods**
- **Test ID:** INT-005
- **Description:** Ensure that expenses are grouped correctly when creating an expense sheet in Odoo.
- **Preconditions:** INT-004
- **Steps:**
  1. Check if expenses are grouped based on predefined methods (e.g., standard, analytic, individual, period).
  2. Validate the total amounts and breakdowns.
- **Expected Result:** An expense sheet is created with correctly grouped expenses.

---

### **6. Send Expense Sheet Status to Okticket**
- **Test ID:** INT-006
- **Description:** Ensure that the status of an expense sheet in Odoo is correctly updated in Okticket.
- **Preconditions:** A validated expense sheet exists in Odoo.
- **Steps:**
  1. Approve or reject an expense sheet in Odoo.
  2. Verify that the status update is sent to Okticket.
  3. Check if Okticket reflects the correct expense sheet status.
- **Expected Result:** The status of the expense sheet in Odoo is mirrored in Okticket in real-time.
- **Note (19.0):** expense sheets do not exist in Odoo 19; the sheet modules are not part of the 19.0 connector, so imported expenses stay as individual draft expenses.
---

### **7. Import Invoice-type Expenses (Facturas / PDFs sent to the robot)**
- **Test ID:** INT-007
- **Description:** Ensure expenses classified in OkTicket as *Factura* (`type_id = 1`) are imported with their `-Invoiceable` product instead of being silently discarded for a missing `product_id`.
- **Root cause fixed:** `_search_okticket_categ_prod_id` returns base + `invoice_prod_id`; the non-working `store=True` attempt was removed so the search method is actually used.
- **Result (19.0, 2026-07-29):** OK — 7 invoice expenses imported.

### **8. Import the PDF document into the expense chatter**
- **Test ID:** INT-008
- **Description:** The actual PDF (`signed_pdf_url`) is attached to the hr.expense chatter (alongside the ticket image), idempotently.
- **Result (19.0, 2026-07-29):** OK — 5 PDFs attached to expense chatters; PDF renders in the attachment preview.

### **9. Robustness against missing optional fields**
- **Test ID:** INT-009
- **Description:** Importer does not crash when expenses omit optional fields (`comments`, `status_id`, `amount`, `type_id`, `company_id`); the mapper uses `record.get(...)`.
- **Result (19.0, 2026-07-29):** OK — 0 error/warning log events over a full import.

### **10. Multi-company: employee/account company scoping**
- **Test ID:** INT-010
- **Description:** `employee_id` and cost-center/account lookups are scoped by the expense company to avoid cross-company mismatches.

### **11. Full clean-DB import run**
- **Test ID:** INT-011
- **Description:** From a freshly reset DB, configure the backend via UI and run the three scheduled actions (Users → Products → Expenses) through the UI.
- **Result (19.0, 2026-07-29):** OK — 44 expenses (28 tickets, 7 invoices, 9 kilometres), 0 errors, PDFs in chatter.
---

## **Final Validation**
- Perform a full integration run and verify that all synchronized data remains consistent.
- Validate logging and error handling mechanisms in case of failed synchronizations.

