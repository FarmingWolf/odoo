# -*- coding: utf-8 -*-
import datetime
import logging
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
import zipfile
from collections import deque
from tkinter.font import Font

import psutil
import pyzipper
import requests
import win32file
import tkinter as tk
from tkinter import ttk, simpledialog, font
from tkinter import PhotoImage
from datetime import datetime
from pyzipper import AESZipFile, WZ_AES

from dateutil.relativedelta import relativedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# class LogHandler(FileSystemEventHandler):
#     def on_modified(self, event):
#         # 当文件被修改时，打印出通知
#         print(f"Hey, {event.src_path} has been modified!")


action_type = "zip"
# action_type = "unzip" attention!!!
"""

pyinstaller -F startup.py -i ./img/491logo.png --noconsole
xcopy /d /y .\dist\startup.exe .\


"""

zip_tgt_folders = [
    'estate',
    'estate_lease_contract',
    'utils',
    'parking',
    'estate_registration_addr',
    'event_option',
    'event_extend',
    'operation_contract',
    'accounting_subject',
    'business_items',
    'operation_contract_event_settle_account',
    'wechat',
    'contacts',
    'estate_dashboard',
    'estate_account',
]

zip_all_addons = True
tmp_fn = "estate_management.x_pptx"
customer_dis_name = "中广艺伍零"
customer_name = "E50"
# 初始化时，仅客户名写入此文件，第一次运行时，客户mac地址写入此文件，压缩包里必须有此文件，如无则判错
customer_name_info_fn = "c_info_2_ck"
out_zip_fld = "../em/"
in_zip_file = out_zip_fld + tmp_fn
tgt_file_pt = "../addons/"
zip_pwd = "491491491Tech+" + customer_name
product_code = customer_name + "@" + zip_pwd
# 压缩空文件夹用文件名
kara_fn = "491Tech.em"

out_zip_file = in_zip_file
fn_2_customer = "estate_management.zip"
file_2_customer = "../" + fn_2_customer  # attention!!!密码如上，压缩对象就一个文件：in_zip_file
py_f_subfix = ".y_pptx"
client_env_code_page = 'cp936'

start_event = threading.Event()

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
# 1.创建一个把日志信息存储到文件中的处理器
# 要加编码，不然后可能会乱码
logFileNM = os.getcwd() + r".\start.log"
fh = logging.FileHandler(logFileNM, encoding="utf-8")
fh.setFormatter(logging.Formatter(fmt="%(asctime)s %(filename)s %(funcName)s %(lineno)d行 %(levelname)s "
                                      "%(message)s ", datefmt="%Y/%m/%d/%X"))
# 2.把文件处理器，加载到logger中
_logger.addHandler(fh)

# 进度条
root = tk.Tk()
root.geometry("900x400")
my_font = font.Font(size=16, weight='bold')
customer_info_label = tk.Label(root, text="", font=my_font)
customer_info_label.grid(row=0, column=0, columnspan=7, sticky=tk.W, padx=(20, 0), pady=(20, 0))

# 创建一个进度条
progress_bar = ttk.Progressbar(root, orient="horizontal", length=600, mode="determinate")
progress_bar.grid(row=1, column=1, columnspan=7, padx=(150, 0), pady=(70, 20))

# 创建一个标签用于显示进度文本
progress_label = tk.Label(root, text="", font=my_font)
progress_label.grid(row=2, column=1, columnspan=7, padx=(20, 0), pady=20)


# 创建一个停止标志
stop_event = threading.Event()
unzip_event_success = threading.Event()
unzip_event_failed = threading.Event()
input_p_code_recheck = threading.Event()
server_start_success = threading.Event()

em_server_conf_file = '../debian/odoo.conf'
conf_config = {}
icon_file = tk.PhotoImage(file='./img/491logo.png')
url = "http://localhost:8069"
browser_opened_event = threading.Event()
web_server_process = None
main_process = 0


def get_mac_address():
    try:
        mac_lst = []
        # 使用 ipconfig /all 命令获取网络信息
        command_output = subprocess.check_output(["ipconfig", "/all"]).decode(client_env_code_page)
        _logger.debug(f"command_output={command_output}")
        block_s = False
        lines = command_output.splitlines()
        for cmd_line in lines:
            # 查找包含 Physical Address 或者 物理地址 的行
            if '网适配器' in cmd_line:
                block_s = True

            if block_s:
                mac_address_search = re.search(r'Physical Address.*: (.*)', cmd_line)
                if not mac_address_search:
                    # 如果没有找到, 尝试另一种可能的格式
                    mac_address_search = re.search(r'物理地址.*: (.*)', cmd_line)

                if mac_address_search:
                    # 清除可能存在的空格，并返回MAC地址
                    mac_lst.append(mac_address_search.group(1).strip())
                    block_s = False

        return mac_lst

    except Exception as ex:
        _logger.error(f"发生未知错误：{ex}{ex.with_traceback}")
        traceback.print_exc()
        return []


def add_file_2_zip_with_password(input_filename, name_in_zip, tmp_z_fn, password, in_zip_type, output_filename=None):
    """
    使用pyzipper库将文件压缩为带密码的ZIP文件。
    :param input_filename: 要压缩的文件的路径
    :param name_in_zip: ZIP文件中的文件名
    :param tmp_z_fn: 临时文件名，最终替换为output_filename
    :param password: ZIP文件的解压密码
    :param in_zip_type: w/a
    :param output_filename: 最终输出的ZIP文件的路径
    """
    # 使用AES加密压缩文件
    with AESZipFile(tmp_z_fn, in_zip_type, compression=zipfile.ZIP_DEFLATED, encryption=WZ_AES) as zf:
        zf.setpassword(password.encode())  # 设置密码，需要转换为bytes
        zf.write(input_filename, arcname=name_in_zip)  # 将文件添加到ZIP中

    if output_filename:
        if os.path.exists(output_filename):
            os.remove(output_filename)
        os.rename(tmp_z_fn, output_filename)


def read_conf_file():
    config = {}

    # 打开文件并逐行读取
    with open(em_server_conf_file, 'r', encoding='utf-8') as file:
        for line in file:
            # 移除行尾的换行符，并忽略注释行和空行
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('['):
                continue

            # 拆分行内容为键和值
            try:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
            except ValueError:  # 没有找到等号
                print(f"警告: 忽略无效行 {line}")

    return config


def set_button_bg(in_action_type):
    if in_action_type == 'zip':
        bg_color = "#bee9ee"
        start_distribute_button.config(text="制作文件")
    else:
        bg_color = "#c6c6c6"

    button_font = Font(family='宋体', size=10, weight='bold')
    start_distribute_button.config(bg=bg_color, fg="black", font=button_font)
    stop_server_button.config(bg=bg_color, fg="black", font=button_font)
    close_button.config(bg=bg_color, fg="black", font=button_font)


def init_param():
    if action_type == 'zip':
        customer_info_label.config(text=f"为{customer_dis_name}打包产品文件！")
        root.title("资产管理服务平台产品发布进度提示——491Tech")

    if action_type == 'unzip':
        customer_info_label.config(text=f"{customer_dis_name}专用版")
        root.title("资产管理服务平台启动进度提示——491Tech")

    set_button_bg(action_type)
    root.iconphoto(True, icon_file)
    # 读取conf文件
    global conf_config
    conf_config = read_conf_file()


def walk_and_delete_folder(del_tgt_folder):
    for root_fld, dirs, files in os.walk(del_tgt_folder):
        for folder in dirs:
            folder_path = os.path.join(root_fld, folder)
            sub_fld = os.listdir(folder_path)
            if sub_fld and len(sub_fld) > 0:
                walk_and_delete_folder(folder_path)
            else:
                os.removedirs(folder_path)


def delete_files():
    for tgt_fld in zip_tgt_folders:
        # 遍历目录树
        for root_fld, dirs, files in os.walk(tgt_file_pt + tgt_fld):
            for file in files:
                # 获取文件绝对路径
                file_path = os.path.join(root_fld, file)
                os.remove(file_path)

        # 服务器启动失败，只删除文件，不删除文件夹
        # walk_and_delete_folder(tgt_file_pt + tgt_fld)


def zip_tgt_files(in_root, in_label, in_bar):

    try:
        # 先创建一个空文件，最后删除
        if not os.path.exists(out_zip_fld + kara_fn):
            with open(out_zip_fld + kara_fn, 'a', encoding='utf-8') as file:
                file.write('')

        for tgt_fld in zip_tgt_folders:
            if not os.path.exists(tgt_file_pt + tgt_fld):
                _logger.info(f"源目录 {tgt_file_pt + tgt_fld} 不存在。")
                return

        # 创建ZIP文件对象
        # with zipfile.ZipFile(out_zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        with AESZipFile(out_zip_file, 'w', compression=zipfile.ZIP_DEFLATED, encryption=WZ_AES) as zipf:
            # 设置密码
            zipf.setpassword(zip_pwd.encode('utf-8'))
            fld_cnt = 0
            file_cnt = 0
            for tgt_fld in zip_tgt_folders:
                if stop_event.is_set():  # 检查是否应该停止
                    break
                fld_cnt += 1
                # 遍历目录树
                for root_fld, dirs, files in os.walk(tgt_file_pt + tgt_fld):
                    if stop_event.is_set():  # 检查是否应该停止
                        break
                    for file in files:
                        if stop_event.is_set():  # 检查是否应该停止
                            break
                        file_cnt += 1
                        in_label.config(text=f"正在处理模块{fld_cnt}/{len(zip_tgt_folders)}，文件数{file_cnt}个")
                        in_root.update_idletasks()
                        # 获取文件绝对路径
                        file_path = os.path.join(root_fld, file)
                        # 在ZIP文件中的相对路径
                        arcname = os.path.relpath(file_path, tgt_file_pt)
                        # 添加文件到ZIP
                        if arcname.endswith(".py"):
                            arcname = arcname.replace(".py", py_f_subfix)
                        _logger.debug(f"压缩文件：{arcname}")
                        zipf.write(file_path, arcname)

                    # 空目录也压缩
                    sub_fld = os.listdir(root_fld)
                    if sub_fld and len(sub_fld) > 0:
                        pass
                    else:
                        empy_fld_nm = os.path.relpath(root_fld, tgt_file_pt)
                        zip_info = zipfile.ZipInfo(os.path.join(empy_fld_nm, kara_fn))
                        _logger.debug(f"压缩空文件夹：{zip_info.filename}。")
                        zipf.write(out_zip_fld + kara_fn, zip_info.filename)

                in_bar['value'] = fld_cnt / len(zip_tgt_folders) * 100
                in_root.update_idletasks()

        in_bar['value'] = 100
        in_label.config(text=f"已处理模块{fld_cnt}/{len(zip_tgt_folders)}，文件数{file_cnt}个\n"
                             f"正在做最后大文件压缩……")
        in_root.update_idletasks()

        # 客户信息初始化文件
        if os.path.exists(out_zip_fld + customer_name_info_fn):
            os.remove(out_zip_fld + customer_name_info_fn)

        with open(out_zip_fld + customer_name_info_fn, 'a', encoding='utf-8') as file:
            file.write(customer_dis_name + "\n")

        # 将上述文件压缩至zip
        with AESZipFile(file_2_customer, 'w', compression=zipfile.ZIP_DEFLATED, encryption=WZ_AES) as zip_f_2_c:
            zip_f_2_c.setpassword(zip_pwd.encode('utf-8'))
            zip_f_2_c.write(out_zip_file, tmp_fn)
            zip_f_2_c.write(out_zip_fld + customer_name_info_fn, customer_name_info_fn)

        _logger.info(f"压缩完成，ZIP文件保存在 {file_2_customer} 。")
        in_label.config(text=f"压缩完成，ZIP文件保存在 {file_2_customer} 。确认文件位置，关闭此窗口！")
        in_root.update_idletasks()
        return True
    except Exception as ex:
        _logger.info(f"制作文件发生未知错误: {ex}{ex.with_traceback}")
        traceback.print_exc()
        return False
    finally:
        # 删除空文件
        if os.path.exists(out_zip_fld + kara_fn):
            os.remove(out_zip_fld + kara_fn)
        # 删除tmp文件
        if os.path.exists(out_zip_file):
            os.remove(out_zip_file)
        if os.path.exists(out_zip_fld + customer_name_info_fn):
            os.remove(out_zip_fld + customer_name_info_fn)


def unzip_customer_file_with_progress(in_root, in_label, in_bar, in_mac_lst):
    try:
        _logger.info("开始解压缩……")
        # with zipfile.ZipFile(file_2_customer, 'r') as zip_ref:
        with AESZipFile(file_2_customer, 'r', compression=zipfile.ZIP_DEFLATED, encryption=WZ_AES) as zip_ref:
            # 设置密码
            zip_ref.setpassword(zip_pwd.encode('utf-8'))
            # 解压所有文件到目标目录，实际上就2个文件
            for member in zip_ref.namelist():
                if stop_event.is_set():  # 检查是否应该停止
                    txt_info = f"用户主动停止"
                    _logger.info(txt_info)
                    in_label.config(text=txt_info)
                    in_root.update_idletasks()
                    unzip_event_failed.set()
                    return False

                # 获取文件的完整路径
                if not member.endswith(tmp_fn) and not member.endswith(customer_name_info_fn):
                    txt_info = f"基础文件损坏，zip文件中的文件：{tmp_fn}并非资产管理平台用文件！"
                    _logger.error(txt_info)
                    in_label.config(text=txt_info)
                    in_root.update_idletasks()
                    unzip_event_failed.set()
                    return False

                if member.endswith(customer_name_info_fn):
                    continue

                # 获取文件信息
                member_zip = zip_ref.getinfo(member)
                total_bytes = member_zip.file_size
                extracted_bytes = 0

                if os.path.exists(out_zip_file):
                    os.remove(out_zip_file)
                # 提取文件
                # 打开ZIP文件中的成员，并逐块读取以跟踪进度
                with zip_ref.open(member_zip) as source, open(out_zip_file, 'wb') as target:
                    while True:
                        if stop_event.is_set():  # 检查是否应该停止
                            txt_info = f"用户主动停止"
                            _logger.info(txt_info)
                            in_label.config(text=txt_info)
                            in_root.update_idletasks()
                            unzip_event_failed.set()
                            return False
                        chunk = source.read(1024 * 1024)  # 每次读取1MB的数据
                        if not chunk:
                            break
                        target.write(chunk)
                        extracted_bytes += len(chunk)
                        _logger.info(f"已解压{round(extracted_bytes / 1024 / 1024 * 10)}M/"
                                     f"{round(total_bytes / 1024 / 1024 * 10)}M")
                        in_bar['value'] = extracted_bytes / total_bytes * 100
                        in_label.config(text=f"已解压{round(extracted_bytes / 1024 / 1024 * 10)}M/"
                                             f"{round(total_bytes / 1024 / 1024 * 10)}M")
                        in_root.update_idletasks()

                _logger.info(f"zip解压缩完成：{extracted_bytes}")
            return True
    except RuntimeError as e:
        _logger.info(f"zip解压时发生错误: {e}{e.with_traceback}")
        traceback.print_exc()
        unzip_event_failed.set()
        return False
    except Exception as e:
        _logger.info(f"zip解压发生未知错误: {e}{e.with_traceback}")
        traceback.print_exc()
        unzip_event_failed.set()
        return False
    finally:
        if os.path.exists(out_zip_file):
            file_attributes = win32file.GetFileAttributes(out_zip_file)
            new_attributes = file_attributes | win32file.FILE_ATTRIBUTE_HIDDEN
            win32file.SetFileAttributes(out_zip_file, new_attributes)


def rezip_customer_file(in_root, in_label, in_bar):
    # 把添加了mac地址的文件加密压回去
    try:
        tmp_z_fn = "../" + datetime.today().strftime("%Y%m%d%H%M%S")
        in_label.config(text="程序正在执行……")
        in_root.update_idletasks()
        add_file_2_zip_with_password(out_zip_fld + customer_name_info_fn, customer_name_info_fn, tmp_z_fn, zip_pwd, 'w')
        if os.path.exists(out_zip_fld + customer_name_info_fn):
            os.remove(out_zip_fld + customer_name_info_fn)

        in_label.config(text="准备部署服务器资源……")
        in_root.update_idletasks()
        add_file_2_zip_with_password(in_zip_file, tmp_fn, tmp_z_fn, zip_pwd, 'a', file_2_customer)
        return True
    except RuntimeError as e:
        _logger.info(f"rezip时发生错误: {e}{e.with_traceback}")
        traceback.print_exc()
        in_label.config(text="rezip时发生错误，请关闭窗口，关闭杀毒软件后，重新启动！")
        in_root.update_idletasks()
        if os.path.exists(tmp_z_fn):
            os.remove(tmp_z_fn)
        return False
    except Exception as ex:
        _logger.info(f"rezip发生未知错误: {ex}{ex.with_traceback}")
        traceback.print_exc()
        in_label.config(text="rezip时发生未知错误，请关闭窗口，关闭杀毒软件后，重新启动！")
        in_root.update_idletasks()
        if os.path.exists(tmp_z_fn):
            os.remove(tmp_z_fn)
        return False


def product_licence_check(in_root, in_label, in_bar, in_mac_list):
    try:
        _logger.info("开始验证产本版权……")
        with pyzipper.AESZipFile(file_2_customer, 'r',
                                 compression=zipfile.ZIP_DEFLATED, encryption=WZ_AES) as zip_ref:
            # 设置密码
            zip_ref.setpassword(zip_pwd.encode('utf-8'))
            if customer_name_info_fn not in zip_ref.namelist():
                txt_info = f"基础文件损坏，找不到：{customer_name_info_fn}，可能被人为删除。请联系管理员解决。"
                _logger.error(txt_info)
                in_label.config(text=txt_info)
                in_root.update_idletasks()
                unzip_event_failed.set()
                return False, False

            zip_info = zip_ref.getinfo(customer_name_info_fn)
            zip_ref.extract(zip_info, out_zip_fld)
            if not os.path.exists(out_zip_fld + customer_name_info_fn):
                txt_info = f"基础文件损坏，文件解压后丢失：{customer_name_info_fn}，请确认本机杀毒软件处于关闭状态。"
                _logger.error(txt_info)
                in_label.config(text=txt_info)
                in_root.update_idletasks()
                unzip_event_failed.set()
                return False, False

            mac_lst_in_f = []
            customer_name_in_f = ""
            with open(out_zip_fld + customer_name_info_fn, 'r', encoding='utf-8') as info_file:
                line_cnt = 0
                for line in info_file:
                    txt_line = line.strip()
                    if txt_line:
                        line_cnt += 1

                    if line_cnt == 1:
                        customer_name_in_f = txt_line
                    if line_cnt > 1:
                        mac_lst_in_f.append(txt_line)

            if not customer_name_in_f:
                txt_info = f"基础文件损坏，文件内容错误：{customer_name_info_fn}，该文件可能遭到人为破坏。"
                _logger.error(txt_info)
                in_label.config(text=txt_info)
                in_root.update_idletasks()
                unzip_event_failed.set()
                return False, False

            if not mac_lst_in_f:
                if not check_product_code(entry_var.get(), product_code):

                    entry_product_code.config(state=tk.NORMAL)
                    txt_info = f"该版本是北京四九一科技有限公司为{customer_name_in_f}开发的专业版产品！\n" \
                               f"请在下方【产品编码】输入框输入正确的产品编码后，再点击【开始/启动】按钮！"
                    start_distribute_button.config(state=tk.NORMAL)
                    _logger.error(txt_info)
                    in_label.config(text=txt_info)
                    in_root.update_idletasks()
                    unzip_event_failed.set()
                    input_p_code_recheck.set()
                    return False, False

                # 产品编码正确，将本机mac地址加进customer_name_info_fn
                with open(out_zip_fld + customer_name_info_fn, 'a', encoding='utf-8') as info_file:
                    for mac in in_mac_list:
                        info_file.write(mac + "\n")

                return True, True

            else:
                for mac in mac_lst_in_f:
                    if mac in in_mac_list:
                        return True, False
                # 如果文件中的地址与本机地址一个都匹配不上，说明产品被拷贝至其他环境了
                txt_info = f"该版本是四九一科技有限公司为{customer_name_in_f}开发的专业版产品！不能再其他环境下使用！"
                _logger.error(txt_info)
                in_label.config(text=txt_info)
                in_root.update_idletasks()
                unzip_event_failed.set()
                return False, False

    except Exception as ex:
        _logger.error(f"版权验证中发生未知错误{ex}{ex.with_traceback}")
        traceback.print_exc()
        txt_info = f"软件基础文件包发生未知错误，请关闭后重试！"
        _logger.error(txt_info)
        in_label.config(text=txt_info)
        in_root.update_idletasks()
        unzip_event_failed.set()

        if os.path.exists(out_zip_fld + customer_name_info_fn):
            os.remove(out_zip_fld + customer_name_info_fn)
        if os.path.exists(out_zip_file):
            os.remove(out_zip_file)

        return False, False
    finally:
        if os.path.exists(out_zip_fld + customer_name_info_fn):
            file_attributes = win32file.GetFileAttributes(out_zip_fld + customer_name_info_fn)
            new_attributes = file_attributes | win32file.FILE_ATTRIBUTE_HIDDEN
            win32file.SetFileAttributes(out_zip_fld + customer_name_info_fn, new_attributes)


def unzip_files(in_root, in_label, in_bar):
    if not os.path.exists(file_2_customer):
        txt_info = f"基础文件 {file_2_customer} 不存在。"
        _logger.info(txt_info)
        in_label.config(text=txt_info)
        in_root.update_idletasks()
        unzip_event_failed.set()
        return False

    # 读取本机mac address
    mac_list = get_mac_address()
    if not mac_list:
        txt_info = f"本机没有网络配置，不具备部署本产品的条件！"
        _logger.error(txt_info)
        in_label.config(text=txt_info)
        in_root.update_idletasks()
        unzip_event_failed.set()
        return False

    # check结果和重写zip文件
    ck_rst, rezip = product_licence_check(in_root, in_label, in_bar, mac_list)
    if not rezip:
        if os.path.exists(out_zip_fld + customer_name_info_fn):
            os.remove(out_zip_fld + customer_name_info_fn)
        if os.path.exists(out_zip_file):
            os.remove(out_zip_file)

    if not ck_rst:
        txt_info = f"产品版权验证失败！"
        _logger.error(txt_info)
        # in_label.config(text=txt_info)
        in_root.update_idletasks()
        unzip_event_failed.set()
        return False

    if not unzip_customer_file_with_progress(in_root, in_label, in_bar, mac_list):
        txt_info = f"基础文件 {file_2_customer} 解压出错，请关闭杀毒软件后重试！"
        _logger.error(txt_info)
        in_label.config(text=txt_info)
        in_root.update_idletasks()
        unzip_event_failed.set()
        return False

    if not os.path.exists(in_zip_file):
        txt_info = f"解压后文件 {in_zip_file} 丢失，请关闭杀毒软件后重试！"
        _logger.error(txt_info)
        in_label.config(text=txt_info)
        in_root.update_idletasks()
        unzip_event_failed.set()
        return False

    if not os.path.exists(tgt_file_pt):
        os.makedirs(tgt_file_pt)

    if rezip:
        if not rezip_customer_file(in_root, in_label, in_bar):
            unzip_event_failed.set()

    try:
        txt_info = f"开始部署服务器必须资源"
        _logger.info(txt_info)
        in_label.config(text=txt_info)
        in_root.update_idletasks()
        # with zipfile.ZipFile(in_zip_file, 'r') as zip_ref:
        with pyzipper.AESZipFile(in_zip_file, 'r',
                                 compression=zipfile.ZIP_DEFLATED, encryption=WZ_AES) as zip_ref:
            # 设置密码
            zip_ref.setpassword(zip_pwd.encode('utf-8'))
            file_cnt = len(zip_ref.namelist())
            file_extracted = 0
            # 解压所有文件到目标目录
            for member in zip_ref.namelist():
                # 获取文件的完整路径
                target_path = os.path.join(tgt_file_pt, member)

                # 如果目标路径是一个目录，则创建它
                if member.endswith('/'):
                    _logger.debug(f"创建文件夹：{target_path}")
                    os.makedirs(target_path, exist_ok=True)
                else:
                    # 如果目标路径是一个文件并且已经存在，则删除它
                    if target_path.endswith(py_f_subfix):
                        target_path = target_path.replace(py_f_subfix, ".py")

                    if os.path.exists(target_path):
                        os.remove(target_path)

                    # 提取文件
                    zip_info = zip_ref.getinfo(member)
                    filename = os.path.basename(member)
                    zip_ref.extract(zip_info, tgt_file_pt)
                    if filename.endswith(py_f_subfix):
                        new_fn = (tgt_file_pt + zip_info.filename).replace(py_f_subfix, ".py")
                        # _logger.debug(f"生成文件：{new_fn}")
                        os.renames(tgt_file_pt + zip_info.filename, new_fn)
                    file_extracted += 1

                in_bar['value'] = file_extracted / file_cnt * 100
                in_label.config(text=f"开始部署服务器必须资源，已部署{file_extracted}/{file_cnt}")
                in_root.update_idletasks()

            _logger.info("部署完成。")

        in_label.config(text=f"已完成部署，开始启动服务……")
        in_root.update_idletasks()
        unzip_event_success.set()
        return True
    except RuntimeError as e:
        _logger.info(f"部署时发生错误: {e.with_traceback}")
        traceback.print_exc()
        return False
    except Exception as e:
        _logger.info(f"部署发生未知错误: {e.with_traceback}")
        traceback.print_exc()
        return False
    finally:
        os.remove(in_zip_file)


def start_em_server(in_root, in_label, in_bar):
    cmd_1 = f'cd /d D:\\users\\Admin\\Documents\\GitHub\\farmingwolf\\"'
    """cmd_2 = f"python ../odoo-bin -c ../debian/odoo.conf -r 491oddevadm -w 491491491 --addons-path=addons 
            f"-d postgres " \
            f"-u utils,parking,estate_registration_addr,estate,estate_lease_contract,event_option,event_extend," \
            f"operation_contract,accounting_subject,business_items,operation_contract_event_settle_account,wechat," \
            f"contacts,estate_dashboard --dev xml --log-handler odoo.tools.convert:DEBUG"
    """
    # 调用Windows命令提示符执行命令
    result = subprocess.run(['cmd', '/c', cmd_1], capture_output=True, text=True)
    # 打印输出结果
    _logger.info(f"result={result}")
    _logger.info(f"result.returncode={result.returncode}")
    _logger.info(result.stdout)
    if result.returncode != 0:
        _logger.info(result.stderr)

    command = ['cmd', '/c', "python ../odoo-bin "]
    command.extend(['-c', em_server_conf_file])
    command.extend(['-w', '491491491'])
    command.extend(['-r', '491oddevadm'])
    command.extend(['--addons-path', '../addons'])
    command.extend(['-d', 'postgres'])
    em_addons = f"utils,parking,estate_registration_addr,estate,estate_lease_contract,event_option,event_extend," \
                f"operation_contract,accounting_subject,business_items,operation_contract_event_settle_account," \
                f"wechat,contacts,estate_dashboard"
    command.extend(['-u', em_addons])

    _logger.debug(f"command={command}")
    try:
        global web_server_process
        web_server_process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
        _logger.info("启动服务执行中……")
        start_event.set()
        web_server_process.wait()
    except Exception as e:
        _logger.info(f"启动错误:{e}{e.with_traceback}")
        traceback.print_exc()
        sys.exit(1)


def tail(file_path, n=10):
    """从给定的文件中读取最后 n 行"""
    with open(file_path, 'r') as f:
        return deque(f, n)


def update_log_and_progress(in_root, in_label, in_bar):
    while not start_event.is_set():
        time.sleep(1)

    pattern = r'\(\d+/\d+\)'
    pattern_end = r'\d{3} modules loaded in \d+\.\d+s'
    pattern_time = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}'
    in_label.config(text="资产管理平台启动中……")
    in_bar['value'] = 0
    in_root.update_idletasks()
    _logger.debug(f"日志文件：{conf_config['logfile']}")
    while in_bar['value'] < 100:
        time.sleep(1)
        in_bar['value'] += 1
        in_root.update_idletasks()
        lines_read = tail(conf_config['logfile'], 10)
        _logger.debug(f"lines_read={lines_read}")
        # 初始化时log为空
        time_waited = 1
        max_wait = 100
        while not lines_read:
            time_waited += 1
            if time_waited > max_wait:
                break
            time.sleep(1)
            lines_read = tail(conf_config['logfile'], 10)

        # 万一日志文件的输出有问题，也不能无限等待下去
        times_wait = 0
        latest_time_read = ""
        while not server_start_success.is_set():
            times_wait += 1
            in_bar['value'] = times_wait if times_wait > in_bar['value'] else in_bar['value']
            in_root.update_idletasks()
            time.sleep(1)
            if times_wait > max_wait:
                break

            lines_read = tail(conf_config['logfile'], 10)
            latest_time_read_in_these_lines = ""
            these_lines_all_error = True
            for line in lines_read:
                _logger.debug(f"一行日志line={line}")
                line = line.strip()
                if not line:
                    _logger.debug(f"not line={line}")
                    continue
                # 取出年月日时分秒
                log_time_match = re.findall(pattern_time, line)
                _logger.debug(f"log_time_match={log_time_match}；latest_time_read={latest_time_read}")
                if log_time_match:
                    these_lines_all_error = False
                    log_time = log_time_match[0]
                    if log_time > latest_time_read_in_these_lines:
                        latest_time_read_in_these_lines = log_time
                    if log_time > latest_time_read:
                        latest_time_read = log_time
                    # 如果日志时间比刚才读出的时间还小，说明log文件尚未更新又都出来了
                    if log_time < latest_time_read:
                        time.sleep(5)
                        break
                else:
                    continue

                # tgt_time = datetime.now() - relativedelta(hours=8, minutes=10)
                # _logger.debug(f"log_time{log_time}与tgt_time{tgt_time}比较")
                # if log_time < tgt_time.strftime("%Y-%m-%d %H:%M:%S"):
                #     _logger.debug(f"再等一圈")
                #     time.sleep(1)
                #     break

                if "INFO postgres odoo.modules.loading load_module_graph" in line and "Loading module" in line:
                    matches = re.findall(pattern, line)
                    if matches:
                        _logger.info(f"启动进度：{matches}")
                        number_s = re.findall(r'\d+', matches[0])
                        tmp_v = int(number_s[0]) / int(number_s[1]) * 100
                        in_bar['value'] = tmp_v if tmp_v > in_bar['value'] else in_bar['value']
                        in_root.update_idletasks()
                end_matches = re.findall(pattern_end, line)
                if end_matches or "Registry loaded in " in line or 'Bus.loop listen imbus on db' in line:
                    _logger.info(f"启动进度直达最后：{end_matches}或者'Registry loaded in'或者'Bus.loop listen imbus on db'")
                    # 保险起见，还是得看is_server_started
                    if is_server_started(in_root, in_label, in_bar):
                        in_bar['value'] = 100
                        in_root.update_idletasks()
                        server_start_success.set()

    # 根据实际情况看，一般不超过100s
    if server_start_success.is_set():
        server_started = True
    else:
        server_started = is_server_started(in_root, in_label, in_bar)

    if server_started:
        _logger.info(f"服务器启动成功！请打开浏览器访问:{url}")

        in_label.config(text="资产管理平台运行中，请勿关闭此窗口！")
        in_bar['value'] = 100
        in_root.update_idletasks()
        if not browser_opened_event.is_set():
            webbrowser.open_new_tab(url)
            browser_opened_event.set()
        time.sleep(60)
        rem_py_files()
        stop_server_button.config(state=tk.NORMAL)
        in_root.update_idletasks()
    else:
        _logger.info("服务器启动失败……")
        in_label.config(text="服务器启动失败……请关闭窗口，重新启动！")
        in_root.update_idletasks()
        # 删除文件
        delete_files()


def is_server_started(in_root, in_label, in_bar, retry_times=None):

    _logger.info("服务器状态校验")
    in_label.config(text=f"资产管理平台启动状态校验中……")
    if retry_times:
        if retry_times > 3:
            return False
        else:
            retry_times += 1
    else:
        retry_times = 1

    in_bar['value'] = retry_times / 3 * 100
    in_root.update_idletasks()

    try:
        response = requests.get(url)
        if response.status_code == 200:
            _logger.info("服务器启动完毕")
            in_label.config(text=f"资产管理平台启动完毕……")
            in_bar['value'] = 100
            in_root.update_idletasks()
            stop_server_button.config(state=tk.NORMAL)
            in_root.update_idletasks()
            if not browser_opened_event.is_set():
                webbrowser.open_new_tab(url)
                browser_opened_event.set()
            return True
        else:
            _logger.info(f"服务器启动失败 status code={response.status_code}。自动再尝试……")
            time.sleep(5)
            is_server_started(in_root, in_label, in_bar, retry_times)
            return False
    except requests.ConnectionError as e:
        _logger.info(f"服务器连接失败。{e.with_traceback}")
        traceback.print_exc()
        time.sleep(5)
        is_server_started(in_root, in_label, in_bar, retry_times)
        return False


def rem_py_files():
    for tgt_fld in zip_tgt_folders:
        # 遍历目录树
        for root_fld, dirs, files in os.walk(tgt_file_pt + tgt_fld):
            for file in files:
                # 获取文件绝对路径
                file_path = os.path.join(root_fld, file)
                if file_path.endswith(".py"):
                    os.remove(file_path)


def start_web_server(in_root, in_label, in_bar):
    # 启动服务，还没解压完成就等待
    _logger.info(f"等待解压完成……")
    while not unzip_event_success.is_set():
        _logger.debug(f"在解压中等待还是在等待中消亡……这是个问题")
        time.sleep(1)
        # 明确的解压错误，同时不是要求重新输入产品编码再校验
        if unzip_event_failed.is_set() and not input_p_code_recheck.is_set():
            _logger.info(f"启动错误:初始化文件错误！")
            sys.exit(1)

    _logger.info(f"开始启动服务……")
    # 解压完成，就启动，内部另起子线程来启动server
    start_em_server(in_root, in_label, in_bar)
    return True


def main():
    global main_process
    main_process += 1
    try:
        progress_bar['value'] = 0
        progress_label.config(text="开始处理...")
        root.update_idletasks()  # 更新GUI，确保进度条立即反映变化
        start_distribute_button.config(state=tk.DISABLED)
        if zip_all_addons:

            progress_label.config(text=f"即将处理模块{len(zip_tgt_folders)}个")
            root.update_idletasks()  # 更新GUI，确保进度条立即反映变化
            for root_fld, dirs, files in os.walk(tgt_file_pt):
                if root_fld == tgt_file_pt:
                    for each_dir in dirs:
                        if os.path.basename(each_dir) not in zip_tgt_folders:
                            zip_tgt_folders.append(os.path.basename(each_dir))
                            progress_label.config(text=f"即将处理模块{len(zip_tgt_folders)}个")
                            root.update_idletasks()  # 更新GUI，确保进度条立即反映变化
                else:
                    break

        _logger.debug(f"zip_tgt_folders{len(zip_tgt_folders)}个={zip_tgt_folders}")

        if action_type == "unzip":
            # 当检查产品编码出错，要求输入产品编码时，要避免主线程中的逻辑重复
            # 先解压缩，部署
            thread_unzip = threading.Thread(target=unzip_files, name="ThreadUnzipTgtFiles",
                                            args=(root, progress_label, progress_bar))
            thread_unzip.daemon = True
            thread_unzip.start()
            if main_process == 1:
                # 另起线程启动服务
                thread_start_webserver = threading.Thread(target=start_web_server, name="ThreadStartWebServer",
                                                          args=(root, progress_label, progress_bar))
                thread_start_webserver.daemon = True
                thread_start_webserver.start()

                # 另起线程观察服务启动状态
                thread_log_progress = threading.Thread(target=update_log_and_progress, name="ThreadLogProcess",
                                                       args=(root, progress_label, progress_bar))
                thread_log_progress.daemon = True
                thread_log_progress.start()

        elif action_type == "zip":
            thread_zip_tgt = threading.Thread(target=zip_tgt_files, name="ThreadZipTgtFiles",
                                              args=(root, progress_label, progress_bar))
            thread_zip_tgt.daemon = True
            thread_zip_tgt.start()

        else:
            _logger.info(f"action_type={action_type}，Nothing done.")

    except Exception as e:
        _logger.info(f"main启动错误:{e}{e.with_traceback}")
        traceback.print_exc()
        sys.exit(1)


def close_window():
    try:
        stop_web_server()
        # 设置标志位以便工作线程检查并退出
        stop_event.set()
        root.after(100, root.destroy)  # 给线程一些时间来检查标志位
    except Exception as e:
        _logger.info(f"停止服务发生未知错误: {e}{e.with_traceback}")
        traceback.print_exc()
        sys.exit(1)


def stop_web_server():
    global web_server_process
    if web_server_process:
        process = psutil.Process(web_server_process.pid)
        for child in process.children(recursive=True):  # 先杀死子进程
            child.kill()
        process.kill()
        web_server_process = None  # 最后杀死父进程

    progress_label.config(text="资产租赁管理平台服务已停止，请关闭此窗口!")
    root.update_idletasks()


def check_product_code(code_input, p_code):
    today_str = datetime.today().strftime("%Y%m%d")
    month_day = int(today_str[4:8])
    tmp_code = month_day + 3014
    p_code_today = str(p_code) + "-" + str(tmp_code)
    if code_input == p_code_today:
        return True
    else:
        return False


start_distribute_button = tk.Button(root, text="开始/启动", command=main, width=10, height=3, font=my_font)
start_distribute_button.grid(row=4, column=3, pady=(20, 0))
stop_server_button = tk.Button(root, text="停止服务", command=stop_web_server, width=10, height=3, font=my_font)
stop_server_button.grid(row=4, column=5, pady=(20, 0))
stop_server_button.config(state=tk.DISABLED)
close_button = tk.Button(root, text="取消/关闭", command=close_window, width=10, height=3, font=my_font)
close_button.grid(row=4, column=7, pady=(20, 0))

# 产品码输入

# 创建一个标签用于显示进度文本
product_code_label = tk.Label(root, text="产品编码：", font=my_font)
product_code_label.grid(row=5, column=2, pady=(30, 20))

entry_var = tk.StringVar()
entry_product_code = tk.Entry(root, width=50, textvariable=entry_var, font=my_font)
entry_product_code.grid(row=5, column=3, columnspan=6, pady=(30, 20))
# entry_product_code.config(state=tk.DISABLED)

if __name__ == '__main__':
    init_param()
    root.mainloop()
