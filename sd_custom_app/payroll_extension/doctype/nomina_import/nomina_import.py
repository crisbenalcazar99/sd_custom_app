# Copyright (c) 2024, Tu Empresa and contributors
# License: MIT. See LICENSE

import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
# Importamos la clase obrera desde el otro archivo
from sd_custom_app.payroll_extension.doctype.nomina_import.nomina_importer import NominaImporter

class NominaImport(Document):
    def validate(self):
        if not (self.import_file):
            frappe.throw("Por favor adjunta el archivo a procesar.")

    @frappe.whitelist()
    def start_import(self):
        """Método llamado desde el botón JS. Encola el trabajo en Redis."""
        # Validamos que no se ejecute dos veces
        if self.status == "In Progress":
            frappe.throw("La importación ya está en progreso.")

        # Encolamos la tarea (igual que data_import.py)
        enqueue(
            method=start_import_job,
            queue="default",
            timeout=3000, # 50 minutos timeout
            event="nomina_import",
            job_id=f"nomina_import::{self.name}",
            nomina_import_name=self.name,
            now=frappe.flags.in_test # Para tests corre inmediato
        )

def start_import_job(nomina_import_name):
    """Esta función corre en el 'Worker' de fondo, no en el navegador del usuario."""
    doc = frappe.get_doc("Nomina Import", nomina_import_name)
    
    try:
        # 1. Actualizamos estado a "En Progreso"
        doc.db_set("status", "In Progress")
        frappe.publish_realtime("data_import_progress", {
            "progress": 0, 
            "message": "Iniciando lectura del archivo...",
            "data_import": doc.name
        })

        # 2. Instanciamos al "Obrero" (Importer) y le decimos ¡Trabaja!
        importer = NominaImporter(doc)
        importer.run()

        # 3. Si todo sale bien
        doc.db_set("status", "Success")

    except Exception as e:
        # 4. Manejo de catástrofes
        frappe.db.rollback()
        doc.db_set("status", "Error")
        doc.log_error("Error en Nomina Import") # Guarda traceback en Error Log
        
        # Notificar al usuario del error
        frappe.publish_realtime("data_import_progress", {
            "progress": 0, 
            "error": True,
            "message": f"Error Crítico: {str(e)}",
            "data_import": doc.name
        })
    finally:
        # Siempre avisar que terminó (bien o mal) para refrescar la pantalla
        frappe.publish_realtime("data_import_refresh", {"data_import": doc.name})
