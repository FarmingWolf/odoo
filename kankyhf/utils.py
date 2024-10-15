import asyncio
import os
from datetime import datetime, timedelta

import tkinter as tk

import win32file
from pyzipper import AESZipFile, zipfile, WZ_AES


class Tooltip:
    """
    创建一个 Tooltip 类，用于在鼠标悬停时显示提示信息。
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None

        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if not self.tooltip:
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25
            self.tooltip = tk.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.tooltip, text=self.text, bg="#ffffe0", relief="solid", borderwidth=1)
            label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


def check_trial_period(in_zip_ref, in_fn, out_zip_fld):
    zip_info = in_zip_ref.getinfo(in_fn)
    in_zip_ref.extract(zip_info, out_zip_fld)
    if not os.path.exists(out_zip_fld + in_fn):
        msg = f"基础文件损坏，文件解压后丢失：{in_fn}，请确认本机杀毒软件处于关闭状态。"
        return False, msg

    trial_period_in_f = []  # date_from, days_limit, days_left
    with open(out_zip_fld + in_fn, 'r', encoding='utf-8') as info_file:
        for line in info_file:
            txt_line = line.strip()
            if txt_line:
                trial_period_in_f.append(txt_line)

    if (not trial_period_in_f) or (len(trial_period_in_f) != 3):
        msg = f"基础文件损坏，文件内容错误：{in_fn}，该文件可能遭到人为破坏。"
        return False, msg

    # 0即无限制
    if int(trial_period_in_f[1]) == 0:
        return True, "OK"

    if int(trial_period_in_f[2]) <= 0 or \
            datetime.strptime(trial_period_in_f[0], "%Y%m%d") + \
            timedelta(minutes=int(trial_period_in_f[1])) < datetime.today():

        msg = f"试用期已结束。"
        return False, msg

    return True, "OK"


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


def unzip_tgt_file(in_args):
    try:
        with AESZipFile(in_args["file_2_customer"], 'r', compression=zipfile.ZIP_DEFLATED,
                        encryption=WZ_AES) as zip_ref:
            # 设置密码
            zip_ref.setpassword(in_args["zip_pwd"].encode('utf-8'))
            if (in_args["customer_name_info_fn"] not in zip_ref.namelist()) or \
                    (in_args["days_limit_info_fn"] not in zip_ref.namelist()) or \
                    (in_args["tmp_fn"] not in zip_ref.namelist()):
                msg = f"基础文件损坏，文件内容错误：找不到" \
                      f"{in_args['customer_name_info_fn']}/{in_args['days_limit_info_fn']}/{in_args['tmp_fn']}，" \
                      f"文件可能遭到人为破坏。"
                return False, msg

            # 解压所有文件到目标目录，实际上就3个文件
            mac_zip_info = zip_ref.getinfo(in_args['customer_name_info_fn'])
            zip_ref.extract(mac_zip_info, in_args['out_zip_fld'])

            trial_period_zip_info = zip_ref.getinfo(in_args['days_limit_info_fn'])
            zip_ref.extract(trial_period_zip_info, in_args['out_zip_fld'])

            addons_zip = zip_ref.getinfo(in_args['tmp_fn'])
            extracted_bytes = 0

            if os.path.exists(in_args['out_zip_file']):
                os.remove(in_args['out_zip_file'])
            # 提取文件
            # 打开ZIP文件中的成员
            with zip_ref.open(addons_zip) as source, open(in_args['out_zip_file'], 'wb') as target:
                while True:
                    chunk = source.read(1024 * 1024)  # 每次读取1MB的数据
                    if not chunk:
                        break
                    target.write(chunk)
                    extracted_bytes += len(chunk)

            return True, "OK"

    except Exception as e:

        return False, f"文件解压出错{e}"
    finally:
        if os.path.exists(in_args['out_zip_file']):
            file_attributes = win32file.GetFileAttributes(in_args['out_zip_file'])
            new_attributes = file_attributes | win32file.FILE_ATTRIBUTE_HIDDEN
            win32file.SetFileAttributes(in_args['out_zip_file'], new_attributes)
        if os.path.exists(in_args['out_zip_fld'] + in_args['customer_name_info_fn']):
            file_attributes = win32file.GetFileAttributes(in_args['out_zip_fld'] + in_args['customer_name_info_fn'])
            new_attributes = file_attributes | win32file.FILE_ATTRIBUTE_HIDDEN
            win32file.SetFileAttributes(in_args['out_zip_fld'] + in_args['customer_name_info_fn'], new_attributes)
        if os.path.exists(in_args['out_zip_fld'] + in_args['days_limit_info_fn']):
            file_attributes = win32file.GetFileAttributes(in_args['out_zip_fld'] + in_args['days_limit_info_fn'])
            new_attributes = file_attributes | win32file.FILE_ATTRIBUTE_HIDDEN
            win32file.SetFileAttributes(in_args['out_zip_fld'] + in_args['days_limit_info_fn'], new_attributes)


def rezip_tgt_file(in_args):
    tmp_z_fn = "../" + datetime.today().strftime("%Y%m%d%H%M%S")
    try:
        add_file_2_zip_with_password(in_args['out_zip_fld'] + in_args['customer_name_info_fn'],
                                     in_args['customer_name_info_fn'],
                                     tmp_z_fn, in_args['zip_pwd'], 'w')
        if os.path.exists(in_args['out_zip_fld'] + in_args['customer_name_info_fn']):
            os.remove(in_args['out_zip_fld'] + in_args['customer_name_info_fn'])

        add_file_2_zip_with_password(in_args['out_zip_fld'] + in_args['days_limit_info_fn'],
                                     in_args['days_limit_info_fn'], tmp_z_fn,
                                     in_args['zip_pwd'], 'a')
        if os.path.exists(in_args['out_zip_fld'] + in_args['days_limit_info_fn']):
            os.remove(in_args['out_zip_fld'] + in_args['days_limit_info_fn'])

        add_file_2_zip_with_password(in_args['in_zip_file'], in_args['tmp_fn'], tmp_z_fn, in_args['zip_pwd'], 'a',
                                     in_args['file_2_customer'])
        return True, "OK"

    except Exception as ex:
        if os.path.exists(tmp_z_fn):
            os.remove(tmp_z_fn)
        return False, f"zip文件处理NG{ex}"
    finally:
        if os.path.exists(in_args['out_zip_fld'] + in_args['customer_name_info_fn']):
            os.remove(in_args['out_zip_fld'] + in_args['customer_name_info_fn'])
        if os.path.exists(in_args['out_zip_fld'] + in_args['days_limit_info_fn']):
            os.remove(in_args['out_zip_fld'] + in_args['days_limit_info_fn'])
        if os.path.exists(in_args['out_zip_file']):
            os.remove(in_args['out_zip_file'])


def countdown_check(in_args):

    trial_period_in_f = []  # date_from, days_limit, days_left
    with open(in_args['out_zip_fld'] + in_args['days_limit_info_fn'], 'r', encoding='utf-8') as info_file:
        for line in info_file:
            txt_line = line.strip()
            if txt_line:
                trial_period_in_f.append(txt_line)

    if (not trial_period_in_f) or (len(trial_period_in_f) != 3):
        msg = f"基础文件损坏，文件内容错误：{in_args['days_limit_info_fn']}，该文件可能遭到人为破坏。"
        return False, msg, 0, 0

    # 0即无限制
    if int(trial_period_in_f[1]) == 0:
        return True, "OK", 0, 0

    min_left = int(trial_period_in_f[2]) - int(in_args['time_check_period'])
    days_past = datetime.today() - datetime.strptime(trial_period_in_f[0], "%Y%m%d")
    min_lef_cal = int(trial_period_in_f[1]) - (days_past.days * 24 * 60 + days_past.seconds // 60)
    if min_lef_cal < min_left:
        min_left = min_lef_cal

    if min_left <= 0 or \
            datetime.strptime(trial_period_in_f[0], "%Y%m%d") + \
            timedelta(minutes=int(trial_period_in_f[1])) < datetime.today():

        msg = f"试用期已结束。"
        return False, msg, int(trial_period_in_f[1]), min_left
    # countdown后写回文件
    if os.path.exists(in_args['out_zip_fld'] + in_args['days_limit_info_fn']):
        os.remove(in_args['out_zip_fld'] + in_args['days_limit_info_fn'])

    with open(in_args['out_zip_fld'] + in_args['days_limit_info_fn'], 'a', encoding='utf-8') as info_file:
        info_file.write(str(trial_period_in_f[0]) + "\n")
        info_file.write(str(trial_period_in_f[1]) + "\n")
        info_file.write(str(min_left) + "\n")

    if os.path.exists(in_args['out_zip_fld'] + in_args['days_limit_info_fn']):
        file_attributes = win32file.GetFileAttributes(in_args['out_zip_fld'] + in_args['days_limit_info_fn'])
        new_attributes = file_attributes | win32file.FILE_ATTRIBUTE_HIDDEN
        win32file.SetFileAttributes(in_args["out_zip_fld"] + in_args["days_limit_info_fn"], new_attributes)

    return True, "OK", int(trial_period_in_f[1]), min_left


def start_countdown_trial_period(in_args):
    unzip_res, unzip_msg = unzip_tgt_file(in_args)
    if not unzip_res:
        return False, unzip_msg, 0, 0

    countdown_res, countdown_msg, min_limit, min_left = countdown_check(in_args)
    if not countdown_res:
        return False, countdown_msg, min_limit, min_left

    rezip_res, rezip_msg = rezip_tgt_file(in_args)
    if not rezip_res:
        return False, rezip_msg, min_limit, min_left

    return True, "OK", min_limit, min_left


async def countdown(duration_minutes):
    """
    倒计时指定的分钟数。
    :param duration_minutes: int 倒计时的分钟数
    """
    end_time = datetime.now() + timedelta(minutes=duration_minutes)
    while datetime.now() < end_time:
        remaining = end_time - datetime.now()
        print(f"Time remaining: {remaining}")
        await asyncio.sleep(60)  # 每分钟检查一次


async def main():
    """
    主函数，用于启动定时器。
    """
    await countdown(100)  # 倒计时100分钟

if __name__ == "__main__":
    asyncio.run(main())
