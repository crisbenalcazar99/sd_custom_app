frappe.listview_settings["Nomina Import"] = {
    // Colores para las bolitas de estado en la lista
    get_indicator: function(doc) {
        const colors = {
            "Pending": "orange",
            "In Progress": "blue",
            "Success": "green",
            "Partial Success": "orange",
            "Error": "red"
        };
        return [__(doc.status), colors[doc.status], "status,=," + doc.status];
    },

    onload: function(listview) {
        // Escuchar eventos globales para refrescar la lista sin F5
        frappe.realtime.on("data_import_refresh", (data) => {
            // Si hay una importación que terminó, refrescar la lista
            listview.refresh();
        });
    },
    
    // Ocultar columnas innecesarias para limpieza visual
    hide_name_column: true,
    add_fields: ["status", "import_source", "company", "payroll_date"]
};
