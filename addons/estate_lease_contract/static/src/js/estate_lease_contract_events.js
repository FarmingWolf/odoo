/** @odoo-module */

export function parent_page_events() {
    $(document).ready(function () {
        let handlePropertyIdsSave = function () {
            console.log("↑↑↑")
            let contractForm = $('.o_form_view.o_form_editable');
            if (contractForm.length) {
                // 直接从DOM中获取已选择的租赁标的
                let propertyIds = [];
                $('.o_field_many2manytags[name="property_ids"] .badge').each(function () {
                    let propertyId = parseInt($(this).data('id'));
                    if (!isNaN(propertyId)) { // 验证是否为有效数字
                        propertyIds.push(propertyId);
                    }
                });

                if (propertyIds.length) {
                    localStorage.setItem('selected_property_ids', JSON.stringify(propertyIds));
                    console.log(propertyIds);
                }
            }
        };

        // 绑定到文档点击事件，但需注意此方法可能会非常频繁触发，根据实际需求调整绑定范围或添加节流/防抖逻辑
        $(document).on('click', handlePropertyIdsSave);
    });
}
