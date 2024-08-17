# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# 小额数字到汉字的映射
import logging

_logger = logging.getLogger(__name__)


class Utils:
    _name = 'utils'
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
        '13': '万亿',
    }

    big_units = {
        '0': '',
        '1': '万',
        '2': '亿',
        '3': '万',
    }

    @staticmethod
    def arabic_to_chinese(amount):
        # 将阿拉伯数字金额转换为汉字大写表示，遵循财务书写规范。
        _logger.debug(f"amount=[{amount}]")

        if not amount or amount == 0:
            return "零元整"

        try:
            is_minus = False
            if str(amount).startswith('-'):
                is_minus = True
                amount = str(amount).strip('-')

            # 分离整数和小数部分
            parts = str(amount).split('.')
            yuan = int(parts[0])  # 整数部分
            decimal = parts[1] if len(parts) > 1 else '00'  # 小数部分，不足两位补0

            # 处理整数部分
            chinese_yuan = []

            while yuan > 0:
                # 首次进入时，个十百千
                segment = yuan % 10000
                segment_str = str(segment).zfill(4)
                chinese_segment = ''.join([
                    Utils.chinese_digits[digit] + (
                        '' + Utils.units[str(len(segment_str) - idx)] if digit != '0' else '')
                    for idx, digit in enumerate(segment_str)])

                chinese_yuan.insert(0, chinese_segment.strip('零').replace('零零', '零'))
                yuan //= 10000

            # _logger.info("chinese_yuan=[{0}]".format(chinese_yuan))
            # 添加单位
            for idx, segment in enumerate(chinese_yuan):
                if segment:
                    chinese_yuan[idx] += Utils.big_units[str(len(chinese_yuan) - idx - 1)]

            for i in range(1, len(chinese_yuan)):  # 从第二个元素开始遍历

                if chinese_yuan[i]:
                    chinese_yuan[i].strip('零')
                    if len(chinese_yuan[i]) > 2 and chinese_yuan[i][1] == '仟':  # 检查当前字符串的第二个字符是否为'仟'
                        pass
                    else:
                        chinese_yuan[i] = '零' + chinese_yuan[i]  # 不是'仟'则在字符串前插入'零'

            chinese_yuan = ''.join(filter(None, chinese_yuan)) or '零'

            # 处理小数部分
            chinese_decimal = ''.join([
                Utils.chinese_digits[digit] + ('角' if idx == 0 else '分')
                for idx, digit in enumerate(decimal) if digit != '0'])

            # 拼接结果
            result = chinese_yuan + ('元' + chinese_decimal if chinese_decimal else '元整')
            if is_minus:
                result = "负" + result

            return result

        except Exception as exc:
            _logger.info(f"金额转换中文出错：{exc}")
            return ""

    @staticmethod
    def remove_last_zero(in_num):
        if in_num:
            value_str = '{:.2f}'.format(in_num)
            # 去除末尾的零
            while value_str.endswith('0'):
                value_str = value_str[:-1]

            # 如果最后一个字符是小数点，则去掉
            if value_str.endswith('.'):
                value_str = value_str[:-1]

            return value_str
        else:
            return ''


# 示例
# print("0={0}".format(Utils.arabic_to_chinese(0)))
# print("0.0={0}".format(Utils.arabic_to_chinese(0.0)))
# print("0.9={0}".format(Utils.arabic_to_chinese(0.9)))
# print("0.98={0}".format(Utils.arabic_to_chinese(0.98)))
# print("1.89={0}".format(Utils.arabic_to_chinese(1.89)))
# print("10.00={0}".format(Utils.arabic_to_chinese(10.00)))
# print("12.89={0}".format(Utils.arabic_to_chinese(12.89)))
# print("100.00={0}".format(Utils.arabic_to_chinese(100.00)))
# print("103.89={0}".format(Utils.arabic_to_chinese(103.89)))
# print("123.89={0}".format(Utils.arabic_to_chinese(123.89)))
# print("1000.89={0}".format(Utils.arabic_to_chinese(1000.89)))
# print("2001.89={0}".format(Utils.arabic_to_chinese(2001.89)))
# print("1011.89={0}".format(Utils.arabic_to_chinese(1011.89)))
# print("3214.89={0}".format(Utils.arabic_to_chinese(3214.89)))
# print("1100.89={0}".format(Utils.arabic_to_chinese(1100.89)))
# print("1109.89={0}".format(Utils.arabic_to_chinese(1109.89)))
# print("10000.89={0}".format(Utils.arabic_to_chinese(10000.89)))
# print("10001.89={0}".format(Utils.arabic_to_chinese(10001.89)))
# print("10011.89={0}".format(Utils.arabic_to_chinese(10011.89)))
# print("10111.89={0}".format(Utils.arabic_to_chinese(10111.89)))
# print("51231.89={0}".format(Utils.arabic_to_chinese(51231.89)))
# print("61011.89={0}".format(Utils.arabic_to_chinese(61011.89)))
# print("71001.89={0}".format(Utils.arabic_to_chinese(71001.89)))
# print("80100.89={0}".format(Utils.arabic_to_chinese(80100.89)))
# print("80010.89={0}".format(Utils.arabic_to_chinese(80010.89)))
# print("81010.89={0}".format(Utils.arabic_to_chinese(81010.89)))
# print("901000.89={0}".format(Utils.arabic_to_chinese(901000.89)))
# print("800100.89={0}".format(Utils.arabic_to_chinese(800100.89)))
# print("700001.89={0}".format(Utils.arabic_to_chinese(700001.89)))
# print("100011.89={0}".format(Utils.arabic_to_chinese(100011.89)))
# print("100111.89={0}".format(Utils.arabic_to_chinese(100111.89)))
# print("101111.89={0}".format(Utils.arabic_to_chinese(101111.89)))
# print("1001000.89={0}".format(Utils.arabic_to_chinese(1001000.89)))
# print("1000101.89={0}".format(Utils.arabic_to_chinese(1000101.89)))
# print("1020301.89={0}".format(Utils.arabic_to_chinese(1020301.89)))
# print("1320101.89={0}".format(Utils.arabic_to_chinese(1320101.89)))
# print("1002101.89={0}".format(Utils.arabic_to_chinese(1002101.89)))
# print("1010111.89={0}".format(Utils.arabic_to_chinese(1010111.89)))
# print("1101101.89={0}".format(Utils.arabic_to_chinese(1101101.89)))
# print("10203040.89={0}".format(Utils.arabic_to_chinese(10203040.89)))
# print("104030201.89={0}".format(Utils.arabic_to_chinese(104030201.89)))
# print("1405060809.89={0}".format(Utils.arabic_to_chinese(1405060809.89)))
# print("30206070809.89={0}".format(Utils.arabic_to_chinese(30206070809.89)))
# print("303060708090.89={0}".format(Utils.arabic_to_chinese(303060708090.89)))
# print("360306070809.89={0}".format(Utils.arabic_to_chinese(360306070809.89)))
# print("3040506070809.89={0}".format(Utils.arabic_to_chinese(3040506070809.89)))
# print("51040506070809.89={0}".format(Utils.arabic_to_chinese(51040506070809.89)))
# print("123456789012345.67={0}".format(Utils.arabic_to_chinese(123456789012345.67)))
# print("223456789012346.7={0}".format(Utils.arabic_to_chinese(223456789012346.7)))
_logger.debug("323456789012347.08={0}".format(Utils.arabic_to_chinese(323456789012347.08)))
