/** @odoo-module */

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

export class CustomTreeRow extends Component {
    static template = 'estate_lease_contract.CustomTreeRow'; // 直接在类定义中设置模板
    setup() {
        debugger;
        console.log("CustomTreeRow组件初始化");
        super.setup();
        this.actionService = useService('action');
        this.state = useState({ clickedId: null });
    }

    // 监听点击事件
    onRowClick(event) {
        debugger;
        console.log("监听list点击事件");
        debugger;
        const record = event.detail.record;
        this.state.clickedId = record.resId;
        this.updateContext();
    }

    updateContext() {
        if (this.state.clickedId !== null) {
            const context = Object.assign({}, this.props.context, {
                active_id: this.state.clickedId,
            });
            this.actionService.updateState({ context });
        }
    }
}
CustomTreeRow.template = 'estate_lease_contract.CustomTreeRow';


