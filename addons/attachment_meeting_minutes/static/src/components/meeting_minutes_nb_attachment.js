/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class AttachmentNumber extends Component {

    setup() {
        super.setup();
        this.meeting_minutes_nb_attachment = this.props.record.data.nb_attachment
    }
    static template = "attachment_meeting_minutes.AttachmentNumber"
}

registry.category("fields").add("meeting_minutes_nb_attachment", {component: AttachmentNumber});
