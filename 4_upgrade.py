import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import paramiko
import hashlib
import os
import time
import logging
import sys

# --- 日志初始化 ---
LOG_FILE = f'F5_Upgrade_{time.strftime("%Y%m%d_%H%M%S")}.txt'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="[%(asctime)s] %(message)s")
volume_summary = {}

def log(msg):
    print(msg)
    logging.info(msg)

root = tk.Tk()
root.withdraw()

firmware_path = filedialog.askopenfilename(
    title="Select F5 Firmware ISO (选择F5固件ISOファイルを選択)",
    filetypes=[("ISO Files", "*.iso")]
)
if not firmware_path:
    messagebox.showerror("Error", "No firmware selected. Exit.\n未选择固件 退出。\nファイルが選択されていません。終了します。")
    sys.exit()
log(f"ISO selected: {firmware_path}")

primary_ip = simpledialog.askstring("F5 Management IP", "Enter the primary F5 management IP:\n输入主F5管理口IP:\nプライマリ管理IPを入力してください:")
if not primary_ip:
    messagebox.showerror("Error", "Primary IP required. Exit.\n主IP不能为空。\nプライマリIPが必要です。")
    sys.exit()

secondary_ip = simpledialog.askstring("F5 Secondary IP", "Enter standby/secondary F5 IP (leave blank if standalone):\n输入备F5 IP（如单机留空）\nセカンダリ/スタンバイIP:")
username = simpledialog.askstring("SSH Username", "Enter SSH username:\nSSH用户名:\nSSHユーザー名:")
password = simpledialog.askstring("SSH Password", "Enter SSH password:\nSSH密码:\nSSHパスワード:", show="*")
if not username or not password:
    messagebox.showerror("Error", "Username/password required. Exit.\n账号密码必填。\nユーザー名/パスワードは必須です。")
    sys.exit()
log(f"IP(s): {primary_ip}" + (f", {secondary_ip}" if secondary_ip else ""))
log(f"Username: {username}")

nodes = [primary_ip]
if secondary_ip:
    nodes.append(secondary_ip)

def ssh_cmd(ip, user, pwd, cmd):
    out, err = "", ""
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(ip, username=user, password=pwd, timeout=20)
        stdin, stdout, stderr = c.exec_command(cmd)
        out = stdout.read().decode(errors='ignore')
        err = stderr.read().decode(errors='ignore')
        c.close()
    except Exception as e:
        err = str(e)
    log(f"[SSH] {ip} $ {cmd}\n[STDOUT]:\n{out}\n[STDERR]:\n{err}")
    return out, err

def check_https(ip):
    import ssl
    import socket
    try:
        context = ssl._create_unverified_context()
        s = socket.create_connection((ip, 443), timeout=5)
        ssock = context.wrap_socket(s, server_hostname=ip)
        ssock.close()
        log(f"[{ip}] 443 port connect OK / 443端口正常 / ポート443接続OK")
        return True
    except Exception as e:
        log(f"[{ip}] 443 port connect fail: {e} / 443端口不通: {e}")
        messagebox.showerror("Error", f"Management IP {ip} 443 unreachable!\n管理口443无法访问: {e}\n管理ポート443に接続できません: {e}")
        return False

for ip in nodes:
    check_https(ip)

def get_all_volumes(ip, user, pwd):
    out, err = ssh_cmd(ip, user, pwd, "tmsh show sys software")
    volumes = []
    for line in out.splitlines():
        if "HD" in line:
            volumes.append(line.strip())
    return out, volumes

def get_mgmt_roles(ip, user, pwd):
    out, err = ssh_cmd(ip, user, pwd, "tmsh show cm device")
    mgmt_list = []
    cur_ip = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Mgmt IP"):
            parts = line.split()
            if len(parts) > 2:
                cur_ip = parts[-1]
            elif len(parts) == 2:
                cur_ip = parts[1]
        elif line.startswith("Device HA State") and cur_ip:
            parts = line.split()
            role = parts[-1].lower()
            mgmt_list.append((cur_ip, role))
            cur_ip = None
    if not mgmt_list:
        mgmt_list = [(ip, "standalone")]
    return mgmt_list

def check_vcmp_host(ip, user, pwd):
    out, err = ssh_cmd(ip, user, pwd, "tmsh show vcmp host")
    return ("Host State" in out) or ("VCMP Host Name" in out)

def get_vcmp_guests(ip, user, pwd):
    out, err = ssh_cmd(ip, user, pwd, "tmsh list vcmp guest field name,state,management-address")
    guests = []
    for block in out.split("vcmp guest"):
        if "name" in block:
            lines = block.splitlines()
            name, addr = None, None
            for l in lines:
                if "name" in l:
                    name = l.split()[-1]
                if "management-address" in l:
                    addr = l.split()[-1]
            if name and addr:
                guests.append((name, addr))
    return guests

def local_md5(file):
    h = hashlib.md5()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


ip_role_map = {}
for ip in nodes:
    mgmt_list = get_mgmt_roles(ip, username, password)
    role = next((r for addr, r in mgmt_list if addr == ip), mgmt_list[0][1] if mgmt_list else "unknown")
    ip_role_map[ip] = role


def check_upgrade_status(ip, user, pwd):
    """
    检查F5当前分区兼容性（例：执行 show sys software status 或其它厂商建议检查命令）
    F5アップグレード互換性チェック（例：show sys software status など）
    F5 upgrade compatibility check (e.g., show sys software status)
    """
    # 推荐：用 show sys software status。可根据实际F5推荐文档调整命令
    cmd = "tmsh show sys software status"
    out, err = ssh_cmd(ip, user, pwd, cmd)

    msg = (
        f"[{ip}] 升级检查结果: {out.strip()}"  # 中文
        f"\n[{ip}] アップグレードチェック結果: {out.strip()}"  # 日文
        f"\n[{ip}] Upgrade check result: {out.strip()}"  # 英文
    )
    print(msg)
    logging.info(msg)
    
    # 检查关键字
def pre_upgrade_check(ip, user, pwd):
    checks = [
        ("系统版本", "tmsh show sys version"),
        ("硬件信息", "tmsh show sys hardware"),
        ("内存状态", "tmsh show sys memory"),
        ("CPU状态", "tmsh show sys cpu"),
        ("磁盘状态", "tmsh show sys disk"),
        ("磁盘空间", "df -h /shared/images /var"),
        ("License信息", "tmsh show sys license"),
        ("证书状态", "tmsh list /sys crypto cert"),
        ("HA状态", "tmsh show cm sync-status"),
        ("Device组状态", "tmsh show cm device-group"),
    ]
    result = []
    for label, cmd in checks:
        out, err = ssh_cmd(ip, user, pwd, cmd)
        result.append(f"[{ip}] === {label} ===\n{out.strip()}\n")
    summary_file = f"F5_PreCheck_{ip.replace('.', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(result))
    log(f"[{ip}] Pre-upgrade check saved to {summary_file}")
    return summary_file

# 调用升级前检查
for ip in nodes:
    pre_upgrade_check(ip, username, password)

# 显示环境信息
md5_local = hashlib.md5(open(firmware_path, 'rb').read()).hexdigest()
role_summary = "\n".join([
    f"{ip} : {'🟢ACTIVE' if role == 'active' else '🟡STANDBY' if role == 'standby' else role.upper()}"
    for ip, role in ip_role_map.items()
])
env_info = (
    f"ISO: {firmware_path}\nMD5: {md5_local}\n"
    f"Nodes:\n" + "\n".join(nodes) + "\n"
    f"Mgmt/HA info:\n{role_summary}\n"
)
messagebox.showinfo("F5 Upgrade - Environment Summary", env_info)
log("环境检测与角色识别已完成")






    


def choose_or_create_install_slot(ip, user, pwd):
    out, _ = ssh_cmd(ip, user, pwd, "tmsh show sys software")
    active_slot = None
    slots = []
    slot_nums = set()
    for line in out.splitlines():
        if "HD" in line:
            parts = line.strip().split()
            slot = parts[0]
            slots.append(slot)
            if "yes" in parts:
                active_slot = slot
            if slot.startswith("HD1."):
                try:
                    num = int(slot.split(".")[1])
                    slot_nums.add(num)
                except:
                    pass
    MAX_SLOT = 3
    available = [s for s in slots if s != active_slot]
    # 1. 有非active分区
    if available:
        msg = (
             # 中文
            f"当前激活分区: {active_slot}\n"
            f"可选升级分区: {', '.join(available)}\n"
            "请选择要升级的分区（否则取消）...\n\n"
            # 日文
            f"現在アクティブなパーティション: {active_slot}\n"
            f"選択可能なアップグレードパーティション: {', '.join(available)}\n"
            "アップグレードするパーティションを選択してください（キャンセルする場合はそのまま閉じてください）...\n\n"
            # 英文
            f"Current active slot: {active_slot}\n"
            f"Available upgrade slots: {', '.join(available)}\n"
            "Please select the slot to upgrade (or cancel to abort)..."
        )
        slot = simpledialog.askstring("选择分区", msg)
        if not slot:
            messagebox.showwarning("Cancelled", "已取消 / キャンセルしました / Cancelled.")
            return None, False
        return slot.strip(), False  # 已有分区，无需新建
    # 2. 只存在active，需要新建分区
    for idx in range(1, MAX_SLOT+1):
        candidate = f"HD1.{idx}"
        if idx not in slot_nums:
            messagebox.showinfo(
                "自动分配新分区 / Auto slot assignment / 自動スロット割り当て",
                (
                    f"当前仅存在: {', '.join(slots)}\n"
                    f"将自动新建分区: {candidate}\n"
                    f"新規スロット {candidate} を作成します。\n"
                    f"Will auto-create new slot: {candidate}"
                )
            )
            return candidate, True  # 新建分区
    # 3. 分区满
    messagebox.showerror(
        "Slot limit reached / 超过最大分区数 / 最大スロット数到達",
        (
            f"最多支持{MAX_SLOT}个分区。请手动删除一个旧分区后重试。\n"
            f"最大{MAX_SLOT}スロットまで。古いスロットを削除してから再実行してください。\n"
            f"Slot count limit ({MAX_SLOT}) reached. Please remove an old slot before continuing."
        )
    )
    return None, False



def get_disk_space(ip, user, pwd, path="/shared/images"):
    out, err = ssh_cmd(ip, user, pwd, f"df -h {path}")
    log(f"[{ip}] Disk space for {path}:\n{out}")
    for line in out.splitlines():
        if "/shared/images" in line:
            parts = line.split()
            if len(parts) > 3:
                return parts[3]
    return "unknown"

def backup_ucs(ip, user, pwd, ucs_dir="./"):
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    ucsname = f"preupgrade_{ip.replace('.', '_')}_{timestamp}.ucs"
    remote_ucs = f"/var/local/ucs/{ucsname}"
    local_ucs = os.path.join(ucs_dir, ucsname)
    log(f"[{ip}] Backing up UCS...")
    cmd = f"tmsh save /sys ucs {remote_ucs}"
    out, err = ssh_cmd(ip, user, pwd, cmd)
    log(f"[{ip}] UCS backup output: {out.strip()} {err.strip()}")
    try:
        transport = paramiko.Transport((ip, 22))
        transport.connect(username=user, password=pwd)
        sftp = paramiko.SFTPClient.from_transport(transport)
        log(f"[{ip}] Downloading UCS backup to local: {local_ucs}")
        sftp.get(remote_ucs, local_ucs)
        sftp.close()
        transport.close()
        log(f"[{ip}] UCS downloaded: {local_ucs}")
        messagebox.showinfo("UCS Download", f"Backup completed: {local_ucs}")
        return True
    except Exception as e:
        log(f"[{ip}] UCS download error: {e}")
        messagebox.showerror("UCS Download Error", str(e))
        return False

def get_next_available_slot(slots):
    # slots=['HD1.1','HD1.2'] 或 ['HD1.1'] 等
    for i in range(1, 4):
        candidate = f'HD1.{i}'
        if candidate not in slots:
            return candidate
    return None

def install_firmware(ip, user, pwd, iso_name, volume, create_volume=False):
    base_name = os.path.basename(iso_name).strip('"').strip("'").strip()
    volume = str(volume).strip('"').strip("'").strip()
    if create_volume:
        cmd = f'tmsh install sys software image {base_name} volume {volume} create-volume'
    else:
        cmd = f'tmsh install sys software image {base_name} volume {volume}'
    print(f"[{ip}] Send command{cmd}")
    logging.info(f"[{ip}] Send command{cmd}")
    out, err = ssh_cmd(ip, user, pwd, cmd)
    logging.info(f"[{ip}] Firmware install output: {out.strip()} {err.strip()}")
    print(f"[{ip}] Install command output:\n{out.strip()} {err.strip()}")
    return out + err


def wait_install_complete(ip, user, pwd, volume, timeout=3600):
    """等待指定卷的安装完成，输出进度，三语提示。"""
    start = time.time()
    last_status = ""
    while True:
        out, _ = ssh_cmd(ip, user, pwd, "tmsh show sys software")
        found = False
        for line in out.splitlines():
            if volume in line:
                found = True
                if "installing" in line or "progress" in line:
                    percent = ""
                    for p in line.split():
                        if "%" in p:
                            percent = p
                            break
                    status_line = f"[{ip}] {volume} installing... {percent} 进度中... Installation progress... インストール進行中..."
                    if status_line != last_status:
                        print(status_line)
                        logging.info(status_line)
                        last_status = status_line
                elif "complete" in line:
                    ok_line = f"[{ip}] {volume} install complete! (ready to reboot) 安装完成！インストール完了！"
                    print(ok_line)
                    logging.info(ok_line)
                    return True
        if not found:
            notfound_line = f"[{ip}] {volume} not found in sys software output. 卷未找到 ボリュームが見つかりません"
            print(notfound_line)
            logging.info(notfound_line)
        if time.time() - start > timeout:
            timeout_line = f"[{ip}] Timeout waiting for {volume} to complete install. 超时 タイムアウト"
            print(timeout_line)
            logging.warning(timeout_line)
            return False
        time.sleep(10)

def reboot_to_volume(ip, user, pwd, volume):
    log = f"[{ip}] Rebooting into {volume}... 再起動中..."
    print(log)
    logging.info(log)
    cmd = f"tmsh reboot volume {volume}"
    out, err = ssh_cmd(ip, user, pwd, cmd)
    logging.info(f"[{ip}] Reboot output: {out.strip()} {err.strip()}")
    print(f"[{ip}] Reboot command output:\n{out.strip()} {err.strip()}")
    return out + err

def get_ha_state(ip, user, pwd):
    out, err = ssh_cmd(ip, user, pwd, "tmsh show cm device")
    for line in out.splitlines():
        if "Device HA State" in line:
            return line.strip().split()[-1].lower()
    return "standalone"

def upload_with_progress(ip, user, pwd, local_iso, remote_dir="/shared/images/"):
    import sys
    import os
    iso_name = os.path.basename(local_iso)
    remote_iso = os.path.join(remote_dir, iso_name)
    filesize = os.path.getsize(local_iso)
    log(f"[{ip}] 开始上传固件（显示进度）... | ファームウェアのアップロードを開始します（進捗表示あり）... | Start uploading firmware (with progress)...")
    try:
        transport = paramiko.Transport((ip, 22))
        transport.connect(username=user, password=pwd)
        sftp = paramiko.SFTPClient.from_transport(transport)
        def callback(done, total):
            percent = int(done * 100 / total)
            sys.stdout.write(f"\r[{ip}] 上传进度/Upload progress/アップロード進行中: {percent}% ")
            sys.stdout.flush()
        sftp.put(local_iso, remote_iso, callback=callback)
        print()
        sftp.close()
        transport.close()
        log(f"[{ip}] 固件上传完成 Firmware upload OK アップロード完了: {remote_iso}")
        return remote_iso
    except Exception as e:
        log(f"[{ip}] 固件上传出错: {e}")
        messagebox.showerror("Upload Error", str(e))
        return None
    
def get_remote_md5(ip, user, pwd, remote_path):
    # 先尝试Linux常见的md5sum命令
    out, err = ssh_cmd(ip, user, pwd, f"md5sum {remote_path}")
    if not out.strip():
        # 有的F5用md5命令
        out, err = ssh_cmd(ip, user, pwd, f"md5 {remote_path}")
    if out:
        return out.strip().split()[0]
    return None


def do_upgrade(ip, user, pwd, iso_path, role_label):
    print(f"\n--- Upgrading {role_label} {ip} ---")
    logging.info(f"=== Upgrading {role_label} {ip} ===")
    # 升级前卷分布
    pre_out, pre_vols = get_all_volumes(ip, user, pwd)
    volume_summary.setdefault(ip, {})['before'] = pre_out
    logging.info(f"[{ip}] BEFORE upgrade volume list:\n{pre_out}")
    # 1. 备份
    if not backup_ucs(ip, user, pwd):
        print(f"[{ip}] UCS backup failed, abort.")
        return False
    # 2. 兼容性检查
    # if not check_upgrade_status(ip, user, pwd):
    #     msg1 = f"[{ip}] 升级兼容性检查失败，终止升级！"
    #     msg2 = f"[{ip}] アップグレード互換性チェック失敗、処理を中止します！"
    #     msg3 = f"[{ip}] Upgrade compatibility check failed, aborting upgrade!"
    #     print(msg1)
    #     print(msg2)
    #     print(msg3)
    #     logging.info(msg1)
    #     logging.info(msg2)
    #     logging.info(msg3)
    #     return False
    # 3. 检查空间
    space = get_disk_space(ip, user, pwd)
    print(f"[{ip}] /shared/images available: {space}")
    logging.info(f"[{ip}] /shared/images available: {space}")
    # 4. 选卷
    volume, create_volume = choose_or_create_install_slot(ip, user, pwd)
    if not volume:
       messagebox.showerror("Error", f"No inactive volume found on {ip}.")
       print(f"[{ip}] No inactive volume found!")
       return False
    print(f"[{ip}] Selected inactive volume: {volume} 需要新建: {create_volume}")
    logging.info(f"[{ip}] Inactive volume: {volume} Create volume: {create_volume}")
    # 5. 上传
    remote_iso = upload_with_progress(ip, user, pwd, iso_path)
    if not remote_iso:
        print(f"[{ip}] Upload failed, abort.")
        return False
    # 6. MD5 校验
    local_md5sum = local_md5(iso_path)
    remote_md5sum = get_remote_md5(ip, user, pwd, remote_iso)
    print(f"[{ip}] Local ISO MD5: {local_md5sum}, Remote ISO MD5: {remote_md5sum}")
    logging.info(f"[{ip}] Local ISO MD5: {local_md5sum}, Remote ISO MD5: {remote_md5sum}")
    if local_md5sum != remote_md5sum:
        messagebox.showerror("MD5 Mismatch", f"Local and remote ISO MD5 do not match on {ip}.")
        print(f"[{ip}] MD5 mismatch!")
        return False
        
    # 7. 安装
    install_output = install_firmware(ip, user, pwd, os.path.basename(iso_path), volume, create_volume=create_volume)
    messagebox.showinfo("Firmware Install", f"{role_label} {ip}: 开始在 {volume} 上安装固件 (Starting firmware install)...\n\n{install_output[:400]}")

    
    
    # 8. 查询安装进度直到 complete
    print(f"[{ip}] 正在安装固件，查询进度...")
    logging.info(f"[{ip}] Waiting for install to complete on {volume}...")
    install_ok = wait_install_complete(ip, user, pwd, volume)
    if not install_ok:
        messagebox.showerror("Install Timeout", f"{role_label} {ip} 安装超时！请检查。")
        return False

    # 安装完成，弹窗人工确认是否重启
    msg = (
        f"{role_label} {ip} 固件安装已完成，准备重启到新分区 {volume}。\n"
        "请确认无误后，点击“确定”重启。\n"
        f"\nFirmware install complete on {ip} ({volume}).\nClick OK to reboot.\n"
        f"\n{ip} のインストール完了。再起動しますか？"
    )
    if not messagebox.askokcancel("安装完成，是否重启？/ Ready to Reboot?", msg):
        print(f"[{ip}] 用户取消重启，流程中止。")
        logging.info(f"[{ip}] User cancelled reboot after install.")
        return False

    # 9. 重启
    reboot_to_volume(ip, user, pwd, volume)
    print(f"[{ip}] Rebooted. Wait for failover or manual confirmation.")
    messagebox.showinfo("Rebooting", f"{role_label} {ip} is rebooting into {volume}.\n\nWait for failover before continuing.")

    # 升级后卷分布
    print(f"[{ip}] Waiting for reboot (90s)...")
    time.sleep(90)
    post_out, post_vols = get_all_volumes(ip, user, pwd)
    volume_summary[ip]['after'] = post_out
    logging.info(f"[{ip}] AFTER upgrade volume list:\n{post_out}")
    return True


ip_role_map = {}
for ip in nodes:
    mgmt_list = get_mgmt_roles(ip, username, password)
    role = None
    for addr, r in mgmt_list:
        if addr == ip:
            role = r
    if not role and mgmt_list:
        role = mgmt_list[0][1]
    if not role:
        role = "unknown"
    ip_role_map[ip] = role

md5_local = local_md5(firmware_path)
role_summary = "\n".join([
    f"{ip} : {'🟢ACTIVE' if role == 'active' else '🟡STANDBY' if role == 'standby' else role.upper()}"
    for ip, role in ip_role_map.items()
])
env_info = (
    f"ISO: {firmware_path}\nMD5: {md5_local}\n"
    f"Nodes:\n" + "\n".join(nodes) + "\n"
    f"Mgmt/HA info:\n{role_summary}\n"
)
messagebox.showinfo("F5 Upgrade - Environment Summary", env_info)
print(f"环境检测与角色识别已完成，日志已写入: {LOG_FILE} | 環境検出とロール認識が完了しました。ログに出力しました: {LOG_FILE} | Environment detection and role identification completed. Log written to: {LOG_FILE}")

ip_role_items = list(ip_role_map.items())
if len(ip_role_items) == 2:
    if ip_role_items[0][1] == "standby" and ip_role_items[1][1] == "active":
        standby, active = ip_role_items[0][0], ip_role_items[1][0]
    elif ip_role_items[0][1] == "active" and ip_role_items[1][1] == "standby":
        standby, active = ip_role_items[1][0], ip_role_items[0][0]
    else:
        standby = ip_role_items[0][0]
        active = ip_role_items[0][0]
else:
    standby = ip_role_items[0][0]
    active = ip_role_items[0][0]

if messagebox.askyesno("Ready to Upgrade", f"Ready to backup and upgrade STANDBY node?\n{standby}"):
    ok = do_upgrade(standby, username, password, firmware_path, "STANDBY")
    if ok:
        messagebox.showinfo("Wait", "Wait for node to reboot and failover. Click OK to continue after standby becomes active.")
        for n in range(30):
            print(f"Waiting for {standby} to become ACTIVE... ({n+1}/30)")
            time.sleep(10)
            ha = get_ha_state(standby, username, password)
            if ha == "active":
                print(f"{standby} is now ACTIVE.")
                break
        messagebox.showinfo("Standby Now Active", f"{standby} is now ACTIVE. Please confirm service OK before upgrading other node.")

if standby != active and messagebox.askyesno("Continue", f"Upgrade ACTIVE node?\n{active}"):
    ok2 = do_upgrade(active, username, password, firmware_path, "ACTIVE")
    if ok2:
        messagebox.showinfo("Upgrade Finished", "All nodes upgraded. Please verify services.")
else:
    messagebox.showinfo("Done", "Upgrade completed or cancelled.")

logging.info("==== F5 UPGRADE ALL FINISHED ====")
print("\n==== F5 UPGRADE ALL FINISHED ====\n")

def write_volume_summary():
    summary_file = f'F5_Volume_Summary_{time.strftime("%Y%m%d_%H%M%S")}.txt'
    with open(summary_file, "w", encoding="utf-8") as f:
        for ip, vols in volume_summary.items():
            f.write(f"=== {ip} 升级前分区分布 (Before Upgrade) ===\n{vols.get('before','')}\n\n")
            f.write(f"=== {ip} 升级后分区分布 (After Upgrade) ===\n{vols.get('after','')}\n\n")
            f.write(f"=== {ip} アップグレード前のパーティション一覧 ===\n{vols.get('before','')}\n\n")
            f.write(f"=== {ip} アップグレード後のパーティション一覧 ===\n{vols.get('after','')}\n\n")
            f.write("-" * 40 + "\n")
    # 屏幕与日志都输出
    msg = (
        f"\n卷分区详细对比已写入: {summary_file}\n"
        f"パーティション差分レポートを保存しました: {summary_file}\n"
        f"Partition summary written: {summary_file}\n"
    )
    print(msg)
    logging.info(msg)

# 在主流程结尾处直接加一句调用：
write_volume_summary()
