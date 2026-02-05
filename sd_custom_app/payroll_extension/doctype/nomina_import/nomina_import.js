frappe.ui.form.on("Nomina Import", {
    setup: function(frm) {
        // Escuchar actualizaciones en tiempo real desde el backend (Python)
        frappe.realtime.on("data_import_progress", (data) => {
            if (data.data_import !== frm.doc.name) return;

            if (data.error) {
                frappe.msgprint({
                    title: __('Error'),
                    message: data.message,
                    indicator: 'red'
                });
                frm.dashboard.hide_progress();
                return;
            }

            // Mostrar barra de progreso nativa
            if (data.progress) {
                frm.dashboard.show_progress(__("Procesando Archivo"), data.progress, data.message);
            }

            // Ocultar barra al finalizar
            if (data.progress === 100) {
                setTimeout(() => {
                    frm.dashboard.hide_progress();
                    frm.reload_doc();
                }, 1000);
            }
        });

        frappe.realtime.on("data_import_refresh", (data) => {
            if (data.data_import === frm.doc.name) {
                frm.reload_doc();
            }
        });
    },

    refresh: function(frm) {
        // Configurar indicadores visuales (Colores de estado)
        frm.trigger("update_indicators");
        frm.trigger("render_log");

        // Botón Principal: "Iniciar Importación"
        if (!frm.is_new() && frm.doc.status !== "In Progress" && frm.doc.status !== "Success") {
            frm.add_custom_button(__("Iniciar Importación"), () => {
                frm.trigger("start_import");
            }).addClass("btn-primary");
        }

        // Botón: "Reintentar" (Si hubo error)
        if (frm.doc.status === "Error" || frm.doc.status === "Partial Success") {
            frm.add_custom_button(__("Reintentar"), () => {
                frm.trigger("start_import");
            });
        }
    },

    import_source: function(frm) {
        // Limpiar archivo si cambia el tipo
        frm.set_value("import_file", null);
    },

    onload: function(frm) {
        // Filtrar extensiones permitidas según selección
        frm.set_query("import_file", function() {
            let extensiones = [];
            if (frm.doc.import_source === "Farmacia (HTML)") {
                extensiones = ["%.html", "%.htm"];
            } else if (frm.doc.import_source === "Supermercado (Excel)") {
                extensiones = ["%.xlsx", "%.xls"];
            }
            return {
                filters: {
                    "file_url": ["like", extensiones]
                }
            };
        });
    },

    start_import: function(frm) {
        if (!frm.doc.import_file) {
            frappe.throw(__("Por favor adjunte un archivo antes de iniciar."));
            return;
        }

        frappe.confirm(__("¿Está seguro de iniciar la importación? Esto creará registros de Salario Adicional."), () => {
            frappe.call({
                method: "start_import", // Llama a tu nomina_import.py
                doc: frm.doc,
                freeze: true,
                freeze_message: __("Encolando trabajo..."),
                callback: function(r) {
                    frm.reload_doc();
                }
            });
        });
    },

    update_indicators: function(frm) {
        // Mapeo de colores para el indicador superior derecho
        const colors = {
            "Pending": "orange",
            "In Progress": "blue",
            "Success": "green",
            "Partial Success": "orange",
            "Error": "red"
        };
        if (frm.doc.status) {
            frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status]);
        }
    },

    render_log: function(frm) {
        // Renderizar el HTML del log si existe contenido
        if (frm.doc.import_log) {
            // Asumimos que el backend guardó un HTML o JSON en import_log
            // Si es JSON, lo parseamos y creamos tabla; si es HTML string, lo pegamos.
            let html_content = frm.doc.import_log; 
            
            // Si guardaste JSON en Python, aquí lo convertimos a tabla:
            try {
                let logs = JSON.parse(frm.doc.import_log);
                if (Array.isArray(logs)) {
                    let rows = logs.map(l => `
                        <tr>
                            <td>${l.row || '-'}</td>
                            <td class="${l.status === 'Error' ? 'text-danger' : 'text-success'}">${l.status}</td>
                            <td>${l.msg}</td>
                        </tr>
                    `).join("");
                    
                    html_content = `
                        <table class="table table-bordered table-condensed">
                            <thead><tr><th>Fila</th><th>Estado</th><th>Mensaje</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    `;
                }
            } catch (e) {
                // Si ya viene como HTML, no hacer nada
            }

            frm.get_field("import_log_preview").$wrapper.html(html_content);
        }
    }
});
