rm -f blocker.py
cat > blocker.py << 'EOF'
from flask import Flask, render_template_string, request, jsonify
import paramiko
import time

app = Flask(__name__)

# ==================== 配置区 ====================
HILLSTONE_IP = "192.168.73.128"
USERNAME = "blockuser"
PASSWORD = "Blockuser@123"          # ←←← 改成你实际设置的密码！
# ===============================================

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>山石防火墙自动封禁工具</title>
    <style>
        body {font-family: Microsoft YaHei,sans-serif; background:#f0f2f5; padding:20px;}
        .container {max-width:800px; margin:auto; background:white; padding:30px; border-radius:12px; box-shadow:0 0 20px rgba(0,0,0,0.1);}
        h1 {text-align:center; color:#1e3a8a;}
        input, button {padding:12px; margin:8px 0; font-size:16px; width:100%; box-sizing:border-box;}
        button {background:#dc3545; color:white; border:none; cursor:pointer; border-radius:6px;}
        button.green {background:#28a745;}
        .result {margin-top:20px; padding:15px; font-size:18px; text-align:center; border-radius:6px; font-weight:bold;}
        .success {background:#d4edda; color:#155724;}
        .error {background:#f8d7da; color:#721c24;}
    </style>
</head>
<body>
<div class="container">
    <h1>🛡️ 山石防火墙自动封禁工具</h1>
    <p style="text-align:center;color:#666;">连接防火墙：{{ hillstone_ip }}</p>
    
    <label>IP地址</label>
    <input type="text" id="ip" placeholder="1.2.3.4">

    <label>子网掩码 / CIDR（单IP请填 32）</label>
    <input type="text" id="mask" value="32">

    <button onclick="blockIP()">封禁</button>
    <button onclick="unblockIP()" class="green">解封</button>
    <button onclick="batchBlock()" style="margin-top:15px;">批量封禁（每行一个IP）</button>

    <div id="result" class="result" style="display:none;"></div>
</div>

<script>
function show(msg, success) {
    let div = document.getElementById('result');
    div.innerHTML = msg;
    div.style.display = 'block';
    div.className = 'result ' + (success ? 'success' : 'error');
    setTimeout(()=>{div.style.display='none';}, 6000);
}

function blockIP() {
    let ip = document.getElementById('ip').value.trim();
    let mask = document.getElementById('mask').value.trim();
    if (!ip) return alert("请输入IP地址");
    fetch('/block', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ip, mask})})
    .then(r=>r.json()).then(d => show(d.message, d.success));
}
function unblockIP() {
    let ip = document.getElementById('ip').value.trim();
    if (!ip) return alert("请输入IP地址");
    fetch('/unblock', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ip})})
    .then(r=>r.json()).then(d => show(d.message, d.success));
}
function batchBlock() {
    let text = prompt("请输入IP，每行一个：");
    if (!text) return;
    fetch('/batch_block', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ips:text})})
    .then(r=>r.json()).then(d => show(d.message, d.success));
}
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML, hillstone_ip=HILLSTONE_IP)

def ssh_exec(cmd):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HILLSTONE_IP, username=USERNAME, password=PASSWORD, timeout=8)
        _, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode() + stderr.read().decode()
        ssh.close()
        return True, out.strip()
    except Exception as e:
        return False, str(e)

@app.route('/block', methods=['POST'])
def block():
    d = request.json
    ip = d['ip']
    mask = d.get('mask', '32')
    cidr = f"{ip}/{mask}" if mask != "32" else ip
    success, msg = ssh_exec(f"blacklist ip add {cidr}")
    return jsonify({"success": success, "message": f"<span style='color:red'>IP封禁成功：</span> {cidr}" if success else f"封禁失败：{msg}"})

@app.route('/unblock', methods=['POST'])
def unblock():
    d = request.json
    ip = d['ip']
    success, msg = ssh_exec(f"blacklist ip delete {ip}")
    return jsonify({"success": success, "message": f"<span style='color:green'>IP解封成功：</span> {ip}" if success else f"解封失败：{msg}"})

@app.route('/batch_block', methods=['POST'])
def batch_block():
    d = request.json
    ips = [x.strip() for x in d['ips'].splitlines() if x.strip()]
    results = []
    for ip in ips:
        success, _ = ssh_exec(f"blacklist ip add {ip}")
        results.append(f"{ip} → {'成功' if success else '失败'}")
    return jsonify({"success": True, "message": "<br>".join(results)})

if __name__ == '__main__':
    print("🚀 自动封禁工具已启动！")
    print("请在浏览器打开： http://192.168.73.132:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
EOF
