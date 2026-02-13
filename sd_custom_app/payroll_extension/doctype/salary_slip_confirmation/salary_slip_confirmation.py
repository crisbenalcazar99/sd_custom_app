import os
import frappe
from frappe.model.document import Document
import base64
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from frappe.utils.file_manager import save_file

from frappe import _
class SalarySlipConfirmation(Document):
    # Configuración de URLs proporcionadas
    URL_LOGIN = "https://datagree.securitydata.net.ec/scexterno/api/firmado/login"
    URL_FIRMAR = "https://datagree.securitydata.net.ec/scexterno/api/firmado/firmarDocumento"

    @frappe.whitelist()
    def procesar_aceptacion(self, password=None):
        if not password:
            frappe.throw("Se requeire la Contrasena para el firmado")
        """
        Esta función se llama cuando el empleado da clic en Aceptar.
        """
        if self.status != "Pendiente":
            frappe.throw("Este rol ya ha sido procesado.")

        # 1. Ejecutar TU LÓGICA PERSONALIZADA
        pdf_firmado = self.ejecutar_logica_negocio(password)

        # 2. Actualizar estado
        #self.status = "Aceptado"
        #self.save(ignore_permissions=True)

        # 3. Notificar
        self.enviar_notificacion_correo(pdf_firmado)

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

    def enviar_notificacion_correo(self, pdf_bytes=None):
        recipient = "crisbenalp@gmail.com"
        subject = f"Respuesta Rol: {self.employee} - {self.status}"

        message = f"""
            <p>El empleado <b>{self.employee}</b> ha marcado su rol <b>{self.salary_slip}</b> como <b>{self.status}</b>.</p>
        """

        if self.status == "Rechazado":
            message += f"<p>Motivo: {self.feedback}</p>"

        attachments = []
        if pdf_bytes:
            attachments.append({
                "fname": f"Rol_Firmado_{self.employee}.pdf".replace(" ", "_"),
                "fcontent": pdf_bytes
            })

        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
            attachments=attachments
        )

    @frappe.whitelist()
    def get_slip_preview(self):
        # Genera el HTML usando el motor oficial de Frappe
        return frappe.get_print(
            "Salary Slip",
            self.salary_slip,
            "salary_slip_sd",
            as_pdf = False,
            no_letterhead=0
        )


    def individual_sign(self, pdf_base64, username, password, tipo_persona, ruc, x_pos, y_pos):
        try:
            # 1. Login para obtener el Bearer Token
            payload_login = {
                "username": "1716165533",  # individualSignUsername en Java
                "password": "El1princesa25**+"  # individualSignPassword en Java
            }

            res_login = requests.post(self.URL_LOGIN, json=payload_login)
            if res_login.status_code != 200:
                raise Exception(f"Error en login de SecurityData: {res_login.text}")

            auth_token = res_login.json().get("resultado")

            # 2. Preparar el cifrado de la contraseña de la firma
            encripted_password = self.cifrar_con_llave_publica(password)

            # 3. Construir el Payload para el firmado
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }

            payload_firma = {
                "dataFirma": {
                    "tipoIdentidad": "cedula",
                    "numeroIdentidad": username,
                    "tipoFirma": tipo_persona,
                    "numeroRuc": ruc,
                    "passwordFirma": encripted_password
                },
                "dataDocumentos": [
                    {
                        "nombreDocumento": "FormularioFirmado.pdf",
                        "isBase64": True,
                        "documentoFirmar": pdf_base64,
                        "dataFirmas": [
                            {
                                "numPageArray": "1",
                                "posicionxArray": str(x_pos),
                                "posicionyArray": str(y_pos)
                            }
                        ]
                    }
                ]
            }
            frappe.logger().info({
                "DEBUG_SIGN_REQUEST":{
                    "url": self.URL_FIRMAR,
                    "headers": headers,
                    "payload": payload_firma
                }
            })

            # 4. Realizar la solicitud de firmado
            res_firma = requests.post(self.URL_FIRMAR, json=payload_firma, headers=headers)
            data_res = res_firma.json()

            if res_firma.status_code == 200 and data_res.get("respuesta"):
                # 1. Obtener el string Base64 del resultado
                base64_string = data_res["resultado"][0]["resultado"]

                # 2. Convertir a bytes para el correo (sin guardar en disco)
                pdf_bytes = base64.b64decode(base64_string)

                # Retornamos solo los bytes
                return pdf_bytes

            elif res_firma.status_code == 200 and not data_res.get("respuesta"):
                raise Exception(f"Contraseña de firma incorrecta: {data_res.get('mensaje')}")

            elif res_firma.status_code == 401:
                raise Exception(f"Error de autorización: {data_res.get('mensaje')}")

            else:
                raise Exception(f"Error en proceso de firmado: {data_res.get('mensaje')} {encripted_password}")

        except Exception as e:
            frappe.log_error(f"Error en individual_sign: {str(e)}", "Security Data Integration")
            raise e


    def ejecutar_logica_negocio(self, password):

        # 1. Validar que el empleado esté asignado
        if not self.employee:
            frappe.throw("No se ha seleccionado un empleado en este documento.")

        # 2. Obtener la cédula del empleado (campo custom_cedula)
        # frappe.db.get_value es más eficiente si solo necesitas un campo
        cedula_empleado = frappe.db.get_value("Employee", self.employee, "custom_cedula")

        if not cedula_empleado:
            frappe.throw(
                f"El empleado {self.employee} no tiene registrada una cédula en 'custom_cedula'.")
        """
        Integración en tu función de Frappe
        """
        frappe.logger().info(f"Iniciando firmado para {self.employee}")

        # 1. Aquí obtendrías tu PDF en base64 (ejemplo desde un file)
        # pdf_b64 = ... tu lógica para obtener el base64 ...

        # 1. OBTENER EL PDF EN BASE64
        # Utilizamos los mismos parámetros que tenías en tu JS:
        # Doctype: Salary Slip, Name: frm.doc.salary_slip, Format: Salary Slip SD
        try:
            if not self.salary_slip:
                frappe.throw("No hay un Rol de Pagos (Salary Slip) asociado para generar el PDF.")

            # Generamos el contenido binario del PDF usando el Print Format específico
            pdf_content = frappe.get_print(
                doctype="Salary Slip",
                name=self.salary_slip,
                print_format="Salary Slip SD",
                no_letterhead=0,
                as_pdf=True
            )

            # Convertimos el binario a Base64 string
            pdf_b64 = base64.b64encode(pdf_content).decode('utf-8')

            frappe.logger().info(f"PDF convertido a Base64 exitosamente para {self.employee}")

        except Exception as e:
            frappe.log_error(f"Error generando PDF para firmado: {str(e)}", "Error PDF Base64")
            frappe.throw("No se pudo generar el PDF del Rol de Pagos para el firmado.")


        # 2. Llamada a la función traducida
        try:
            pdf_bytes = self.individual_sign(
                pdf_base64=pdf_b64,
                username=cedula_empleado,
                password=password,
                tipo_persona="ME",
                ruc='1792261848001',
                x_pos="100",
                y_pos="100"
            )

            if pdf_bytes:
                frappe.logger().info(
                    f"Documento firmado y listo para envío para {self.employee}")
                return pdf_bytes

        except Exception as e:
            frappe.msgprint(f"Error al firmar: {str(e)}")
            return None

        pass

    def cifrar_con_llave_publica(self, signature_password):
        # 1. Construir la ruta absoluta usando el nombre de tu app
        # frappe.get_app_path busca dentro de 'apps/sd_custom_app/sd_custom_app/...'
        path_to_pem = frappe.get_app_path(
            'sd_custom_app',
            'payroll_extension',
            'doctype',
            'salary_slip_confirmation',
            'public_key.pem'
        )

        # Verificación de seguridad
        if not os.path.exists(path_to_pem):
            frappe.throw(f"No se encontró el archivo de la llave en: {path_to_pem}")

        # 2. Cargar la llave desde el archivo PEM
        try:
            with open(path_to_pem, "rb") as key_file:
                public_key = serialization.load_pem_public_key(
                    key_file.read()
                )
        except Exception as e:
            frappe.throw(f"Error al leer el archivo PEM: {str(e)}")

        # 3. Cifrar
        datos_bytes = signature_password.encode('utf-8')
        datos_cifrados = public_key.encrypt(
            datos_bytes,
            padding.PKCS1v15()
        )

        # 4. Retornar en Base64
        return base64.b64encode(datos_cifrados).decode('utf-8')
