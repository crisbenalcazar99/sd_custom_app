import frappe
from frappe.model.document import Document

class SalarySlipConfirmation(Document):
    
    @frappe.whitelist()
    def procesar_aceptacion(self, passwword=None):
        if not password:
            frappe.throw("Se requeire la Contrasena para el firmado")
        """
        Esta función se llama cuando el empleado da clic en Aceptar.
        """
        if self.status != "Pendiente":
            frappe.throw("Este rol ya ha sido procesado.")

        # 1. Ejecutar TU LÓGICA PERSONALIZADA
        self.ejecutar_logica_negocio()

        # 2. Actualizar estado
        self.status = "Aceptado"
        self.save(ignore_permissions=True)

        # 3. Notificar
        self.enviar_notificacion_correo()
        
        return "Aceptado correctamente"

    @frappe.whitelist()
    def procesar_rechazo(self, motivo):
        """
        Esta función se llama cuando el empleado da clic en Rechazar.
        """
        if self.status != "Pendiente":
            frappe.throw("Este rol ya ha sido procesado.")

        self.status = "Rechazado"
        self.feedback = motivo
        self.save(ignore_permissions=True)
        
        self.enviar_notificacion_correo()
        return "Rechazo enviado"

    def ejecutar_logica_negocio(self):
        """
        AQUÍ COLOCAS TU CÓDIGO PERSONALIZADO
        """
        # Ejemplo: Marcar un checkbox en el Employee, o llamar a una API externa
        # frappe.db.set_value("Employee", self.employee, "ultimo_rol_aceptado", self.salary_slip)
        frappe.logger().info(f"Lógica personalizada ejecutada para {self.employee}")
        pass

    def enviar_notificacion_correo(self):
        recipient = "bi@securitydata.net.ec"
        subject = f"Respuesta Rol: {self.employee} - {self.status}"
        
        message = f"""
            <p>El empleado {self.employee} ha marcado su rol {self.salary_slip} como <b>{self.status}</b>.</p>
        """
        
        if self.status == "Rechazado":
            message += f"<p>Motivo: {self.feedback}</p>"

        frappe.sendmail(recipients=[recipient], subject=subject, message=message)

    @frappe.whitelist()
    def get_print_preview(self):
        """
        Obtiene el HTML del Salary Slip asociado para mostrarlo en pantalla.
        """
        if not self.salary_slip:
            return "<div>No hay rol de pagos asociado.</div>"
            
        # IMPORTANTE: Cambia "Standard" por el nombre exacto de tu formato de impresión si usas uno personalizado
        html = frappe.get_print("Salary Slip", self.salary_slip, "Standard")
        return html
