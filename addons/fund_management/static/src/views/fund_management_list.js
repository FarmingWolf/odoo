/** @odoo-module */

import { FundManagementDashboard } from '../components/fund_management_dashboard';

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { listView } from "@web/views/list/list_view";

import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillStart } from "@odoo/owl";
import {FundManagementDocumentDropZone, FundManagementDocumentUpload} from "../mixins/document_upload";
import {ExpenseDocumentDropZone} from "../../../../hr_expense/static/src/mixins/document_upload";
import {ExpenseMobileQRCode} from "../../../../hr_expense/static/src/mixins/qrcode";
import {FundManagementMobileQRCode} from "../mixins/qrcode";
import {ApprovalProcess} from "../components/approval_process";

export class FundManagementListController extends FundManagementDocumentUpload(ListController) {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService('action');
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.isExpenseSheet = this.model.config.resModel === "fund.management.sheet";

        this.env.config.context = {
            ...this.env.config.context,
            default_category_id: this.props.context?.default_category_id,
            default_fund_management_id: this.props.context?.default_fund_management_id,
        };

        onWillStart(async () => {
            this.userIsExpenseTeamApprover = await this.user.hasGroup("fund_management.group_fund_management_team_approver");
            this.userIsAccountInvoicing = await this.user.hasGroup("account.group_account_invoice");
        });
    }

    displaySubmit() {
        const records = this.model.root.selection;
        return records.length && records.every(record => record.data.state === 'draft') && this.isExpenseSheet;
    }

    displayApprove() {
        const records = this.model.root.selection;
        return this.userIsExpenseTeamApprover && records.length && records.every(record => record.data.state === 'submit') && this.isExpenseSheet;
    }

    displayPost() {
        const records = this.model.root.selection;
        return this.userIsAccountInvoicing && records.length && records.every(record => record.data.state === 'approve') && this.isExpenseSheet;
    }

    displayPayment() {
        const records = this.model.root.selection;
        return this.userIsAccountInvoicing && records.length && records.every(record => record.data.state === 'post') && this.isExpenseSheet;
    }

    async onClick (action) {
        const records = this.model.root.selection;
        const recordIds = records.map((a) => a.resId);
        const model = this.model.config.resModel;
        const context = {};
        if (action === 'action_approve_expense_sheets') {
            context['validate_analytic'] = true;
        }
        const res = await this.orm.call(model, action, [recordIds], {context: context});
        if (res) {
            await this.actionService.doAction(res, {
                additionalContext: {
                    dont_redirect_to_payments: 1,
                },
                onClose: async () => {
                    await this.model.root.load();
                    this.render(true);
                }
            });
        }
        await this.model.root.load();
    }

    async action_show_fund_management_to_submit () {
        const records = this.model.root.selection;
        const res = await this.orm.call(this.model.config.resModel, 'get_fund_management_to_submit', [records.map((record) => record.resId)]);
        if (res) {
            await this.actionService.doAction(res, {});
        }
    }
}
export class FundManagementListRenderer extends FundManagementDocumentDropZone(FundManagementMobileQRCode(ListRenderer)) {}
FundManagementListRenderer.template = 'fund_management.ListRenderer';

export class FundManagementDashboardListRenderer extends FundManagementListRenderer {}

FundManagementDashboardListRenderer.components = { ...FundManagementDashboardListRenderer.components, FundManagementDashboard};
FundManagementDashboardListRenderer.template = 'fund_management.DashboardListRenderer';

export class FundManagementStageListRenderer extends FundManagementListRenderer {
    setup() {
        super.setup();
        this.default_category_id = this.props.context?.default_category_id || this.env.config.context?.default_category_id;
    }
}

FundManagementStageListRenderer.components = { ...FundManagementStageListRenderer.components, ApprovalProcess};
FundManagementStageListRenderer.template = 'fund_management.StageListRenderer';

registry.category('views').add('fund_management_tree', {
    ...listView,
    buttonTemplate: 'fund_management.ListButtons',
    Controller: FundManagementListController,
    Renderer: FundManagementListRenderer,
});

registry.category('views').add('fund_management_dashboard_tree', {
    ...listView,
    buttonTemplate: 'fund_management.ListButtons',
    Controller: FundManagementListController,
    Renderer: FundManagementDashboardListRenderer,
});

registry.category('views').add('fund_management_stage_tree', {
    ...listView,
    buttonTemplate: 'fund_management.ListButtons',
    Controller: FundManagementListController,
    Renderer: FundManagementStageListRenderer,
});
