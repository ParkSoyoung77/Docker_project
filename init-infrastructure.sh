#!/bin/bash
# init-infrastructure.sh

set -e

# --- [0. 설정부] ---
MASTER_IP=$(hostname -I | awk '{print $1}')
REGISTRY="$MASTER_IP:5000"
WORKER_USER="ubuntu"        # 워커 접속 계정
WORKER_NODES=("k3s-worker1" "k3s-worker2") # 추가할 노드들

echo "🚀 인프라 통합 설정을 시작합니다..."

# --- [1. 필수 도구 설치 (sshpass)] ---
if ! command -v sshpass &> /dev/null; then
    echo "📦 sshpass가 없어서 설치합니다..."
    sudo apt-get update && sudo apt-get install -y sshpass
fi

# --- [2. SSH 비밀번호 입력 받기] ---
# 보안을 위해 스크립트에 적지 않고 실행 시점에 입력받습니다.
echo -n "🔑 워커 노드($WORKER_USER)의 비밀번호를 입력하세요: "
read -s WORKER_PASS
echo ""

# --- [3. SSH 키 생성 및 배포] ---
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "🔑 마스터 노드 SSH 키 생성 중..."
    ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
fi

for node in "${WORKER_NODES[@]}"; do
    echo "🚚 $node 노드로 SSH 키 복사 중..."
    sshpass -p "$WORKER_PASS" ssh-copy-id -o StrictHostKeyChecking=no "$WORKER_USER@$node"
done

# --- [4. 마스터 노드 Docker insecure registry 설정] ---
echo "🐳 마스터 노드 Docker insecure registry 설정 중..."
cat <<EOF | sudo tee /etc/docker/daemon.json > /dev/null
{
  "insecure-registries": ["$REGISTRY"]
}
EOF
sudo systemctl restart docker
echo "✅ 마스터 Docker 설정 완료"

# --- [5. 마스터 레지스트리 컨테이너 실행] ---
if [ ! "$(sudo docker ps -q -f name=registry)" ]; then
    echo "📦 로컬 레지스트리 창고 생성 중..."
    if [ "$(sudo docker ps -aq -f name=registry)" ]; then sudo docker rm registry; fi
    sudo docker run -d -p 5000:5000 --restart=always --name registry registry:2
fi

# --- [6. 노드별 설정 (SSH 활용)] ---
setup_node() {
    local target=$1
    echo "⚙️  $target 노드 설정 및 k3s 재시작 중..."

    local registries_config="mirrors:
  \"$REGISTRY\":
    endpoint:
      - \"http://$REGISTRY\""

    local docker_config="{
  \"insecure-registries\": [\"$REGISTRY\"]
}"

    ssh -o StrictHostKeyChecking=no "$WORKER_USER@$target" "
        # k3s registries.yaml 설정
        sudo mkdir -p /etc/rancher/k3s
        echo '$registries_config' | sudo tee /etc/rancher/k3s/registries.yaml > /dev/null

        # Docker insecure registry 설정
        echo '$docker_config' | sudo tee /etc/docker/daemon.json > /dev/null
        sudo systemctl restart docker

        # k3s 재시작
        if systemctl is-active --quiet k3s; then
            sudo systemctl restart k3s
        else
            sudo systemctl restart k3s-agent
        fi
    "
    echo "✅ $target 설정 완료"
}

# 마스터(자신)와 모든 워커 노드 순회
setup_node "localhost"
for worker in "${WORKER_NODES[@]}"; do
    setup_node "$worker"
done

echo "✨ 모든 인프라 설정이 완료되었습니다!"
echo "✅ 이제 deploy.sh를 실행하여 앱을 배포하세요."