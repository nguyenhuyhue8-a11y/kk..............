import requests
import time
import threading
import uuid
import os
import json
from flask import Flask, request, jsonify
from requests.exceptions import ReadTimeout, ConnectTimeout
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# ================= CẤU HÌNH HỆ THỐNG V22 (DAILY LIMIT 20) =================
HISTORY_FILE = "history_buff.txt"
STATS_FILE = "auto_stats.json"
KEYS_FILE = "keys_store.json"
DAILY_LIMIT_FILE = "daily_limit.json" # File lưu giới hạn ngày

tasks_status = {}
running_users = {}

# Thời gian chờ giữa các lần buff (15 phút = 900 giây)
COOLDOWN_SECONDS = 15 * 60 
DELETE_TASK_AFTER = 5 * 60 

# GIỚI HẠN BUFF FREE
MAX_DAILY_FREE = 20  # Số lần tối đa 1 ngày cho User Free

ADMIN_KEY_MASTER = "ADMINVIPFREEFL"
SERVER_KEY = "SEVERKINGADMINFL"
SERVER_ACTIVE = True

# ==========================================
# 0. GIAO DIỆN WEB (v22)
# ==========================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 TIKTOK BUFF PRO v22 ULTIMATE</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;800&display=swap');
        :root { --bg: #e0e5ec; --text: #4d4d4d; --primary: #6d5dfc; --success: #00b894; --error: #d63031; --shadow-light: #ffffff; --shadow-dark: #a3b1c6; --log-bg: #dde1e7; }
        body.dark-mode { --bg: #1b1b1b; --text: #00ff41; --primary: #00ff41; --success: #00ff41; --error: #ff4757; --shadow-light: #262626; --shadow-dark: #101010; --log-bg: #000000; }
        * { box-sizing: border-box; transition: all 0.3s ease; }
        body { background-color: var(--bg); color: var(--text); font-family: 'Nunito', sans-serif; display: flex; flex-direction: column; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }
        .neu-box { border-radius: 20px; background: var(--bg); box-shadow: 9px 9px 16px var(--shadow-dark), -9px -9px 16px var(--shadow-light); padding: 30px; width: 100%; max-width: 700px; margin-bottom: 25px; }
        h1 { text-align: center; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 2px; margin-top: 0; }
        .neu-input { width: 100%; border: none; border-radius: 15px; padding: 15px; background: var(--bg); box-shadow: inset 5px 5px 10px var(--shadow-dark), inset -5px -5px 10px var(--shadow-light); color: var(--text); font-family: inherit; font-weight: 600; outline: none; resize: vertical; }
        .neu-btn { width: 100%; padding: 15px; margin-top: 20px; border-radius: 50px; border: none; background: var(--bg); box-shadow: 6px 6px 10px var(--shadow-dark), -6px -6px 10px var(--shadow-light); color: var(--primary); font-weight: 800; font-size: 16px; cursor: pointer; }
        .neu-btn:hover { transform: translateY(-2px); }
        .neu-btn:active { box-shadow: inset 4px 4px 8px var(--shadow-dark), inset -4px -4px 8px var(--shadow-light); transform: translateY(0); }
        .neu-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .ping-btn { width: auto; padding: 10px 20px; font-size: 14px; margin-bottom: 15px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
        .ping-good { color: #00b894; }
        .ping-bad { color: #d63031; }
        #log-area { height: 350px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 13px; padding: 15px; border-radius: 15px; background: var(--log-bg); box-shadow: inset 5px 5px 10px var(--shadow-dark), inset -5px -5px 10px var(--shadow-light); line-height: 1.5; }
        .theme-toggle { position: fixed; top: 20px; right: 20px; width: 50px; height: 50px; border-radius: 50%; background: var(--bg); box-shadow: 5px 5px 10px var(--shadow-dark), -5px -5px 10px var(--shadow-light); display: flex; align-items: center; justify-content: center; cursor: pointer; color: var(--text); font-size: 20px; z-index: 1000; }
        .theme-toggle:active { box-shadow: inset 3px 3px 6px var(--shadow-dark), inset -3px -3px 6px var(--shadow-light); }
        .log-time { color: #888; margin-right: 5px; font-size: 11px; }
        .st-run { color: #e67e22; }
        .st-ok { color: var(--success); font-weight: bold; }
        .st-err { color: var(--error); }
        .st-info { color: var(--text); opacity: 0.8; }
        .user-tag { background: var(--primary); color: var(--bg); padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="theme-toggle" onclick="toggleTheme()"><i id="theme-icon" class="fas fa-moon"></i></div>
    <div class="neu-box">
        <h1><i class="fab fa-tiktok"></i> ADMIN BUFF v22</h1>
        <div style="text-align: center;">
            <button class="neu-btn ping-btn" onclick="checkServerPing()"><i class="fas fa-satellite-dish"></i> CHECK SEVER PING: <span id="ping-val">--</span></button>
        </div>
        <p style="text-align:center; font-weight:600; margin-bottom: 20px;">Nhập danh sách User (ID) bên dưới.</p>
        <textarea id="users-input" class="neu-input" rows="5" placeholder="user1&#10;user2..."></textarea>
        <button id="btn-buff" class="neu-btn" onclick="startMultiBuff()"><i class="fas fa-bolt"></i> CHẠY TIẾN TRÌNH</button>
    </div>
    <div class="neu-box">
        <h3 style="margin-top:0"><i class="fas fa-terminal"></i> LIVE LOGS</h3>
        <div id="log-area"><div class="st-info">[SYSTEM] Hệ thống v22 sẵn sàng...</div></div>
    </div>
    <script>
        function toggleTheme() { document.body.classList.toggle('dark-mode'); const icon = document.getElementById('theme-icon'); icon.className = document.body.classList.contains('dark-mode') ? 'fas fa-sun' : 'fas fa-moon'; }
        function log(msg, type = 'st-info', user = null) { const area = document.getElementById('log-area'); const time = new Date().toLocaleTimeString('vi-VN', {hour12: false}); let userHtml = user ? `<span class="user-tag">${user}</span>` : ''; area.insertAdjacentHTML('beforeend', `<div style="margin-bottom:4px"><span class="log-time">[${time}]</span>${userHtml}<span class="${type}">${msg}</span></div>`); area.scrollTop = area.scrollHeight; }
        async function checkServerPing() {
            const span = document.getElementById('ping-val'); span.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; const start = Date.now();
            try { await fetch('/ping'); const ms = Date.now() - start; let colorClass = ms < 200 ? 'ping-good' : 'ping-bad'; span.innerHTML = `<span class="${colorClass}">${ms}ms</span>`; } catch (e) { span.innerHTML = `<span class="ping-bad">Error</span>`; }
        }
        async function startMultiBuff() {
            const input = document.getElementById('users-input').value; const users = input.split(/[\n,]+/).map(u => u.trim()).filter(u => u);
            if (users.length === 0) return alert("⚠️ Vui lòng nhập ít nhất 1 username!");
            document.getElementById('btn-buff').disabled = true;
            for (const user of users) { runSingleUser(user); await new Promise(r => setTimeout(r, 500)); }
            setTimeout(() => { document.getElementById('btn-buff').disabled = false; }, 3000);
        }
        async function runSingleUser(user) {
            log(`Đang gửi yêu cầu...`, 'st-run', user);
            try {
                const res = await fetch(`/bufffl?username=${user}`); const data = await res.json();
                if (data.status === 'error' && data.msg.includes('Đang chạy')) { log(`⛔ ${data.msg}`, 'st-err', user); return; }
                if (data.status === 'cooldown' || data.status === 'maintenance') { log(`⏳ ${data.msg}`, 'st-info', user); return; }
                if (data.status === 'daily_limit') { log(`⛔ ${data.msg}`, 'st-err', user); return; }
                if (data.status === 'pending') { log(`✅ Task ID: ${data.task_id}`, 'st-ok', user); trackTask(data.task_id, user); } 
                else { log(`❌ ${data.msg}`, 'st-err', user); }
            } catch (e) { log(`❌ Lỗi kết nối!`, 'st-err', user); }
        }
        async function trackTask(taskId, user) {
            let lastMsg = "";
            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/checkfl?task_id=${taskId}`); const data = await res.json();
                    if (data.status === 'running') { if (data.msg !== lastMsg) { log(`🔄 ${data.msg}`, 'st-run', user); lastMsg = data.msg; } } 
                    else if (data.status === 'success') { 
                        clearInterval(interval); 
                        log(`🎉 ${data.msg}`, 'st-ok', user); 
                        if(data.cooldown_msg) { log(`⏳ ${data.cooldown_msg}`, 'st-info', user); }
                    } 
                    else { clearInterval(interval); log(`☠️ ${data.msg}`, 'st-err', user); }
                } catch (e) { clearInterval(interval); }
            }, 3000);
        }
    </script>
</body>
</html>
"""

# ==========================================
# 1. QUẢN LÝ DỮ LIỆU
# ==========================================
def load_json(file_path):
    if not os.path.exists(file_path): return {}
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except: return {}

def save_json(file_path, data):
    with open(file_path, 'w') as f: json.dump(data, f, indent=4)

def parse_duration(duration_str):
    try:
        val = int(duration_str[:-1])
        unit = duration_str[-1].lower()
        if unit == 'm': return val * 60
        if unit == 'h': return val * 3600
        if unit == 'd': return val * 86400
    except: pass
    return 0

def format_time_diff(seconds):
    if seconds < 0: return "Hết hạn"
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    parts = []
    if d > 0: parts.append(f"{int(d)} ngày")
    if h > 0: parts.append(f"{int(h)} giờ")
    if m > 0: parts.append(f"{int(m)} phút")
    if not parts: return f"{int(seconds)} giây"
    return " ".join(parts)

def get_vn_date_str():
    # Lấy ngày giờ VN để làm chuẩn reset (UTC+7)
    return datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d')

# --- HÀM LẤY IP THẬT (FIX PROXY/RENDER) ---
def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

# ==========================================
# 2. HELPER LOGIC (THÊM DAILY LIMIT)
# ==========================================

# --- HÀM KIỂM TRA GIỚI HẠN NGÀY ---
def check_and_update_daily_limit(username):
    today = get_vn_date_str()
    data = load_json(DAILY_LIMIT_FILE)
    
    # Nếu file chưa có dữ liệu hoặc đã qua ngày mới -> Reset
    if "date" not in data or data["date"] != today:
        data = {
            "date": today,
            "users": {}
        }
    
    # Lấy số lần đã dùng hôm nay
    current_count = data["users"].get(username, 0)
    
    if current_count >= MAX_DAILY_FREE:
        return False, current_count
    
    # Nếu chưa vượt quá, cộng thêm 1 và lưu
    data["users"][username] = current_count + 1
    save_json(DAILY_LIMIT_FILE, data)
    
    return True, current_count + 1

def check_history_cooldown(username):
    if not os.path.exists(HISTORY_FILE): return True, 0
    current_time = time.time()
    with open(HISTORY_FILE, 'r') as f: lines = f.readlines()
    for line in lines:
        parts = line.strip().split('|')
        if parts[0] == username:
            if len(parts) > 1 and float(parts[1]) > 0:
                diff = current_time - float(parts[1])
                if diff < COOLDOWN_SECONDS: return False, int(COOLDOWN_SECONDS - diff)
    return True, 0

def record_cooldown_history(username):
    current_time = time.time()
    lines = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f: lines = f.readlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{username}|"):
            new_lines.append(f"{username}|{current_time}")
            found = True
        else: new_lines.append(line.strip())
    if not found: new_lines.append(f"{username}|{current_time}")
    with open(HISTORY_FILE, 'w') as f: f.write('\n'.join(new_lines))

def increment_success_count(username):
    stats = load_json(STATS_FILE)
    if username not in stats: stats[username] = 0
    stats[username] += 1
    save_json(STATS_FILE, stats)

def get_success_count(username):
    stats = load_json(STATS_FILE)
    return stats.get(username, 0)

def get_key_expiry_info(key):
    if key == ADMIN_KEY_MASTER: return "Vĩnh viễn (Admin)"
    keys_db = load_json(KEYS_FILE)
    if key not in keys_db: return "Không xác định"
    data = keys_db[key]
    if data["type"] == "unlimited": return "Vĩnh viễn"
    remaining = data["expire"] - time.time()
    if remaining <= 0: return "Đã hết hạn"
    return format_time_diff(remaining)

# ==========================================
# 3. WORKER BUFF
# ==========================================
def get_live_follower_count(username):
    try:
        url = "https://www.tikwm.com/api/user/info"
        params = {"unique_id": username}
        headers = { "User-Agent": "Mozilla/5.0" }
        r = requests.get(url, params=params, headers=headers, timeout=18)
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 0: return int(data["data"]["stats"]["followerCount"])
        return None
    except: return None

def worker_buff(task_id, username, used_key=None, target_counts=1):
    try:
        # Khởi tạo trạng thái
        tasks_status[task_id] = { 
            "status": "running", 
            "msg": f"Bắt đầu buff 0/{target_counts}...", 
            "start_time": time.time(), 
            "username": username,
            "key_used": used_key,
            "current_followers": "Đang tải...",
            "target_counts": target_counts,
            "done_counts": 0
        }
        
        ss = requests.Session()
        headers_search = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Origin": "https://tikfollowers.com",
            "Referer": "https://tikfollowers.com/"
        }

        success_round = 0

        # --- VÒNG LẶP BUFF (Chạy đủ số lần requested) ---
        while success_round < target_counts:
            round_display = success_round + 1
            
            # 1. Quét thông tin User
            try:
                tasks_status[task_id]["msg"] = f"[Lần {round_display}/{target_counts}] Đang quét thông tin..."
                r1 = ss.post("https://tikfollowers.com/api/search", 
                             json={"input": username, "type": "getUserDetails"}, 
                             headers=headers_search, timeout=22)
                d1 = r1.json()
                if d1.get("status") != "success": 
                    raise Exception(d1.get("message", "User không tồn tại."))
                
                current_fl = get_live_follower_count(username)
                start_fl = current_fl if current_fl else d1.get('followers_count', 0)
                nickname = d1.get('nickname')
                
            except Exception as e:
                tasks_status[task_id]["status"] = "error"
                tasks_status[task_id]["msg"] = str(e)
                return # Dừng luôn nếu lỗi info

            # 2. Gửi lệnh Buff
            tasks_status[task_id]["msg"] = f"[Lần {round_display}/{target_counts}] User: {nickname}. Đang gửi lệnh..."
            payload = { 
                "status": "success", "token": d1.get("token"), "user_id": d1.get("user_id"), 
                "sec_uid": d1.get("sec_uid"), "username": username, "followers_count": start_fl, 
                "nickname": nickname, "type": "followers", "success": True 
            }

            api_slow = False
            try:
                ss.post("https://tikfollowers.com/api/process", json=payload, headers=headers_search, timeout=28)
            except (ReadTimeout, ConnectTimeout):
                api_slow = True
                tasks_status[task_id]["msg"] = f"[Lần {round_display}] API chậm, chờ 1 chút..."

            # 3. Check kết quả (Chờ follow lên)
            loop_count = 0
            max_loops = 20 if api_slow else 18
            round_success = False

            while loop_count < max_loops:
                time.sleep(10)
                now_fl = get_live_follower_count(username)
                if now_fl and now_fl > start_fl:
                    diff = now_fl - start_fl
                    round_success = True
                    # Ghi nhận thành công lần này
                    record_cooldown_history(username) 
                    increment_success_count(username)
                    tasks_status[task_id]["current_followers"] = now_fl
                    break
                tasks_status[task_id]["msg"] = f"[Lần {round_display}] Đang check... ({loop_count+1}/{max_loops})"
                loop_count += 1
            
            if round_success:
                success_round += 1
                tasks_status[task_id]["done_counts"] = success_round
                
                # Nếu chưa phải lần cuối thì Sleep chờ cooldown
                if success_round < target_counts:
                    # Đếm ngược 15 phút (900 giây)
                    for wait_s in range(COOLDOWN_SECONDS, 0, -1):
                        m, s = divmod(wait_s, 60)
                        tasks_status[task_id]["msg"] = f"✅ Xong lần {success_round}. Đợi {m}p {s}s buff tiếp lần {success_round+1}..."
                        time.sleep(1)
                else:
                    # Đã xong tất cả các lần
                    tasks_status[task_id]["msg"] = f"🎉 Đã hoàn thành {success_round}/{target_counts} lần buff!"
            else:
                # Nếu lần này thất bại -> Thử lại sau 1 phút (hoặc dừng tùy logic)
                tasks_status[task_id]["msg"] = f"[Lần {round_display}] Thất bại. Thử lại sau 60s..."
                time.sleep(60)

        tasks_status[task_id]["status"] = "success"

    except Exception as e:
        tasks_status[task_id] = {"status": "error", "msg": f"System Error: {str(e)}"}
    finally:
        if username in running_users: del running_users[username]
        time.sleep(DELETE_TASK_AFTER)
        if task_id in tasks_status: del tasks_status[task_id]

# ==========================================
# 4. API ENDPOINTS (NÂNG CẤP V22)
# ==========================================

@app.route('/ping', methods=['GET'])
def ping_server():
    return jsonify({"status": "ok", "msg": "pong"})

@app.route('/checkkey', methods=['GET'])
def check_key_info():
    key = request.args.get('key')
    if not key: return jsonify({"status": "error", "msg": "Thiếu key"})
    if key == ADMIN_KEY_MASTER:
        return jsonify({ "status": "success", "type": "ADMIN MASTER", "expiry": "Vĩnh viễn", "msg": "Key Admin quyền lực nhất" })
    keys_db = load_json(KEYS_FILE)
    if key not in keys_db: return jsonify({"status": "error", "msg": "Key không tồn tại"})
    data = keys_db[key]
    if data["type"] == "auto":
        remaining = data["expire"] - time.time()
        expiry_date = datetime.fromtimestamp(data["expire"]).strftime('%Y-%m-%d %H:%M:%S')
        if remaining <= 0: return jsonify({ "status": "expired", "msg": "Key đã hết hạn", "expiry_date": expiry_date })
        time_left = format_time_diff(remaining)
        max_users = data.get("max_users", 9999)
        used_users_list = data.get("used_users", [])
        return jsonify({
            "status": "success", "type": "AUTO", "expiry": time_left, "expiry_date": expiry_date,
            "max_devices": data.get("max_devices", 1), "used_devices": len(data.get("used_ips", [])),
            "max_stk": max_users, "used_stk": len(used_users_list), "msg": "Key hợp lệ"
        })
    elif data["type"] == "unlimited":
        return jsonify({ "status": "success", "type": "VIP UNLIMITED", "expiry": "Vĩnh viễn", "msg": "Key VIP vĩnh viễn" })
    return jsonify({"status": "error", "msg": "Lỗi định dạng key"})

@app.route('/checkauto', methods=['GET'])
def check_auto_details():
    task_id = request.args.get('task_id')
    if not task_id: return jsonify({"status": "error", "msg": "Thiếu task_id"})
    task_data = tasks_status.get(task_id)
    if not task_data: return jsonify({"status": "not_found", "msg": "Task không tồn tại/đã xóa"})
    
    start_t = task_data.get("start_time", time.time())
    m, s = divmod(int(time.time() - start_t), 60)
    user = task_data.get("username", "unknown")
    
    target = task_data.get("target_counts", 1)
    done = task_data.get("done_counts", 0)

    response = {
        "status": task_data.get("status"), 
        "msg": task_data.get("msg"),
        "username": user, 
        "time_running": f"{m} phút {s} giây",
        "progress": f"{done}/{target} lần", 
        "date": get_vn_date_str(), 
        "total_success_count": get_success_count(user),
        "current_followers": task_data.get("current_followers", "Chưa cập nhật"),
        "cooldown_msg": ""
    }

    if task_data.get("status") == "success":
        response["msg"] = "✅ Đã hoàn thành toàn bộ yêu cầu!"
        can_buff, wait_time = check_history_cooldown(user)
        if not can_buff:
            wm, ws = divmod(wait_time, 60)
            response["cooldown_msg"] = f"⏳ Đợi {wm} phút {ws} giây nếu muốn tạo task mới"

    used_key = task_data.get("key_used")
    key_info = "Không xác định"
    if used_key: key_info = get_key_expiry_info(used_key)
    response["key_remaining"] = key_info

    return jsonify(response)

# --- AUTO: STRICT IP LOCK ---
@app.route('/auto', methods=['GET'])
def api_auto():
    username = request.args.get('username')
    key = request.args.get('keyauto')
    try:
        req_counts = int(request.args.get('counts', 1))
    except:
        req_counts = 1

    ip = get_client_ip()
    
    if not SERVER_ACTIVE and key != SERVER_KEY: return jsonify({"status": "maintenance"})
    keys_db = load_json(KEYS_FILE)
    
    key_expiry_str = ""
    if key != ADMIN_KEY_MASTER:
        if key not in keys_db: return jsonify({"status": "error", "msg": "Sai key"})
        data = keys_db[key]
        if data["type"] == "auto":
            current_t = time.time()
            if current_t > data["expire"]: 
                del keys_db[key]; save_json(KEYS_FILE, keys_db)
                return jsonify({"status": "error", "msg": "Key hết hạn"})
            
            if ip not in data["used_ips"]:
                if len(data["used_ips"]) >= data["max_devices"]:
                    return jsonify({
                        "status": "error", 
                        "msg": f"Key đã bị khóa theo IP khác ({data['used_ips'][0]})! IP của bạn: {ip}"
                    })
                data["used_ips"].append(ip)
                save_json(KEYS_FILE, keys_db)
            
            used_users = data.get("used_users", [])
            limit_users = data.get("max_users", 9999)
            
            if username not in used_users:
                if len(used_users) >= limit_users:
                    return jsonify({
                        "status": "error", 
                        "msg": f"Key đã hết lượt thêm User mới (Max: {limit_users} accs)"
                    })
                used_users.append(username)
                data["used_users"] = used_users
                save_json(KEYS_FILE, keys_db)
            
            required_seconds = req_counts * COOLDOWN_SECONDS
            remaining_key_seconds = data["expire"] - current_t
            if required_seconds > remaining_key_seconds:
                max_possible = int(remaining_key_seconds // COOLDOWN_SECONDS)
                if max_possible < 1: max_possible = 1
                return jsonify({
                    "status": "error",
                    "msg": f"Key không đủ thời gian cho {req_counts} lần! Max: {max_possible} lần.",
                    "max_allowed": max_possible
                })
            
            key_expiry_str = format_time_diff(remaining_key_seconds)
        else:
            key_expiry_str = "Vĩnh viễn"
    else:
        key_expiry_str = "Vĩnh viễn (Admin)"

    if username in running_users:
        return jsonify({ "status": "running", "msg": "Đang chạy task cũ", "task_id": running_users[username], "key_time_left": key_expiry_str })
    
    can_buff, wait_time = check_history_cooldown(username)
    if not can_buff: return jsonify({"status": "cooldown", "msg": f"Wait {wait_time}s"})
    
    task_id = str(uuid.uuid4())
    running_users[username] = task_id
    threading.Thread(target=worker_buff, args=(task_id, username, key, req_counts)).start()
    
    return jsonify({ 
        "status": "pending", 
        "task_id": task_id, 
        "key_time_left": key_expiry_str, 
        "msg": f"Đã nhận lệnh buff {req_counts} lần liên tục!",
        "total_counts": req_counts 
    })

@app.route('/admintiktoksv', methods=['GET'])
def admin_server():
    global SERVER_ACTIVE
    if request.args.get('key') != SERVER_KEY: return jsonify({"status": "error", "msg": "Sai key"})
    mode = request.args.get('sever')
    if mode == 'on': SERVER_ACTIVE = True
    elif mode == 'off': SERVER_ACTIVE = False
    return jsonify({"status": "success", "server": SERVER_ACTIVE})

@app.route('/admintik', methods=['GET'])
def create_auto_key():
    key = request.args.get('createkeyauto')
    max_dev = request.args.get('devices', type=int)
    dur = request.args.get('time')
    stk_limit = request.args.get('stk', type=int, default=999)
    if not key or not max_dev or not dur: return jsonify({"msg": "Thiếu tham số"})
    keys = load_json(KEYS_FILE)
    keys[key] = {
        "type": "auto", "expire": time.time() + parse_duration(dur), 
        "max_devices": max_dev, "max_users": stk_limit, 
        "used_ips": [], "used_users": []
    }
    save_json(KEYS_FILE, keys)
    return jsonify({"status": "success", "msg": f"Created Key limit {stk_limit} users"})

@app.route('/admintiktok', methods=['GET'])
def create_vip_key():
    key = request.args.get('createkey')
    if not key: return jsonify({"msg": "Thiếu key"})
    keys = load_json(KEYS_FILE)
    keys[key] = {"type": "unlimited"}
    save_json(KEYS_FILE, keys)
    return jsonify({"status": "success"})

@app.route('/url.html')
def ui(): return HTML_PAGE

@app.route('/')
def index(): return '<meta http-equiv="refresh" content="0; url=/url.html" />'

# --- API BUFF FREE (CÓ CHECK DAILY LIMIT) ---
@app.route('/bufffl', methods=['GET'])
def web_buff():
    if not SERVER_ACTIVE: return jsonify({"status": "maintenance", "msg": "Bảo trì."})
    username = request.args.get('username')
    if not username: return jsonify({"msg": "Thiếu username"}), 400
    
    if username in running_users:
        return jsonify({ "status": "error", "msg": f"Đang chạy tiến trình khác!", "task_id": running_users[username] })
    
    # 1. Check Cooldown
    can_buff, wait_time = check_history_cooldown(username)
    if not can_buff: 
        return jsonify({"status": "cooldown", "msg": f"Đợi {wait_time // 60}p {wait_time % 60}s"})
    
    # 2. Check Daily Limit (V22)
    is_allowed, count = check_and_update_daily_limit(username)
    if not is_allowed:
        return jsonify({
            "status": "daily_limit",
            "msg": f"Bạn đã hết lượt Free hôm nay ({MAX_DAILY_FREE}/{MAX_DAILY_FREE}). Quay lại vào ngày mai!"
        })

    task_id = str(uuid.uuid4())
    running_users[username] = task_id
    threading.Thread(target=worker_buff, args=(task_id, username, "WEB_FREE", 1)).start()
    return jsonify({"status": "pending", "task_id": task_id})

@app.route('/checkfl', methods=['GET'])
def check_status():
    task_id = request.args.get('task_id')
    task_data = tasks_status.get(task_id)
    if not task_data: return jsonify({"status": "not_found", "msg": "Not found"})
    response = task_data.copy()
    start_t = task_data.get("start_time", time.time())
    m, s = divmod(int(time.time() - start_t), 60)
    response["time_running"] = f"{m} phút {s} giây"
    if task_data.get("status") == "success":
        user = task_data.get("username")
        can_buff, wait_time = check_history_cooldown(user)
        if not can_buff:
             wm, ws = divmod(wait_time, 60)
             response["cooldown_msg"] = f"⏳ Đợi {wm}p {ws}s để buff tiếp"
             response["msg"] += f" (Wait {wm}p{ws}s)"
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
