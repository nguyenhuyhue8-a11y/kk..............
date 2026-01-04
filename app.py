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

# ================= CẤU HÌNH HỆ THỐNG =================
# File lưu lịch sử: username|timestamp|daily_count|last_date
HISTORY_FILE = "history_buff.txt"
tasks_status = {}
# Thời gian chờ (giây) - 15 phút
COOLDOWN_SECONDS = 15 * 60 
# Thời gian xóa Task ID sau khi hoàn thành (giây)
DELETE_TASK_AFTER = 5 * 60
# Giới hạn số lần buff trong 1 ngày
MAX_DAILY_REQUESTS = 20
# Key Admin
ADMIN_KEY = "ADMINVIPFREEFL"

# ==========================================
# 0. GIAO DIỆN WEB
# ==========================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 MULTI TIKTOK BUFF v3.0</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;800&display=swap');

        :root {
            --bg: #e0e5ec;
            --text: #4d4d4d;
            --primary: #6d5dfc;
            --success: #00b894;
            --error: #d63031;
            --shadow-light: #ffffff;
            --shadow-dark: #a3b1c6;
            --log-bg: #dde1e7;
        }

        body.dark-mode {
            --bg: #1b1b1b;
            --text: #00ff41;
            --primary: #00ff41;
            --success: #00ff41;
            --error: #ff4757;
            --shadow-light: #262626;
            --shadow-dark: #101010;
            --log-bg: #000000;
        }

        * { box-sizing: border-box; transition: all 0.3s ease; }

        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Nunito', sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }

        .neu-box {
            border-radius: 20px;
            background: var(--bg);
            box-shadow: 9px 9px 16px var(--shadow-dark), -9px -9px 16px var(--shadow-light);
            padding: 30px;
            width: 100%;
            max-width: 700px;
            margin-bottom: 25px;
        }

        h1 {
            text-align: center;
            font-weight: 800;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-top: 0;
        }

        .neu-input {
            width: 100%;
            border: none;
            border-radius: 15px;
            padding: 15px;
            background: var(--bg);
            box-shadow: inset 5px 5px 10px var(--shadow-dark), inset -5px -5px 10px var(--shadow-light);
            color: var(--text);
            font-family: inherit;
            font-weight: 600;
            outline: none;
            resize: vertical;
        }

        .neu-btn {
            width: 100%;
            padding: 15px;
            margin-top: 20px;
            border-radius: 50px;
            border: none;
            background: var(--bg);
            box-shadow: 6px 6px 10px var(--shadow-dark), -6px -6px 10px var(--shadow-light);
            color: var(--primary);
            font-weight: 800;
            font-size: 16px;
            cursor: pointer;
        }

        .neu-btn:hover { transform: translateY(-2px); }
        .neu-btn:active {
            box-shadow: inset 4px 4px 8px var(--shadow-dark), inset -4px -4px 8px var(--shadow-light);
            transform: translateY(0);
        }
        .neu-btn:disabled { opacity: 0.6; cursor: not-allowed; }

        #log-area {
            height: 350px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            padding: 15px;
            border-radius: 15px;
            background: var(--log-bg);
            box-shadow: inset 5px 5px 10px var(--shadow-dark), inset -5px -5px 10px var(--shadow-light);
            line-height: 1.5;
        }

        .theme-toggle {
            position: fixed;
            top: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: var(--bg);
            box-shadow: 5px 5px 10px var(--shadow-dark), -5px -5px 10px var(--shadow-light);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            color: var(--text);
            font-size: 20px;
            z-index: 1000;
        }
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

    <div class="theme-toggle" onclick="toggleTheme()">
        <i id="theme-icon" class="fas fa-moon"></i>
    </div>

    <div class="neu-box">
        <h1><i class="fab fa-tiktok"></i> MULTI BUFF TOOL 🚀</h1>
        <p style="text-align:center; font-weight:600; margin-bottom: 20px;">
            Nhập danh sách User (ID) bên dưới.<br>
            <span style="font-size:12px; opacity:0.7">(Mỗi dòng 1 user hoặc cách nhau dấu phẩy)</span>
        </p>
        
        <textarea id="users-input" class="neu-input" rows="5" placeholder="user1&#10;user2&#10;user3..."></textarea>
        
        <button id="btn-buff" class="neu-btn" onclick="startMultiBuff()">
            <i class="fas fa-bolt"></i> CHẠY TIẾN TRÌNH (AUTO)
        </button>
    </div>

    <div class="neu-box">
        <h3 style="margin-top:0"><i class="fas fa-terminal"></i> LIVE LOGS</h3>
        <div id="log-area">
            <div class="st-info">[SYSTEM] Hệ thống sẵn sàng... Nhập user để bắt đầu.</div>
        </div>
    </div>

    <script>
        // 1. Logic Giao diện (Dark Mode)
        function toggleTheme() {
            document.body.classList.toggle('dark-mode');
            const icon = document.getElementById('theme-icon');
            if (document.body.classList.contains('dark-mode')) {
                icon.className = 'fas fa-sun';
            } else {
                icon.className = 'fas fa-moon';
            }
        }

        // 2. Logic Log
        function log(msg, type = 'st-info', user = null) {
            const area = document.getElementById('log-area');
            const time = new Date().toLocaleTimeString('vi-VN', {hour12: false});
            
            let userHtml = user ? `<span class="user-tag">${user}</span>` : '';
            let html = `<div style="margin-bottom:4px">
                <span class="log-time">[${time}]</span>${userHtml}<span class="${type}">${msg}</span>
            </div>`;
            
            area.insertAdjacentHTML('beforeend', html);
            area.scrollTop = area.scrollHeight;
        }

        // 3. Xử lý đa luồng (Multi Users)
        async function startMultiBuff() {
            const input = document.getElementById('users-input').value;
            // Tách user bằng dấu xuống dòng hoặc dấu phẩy
            const users = input.split(/[\n,]+/).map(u => u.trim()).filter(u => u);

            if (users.length === 0) return alert("⚠️ Vui lòng nhập ít nhất 1 username!");

            const btn = document.getElementById('btn-buff');
            btn.disabled = true;
            btn.innerHTML = `<i class="fas fa-circle-notch fa-spin"></i> ĐANG XỬ LÝ ${users.length} USER...`;

            log(`========================================`);
            log(`Bắt đầu xử lý danh sách: ${users.length} tài khoản.`, 'st-info');

            // Chạy vòng lặp cho từng user
            for (const user of users) {
                runSingleUser(user);
                // Delay nhẹ 500ms giữa các request để tránh spam server quá nhanh
                await new Promise(r => setTimeout(r, 500));
            }

            // Sau 3 giây bật lại nút (để spam tiếp nếu muốn, task cũ vẫn chạy ngầm)
            setTimeout(() => {
                btn.disabled = false;
                btn.innerHTML = `<i class="fas fa-bolt"></i> CHẠY TIẾP DANH SÁCH MỚI`;
            }, 3000);
        }

        // 4. Logic Buff cho 1 User
        async function runSingleUser(user) {
            log(`Đang gửi yêu cầu...`, 'st-run', user);

            try {
                // Gọi API Create Task
                const res = await fetch(`/bufffl?username=${user}`);
                const data = await res.json();

                if (data.status === 'cooldown') {
                    log(`⏳ ${data.msg}`, 'st-info', user);
                    return;
                }

                if (data.status === 'pending') {
                    log(`✅ Đã tạo Task ID: ${data.task_id}`, 'st-ok', user);
                    trackTask(data.task_id, user); // Bắt đầu theo dõi
                } else {
                    log(`❌ Lỗi tạo: ${data.msg}`, 'st-err', user);
                }
            } catch (e) {
                log(`❌ Lỗi kết nối Server!`, 'st-err', user);
            }
        }

        // 5. Logic Theo dõi Task (Polling)
        async function trackTask(taskId, user) {
            let lastMsg = "";
            
            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/checkfl?task_id=${taskId}`);
                    const data = await res.json();

                    if (data.status === 'running') {
                        // Chỉ log khi tin nhắn thay đổi để đỡ spam
                        if (data.msg !== lastMsg) {
                            log(`🔄 ${data.msg}`, 'st-run', user);
                            lastMsg = data.msg;
                        }
                    } 
                    else if (data.status === 'success') {
                        clearInterval(interval);
                        log(`🎉 THÀNH CÔNG! ${data.msg}`, 'st-ok', user);
                        if(data.data) {
                            log(`Name: ${data.data.nickname} | +${data.data.increased} Follow`, 'st-ok', user);
                        }
                    } 
                    else if (data.status === 'error') {
                        clearInterval(interval);
                        log(`☠️ Thất bại: ${data.msg}`, 'st-err', user);
                    }
                    else if (data.status === 'not_found') {
                        clearInterval(interval);
                        log(`❓ Task không tồn tại (đã xóa)`, 'st-err', user);
                    }

                } catch (e) {
                    clearInterval(interval);
                }
            }, 2000); // Check mỗi 2s
        }
    </script>
</body>
</html>
"""

# ==========================================
# 1. HÀM CHECK FL MỚI (DÙNG API TIKWM)
# ==========================================
def get_live_follower_count(username):
    try:
        url = "https://www.tikwm.com/api/user/info"
        params = {"unique_id": username}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Gửi request như yêu cầu
        r = requests.get(url, params=params, headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 0 and "data" in data and "stats" in data["data"]:
                return int(data["data"]["stats"]["followerCount"])
        return None
    except Exception as e:
        print(f"Lỗi check fl tikwm: {e}")
        return None

# ==========================================
# 2. XỬ LÝ GIỚI HẠN & TIMEOUT
# ==========================================

# Hàm lấy giờ Việt Nam
def get_today_vn_str():
    # UTC+7
    vn_tz = timezone(timedelta(hours=7))
    return datetime.now(vn_tz).strftime("%Y-%m-%d")

def check_limits_and_cooldown(username, is_admin_key):
    """
    Check cooldown 15p VÀ limit 20 lần/ngày.
    Nếu is_admin_key = True -> Bỏ qua limit 20 lần, nhưng VẪN TÍNH timeout 15p.
    """
    current_time = time.time()
    today_str = get_today_vn_str()
    
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, 'w').close()

    with open(HISTORY_FILE, 'r') as f:
        lines = f.readlines()

    new_lines = []
    user_found = False
    
    can_proceed = True
    msg_error = ""
    wait_time = 0

    for line in lines:
        line = line.strip()
        if not line: continue
        
        parts = line.split('|')
        saved_user = parts[0]
        
        if saved_user == username:
            user_found = True
            saved_time = float(parts[1])
            saved_count = int(parts[2]) if len(parts) >= 4 else 0
            saved_date = parts[3] if len(parts) >= 4 else "2000-01-01"

            # 1. Reset ngày mới
            if saved_date != today_str:
                saved_count = 0
                saved_date = today_str

            # 2. Check Cooldown (Admin vẫn bị check cái này)
            time_diff = current_time - saved_time
            if time_diff < COOLDOWN_SECONDS:
                can_proceed = False
                wait_time = int(COOLDOWN_SECONDS - time_diff)
                msg_error = f"Vui lòng đợi {wait_time // 60}p {wait_time % 60}s (Timeout)."
                new_lines.append(line)
                continue

            # 3. Check Limit 20 lần/ngày (Chỉ check nếu KHÔNG phải admin)
            if not is_admin_key:
                if saved_count >= MAX_DAILY_REQUESTS:
                    can_proceed = False
                    msg_error = f"Đã hết lượt hôm nay ({MAX_DAILY_REQUESTS}/{MAX_DAILY_REQUESTS}). Reset lúc 0h."
                    new_lines.append(line)
                    continue

            # Nếu thỏa mãn: Update time và count
            new_lines.append(f"{username}|{current_time}|{saved_count + 1}|{today_str}")

        else:
            new_lines.append(line)

    if not user_found:
        new_lines.append(f"{username}|{current_time}|1|{today_str}")

    if can_proceed:
        with open(HISTORY_FILE, 'w') as f:
            f.write('\n'.join(new_lines))
        return True, 0, ""
    else:
        return False, wait_time, msg_error

def remove_cooldown_entry(username):
    # Xóa dòng user nếu buff lỗi để user làm lại
    if not os.path.exists(HISTORY_FILE): return
    with open(HISTORY_FILE, 'r') as f: lines = f.readlines()
    new_lines = [line.strip() for line in lines if not line.startswith(f"{username}|")]
    with open(HISTORY_FILE, 'w') as f: f.write('\n'.join(new_lines))

# ==========================================
# 3. WORKER BUFF
# ==========================================
def schedule_task_cleanup(task_id):
    def cleanup():
        time.sleep(DELETE_TASK_AFTER)
        if task_id in tasks_status:
            del tasks_status[task_id]
    t = threading.Thread(target=cleanup)
    t.daemon = True
    t.start()

def process_buff(task_id, username):
    tasks_status[task_id] = {"status": "running", "msg": "Đang khởi tạo..."}
    ss = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Origin": "https://tikfollowers.com",
        "Referer": "https://tikfollowers.com/"
    }

    try:
        tasks_status[task_id] = {"status": "running", "msg": "Đang tìm kiếm user..."}
        r1 = ss.post("https://tikfollowers.com/api/search", 
                     json={"input": username, "type": "getUserDetails"}, 
                     headers=headers, timeout=22)
        d1 = r1.json()

        if d1.get("status") != "success":
            tasks_status[task_id] = {"status": "error", "msg": "Không tìm thấy User."}
            schedule_task_cleanup(task_id)
            return
            
        # Lấy Follow từ TikWM
        live_start_fl = get_live_follower_count(username)
        if live_start_fl is not None:
            start_fl = live_start_fl
        else:
            start_fl = d1.get('followers_count', 0)
        nickname = d1.get('nickname')
        
    except (ReadTimeout, ConnectTimeout):
        remove_cooldown_entry(username)
        tasks_status[task_id] = {"status": "error", "msg": "Lỗi kết nối Search (Timeout)."}
        schedule_task_cleanup(task_id)
        return
    except Exception as e:
        tasks_status[task_id] = {"status": "error", "msg": f"Lỗi: {str(e)}"}
        schedule_task_cleanup(task_id)
        return

    tasks_status[task_id] = {"status": "running", "msg": f"Tìm thấy {nickname} ({start_fl} FL). Đang buff..."}
    payload = {
        "status": "success", "token": d1.get("token"), "user_id": d1.get("user_id"),
        "sec_uid": d1.get("sec_uid"), "username": d1.get("username"),
        "followers_count": start_fl, "nickname": nickname, "type": "followers", "success": True
    }
    
    waiting_mode = False
    time.sleep(2)
    
    try:
        r2 = ss.post("https://tikfollowers.com/api/process", json=payload, headers=headers, timeout=22)
    except (ReadTimeout, ConnectTimeout):
        waiting_mode = True
        tasks_status[task_id] = {"status": "running", "msg": "API chậm, đợi 1-2 phút check lại..."}
        time.sleep(90)
    except Exception as e:
        tasks_status[task_id] = {"status": "error", "msg": f"Lỗi gửi buff vui lòng đợi"}
        schedule_task_cleanup(task_id)
        return

    tasks_status[task_id]["msg"] = "Đang kiểm tra kết quả..."
    live_end_fl = get_live_follower_count(username)
    if live_end_fl is None: live_end_fl = start_fl

    diff = live_end_fl - start_fl
    if diff < 0: diff = 0
    msg_result = "API đã phản hồi sau khi chờ." if waiting_mode else "Buff thành công!"
    
    tasks_status[task_id] = {
        "status": "success", 
        "msg": f"{msg_result} Đã tăng: {diff} Follower.",
        "data": { "nickname": nickname, "before": start_fl, "after": live_end_fl, "increased": diff }
    }
    schedule_task_cleanup(task_id)

# ==========================================
# 4. API & WEB ROUTES
# ==========================================

@app.route('/url.html')
def page_ui():
    return HTML_PAGE

@app.route('/')
def home():
    return '<meta http-equiv="refresh" content="0; url=/url.html" />'

@app.route('/bufffl', methods=['GET'])
def api_buff():
    username = request.args.get('username')
    key = request.args.get('key')
    
    if not username: 
        return jsonify({"status": "error", "msg": "Thiếu username"}), 400

    # Kiểm tra key admin
    is_admin = False
    if key == ADMIN_KEY:
        is_admin = True

    is_allowed, wait_time, msg_err = check_limits_and_cooldown(username, is_admin)
    
    if not is_allowed:
        return jsonify({
            "status": "cooldown", 
            "msg": msg_err, 
            "remaining_seconds": wait_time
        })

    task_id = str(uuid.uuid4())
    threading.Thread(target=process_buff, args=(task_id, username)).start()

    return jsonify({"status": "pending", "msg": "Đang xử lý...", "task_id": task_id, "username": username})

@app.route('/checkfl', methods=['GET'])
def api_check():
    task_id = request.args.get('task_id')
    if not task_id: return jsonify({"status": "error", "msg": "Thiếu task_id"}), 400
    result = tasks_status.get(task_id)
    if result: return jsonify(result)
    else: return jsonify({"status": "not_found", "msg": "Task ID không tồn tại."}), 404

@app.route('/ping')
def ping_server():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
