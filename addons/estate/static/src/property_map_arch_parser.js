/** @odoo-module */

export class PropertyMapArchParser {
    parse(xmlDoc) {
        const propertyName = xmlDoc.getAttribute("name");
        return {
            propertyName,
        };
    }
}
