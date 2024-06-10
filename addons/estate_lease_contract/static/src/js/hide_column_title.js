/** @odoo-module */

export function useClicker() {

    $(document).ready(function () {
        // 使用data-name属性来定位并隐藏表头中的指定列
        $('.o_list_view .o_list_view_header .o_column_title[data-name="state"]').addClass('hidden-title');
    });
}
