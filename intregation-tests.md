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
- **Preconditions:** Odoo has projects configured with analytic accounts enabled.
- **Steps:**
  1. Create a new project in Odoo.
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
---

## **Final Validation**
- Perform a full integration run and verify that all synchronized data remains consistent.
- Validate logging and error handling mechanisms in case of failed synchronizations.

