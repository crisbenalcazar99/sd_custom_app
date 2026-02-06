# nomina_custom/nomina_custom/utils.py
import frappe

def crear_confirmacion(doc, method):
    # Verificar que no exista ya una confirmación para evitar duplicados
    exists = frappe.db.exists("Salary Slip Confirmation", {"salary_slip": doc.name})
    if exists:
        return

    new_doc = frappe.new_doc("Salary Slip Confirmation")
    new_doc.employee = doc.employee
    new_doc.salary_slip = doc.name
    new_doc.status = "Pendiente"
    # Copiamos datos útiles para no tener que consultar el Salary Slip a cada rato
    new_doc.total_pay = doc.rounded_total 
    new_doc.insert(ignore_permissions=True)
