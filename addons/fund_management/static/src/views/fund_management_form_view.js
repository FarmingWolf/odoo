/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class FundManagementFormController extends FormController {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
    }

}

export const FundManagementFormView = {
    ...formView,
    Controller: FundManagementFormController,
};

registry.category("views").add("fund_management_form_view", FundManagementFormView);
