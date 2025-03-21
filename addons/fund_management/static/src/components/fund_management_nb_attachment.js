/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class AttachmentNumber extends Component {

    setup() {
        super.setup();
        this.fund_management_nb_attachment = this.props.record.data.nb_attachment
    }
    static template = "fund_management.AttachmentNumber"
}

registry.category("fields").add("fund_management_nb_attachment", {component: AttachmentNumber});
