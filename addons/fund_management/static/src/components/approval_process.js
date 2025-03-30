/** @odoo-module */

import {useService} from '@web/core/utils/hooks';
import {Component, onWillStart, useState} from "@odoo/owl";

export class ApprovalProcess extends Component {

    setup() {
        super.setup();
        this.default_category_id = this.props.default_category_id || this.env.config.context?.default_category_id;
        this.default_fund_management_id = this.props.default_fund_management_id || this.env.config.context?.default_fund_management_id;
        this.orm = useService('orm');

        this.state = useState({
            process_stages: {}
        });

        onWillStart(async () => {
            this.state.process_stages = await this.orm.call("fund.management", 'get_approval_process_stages',
                [], {default_category_id: this.default_category_id, default_fund_management_id: this.default_fund_management_id});
        });
    }
}
ApprovalProcess.template = 'fund_management.ApprovalProcess';
