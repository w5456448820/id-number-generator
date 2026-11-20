# -*- coding: utf-8 -*-
"""
证件号生成器 V2.3
基于原作者 V1.0.0（统一社会信用代码 / 组织机构代码）扩展：
  1) 新增居民身份证号码生成（GB 11643-1999 校验）；
  2) 地区码改为按真实行政区划三级联动选择（省 / 市 / 区县，GB/T 2260）。

【用途声明】本程序生成的号码均为随机虚构，仅供软件开发测试、系统联调、
数据脱敏演示等合法场景使用。严禁用于伪造证件、冒用他人身份、绕过实名认证
或任何其他违法违规用途，使用者须自行承担全部法律责任。
"""
import os
import re
import sys
import json
import random
import ctypes
from datetime import date, timedelta
from tkinter import *
from tkinter import ttk, messagebox

# ---------------- 统一社会信用代码 / 组织机构代码 ----------------
check_dict = {
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17, 'J': 18, 'K': 19,
    'L': 20, 'M': 21, 'N': 22, 'P': 23, 'Q': 24, 'R': 25, 'T': 26, 'U': 27, 'W': 28,
    'X': 29, 'Y': 30}
dict_check = {value: key for key, value in check_dict.items()}
area_code = [
    110000, 120000, 130000, 140000, 150000, 210000, 220000, 230000, 310000,
    320000, 330000, 340000, 350000, 360000, 370000, 410000, 420000, 430000,
    440000, 450000, 460000, 500000, 510000, 520000, 530000, 540000, 610000,
    620000, 630000, 640000, 650000, 710000, 810000, 820000]
manage_code = [9]
type_code = [1, 2, 3, 9]

weight_code = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]


def create_organization():
    """生成 9 位组织机构代码（8 位本体 + 1 位校验码）"""
    ww = [3, 7, 9, 10, 5, 8, 4, 2]
    cc = []
    dd = 0
    for i in range(8):
        cc.append(random.randint(1, 9))
        dd = dd + cc[i] * ww[i]
    for i in range(len(cc)):
        cc[i] = str(cc[i])
    C9 = 11 - dd % 11
    if C9 == 10:
        C9 = "X"
    elif C9 == 11:
        # 修正原版缺陷：GB11714 规定校验码为 11 时应取 "0"，原版返回空串导致后续越界
        C9 = "0"
    else:
        C9 = str(C9)
    cc.append(C9)
    return "".join(cc)


def create_social_credit():
    """生成 18 位统一社会信用代码"""
    org_code = create_organization().replace("-", "")
    total = 0
    code = (str(random.choice(manage_code)) + str(random.choice(type_code))
            + str(random.choice(area_code)) + org_code)
    for i in range(17):
        total = total + check_dict[code[i]] * weight_code[i]
    # 修正原版缺陷：total % 31 == 0 时 31-0=31 会触发 KeyError
    C18 = dict_check[(31 - total % 31) % 31]
    return code + C18


def Org_code():
    """生成 8 位-1 位格式的组织机构代码，如 12345678-X"""
    org_code = create_organization().replace("-", "")
    return org_code[:8] + "-" + org_code[-1]


# ---------------- 居民身份证号码（GB 11643-1999） ----------------
ID_WEIGHT = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
ID_CHECK = "10X98765432"


def id_check_code(body17):
    """按 GB 11643-1999 计算第 18 位校验码"""
    total = 0
    for i in range(17):
        total += int(body17[i]) * ID_WEIGHT[i]
    return ID_CHECK[total % 11]


def build_area6(prov, city, dist):
    """
    由三级选择的行政区划代码拼出 6 位地址码：
    prov/city/dist 分别为 2 / 4 / 6 位代码。
    选“随机”（空）时，从该层级下真实存在的区县码中随机抽取，不再拼凑随机数字，
    保证生成的地址码在 GB/T 2260 中有对应行政区划。
    """
    if dist:
        return dist
    if city:
        pool = CITY_CODES.get(city) or []
        if pool:
            return random.choice(pool)
        return city + "00"
    if prov:
        pool = PROV_CODES.get(prov) or []
        if pool:
            return random.choice(pool)
        return prov + "0000"
    if ALL_DISTRICT_CODES:
        return random.choice(ALL_DISTRICT_CODES)
    return "110101"


# ---------------- 出生日期：随机默认值 / 手输自规范化 / 日历选择 ----------------
MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def days_in_month(y, m):
    """返回指定年月的天数（含闰年判断）"""
    if m == 2 and y % 4 == 0 and (y % 100 != 0 or y % 400 == 0):
        return 29
    return MONTH_DAYS[m - 1]


def valid_date(y, m, d):
    try:
        date(y, m, d)
        return True
    except ValueError:
        return False


# 出生年份允许范围：下限 1900，上限 = 系统当前年份 + 10 年（下拉框最大年份同此值）
YEAR_MIN = 1900
YEAR_MAX = date.today().year + 10


def random_birthday():
    """随机生日（1960-01-01 ~ 2005-12-31），8 位 YYYYMMDD"""
    start = date(1960, 1, 1)
    span = (date(2005, 12, 31) - start).days
    return (start + timedelta(days=random.randint(0, span))).strftime("%Y%m%d")


def normalize_birth(raw):
    """
    把手输的多种日期写法规范为 8 位 YYYYMMDD：
      19900101 / 1990-1-1 / 1990.1.1 / 1990/01/01 / 1990年1月1日 / 900101（两位年）/ 1990（仅年份）
    空串返回 ""（表示随机生成）；无法识别返回 None
    """
    t = (raw or "").strip()
    if not t or t == "随机":
        return ""
    for sep in ("年", "月", "/", ".", "。", "\\", "－", "—", "_", "－"):
        t = t.replace(sep, "-")
    t = t.replace("日", "")
    groups = [g for g in re.split(r"[-\s,，、]+", t) if g]
    y = m = d = None
    if len(groups) >= 3 and all(g.isdigit() for g in groups[:3]):
        y, m, d = int(groups[0]), int(groups[1]), int(groups[2])
        if y < 100:
            y += 1900 if y > 40 else 2000
    elif len(groups) == 1 and groups[0].isdigit():
        dig = groups[0]
        if len(dig) == 8:
            y, m, d = int(dig[:4]), int(dig[4:6]), int(dig[6:8])
        elif len(dig) == 6:
            yy = int(dig[:2])
            y, m, d = (1900 if yy > 40 else 2000) + yy, int(dig[2:4]), int(dig[4:6])
        elif len(dig) == 4:
            y, m, d = int(dig), 1, 1
    if y is None:
        return None
    if not (YEAR_MIN <= y <= YEAR_MAX):
        return None
    if not valid_date(y, m, d):
        return None
    return "%04d%02d%02d" % (y, m, d)


def create_id_number(area="", birthday="", sex="随机"):
    """
    生成 18 位居民身份证号码（随机虚构，仅测试用）
    area     : 6 位地址码，留空则随机
    birthday : 8 位出生日期 YYYYMMDD，留空则随机 1960-01-01 ~ 2005-12-31
    sex      : "随机" / "男" / "女"，决定顺序码第 3 位的奇偶
    返回 (号码, 错误信息)
    """
    area = str(area).strip()
    if area == "":
        area = build_area6("", "", "")
    elif len(area) == 2 and area.isdigit():
        area = build_area6(area, "", "")
    elif len(area) == 4 and area.isdigit():
        area = build_area6("", area, "")
    elif not (len(area) == 6 and area.isdigit()):
        return "", "地区码需为 6 位数字"

    # 出生日期
    birthday = str(birthday).strip()
    if birthday == "":
        start = date(1960, 1, 1)
        span = (date(2005, 12, 31) - start).days
        d = start + timedelta(days=random.randint(0, span))
        birthday = d.strftime("%Y%m%d")
    else:
        if len(birthday) != 8 or not birthday.isdigit():
            return "", "出生日期需为 8 位数字，格式 YYYYMMDD"
        try:
            date(int(birthday[0:4]), int(birthday[4:6]), int(birthday[6:8]))
        except ValueError:
            return "", "出生日期不是有效日期"
        if not (YEAR_MIN <= int(birthday[0:4]) <= YEAR_MAX):
            return "", "出生年份超出合理范围"

    # 顺序码（第 17 位奇数为男、偶数为女）
    order = random.randint(1, 999)
    if sex == "男" and order % 2 == 0:
        order = order - 1 if order > 1 else order + 1
    elif sex == "女" and order % 2 == 1:
        order = order + 1 if order < 999 else order - 1
    body = area + birthday + "%03d" % order
    return body + id_check_code(body), ""


# ---------------- 行政区划数据（GB/T 2260） ----------------
def resource_path(rel):
    """按优先级查找资源：onefile 解压目录 -> exe 所在目录 -> 源码目录。"""
    cands = []
    mei = getattr(sys, "_MEIPASS", None)
    if mei:
        cands.append(mei)
    if getattr(sys, "frozen", False):
        cands.append(os.path.dirname(os.path.abspath(sys.executable)))
    cands.append(os.path.dirname(os.path.abspath(__file__)))
    for b in cands:
        p = os.path.join(b, rel)
        if os.path.exists(p):
            return p
    return os.path.join(cands[-1], rel)


def load_districts():
    path = resource_path("pca-code.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def normalize_districts(raw):
    """
    规整行政数据：只保留合法的 6 位区县码作为身份证地址码。
    东莞、中山等不设区的地级市，原始数据下挂的是 9 位街道码（如 441900003），
    这类不能作为身份证地址码，统一替换为“市本级”选项（市码 + 00，即 441900）。
    """
    out = []
    for p in raw:
        pcode = str(p.get("code", ""))
        if len(pcode) != 2 or not pcode.isdigit():
            continue
        cities = []
        for c in p.get("children") or []:
            ccode = str(c.get("code", ""))
            if len(ccode) != 4 or not ccode.isdigit():
                continue
            raw_children = c.get("children") or []
            valid = [d for d in raw_children
                     if len(str(d.get("code", ""))) == 6 and str(d.get("code")).isdigit()]
            dists = []
            if len(valid) != len(raw_children):
                dists.append({"code": ccode + "00", "name": "（市本级）" + c.get("name", "")})
            dists.extend({"code": d["code"], "name": d["name"]} for d in valid)
            cities.append({"code": ccode, "name": c.get("name", ""), "children": dists})
        out.append({"code": pcode, "name": p.get("name", ""), "children": cities})
    return out


DISTRICTS = load_districts()
PROVINCES = [(p["code"], p["name"], p["children"]) for p in normalize_districts(DISTRICTS)]

# 真实区县地址码索引：随机选择时只在真实存在的层级代码中抽取
ALL_DISTRICT_CODES = [d["code"]
                      for _pc, _pn, _cs in PROVINCES
                      for _c in _cs
                      for d in (_c.get("children") or [])
                      if len(str(d.get("code", ""))) == 6 and str(d.get("code")).isdigit()]
PROV_CODES = {}
CITY_CODES = {}
for _pc, _pn, _cs in PROVINCES:
    _prov_pool = []
    for _c in _cs:
        _dpool = [d["code"] for d in (_c.get("children") or [])
                  if len(str(d.get("code", ""))) == 6 and str(d.get("code")).isdigit()]
        if _dpool:
            CITY_CODES[_c["code"]] = _dpool
            _prov_pool.extend(_dpool)
    if _prov_pool:
        PROV_CODES[_pc] = _prov_pool

# ---------------- 界面 ----------------
# 让 Windows 任务栏把本程序识别为独立应用，图标取进程图标（与 exe 内嵌图标一致）
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "Marvis.ZhengJianHaoGenerator.V23")
except Exception:
    pass

window = Tk()
window.title("证件号生成器 V2.3")

# 统一配色 / 字体
BG        = "#EEF2F8"    # 窗口底色
CARD      = "#FFFFFF"    # 卡片底色
CARD_BD   = "#D8E0EC"    # 卡片描边
SHADOW    = "#DFE6F1"    # 卡片投影
PRIMARY   = "#2F6FD0"    # 主色
PRIMARY_D = "#2559A8"    # 主色悬停
HDR_BTN   = "#4E88DC"    # 标题栏按钮
HDR_BTN_H = "#3C74C8"
TXT       = "#2C3E50"    # 主文字
SUB       = "#7A8899"    # 次要文字
DANGER    = "#C0392B"    # 声明文字
F_UI      = "Microsoft YaHei"
F_MONO    = "Consolas"

WW, WH = 560, 462
sw = window.winfo_screenwidth()
sh = window.winfo_screenheight()
window.geometry("%dx%d+%d+%d" % (WW, WH, (sw - WW) / 2, (sh - WH) / 2))
window.resizable(False, False)
window.configure(bg=BG)

# 窗口图标：统一使用程序图标 app.ico（标题栏 / 任务栏 / Alt+Tab 一致）
_icon = resource_path("app.ico")


def apply_icon(win):
    if not _icon or not os.path.exists(_icon):
        return
    try:
        win.iconbitmap(default=_icon)
    except TclError:
        try:
            win.iconbitmap(_icon)
        except TclError:
            pass


apply_icon(window)

# 下拉框风格：扁平、圆润、与整体配色统一
style = ttk.Style(window)
try:
    style.theme_use("clam")
except TclError:
    pass
style.configure("TCombobox", fieldbackground="#F7FAFD", background=CARD, foreground=TXT,
                bordercolor=CARD_BD, lightcolor=CARD_BD, darkcolor=CARD_BD,
                arrowcolor="#8496A8", arrowsize=12, padding=4, relief="flat",
                selectbackground="#F7FAFD", selectforeground=TXT)
style.map("TCombobox",
          fieldbackground=[("readonly", "#F7FAFD"), ("disabled", "#F0F2F6")],
          selectbackground=[("readonly", "#F7FAFD")],
          selectforeground=[("readonly", TXT)],
          bordercolor=[("focus", "#9BC0EE"), ("hover", "#B8CFEC")])
window.option_add("*TCombobox*Listbox.background", CARD)
window.option_add("*TCombobox*Listbox.foreground", TXT)
window.option_add("*TCombobox*Listbox.selectBackground", PRIMARY)
window.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
window.option_add("*TCombobox*Listbox.font", (F_UI, 9))


def make_card(y, h, accent=PRIMARY):
    """白底卡片：底部浅色投影 + 1px 描边 + 左侧色条"""
    Frame(window, bg=SHADOW).place(x=15, y=y + 2, width=532, height=h)
    body = Frame(window, bg=CARD, highlightbackground=CARD_BD, highlightthickness=1)
    body.place(x=14, y=y, width=532, height=h)
    Frame(body, bg=accent).place(x=1, y=1, width=4, height=h - 2)
    return body


def flat_btn(parent, text, cmd, x, y, w, h, bg=PRIMARY, hover=PRIMARY_D, font=None):
    """扁平按钮，鼠标悬停变色"""
    b = Button(parent, text=text, command=cmd, bg=bg, fg="#FFFFFF",
               activebackground=hover, activeforeground="#FFFFFF",
               relief="flat", bd=0, highlightthickness=0, cursor="hand2",
               font=font or (F_UI, 9, "bold"))
    b.place(x=x, y=y, width=w, height=h)
    b.bind("<Enter>", lambda e: b.configure(bg=hover))
    b.bind("<Leave>", lambda e: b.configure(bg=bg))
    return b


def out_box(parent, x, y, w, h):
    """号码展示框：浅底色 + 等宽字体，便于逐位核对"""
    holder = Frame(parent, bg="#F7FAFD", highlightbackground=CARD_BD, highlightthickness=1)
    holder.place(x=x, y=y, width=w, height=h)
    t = Text(holder, bd=0, highlightthickness=0, bg="#F7FAFD", fg="#1B2B3A",
             font=(F_MONO, 12), padx=9, pady=4, wrap="none", cursor="xterm")
    t.place(x=0, y=0, width=w - 2, height=h - 2)
    return t


def card_title(parent, title, note):
    """卡片标题：主标题 + 灰色规格说明"""
    row = Frame(parent, bg=CARD)
    row.place(x=14, y=8)
    Label(row, text=title, font=(F_UI, 9, "bold"), bg=CARD, fg=TXT).pack(side=LEFT)
    Label(row, text=note, font=(F_UI, 7), bg=CARD, fg=SUB).pack(side=LEFT, padx=(8, 0), pady=(2, 0))



def about1():
    no_love = Toplevel(window)
    no_love.geometry("448x574+%d+%d" % ((sw - 448) / 2, (sh - 574) / 2))
    no_love.title("关于本程序")
    no_love.configure(bg=CARD)
    no_love.resizable(False, False)
    apply_icon(no_love)
    Label(no_love, text="证件号生成器 V2.3.0", font=(F_UI, 12, "bold"),
          bg=CARD, fg=TXT).place(x=20, y=14)
    Label(no_love, text="仅供软件测试与系统联调使用", font=(F_UI, 8),
          bg=CARD, fg=SUB).place(x=20, y=42)
    Frame(no_love, bg=CARD_BD).place(x=20, y=64, width=408, height=1)
    EditText0 = Text(no_love, bd=0, highlightthickness=1, highlightbackground=CARD_BD,
                     bg="#F7FAFD", fg=TXT, font=(F_UI, 8), padx=10, pady=8, wrap="word")
    EditText0.place(x=18, y=72, width=412, height=438)
    EditText0.insert(1.0, "【使用说明】\n"
                          "    本程序为单文件绿色版，双击即可运行，无需安装 Python。\n"
                          "    生成的号码均为随机虚构，仅供软件测试与系统联调。\n"
                          "    身份证地区码按真实行政区划（省 / 市 / 区县）选择；\n"
                          "    出生日期为“年 / 月 / 日”三个下拉框，也可直接手工输入：\n"
                          "      可整串粘贴 19900101 / 1990-1-1 / 1990年1月1日 自动拆分；\n"
                          "      也可单独在年 / 月 / 日框内输入数字；“随机”即自动取值。\n"
                          "    严禁用于伪造证件、冒用他人身份或绕过实名认证。\n"
                          "\n"
                          "【版本历史】\n"
                          "V1.2 新增：身份证号码生成，地区码按真实行政区划选择\n"
                          "V1.3 改进：性别改为下拉框，与地区选择样式统一\n"
                          "V1.4 改进：地区选“随机”时只从真实区县中抽取\n"
                          "V1.5 改进：软件更名为“证件号生成器”，底部改为滚动声明\n"
                          "V1.6 改进：移除原作者与联系方式信息\n"
                          "V1.7 改进：出生日期默认随机，支持多种手输格式自动规范化\n"
                          "V1.8 改进：点击输入框直接弹出日历；“全部清空”改为“重置”\n"
                          "V1.9 改进：地区下拉框后标注“省”“市”“区”；去除日历控件\n"
                          "V2.0 改进：全新界面（卡片式分区、统一配色与微软雅黑字体、\n"
                          "          扁平按钮、号码等宽显示、悬停反馈）；更换程序图标\n"
                          "V2.1 改进：身份证号码与地区信息合并为同一区域；标签“地区”；\n"
                          "          输入框统一对齐；出生日期改为年/月/日下拉框；\n"
                          "          使用说明并入本窗口，取消“帮助”按钮\n"
                          "V2.2 改进：出生日期支持手工输入（整串日期自动拆分）；\n"
                          "          年份下拉框最大年份改为系统年份 +10 年\n"
                          "V2.3 修正：窗口与任务栏图标统一为程序图标")
    EditText0.configure(state="disabled")
    flat_btn(no_love, "确 定", no_love.destroy, 354, 522, 76, 28)


# ===== 顶部标题栏 =====
hdr = Frame(window, bg=PRIMARY)
hdr.place(x=0, y=0, width=WW, height=62)
Label(hdr, text="证件号生成器", font=(F_UI, 15, "bold"), bg=PRIMARY, fg="#FFFFFF").place(x=20, y=9)
Label(hdr, text="统一社会信用代码 · 组织机构代码 · 身份证号码        V2.3",
      font=(F_UI, 8), bg=PRIMARY, fg="#C9DDF7").place(x=22, y=38)

# ===== 三段号码卡片 =====
card1 = make_card(72, 76)
card_title(card1, "统一社会信用代码", "18 位 · GB 32100-2015")
EditText = out_box(card1, 14, 30, 384, 32)

card2 = make_card(154, 76)
card_title(card2, "组织机构代码", "9 位 · 随机生成")
EditText1 = out_box(card2, 14, 30, 384, 32)

card3 = make_card(236, 184)
card_title(card3, "身份证号码", "18 位 · GB 11643-1999，含校验位")
EditText2 = out_box(card3, 14, 30, 384, 32)


def deleteValue1():
    """清空三证合一文本框"""
    EditText.delete(1.0, END)


def deleteValue2():
    """清空组织机构代码文本框"""
    EditText1.delete(1.0, END)


def deleteValue3():
    """清空身份证号文本框"""
    EditText2.delete(1.0, END)


def printtext1():
    """三证合一文本框"""
    EditText.insert(0.0, create_social_credit())


def printtext2():
    """组织机构代码文本框"""
    EditText1.insert(0.0, Org_code())


def printtext3():
    """身份证号码文本框"""
    birthday = get_birthday()
    if birthday is None:
        return
    num, err = create_id_number(current_area(), birthday, sex_var.get())
    if err:
        messagebox.showwarning(title="提示", message=err)
        return
    EditText2.insert(0.0, num)


Bu1 = flat_btn(card1, "生 成", (lambda: [deleteValue1(), printtext1()]), 410, 30, 108, 32)
Bu2 = flat_btn(card2, "生 成", (lambda: [deleteValue2(), printtext2()]), 410, 30, 108, 32)
Bu3 = flat_btn(card3, "生 成", (lambda: [deleteValue3(), printtext3()]), 410, 30, 108, 32)
RANDOM_TEXT = "随机"
prov_var = StringVar(value=RANDOM_TEXT)
city_var = StringVar(value=RANDOM_TEXT)
dist_var = StringVar(value=RANDOM_TEXT)
area_var = StringVar(value="")          # 最终 6 位地址码
year_var = StringVar(value=RANDOM_TEXT)
month_var = StringVar(value=RANDOM_TEXT)
day_var = StringVar(value=RANDOM_TEXT)
sex_var = StringVar(value="随机")

PROV_BY_NAME = {name: (code, children) for code, name, children in PROVINCES}

# 号码框与下方参数之间的分隔线（同一卡片内分区）
Frame(card3, bg=CARD_BD).place(x=14, y=70, width=504, height=1)

# ---------------- 地区：省 / 市 / 区县 三级联动 ----------------
Label(card3, text="地区", font=(F_UI, 9), bg=CARD, fg=TXT).place(x=14, y=83)
prov_box = ttk.Combobox(card3, textvariable=prov_var, state="readonly",
                        values=[RANDOM_TEXT] + [name for _, name, _ in PROVINCES],
                        font=(F_UI, 9))
prov_box.place(x=74, y=78, width=104, height=26)
Label(card3, text="省", font=(F_UI, 8), bg=CARD, fg=SUB).place(x=182, y=83)
city_box = ttk.Combobox(card3, textvariable=city_var, state="readonly",
                        values=[RANDOM_TEXT], font=(F_UI, 9))
city_box.place(x=196, y=78, width=104, height=26)
Label(card3, text="市", font=(F_UI, 8), bg=CARD, fg=SUB).place(x=304, y=83)
dist_box = ttk.Combobox(card3, textvariable=dist_var, state="readonly",
                        values=[RANDOM_TEXT], font=(F_UI, 9))
dist_box.place(x=318, y=78, width=116, height=26)
Label(card3, text="区", font=(F_UI, 8), bg=CARD, fg=SUB).place(x=438, y=83)

# ---------------- 出生日期（年 / 月 / 日 下拉，与地区样式一致）+ 性别 ----------------
Label(card3, text="出生日期", font=(F_UI, 9), bg=CARD, fg=TXT).place(x=14, y=117)
year_box = ttk.Combobox(card3, textvariable=year_var, state="normal",
                        values=[RANDOM_TEXT] + [str(y) for y in range(YEAR_MAX, YEAR_MIN - 1, -1)],
                        font=(F_UI, 9))
year_box.place(x=74, y=112, width=104, height=26)
Label(card3, text="年", font=(F_UI, 8), bg=CARD, fg=SUB).place(x=182, y=117)
month_box = ttk.Combobox(card3, textvariable=month_var, state="normal",
                         values=[RANDOM_TEXT] + ["%02d" % m for m in range(1, 13)],
                         font=(F_UI, 9))
month_box.place(x=196, y=112, width=104, height=26)
Label(card3, text="月", font=(F_UI, 8), bg=CARD, fg=SUB).place(x=304, y=117)
day_box = ttk.Combobox(card3, textvariable=day_var, state="normal",
                       values=[RANDOM_TEXT] + ["%02d" % d for d in range(1, 32)],
                       font=(F_UI, 9))
day_box.place(x=318, y=112, width=116, height=26)
Label(card3, text="日", font=(F_UI, 8), bg=CARD, fg=SUB).place(x=438, y=117)
Label(card3, text="可直接输入", font=(F_UI, 7), bg=CARD, fg=SUB).place(x=458, y=117)
Label(card3, text="性别", font=(F_UI, 9), bg=CARD, fg=TXT).place(x=14, y=151)
sex_box = ttk.Combobox(card3, textvariable=sex_var, state="readonly",
                       values=["随机", "男", "女"], font=(F_UI, 9))
sex_box.place(x=74, y=146, width=104, height=26)
def current_area():
    """
    按当前三级下拉选择即时计算 6 位地址码并返回。
    三级均为“随机”时，每次生成都会重新从真实区县中抽取一个，
    因此连续生成会出现不同的真实地区码，而不是固定同一个。
    """
    prov = prov_var.get()
    city = city_var.get()
    dist = dist_var.get()
    pcode, children = (PROV_BY_NAME.get(prov, ("", [])))
    ccode, dchildren = ("", [])
    for c in children:
        if c["name"] == city:
            ccode, dchildren = c["code"], c.get("children") or []
            break
    dcode = ""
    for d in dchildren:
        if d["name"] == dist:
            dcode = d["code"]
            break
    return build_area6(pcode if prov != RANDOM_TEXT else "",
                       ccode if city != RANDOM_TEXT else "",
                       dcode)


def refresh_area(*_):
    """刷新地址码显示状态（生成时以 current_area() 实时计算为准）"""
    area_var.set(current_area())


def _pick_int(raw):
    """把下拉框 / 输入框文本解析为整数；“随机”、空串、无数字字符返回 None"""
    t = (raw or "").strip()
    if t in ("", RANDOM_TEXT):
        return None
    dg = re.sub(r"\D", "", t)
    return int(dg) if dg else None


def _birth_warn(alert, msg):
    if alert:
        messagebox.showwarning(title="提示", message=msg)
    return None


def on_date_change(*_):
    """年 / 月变化（含手输）时收窄“日”的候选范围，避免出现 2 月 30 日之类的组合"""
    yi = _pick_int(year_var.get())
    mi = _pick_int(month_var.get())
    days = 31
    if mi is not None and 1 <= mi <= 12:
        base_y = yi if (yi is not None and YEAR_MIN <= yi <= YEAR_MAX) else 2000
        days = days_in_month(base_y, mi)
    day_box["values"] = [RANDOM_TEXT] + ["%02d" % d for d in range(1, days + 1)]
    cur = _pick_int(day_var.get())
    if cur is not None and cur > days:
        day_var.set("%02d" % days)


def _split_whole_date():
    """年份框里若被整串粘入日期（19900101 / 1990-1-1 / 1990年1月1日），自动拆分到月 / 日"""
    raw = year_var.get().strip()
    if raw in ("", RANDOM_TEXT):
        return False
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 6 and not re.search(r"[^\d]", raw):
        return False
    nb = normalize_birth(raw)
    if nb and len(nb) == 8:
        year_var.set(nb[0:4])
        month_var.set(nb[4:6])
        day_var.set(nb[6:8])
        on_date_change()
        return True
    return False


def commit_year(*_):
    """年份框提交：整串日期自动拆分；只填年份则保留；两位年份按 1940 分界补全"""
    if _split_whole_date():
        return
    raw = year_var.get().strip()
    if raw in ("", RANDOM_TEXT):
        year_var.set(RANDOM_TEXT)
        on_date_change()
        return
    dg = re.sub(r"\D", "", raw)
    if len(dg) == 2:
        year_var.set("%04d" % ((1900 if int(dg) > 40 else 2000) + int(dg)))
    elif dg:
        year_var.set(dg)
    else:
        year_var.set(RANDOM_TEXT)
    on_date_change()


def commit_month(*_):
    """月份框提交：数字自动补零为两位，越界值保留待生成时提示"""
    raw = month_var.get().strip()
    if raw in ("", RANDOM_TEXT):
        month_var.set(RANDOM_TEXT)
        on_date_change()
        return
    dg = re.sub(r"\D", "", raw)
    if dg and 1 <= int(dg) <= 12:
        month_var.set("%02d" % int(dg))
    elif not dg:
        month_var.set(RANDOM_TEXT)
    on_date_change()


def commit_day(*_):
    """日框提交：数字自动补零为两位，超出当月天数时夹到当月最后一天"""
    raw = day_var.get().strip()
    if raw in ("", RANDOM_TEXT):
        day_var.set(RANDOM_TEXT)
        on_date_change()
        return
    dg = re.sub(r"\D", "", raw)
    if dg and 1 <= int(dg) <= 31:
        day_var.set("%02d" % int(dg))
    elif not dg:
        day_var.set(RANDOM_TEXT)
    on_date_change()


for _b in (year_box, month_box, day_box):
    _b.bind("<<ComboboxSelected>>", on_date_change)
    _b.bind("<FocusOut>", lambda e: (commit_year(), commit_month(), commit_day()))
    _b.bind("<Return>", lambda e: (commit_year(), commit_month(), commit_day()))


def get_birthday(alert=True):
    """
    读取出生日期（支持下拉选择与手工输入）：
      三框均为“随机” → 返回 ""（由生成逻辑随机取整段生日）
      只填了部分       → 未填的年份 / 月份 / 日在合法范围内随机补齐
      组合非法 / 年份越界 → 返回 None（已弹提示）
    返回 8 位 YYYYMMDD 字符串
    """
    _split_whole_date()
    yi = _pick_int(year_var.get())
    mi = _pick_int(month_var.get())
    di = _pick_int(day_var.get())
    if yi is None and mi is None and di is None:
        return ""
    if mi is not None and not (1 <= mi <= 12):
        return _birth_warn(alert, "出生月份请填写 1 ~ 12 之间的数字。")
    if yi is not None and not (YEAR_MIN <= yi <= YEAR_MAX):
        return _birth_warn(alert, "出生年份请填写 %d ~ %d 之间的四位年份。"
                                  % (YEAR_MIN, YEAR_MAX))
    if mi is None:
        base_y = yi if yi is not None else 2000
        months = [m for m in range(1, 13) if di is None or valid_date(base_y, m, di)]
        mi = random.choice(months or list(range(1, 13)))
    if yi is None:
        lo, hi = 1960, min(2005, YEAR_MAX)
        years = [y for y in range(lo, hi + 1) if valid_date(y, mi, di if di is not None else 1)]
        yi = random.choice(years or [random.randint(lo, hi)])
    if di is None:
        di = random.randint(1, days_in_month(yi, mi))
    if not valid_date(yi, mi, di):
        return _birth_warn(alert, "%d 年 %d 月没有 %d 日，请调整出生日期。" % (yi, mi, di))
    return "%04d%02d%02d" % (yi, mi, di)



def on_prov_change(*_):
    prov = prov_var.get()
    children = PROV_BY_NAME.get(prov, ("", []))[1]
    city_box["values"] = [RANDOM_TEXT] + [c["name"] for c in children]
    city_var.set(RANDOM_TEXT)
    dist_box["values"] = [RANDOM_TEXT]
    dist_var.set(RANDOM_TEXT)
    refresh_area()


def on_city_change(*_):
    prov = prov_var.get()
    city = city_var.get()
    children = PROV_BY_NAME.get(prov, ("", []))[1]
    dchildren = []
    for c in children:
        if c["name"] == city:
            dchildren = c.get("children") or []
            break
    dist_box["values"] = [RANDOM_TEXT] + [d["name"] for d in dchildren]
    dist_var.set(RANDOM_TEXT)
    refresh_area()


prov_box.bind("<<ComboboxSelected>>", on_prov_change)
city_box.bind("<<ComboboxSelected>>", on_city_change)
dist_box.bind("<<ComboboxSelected>>", refresh_area)



def reset_all():
    """重置：清空三个号码框，生日 / 性别 / 地区恢复随机"""
    deleteValue1()
    deleteValue2()
    deleteValue3()
    year_var.set(RANDOM_TEXT)
    month_var.set(RANDOM_TEXT)
    day_var.set(RANDOM_TEXT)
    on_date_change()
    sex_var.set("随机")
    prov_var.set(RANDOM_TEXT)
    on_prov_change()


# 标题栏右侧按钮
flat_btn(hdr, "关 于", about1, 390, 16, 78, 30, bg=HDR_BTN, hover=HDR_BTN_H, font=(F_UI, 9))
flat_btn(hdr, "重 置", reset_all, 476, 16, 70, 30, bg=HDR_BTN, hover=HDR_BTN_H, font=(F_UI, 9))

# ---------------- 底部声明：滚动字幕 ----------------
TIP_TEXT = ("【声明】本工具生成的号码均为随机虚构，仅供软件测试与系统联调使用。"
            "严禁用于伪造证件、冒用他人身份或绕过实名认证，违者责任自负。")
Frame(window, bg=CARD_BD).place(x=14, y=426, width=532, height=1)
tip_canvas = Canvas(window, height=26, bg=BG, highlightthickness=0, bd=0)
tip_canvas.place(x=0, y=430, width=WW, height=26)
tip_item = tip_canvas.create_text(WW, 13, text=TIP_TEXT, anchor="w",
                                  font=(F_UI, 8), fill=DANGER)
tip_paused = [False]
tip_canvas.bind("<Enter>", lambda e: tip_paused.__setitem__(0, True))
tip_canvas.bind("<Leave>", lambda e: tip_paused.__setitem__(0, False))
def tip_scroll():
    try:
        if not tip_paused[0]:
            tip_canvas.move(tip_item, -1, 0)
            box = tip_canvas.bbox(tip_item)
            if box and box[2] < 0:
                tip_canvas.coords(tip_item, WW + 20, 13)
        window.after(30, tip_scroll)
    except TclError:
        pass


tip_scroll()

refresh_area()
window.mainloop()
