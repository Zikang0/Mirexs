第三步拆解版（共 3 小步）
第 3.1 步：创建目录（防止报错）
复制下面这行，按 Enter 执行：
Bashsudo mkdir -p /etc/docker
第 3.2 步：创建并写入加速配置文件
直接复制下面整段（从 sudo bash -c 开始，一直到最后的 EOF），一次性粘贴执行：
Bashsudo bash -c 'cat > /etc/docker/daemon.json << EOF
{
  "registry-mirrors": [
    "https://docker.xuanyuan.me",
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run",
    "https://hub-mirror.c.163.com"
  ]
}
EOF'temp.sh: line 1: sudo: command not found

第 3.3 步：检查刚才创建的文件是否正确（可选，但建议执行）
复制这行执行：
Bashcat /etc/docker/daemon.json
执行完后，应该会显示类似下面这样的内容：
JSON{
  "registry-mirrors": [
    "https://docker.xuanyuan.me",
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run",
    "https://hub-mirror.c.163.com"
  ]
}

接下来继续执行后面的步骤
执行完上面 3 小步后，继续执行下面这两条：
第 4 步：重启 Docker 服务
Bashsudo systemctl restart docker
第 5 步：测试 Docker 加速是否生效（最重要！）





sudo apt update && sudo apt install ca-certificates curl -y
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
第2步：把你的用户加入 docker 组（以后不用每次加 sudo）
sudo usermod -aG docker $USER
第3步：重启 Docker 服务并测试
sudo systemctl enable --now docker
sudo systemctl status docker --no-pager
第4步：测试 Docker 是否能拉取镜像（关键！用中国加速）
先确认加速文件还在：
cat /etc/docker/daemon.json
然后重启 Docker 并测试：
sudo systemctl restart docker
sudo docker run --rm hello-world
sudo docker run --rm hello-world


