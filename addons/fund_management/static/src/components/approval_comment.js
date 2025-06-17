/** @odoo-module */

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import {standardWidgetProps} from "../../../../web/static/src/views/widgets/standard_widget_props";

export class ApprovalComment extends Component {
    // static template = "fund_management.ApprovalComment";
    // static components = { Dialog };
    // static props = ["*"];

    setup() {
        super.setup();
        console.log("this.props", this.props);
        console.log("context.action_type", this.props.action.context.action_type);
        console.log("active_id", this.props.action.context.res_id);

        let defaultValue = "同意";
        if (this.props.action.context.action_type === "action_agree") {
            defaultValue = "同意";
        } else if (this.props.action.context.action_type === "action_reject") {
            defaultValue = "驳回";
        } else {
            defaultValue = "一键叫停";
        }

        this.state = useState({
            actionType: this.props.action.context.action_type,
            inputValue: defaultValue,
            active_id: this.props.action.context.res_id,
        });
        this.action = useService("action");
        this.dialog = useService("dialog");

        onWillStart(() => {
            console.log("Dialog initialized with:", {
                actionType: this.state.actionType,
                defaultValue: defaultValue
            });
        });
    }

    get buttonText() {

        let defaultValue = "同意";
        if (this.state.actionType === "action_agree") {
            defaultValue = "同意";
        } else if (this.state.actionType === "action_reject") {
            defaultValue = "驳回";
        } else {
            defaultValue = "一键叫停";
        }
        return defaultValue;
    }

    confirm_button_disable(){
        return this.state.inputValue === "";
    }

    async onClickApproval() {
        const params = {
            comment: this.state.inputValue,
            action_type: this.state.actionType,
            active_id: this.state.active_id,
        };

        try {
            const svr_action = "fund_management." + this.state.actionType + "_svr_action"
            this.action.doAction(svr_action, {additionalContext: params});
            this.props.close()
        } catch (error) {
            console.error("Error:", error);
        }
    }

    onInputChange(ev) {
        this.state.inputValue = ev.target.value;
    }

}

ApprovalComment.template = "fund_management.ApprovalComment";
ApprovalComment.components = { Dialog };
ApprovalComment.props = {
    ...standardWidgetProps,
};

registry.category("actions").add("fund_management.approval_comment_dialog", ApprovalComment);
