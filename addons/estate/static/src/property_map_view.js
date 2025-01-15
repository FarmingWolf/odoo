/** @odoo-module */

import { registry } from "@web/core/registry";
import { PropertyMapController } from "./property_map_controller";
import { PropertyMapArchParser } from "./property_map_arch_parser";

export const propertyMapView = {
    type: "property_map",
    display_name: "Property Map",
    icon: "fa fa-map-marker",
    multiRecord: true,
    Controller: PropertyMapController,
    ArchParser: PropertyMapArchParser,

    props(genericProps, view) {
        const { ArchParser } = view;
        const { arch } = genericProps;
        const archInfo = new ArchParser().parse(arch);
        return {
            ...genericProps,
            archInfo,
        };
    },
};

registry.category("views").add("property_map", propertyMapView);
