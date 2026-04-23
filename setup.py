cat > /home/lee/blocker.py << 'EOF'
from flask import Flask, render_template_string, request, jsonify
import paramiko
import time
import threading

app = Flask(__name__)

# ==================== 配置区 ====================
HILLSTONE_IP = "192.168.73.128"
USERNAME = "blockuser"
PASSWORD = "Blockuser@123"          # ←←← 请改成你实际设置的密码
BLOCK_GROUP = "UTM-Auto-Block"      # 如果你没有创建这个组，可以改成 None
# ===============================================

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>UTMStack + 山石防火墙 自动封禁工具</title>
    <style>
        body { font-family: Microsoft YaHei, sans-serif; background: #f4f4f4; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 15px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        input, button { padding: 12px; margin: 8px 0; font-size: 16px; }
        input { width: 100%; box-sizing: border-box; }
        button { width: 48%; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 5px; }
        button.red { background: #dc3545; }
        button.green { background: #28a745; }
        .result { margin-top: 20px; padding: 15px; font-size: 18px; text-align: center; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
<div class="container">
    <h1>山石防火墙 自动封禁工具</h1>
    <p style="text-align:center;color:#666;">当前连接防火墙：{{ hillstone_ip }}</p>
    
    <label>IP地址</label>
    <input type="text" id="ip" placeholder="例如：1.2.3.4" value="">

    <label>子网掩码 / CIDR（可选，留空表示单IP）</label>
    <input type="text" id="mask" placeholder="例如：32 或 255.255.255.0" value="32">

    <button onclick="blockIP()">封禁</button>
    <button onclick="unblockIP()" class="green">解封</button>
    <button onclick="batchBlock()" style="width:100%;margin-top:10px;">批量封禁（每行一个IP）</button>

    <div id="result" class="result" style="display:none;"></div>
</div>

<script>
function showResult(msg, isSuccess) {
    let div = document.getElementById('result');
    div.innerHTML = msg;
    div.style.display = 'block';
    div.className = 'result ' + (isSuccess ? 'success' : 'error');
    setTimeout(() => { div.style.display = 'none'; }, 5000);
}

function blockIP() {
    let ip = document.getElementById('ip').value.trim();
    let mask = document.getElementById('mask').value.trim() || "32";
    if (!ip) return alert("请输入IP地址");
    fetch('/block', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ip: ip, mask: mask})
    }).then(r => r.json()).then(data => {
        showResult(data.message, data.success);
    });
}

function unblockIP() {
    let ip = document.getElementById('ip').value.trim();
    if (!ip) return alert("请输入IP地址");
    fetch('/unblock', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ip: ip})
    }).then(r => r.json()).then(data => {
        showResult(data.message, data.success);
    });
}

function batchBlock() {
    let text = prompt("请输入需要批量封禁的IP，每行一个：");
    if (!text) return;
    fetch('/batch_block', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ips: text})
    }).then(r => r.json()).then(data => {
        showResult(data.message, data.success);
    });
}
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML, hillstone_ip=HILLSTONE_IP)

def ssh_exec(command):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HILLSTONE_IP, username=USERNAME, password=PASSWORD, timeout=10)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode() + stderr.read().decode()
        ssh.close()
        return True, output.strip()
    except Exception as e:
        return False, str(e)

@app.route('/block', methods=['POST'])
def block():
    data = request.json
    ip = data['ip']
    mask = data.get('mask', '32')
    cidr = f"{ip}/{mask}" if mask != "32" else ip
    
    cmd = f"blacklist ip add {cidr}"
    success, msg = ssh_exec(cmd)
    
    if success:
        return jsonify({"success": True, "message": f"<b style='color:red'>IP封禁成功：</b> {cidr}"})
    else:
        return jsonify({"success": False, "message": f"封禁失败：{msg}"})

@app.route('/unblock', methods=['POST'])
def unblock():
    data = request.json
    ip = data['ip']
    cmd = f"blacklist ip delete {ip}"
    success, msg = ssh_exec(cmd)
    if success:
        return jsonify({"success": True, "message": f"<b style='color:green'>IP解封成功：</b> {ip}"})
    else:
        return jsonify({"success": False, "message": f"解封失败：{msg}"})

@app.route('/batch_block', methods=['POST'])
def batch_block():
    data = request.json
    ips = data['ips'].strip().splitlines()
    results = []
    for ip in ips:
        ip = ip.strip()
        if ip:
            cmd = f"blacklist ip add {ip}"
            success, _ = ssh_exec(cmd)
            results.append(f"{ip} → {'成功' if success else '失败'}")
    return jsonify({"success": True, "message": "<br>".join(results)})

if __name__ == '__main__':
    print("🚀 自动封禁 Web 工具已启动")
    print("请用浏览器打开：http://192.168.73.132:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
EOF
