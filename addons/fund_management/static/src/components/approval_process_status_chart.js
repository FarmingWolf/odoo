/** @odoo-module */

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormController } from '@web/views/form/form_controller';
import { useService } from "@web/core/utils/hooks";
import {ApprovalProcess} from "./approval_process";

export class ApprovalProcessStatusChartCompiler extends FormCompiler {
    setup() {
        super.setup();
    }
}

export class ApprovalProcessStatusChartController extends FormController {
    setup() {
        super.setup();

        this.orm = useService('orm');
        this.actionService = useService('action');
        this.rpc = useService("rpc");
        this.user = useService("user");

        this.env.config.context = {
            ...this.env.config.context,
            default_category_id: this.props.context?.default_category_id,
            default_fund_management_id: this.props.context?.default_fund_management_id,
        };
    }

};

export class ApprovalProcessStatusChartRenderer extends FormRenderer {
    setup() {
        super.setup();
        this.default_category_id = this.props.context?.default_category_id || this.env.config.context?.default_category_id;
    }
};

ApprovalProcessStatusChartRenderer.components = { ...ApprovalProcessStatusChartRenderer.components, ApprovalProcess};
ApprovalProcessStatusChartRenderer.template = 'fund_management.StageStatusChartRenderer';

export const ApprovalProcessStatusChartView = {
    ...formView,
    buttonTemplate: 'fund_management.ListButtons',
    Compiler: ApprovalProcessStatusChartCompiler,
    Controller: ApprovalProcessStatusChartController,
    Renderer: ApprovalProcessStatusChartRenderer,
};

registry.category("views").add("fund_management_stage_status_chart", ApprovalProcessStatusChartView);
