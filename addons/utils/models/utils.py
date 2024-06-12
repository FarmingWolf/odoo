# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# 小额数字到汉字的映射
class Utils:
    # 小额数字到汉字的映射
    chinese_digits = {
        '0': '零',
        '1': '壹',
        '2': '贰',
        '3': '叁',
        '4': '肆',
        '5': '伍',
        '6': '陆',
        '7': '柒',
        '8': '捌',
        '9': '玖',
    }

    # 单位映射，注意中文里金额的单位表达与普通数字的不同
    units = {
        '0': '',
        '1': '',
        '2': '拾',
        '3': '佰',
        '4': '仟',
        '5': '万',
        '6': '拾万',
        '7': '佰万',
        '8': '仟万',
        '9': '亿',
        '10': '拾亿',
        '11': '佰亿',
        '12': '仟亿',
    }

    @staticmethod
    def arabic_to_chinese(amount):
        """
        将阿拉伯数字金额转换为汉字大写表示，遵循财务书写规范。
        """

        # 分离整数和小数部分
        parts = str(amount).split('.')
        yuan = int(parts[0])  # 整数部分
        decimal = parts[1] if len(parts) > 1 else '00'  # 小数部分，不足两位补0

        # 处理整数部分
        chinese_yuan = []
        while yuan > 0:
            segment = yuan % 100000
            segment_str = str(segment).zfill(4)
            chinese_segment = ''.join([
                Utils.chinese_digits[digit] + ('' + Utils.units[str(idx)] if digit != '0' else '')
                for idx, digit in enumerate(segment_str)])
            chinese_yuan.insert(0, chinese_segment.strip('零'))
            yuan //= 10000

        # 添加单位
        for idx, segment in enumerate(chinese_yuan):
            if segment:
                chinese_yuan[idx] += Utils.units[str(len(chinese_yuan) - idx - 1)]

        chinese_yuan = ''.join(filter(None, chinese_yuan)).strip('零') or '零元'

        # 处理小数部分
        chinese_decimal = ''.join([
            Utils.chinese_digits[digit] + ('角' if idx == 0 else '分')
            for idx, digit in enumerate(decimal) if digit != '0'])

        # 拼接结果
        result = chinese_yuan + ('元' + chinese_decimal if chinese_decimal else '元整')
        return result
# 示例

print("0={0}".format(Utils.arabic_to_chinese(0)))
print("0.0={0}".format(Utils.arabic_to_chinese(0.0)))
print("1.89={0}".format(Utils.arabic_to_chinese(1.89)))
print("123.89={0}".format(Utils.arabic_to_chinese(123.89)))
print("1234567890.89={0}".format(Utils.arabic_to_chinese(1234567890.89)))
