import frappe
from bs4 import BeautifulSoup
import openpyxl
from frappe.utils import flt, getdate

class NominaImporter:
    def __init__(self, doc):
        self.doc = doc
        self.items = []
        self.log = []

    def run(self):
        """Orquesta el proceso completo: Leer -> Validar -> Guardar"""
        self.parse_file()
        self.process_rows()
        self.save_logs()

    def parse_file(self):
        """Decide qué estrategia de lectura usar basado en el Select"""
        file_doc = frappe.get_doc("File", {"file_url": self.doc.import_file})
        
        # Estrategia Farmacia (HTML)
        if self.doc.import_source == "Farmacia (HTML)":
            content = file_doc.get_content()
            if isinstance(content, bytes): 
                content = content.decode("utf-8")
            self._parse_html_farmacia(content)

        # Estrategia Supermercado (Excel)
        elif self.doc.import_source == "Supermercado (Excel)":
            # openpyxl necesita ruta física
            file_path = file_doc.get_full_path()
            self._parse_excel_supermercado(file_path)

    def _parse_html_farmacia(self, content):
        """Tu lógica original de farmacia.py portada aquí"""
        soup = BeautifulSoup(content, "html.parser")
        
        # Búsqueda de tabla (optimizada)
        tabla_datos = None
        for tabla in soup.find_all("table"):
            if "CÉDULA" in tabla.get_text() and "MES CONSUMO" in tabla.get_text():
                tabla_datos = tabla
                break
        
        if not tabla_datos:
            frappe.throw("No se encontró la tabla de 'CÉDULA' y 'MES CONSUMO' en el HTML")

        for fila in tabla_datos.find_all("tr"):
            celdas = fila.find_all("td")
            texto = fila.get_text(strip=True)
            # Validaciones de estructura de tu HTML
            if len(celdas) >= 5 and "CÉDULA" not in texto and "TOTAL" not in texto:
                try:
                    # Asumiendo posiciones fijas según tu script original
                    cedula = celdas[2].get_text(strip=True).replace("&nbsp;", "").strip()
                    nombre = celdas[3].get_text(strip=True)
                    valor = celdas[5].get_text(strip=True).replace(".", "").replace(",", ".")
                    
                    if cedula.isdigit() and float(valor) > 0:
                        self.items.append({
                            "cedula": cedula,
                            "nombre": nombre,
                            "monto": flt(valor)
                        })
                except Exception:
                    continue

    def _parse_excel_supermercado(self, file_path):
        """Nueva lógica para Excel"""
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active # Toma la primera hoja
        
        # Iterar filas (asumiendo cabecera en fila 1)
        for row in ws.iter_rows(min_row=2, values_only=True):
            # Asumimos columnas: A=Cedula, B=Nombre, C=Monto
            cedula, nombre, monto = row[0], row[1], row[2]
            
            if cedula and monto:
                self.items.append({
                    "cedula": str(cedula).strip(),
                    "nombre": nombre,
                    "monto": flt(monto)
                })

    def process_rows(self):
        """Procesa los datos extraídos y crea/actualiza registros"""
        total = len(self.items)
        if total == 0:
            frappe.throw("El archivo no contiene registros válidos.")

        for i, item in enumerate(self.items):
            try:
                # 1. Reportar progreso cada 10 filas (para no saturar red)
                if i % 10 == 0:
                    progress = int((i / total) * 100)
                    frappe.publish_realtime("data_import_progress", {
                        "progress": progress,
                        "current": i + 1,
                        "total": total,
                        "message": f"Procesando {item['cedula']}",
                        "data_import": self.doc.name
                    })

                # 2. Lógica de negocio (Buscar empleado)
                empleado = frappe.db.get_value("Employee", 
                    {"custom_cedula": item['cedula'], "status": "Active"}, 
                    "name"
                )

                if not empleado:
                    self.log.append(f"Fila {i+1}: Cédula {item['cedula']} no encontrada.")
                    continue

                # 3. Crear Salario Adicional (Transaccional)
                self.create_additional_salary(empleado, item['monto'])
                
            except Exception as e:
                self.log.append(f"Fila {i+1} ({item['cedula']}): {str(e)}")

        frappe.db.commit() # Commit final si todo el bloque pasa

    def create_additional_salary(self, empleado, monto):
        # Evitar duplicados
        existe = frappe.db.exists("Additional Salary", {
            "employee": empleado,
            "salary_component": self.doc.componente_salarial,
            "payroll_date": self.doc.payroll_date,
            "amount": monto,
            "docstatus": 1
        })
        
        if existe:
            self.log.append(f"Omitido: Ya existe descuento para {empleado}")
            return

        doc = frappe.get_doc({
            "doctype": "Additional Salary",
            "company": self.doc.company,
            "employee": empleado,
            "salary_component": self.doc.componente_salarial,
            "amount": monto,
            "payroll_date": self.doc.payroll_date,
            "overwrite_salary_structure_amount": 1,
            "ref_doctype": self.doc.doctype,
            "ref_docname": self.doc.name
        })
        doc.insert()
        doc.submit()

    def save_logs(self):
        """Guarda los logs en el documento padre"""
        if self.log:
            # Opción A: Guardar en campo HTML
            log_html = "<ul>" + "".join([f"<li>{l}</li>" for l in self.log]) + "</ul>"
            self.doc.db_set("import_log", log_html)
            
            # Opción B (Más robusta): Si hay muchos errores, marcar como Partial Success
            if len(self.log) > 0:
                self.doc.db_set("status", "Partial Success")
