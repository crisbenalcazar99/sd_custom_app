frappe.ui.form.on('Farmacia', {
    refresh: function(frm) {
        // Añadir el botón solo si hay registros cargados y el documento no es nuevo
        if (frm.doc.items_lectura && frm.doc.items_lectura.length > 0 && !frm.is_new()) {
            frm.add_custom_button(__('Iniciar Importación'), function() {
                frm.events.procesar_carga(frm);
            }).addClass("btn-primary");
        }
    },

    procesar_carga: function(frm) {
        frappe.confirm('¿Desea iniciar la creación de los Salarios Adicionales?', () => {
            frappe.call({
                method: "iniciar_procesamiento", // Llama al método en farmacia.py
                doc: frm.doc,
                freeze: true,
                freeze_message: __("Generando descuentos..."),
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.msgprint(__("Importación completada. Revise el log de registros."));
                    }
                }
            });
        });
    }
});
