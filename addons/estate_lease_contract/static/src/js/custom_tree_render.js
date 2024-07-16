/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";
import { Component, useState, useExternalListener } from "@odoo/owl";

export class CustomTreeRenderer extends Component {
    static template = "estate_lease_contract.CustomTreeRenderer";
    static props = {};

    setup() {
        super.setup();
        this.actionService = useService('action');
        this.state = useState({ clickedRecordId: null });
        this.onClick = this.onClick.bind(this);
        useExternalListener(document.body, "click", this.onClick, true);
    }


    async onClick(event, record) {
        if (event == undefined) {
            return
        }
        if (event.currentTarget == undefined) {
            return
        }

        const fieldValue = document.getElementsByName('context_contract_id');
        let tgtVal = 0
        if (fieldValue != undefined && fieldValue.length > 0) {
            tgtVal = fieldValue[0].innerText
            console.log(tgtVal);
        }
        //
        // // 如果不是点击list
        // if (!record) {
        //     console.error('Record is undefined or null.');
        //     return;
        // }

        // let context = {};
        // if (record && record.context) {
        //     context = { ...record.context };
        // }

        // this.actionService.doAction({
        //     type: 'ir.actions.act_window',
        //     res_model: 'estate.property',
        //     views: [[false, "form"]],
        //     // res_id: record.resId,
        //     res_id: 1,
        //     view_mode: "form",
        //     target: "new",
        //     context: context,
        // });
    }
}

export const systrayItem = {
    Component: CustomTreeRenderer,
};

CustomTreeRenderer.template = 'estate_lease_contract.CustomTreeRenderer';

registry.category("systray").add("estate_lease_contract.CustomTreeRenderer", systrayItem, { sequence: 500 });
