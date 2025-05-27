# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# 小额数字到汉字的映射
import logging
import re

from pypinyin import lazy_pinyin, Style
from pyzipper import AESZipFile, zipfile, WZ_AES

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

    @staticmethod
    def get_property_cnt_limit(in_args):
        limit_default = 100
        limit_return = limit_default

        # 从tiered_pricing_info_fn文件中读取
        try:
            with AESZipFile(in_args["file_2_customer"], 'r', compression=zipfile.ZIP_DEFLATED,
                            encryption=WZ_AES) as zip_ref:
                # 设置密码
                zip_ref.setpassword(in_args["zip_pwd"].encode('utf-8'))
                if ("tiered_pricing_info_fn" not in in_args.keys()) or \
                        (in_args["tiered_pricing_info_fn"] not in zip_ref.namelist()):
                    return limit_return

                tiered_pricing_zip_info = zip_ref.getinfo(in_args['tiered_pricing_info_fn'])
                file_content = zip_ref.read(tiered_pricing_zip_info)
                context_text = file_content.decode('utf-8').splitlines()
                for each_l in context_text:
                    if "property_limit" in each_l:
                        limit_return = int(each_l.split('=')[1])
                        break

                return limit_return

        except Exception as e:
            _logger.error(f"读取资产条目限制数出错了{e}")
            return limit_return

    @staticmethod
    def get_customer_name_short(in_args):
        name_default = ""
        name_return = name_default

        # 从tiered_pricing_info_fn文件中读取
        try:
            with AESZipFile(in_args["file_2_customer"], 'r', compression=zipfile.ZIP_DEFLATED,
                            encryption=WZ_AES) as zip_ref:
                # 设置密码
                zip_ref.setpassword(in_args["zip_pwd"].encode('utf-8'))
                if ("customer_name_4_pwd_fn" not in in_args.keys()) or \
                        (in_args["customer_name_4_pwd_fn"] not in zip_ref.namelist()):
                    return name_return

                customer_name_4_pwd_zip_info = zip_ref.getinfo(in_args['customer_name_4_pwd_fn'])
                file_content = zip_ref.read(customer_name_4_pwd_zip_info)
                context_text = file_content.decode('utf-8').splitlines()
                for each_l in context_text:
                    name_return = each_l
                    break

                return name_return

        except Exception as e:
            _logger.error(f"读取客户名简拼出错了{e}")
            return name_return

    @staticmethod
    def mixed_sort_key(s):
        """
        最终版混合字符串排序键生成器：
        完全符合以下规则：
        1. 总体排序：数字开头的 → 英文开头的 → 中文开头的
        2. 数字部分：按长度排序，同长度按字典序
        3. 英文部分：按字母顺序（不区分大小写）
        4. 中文部分：按拼音顺序
        5. 混合字符串按开头部分类型分类，后续部分作为次级排序基准
        """
        # 定义特殊字符
        special_chars = r"\-_()~@#&*"

        # 生成不包含特殊字符的纯净版字符串
        clean_str = re.sub(f"[{special_chars}]", "", s)

        # 判断纯净字符串的开头类型
        if re.match(r'^\d', clean_str):  # 数字开头
            type_rank = 0
        elif re.match(r'^[a-zA-Z]', clean_str):  # 英文开头
            type_rank = 1
        else:  # 中文开头
            type_rank = 2

        # 主排序键（数字值/小写英文/拼音）
        if type_rank == 0:
            main_key = int(re.match(r'^\d+', clean_str).group())
        elif type_rank == 1:
            main_key = clean_str.lower()
        else:
            main_key = ''.join(lazy_pinyin(clean_str, style=Style.NORMAL))

        # 检查原字符串是否包含特殊字符
        has_special = any(c in s for c in special_chars)

        # 处理混合字符串中的数字部分（确保数值正确排序）
        def process_mixed(text):
            parts = re.split(r'(\d+)', text)
            processed = []
            for part in parts:
                if part.isdigit():
                    processed.append(f"{int(part):010d}")  # 10位数字，前面补零
                elif part:
                    if re.match(r'^[\u4e00-\u9fff]', part):  # 中文
                        processed.append(''.join(lazy_pinyin(part, style=Style.NORMAL)))
                    else:  # 英文或其他
                        processed.append(part.lower())
            return ''.join(processed)

        # 正确的排序键顺序
        sort_key = (type_rank, process_mixed(clean_str), main_key, has_special, s)
        return sort_key

    @staticmethod
    def compare_strings(a, b):
        """
        比较两个字符串，按照我们的排序规则
        返回:
        - -1 如果 a < b
        - 0  如果 a == b
        - 1  如果 a > b
        """
        key_a = Utils.mixed_sort_key(a)
        key_b = Utils.mixed_sort_key(b)

        if key_a < key_b:
            return -1
        elif key_a == key_b:
            return 0
        else:
            return 1

def main():
    str_list = ["B02", "B-01", "B01", "B10", "B05", "B-05-02", "B-05", "B05-01", "B0101", "B101", "梨树地E-01", "梨树地-01",
                "梨树地01", "梨树地E", "梨树地", "香蕉", "中文100test", "中文50test", "50", "100", "Banana", "apple", "Apple", "第5章", "第10章"]
    sorted_strings = sorted(str_list, key=Utils.mixed_sort_key)
    print(sorted_strings)

    test_pairs = [
        ("10", "10苹果"),
        ("apple", "apple10"),
        ("香蕉", "中文100test"),
        ("50", "100"),
        ("Banana", "apple"),
        ("第5章", "第15章"),
        ("发驾校", "阿布阿")
    ]

    # 测试比较函数
    for a, b in test_pairs:
        result = Utils.compare_strings(a, b)
        if result == -1:
            print(f"'{a}' < '{b}'")
        elif result == 0:
            print(f"'{a}' == '{b}'")
        else:
            print(f"'{a}' > '{b}'")

    args = {
        "file_2_customer": "../../../estate_management.zip",
        "customer_name_4_pwd_fn": "c_info_5_ck",
        "zip_pwd": "491491491Tech+",
    }
    ret_val = Utils.get_customer_name_short(args)
    print(ret_val)

    args = {
        "file_2_customer": "../../../estate_management.zip",
        "tiered_pricing_info_fn": "c_info_4_ck",
        "zip_pwd": "491491491Tech+" + ret_val,
    }
    print("491491491Tech+" + ret_val)
    ret_val = Utils.get_property_cnt_limit(args)
    print(ret_val)

if __name__ == "__main__":
    main()
# 示例
# print("0={0}".format(Utils.arabic_to_chinese(0)))
# print("303060708090.89={0}".format(Utils.arabic_to_chinese(303060708090.89)))
# print("360306070809.89={0}".format(Utils.arabic_to_chinese(360306070809.89)))
# print("3040506070809.89={0}".format(Utils.arabic_to_chinese(3040506070809.89)))
# print("51040506070809.89={0}".format(Utils.arabic_to_chinese(51040506070809.89)))
# print("123456789012345.67={0}".format(Utils.arabic_to_chinese(123456789012345.67)))
# print("223456789012346.7={0}".format(Utils.arabic_to_chinese(223456789012346.7)))
# _logger.debug("323456789012347.08={0}".format(Utils.arabic_to_chinese(323456789012347.08)))
