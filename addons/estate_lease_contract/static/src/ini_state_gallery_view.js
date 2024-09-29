/** @odoo-module */

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { IniStateGalleryController } from "./ini_state_gallery_controller";
import { mount, whenReady } from "@odoo/owl";
import { templates } from "@web/core/assets";

// Mount the component when the document.body is ready
whenReady(() => {
    console.log('Document is ready.');
    const targetDiv = document.getElementById("div_property_ini_img_ids") || document.querySelector('[name="div_property_ini_img_ids"]');
    if (targetDiv) {
        console.log('Target div found:', targetDiv);
        const props = {
            // Initialize your props here, e.g., model, id, etc.
            // Example:
            // model: "estate.lease.contract",
            // id: 123,
            // ... other required props
            record: {} // 示例记录对象
        };
        // 将组件挂载到目标 div 中
        mount(IniStateGalleryController, targetDiv, { dev: true, name: "Property_Ini_State_Ready", ...props });
    } else {
        console.log('Target div with name "div_property_ini_img_ids" not found.');
    }
});

function webViewerLoad() {
    const targetDiv = document.getElementById("div_property_ini_img_ids") || document.querySelector('[name="div_property_ini_img_ids"]');
    if (targetDiv) {
        console.log('Target div found:', targetDiv);
        const props = {
            // Initialize your props here, e.g., model, id, etc.
            // Example:
            // model: "estate.lease.contract",
            // id: 123,
            // ... other required props
            record: {} // 示例记录对象
        };
        // 将组件挂载到目标 div 中
        mount(IniStateGalleryController, targetDiv, { dev: true, name: "Property_Ini_State_Ready", ...props });
    } else {
        console.log('Target div with name "div_property_ini_img_ids" still not found.');
    }
}

document.addEventListener("DOMContentLoaded", webViewerLoad, true);
