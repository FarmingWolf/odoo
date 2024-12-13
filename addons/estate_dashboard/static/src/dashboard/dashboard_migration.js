/** @odoo-module */

import {browser} from "@web/core/browser/browser";

export const CURRENT_VERSION = 1.00;
export const migrations = [
    {
        fromVersion: 1.00,
        toVersion: 1.01,
        apply: (state) => {
            browser.localStorage.setItem("ConfigurationSet", "no",);
        },
    },
];

export function migrate(localState) {
    if (localState?.version === undefined || localState?.version <= CURRENT_VERSION) {
        for (const migration of migrations) {
            if (localState?.version === undefined || localState?.version === migration.fromVersion) {
                migration.apply(localState);
                if (localState !== undefined && localState != null) {
                    localState.version = migration.toVersion
                }
            }
        }
    }
    return localState;
}
