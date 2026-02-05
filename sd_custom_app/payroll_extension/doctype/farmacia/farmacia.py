import frappe
from frappe.model.document import Document
from frappe.utils import getdate, format_date, get_first_day, get_last_day
from bs4 import BeautifulSoup


class Farmacia(Document):

    # 1. Carga visual de datos (lo que ya tenías)
    def before_save(self):
        if self.archivo_reporte:
            self.cargar_datos_html()

    @frappe.whitelist()
    # 2. PROCESAMIENTO REAL (Al dar Submit/Validar)
    def iniciar_procesamiento(self):
        if not self.items_lectura:
            frappe.throw("No hay datos leídos en la tabla para procesar.")

        if not self.custom_componente_salarial:
            frappe.throw("Por favor selecciona el Componente Salarial (ej. Descuento Farmacia).")

        count_success = 0
        log_entries = []
        log_entries.append(f"<b>Iniciando proceso: {frappe.utils.now_datetime()}</b>")

        for row in self.items_lectura:
            try:
                # Paso A: Obtener el ID real del empleado basado en la cédula
                empleado_id = self.obtener_empleado(row.cedula)

                if not empleado_id:
                    log_entries.append(f"<span style='color:red'>✘ Cédula {row.cedula}:</span> Empleado no encontrado.")
                    continue

                    # Llamamos a tu lógica de creación
                self.crear_salario_adicional(empleado_id, row.monto)
                count_success += 1
                log_entries.append(f"<span style='color:green'>✔ Cédula {row.cedula}:</span> Procesado ({empleado_id})")

            except Exception as e:
                log_entries.append(f"<span style='color:orange'>⚠ Cédula {row.cedula}:</span> Error: {str(e)}")

        # Actualizar el log en el documento y guardar
        log_entries.append(f"<br><b>Total exitosos: {count_success}</b>")
        self.registro_log = "<br>".join(log_entries)
        self.save()  # Guardamos los cambios en el Doctype

        return True
    # --- Métodos de Ayuda ---

    def cargar_datos_html(self):
        self.set("items_lectura", [])
        file_doc = frappe.get_doc("File", {"file_url": self.archivo_reporte})
        content = file_doc.get_content()
        if isinstance(content, bytes): content = content.decode("utf-8")

        soup = BeautifulSoup(content, "html.parser")

        # Lógica de búsqueda de tabla (igual que antes)
        tablas = soup.find_all("table")
        tabla_datos = None
        for tabla in tablas:
            if "CÉDULA" in tabla.get_text() and "MES CONSUMO" in tabla.get_text():
                tabla_datos = tabla
                break

        if not tabla_datos: return

        for fila in tabla_datos.find_all("tr"):
            celdas = fila.find_all("td")
            texto_fila = fila.get_text(strip=True)
            if len(celdas) < 5 or "CÉDULA" in texto_fila or "TOTAL" in texto_fila: continue

            try:
                cedula = celdas[2].get_text(strip=True).replace("&nbsp;", "").strip()
                nombre = celdas[3].get_text(strip=True)
                valor_str = celdas[5].get_text(strip=True).replace(".", "").replace(",", ".")

                if cedula.isdigit() and float(valor_str) > 0:
                    self.append("items_lectura", {
                        "cedula": cedula,
                        "nombre_empleado": nombre,
                        "monto": float(valor_str)
                    })
            except:
                pass

    def obtener_empleado(self, cedula):
        # Busca empleado activo por cédula
        return frappe.db.get_value("Employee",
                                   {"custom_cedula": cedula, "status": "Active"},
                                   "name"
                                   )

    def crear_salario_adicional(self, empleado, monto):
        """
        Crea un 'Additional Salary' que sobrescribe la fórmula del componente
        """

        # AQUÍ ESTÁ LA RESPUESTA A TU PREGUNTA DEL DOCENTRY/SALARY SLIP:
        # Aunque NO necesitamos enlazarlo manualmente (ERPNext lo hace solo por fecha),
        # así es como detectarías si ya existe un Salary Slip Borrador para validaciones:

        fecha_ref = getdate(self.fecha_corte)  # Asumiendo que tienes este campo
        inicio_mes = get_first_day(fecha_ref)
        fin_mes = get_last_day(fecha_ref)

        # Query para detectar el ID (name) del Salary Slip
        salary_slip_existente = frappe.db.get_value("Salary Slip", {
            "employee": empleado,
            "start_date": [">=", inicio_mes],
            "end_date": ["<=", fin_mes],
            "docstatus": 0  # 0=Draft, 1=Submitted
        }, "name")

        # Nota: Si salary_slip_existente tiene valor, ese es el ID.

        # Verificar si ya existe el Descuento para no duplicar
        existe_adicional = frappe.db.exists("Additional Salary", {
            "employee": empleado,
            "salary_component": self.custom_componente_salarial,
            "payroll_date": self.fecha_corte,
            "amount": monto,
            "docstatus": 1
        })

        if existe_adicional:
            frappe.msgprint(f"Omitido: Ya existe descuento para {empleado}")
            return

        # Crear el documento
        add_salary = frappe.get_doc({
            "doctype": "Additional Salary",
            "company": frappe.defaults.get_user_default("Company"),
            "employee": empleado,
            "salary_component": self.custom_componente_salarial,
            "amount": monto,
            "payroll_date": self.fecha_corte,
            "overwrite_salary_structure_amount": 1,  # CLAVE: Esto anula tu fórmula y fuerza este valor
            "ref_doctype": self.doctype,
            "ref_docname": self.name
        })
        add_salary.insert()
        add_salary.submit()

