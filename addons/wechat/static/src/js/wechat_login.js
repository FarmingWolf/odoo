/** @odoo-module **/

import { session } from "@web/session";

export async function wechatLogin() {
    console.log("wechat module entered session.connectionState=" + session.connectionState)
    console.log("redirect_uri=" + window.location.origin + "……")
    if (session.connectionState === undefined) {
        try {
            return new WxLogin({
                self_redirect: true,
                id: "wechat_qr_code_container",
                appid: "wx2dadd8272b906e46",
                scope: "snsapi_login",
                redirect_uri: window.location.origin + "/wechat/callback",
                state: "STATE",
                style: "black",
                href: ""
            });
        } catch (error) {
            console.error("Error fetching QR code:", error);
        }
    }
}

$(document).ready(() => {
    wechatLogin();
});
