/** @odoo-module */

import { listView } from "@web/views/list/list_view";

export function child_view_filter(){

    listView.include({
        init: function () {
            this._super.apply(this, arguments);
            var selectedPropertyIds = JSON.parse(localStorage.getItem('selected_property_ids') || '[]');
            if (selectedPropertyIds.length) {
                this.dataset.domain.push(['rent_target', 'in', selectedPropertyIds]);
                // 重载列表视图以应用新的domain
                this.reload();
            }
        },
    });
}
