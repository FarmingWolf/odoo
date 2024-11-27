/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {browser} from "../../../../web/static/src/core/browser/browser";

var EstateSlideLikeWidget = publicWidget.Widget.extend({
    events: {
        'click .o_wslides_js_slide_like_heart': '_onClickUp',
        'click .o_wslides_js_slide_like_up': '_onClickUp',
        'click .o_wslides_js_slide_like_down': '_onClickDown',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} $el
     * @param {String} message
     */
    _popoverAlert: function ($el, message) {
        $el.popover({
            trigger: 'focus',
            delay: {'hide': 300},
            placement: 'bottom',
            container: 'body',
            html: true,
            content: function () {
                return message;
            }
        }).popover('show');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick: function (slideId, voteType) {
        console.log("in _onClick")
        let tgt = browser.localStorage.getItem('liked_' + slideId.toString())

        if (tgt === "1") {
            console.log('liked' + slideId.toString())
            return;
        }

        var self = this;
        this.rpc('/estate_slides/like', {
            ad_id: slideId,
            upvote: voteType === 'like',
        }).then(function (data) {
            if (! data.error) {
                const $likesBtn = self.$('span.o_wslides_js_slide_like_heart');
                const $likesIcon = $likesBtn.find('span.fa');

                // update 'thumbs-up' button with latest state
                $likesBtn.find('b').text(data.times_liked);
                $likesIcon.addClass("liked");
                browser.localStorage.setItem('liked_' + slideId.toString(), "1");

            } else {
                console.error(data.error)
            }
        });
    },

    _onClickUp: function (ev) {
        var slideId = $(ev.currentTarget).data('slide-id');
        return this._onClick(slideId, 'like');
    },

    _onClickDown: function (ev) {
        var slideId = $(ev.currentTarget).data('slide-id');
        return this._onClick(slideId, 'dislike');
    },
});

publicWidget.registry.websiteEstateSlideLike = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        $('.o_wslides_js_slide_like').each(function () {
            defs.push(new EstateSlideLikeWidget(self).attachTo($(this)));

            var $div = $(this);
            var slideId = $div.find('.o_wslides_js_slide_like_heart').attr('data-slide-id');

            // 检查 localStorage 中是否存在对应的 estate_ad.id
            if (localStorage.getItem(`liked_${slideId}`)) {
                // 如果存在，则给 fa-heart 类的 span 控件添加 liked 类
                $div.find('.fa-heart').addClass('liked');
            }
        });
        return Promise.all(defs);
    },
});

export default {
    estateSlideLikeWidget: EstateSlideLikeWidget,
    websiteEstateSlideLike: publicWidget.registry.websiteEstateSlideLike
};
