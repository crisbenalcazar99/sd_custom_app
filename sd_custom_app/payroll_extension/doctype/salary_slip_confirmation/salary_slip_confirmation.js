frappe.ui.form.on('Salary Slip Confirmation', {
    refresh: function(frm) {
        if (frm.doc.salary_slip) {
            
            // 1. Botón para visualizar el Rol (Usando ruta relativa pura)
            frm.add_custom_button(__('Ver Rol de Pagos'), function() {
                
                const doctype = 'Salary Slip';
                const name = frm.doc.salary_slip;
                const format = 'Salary Slip SD';
                
                // Construimos la URL como un string plano. 
                // Al empezar con "/", el navegador asume la raíz del sitio automáticamente.
                const url = "/printview?doctype=" + encodeURIComponent(doctype) + 
                            "&name=" + encodeURIComponent(name) + 
                            "&format=" + encodeURIComponent(format) + 
                            "&no_letterhead=0";
                
                window.open(url, '_blank');

            }, __("Acciones")).addClass('btn-info');
        }

        // 2. Lógica de Botones (Solo si el estado es Pendiente)
        if (frm.doc.status === 'Pendiente' && !frm.doc.__islocal) {
            
            frm.add_custom_button(__('Aceptar y Firmar'), function() {
                frappe.prompt([
                    {
                        label: __('Contraseña de Usuario'),
                        fieldname: 'password',
                        fieldtype: 'Password',
                        reqd: 1,
                        description: __('Ingrese su contraseña para validar la firma.')
                    }
                ], (values) => {
                    frappe.call({
                        doc: frm.doc,
                        method: 'procesar_aceptacion',
                        args: { password: values.password },
                        freeze: true,
                        freeze_message: __("Validando..."),
                        callback: (r) => { 
                            if(!r.exc) {
                                frappe.show_alert({message: __('Documento firmado'), indicator: 'green'});
                                frm.reload_doc(); 
                            }
                        }
                    });
                }, __('Confirmación de Identidad'), __('Confirmar Firma'));
                
            }).addClass('btn-primary');

            frm.add_custom_button(__('Solicitar Rectificación'), function() {
                frappe.prompt([
                    { label: 'Motivo', fieldname: 'motivo', fieldtype: 'Small Text', reqd: 1 }
                ], (values) => {
                    frappe.call({
                        doc: frm.doc,
                        method: 'procesar_rechazo',
                        args: { motivo: values.motivo },
                        freeze: true,
                        callback: (r) => { if(!r.exc) frm.reload_doc(); }
                    });
                }, 'Rechazar Rol', 'Enviar Reporte');
            }).addClass('btn-danger');
        }
    }
});
