/** @odoo-module */

import { Component } from "@odoo/owl";
import { standardViewProps } from "@web/views/standard_view_props";
import { Layout } from "@web/search/layout";

export class PropertyMapController extends Component {
    static template = "estate.PropertyMapController";
    static props = {
        ...standardViewProps,
        archInfo: Object,
    };
    static components = { Layout };
}
