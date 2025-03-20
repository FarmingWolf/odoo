/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class FundManagementLinesListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.threadService = useService("mail.thread");
    }

    /** @override **/
    async onCellClicked(record, column, ev) {
        super.onCellClicked(record, column, ev);
    }
}

export class FundManagementLinesWidget extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: FundManagementLinesListRenderer,
    };

    setup() {
        super.setup();
        this.canOpenRecord = false;
    }

    get isMany2Many() {
        // The field is used like a many2many to allow for adding existing lines to the sheet.
        return true;
    }
}

export const fundManagementLinesWidget = {
    ...x2ManyField,
    component: FundManagementLinesWidget,
};

registry.category("fields").add("fund_management_lines_widget", fundManagementLinesWidget);
