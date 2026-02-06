from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
import frappe

class CustomSalarySlip(SalarySlip):

    def on_submit(self):
        # 1️⃣ LOG DURO (para confirmar ejecución)
        frappe.logger().info(f"[SD_CUSTOM] on_submit Salary Slip {self.name}")

        # 2️⃣ TU LÓGICA (crear Employee Role Approval)
        self.create_employee_role_approval()

        # 3️⃣ SIEMPRE llamar al padre
        super().on_submit()

    def create_employee_role_approval(self):
        frappe.logger().info(f"[SD_CUSTOM] creando approval para {self.name}")

        doc = frappe.get_doc({
            "doctype": "Employee Role Approval",
            "employee": self.employee,
            "salary_slip": self.name,
            "status": "Pending"
        })
        doc.insert(ignore_permissions=True)
