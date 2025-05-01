/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { Component, onMounted, useState, xml } from "@odoo/owl";

export const sharedState = reactive({
    out_of_rent_p_info_show: null,
});

export class SharedInfoComponent extends Component {
    static template = xml`
        <div class="board-shared-info">
            <div t-esc="state.sharedState.out_of_rent_p_info_show" />
        </div>
        `;

    setup() {
        this.state = useState({
            sharedState: sharedState,
        });

    }
}
