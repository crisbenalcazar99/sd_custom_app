frappe.ui.form.on('Salary Slip Confirmation', {
    refresh: function(frm) {
        // 1. Cargar la vista previa del rol automáticamente
        if (frm.doc.salary_slip && !frm.doc__islocal) {
            frappe.call({
                method: 'get_print_preview',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        // Inyectamos el HTML del rol en el campo HTML
                        frm.set_df_property('salary_slip_preview', 'options', r.message);
                        frm.refresh_field('salary_slip_preview');
                    }
                }
            });
        }

        // 2. Lógica de Botones (Igual que antes, pero asegurando el rechazo)
        if (frm.doc.status === 'Pendiente' && !frm.doc.__islocal) {
            
            // Botón ACEPTAR
// Botón ACEPTAR CON CONTRASEÑA
	   // Botón ACEPTAR CON CONTRASEÑA
frm.add_custom_button(__('Aceptar y Firmar'), function() {
    frappe.prompt([
        {
            label: 'Ingrese su contraseña para firmar',
            fieldname: 'password_firma',
            fieldtype: 'Password',
            reqd: 1
        }
    ], (values) => {
        // Esta función se ejecuta cuando el usuario da click en "Firmar"
        frappe.call({
            doc: frm.doc,
            method: 'procesar_aceptacion',
            args: {
                password: values.password_firma // Enviamos la contraseña como argumento
            },
            freeze: true,
            freeze_message: 'Verificando credenciales y firmando...',
            callback: (r) => {
                if (!r.exc) {
                    frappe.msgprint('Documento firmado y aceptado correctamente.');
                    frm.reload_doc();
                }
            }
        });
    }, 'Confirmar Aceptación', 'Firmar Documento'); // Título del modal y Texto del botón
}).addClass('btn-primary');

            // Botón RECHAZAR
            frm.add_custom_button(__('Solicitar Rectificación'), function() {
                frappe.prompt([
                    { label: 'Motivo', fieldname: 'motivo', fieldtype: 'Small Text', reqd: 1 }
                ], (values) => {
                    frappe.call({
                        doc: frm.doc,
                        method: 'procesar_rechazo',
                        args: { motivo: values.motivo },
                        freeze: true,
                        freeze_message: "Enviando notificación a RRHH...",
                        callback: (r) => { if(!r.exc) frm.reload_doc(); }
                    });
                }, 'Rechazar Rol', 'Enviar Reporte');
            }).addClass('btn-danger');
        }
    }
});
