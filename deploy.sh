#!/bin/bash

set -e

# --- [설정부] ---
MASTER_IP=$(hostname -I | awk '{print $1}')
REGISTRY="$MASTER_IP:5000"

echo "🌐 레지스트리 주소: $REGISTRY"

# 1. 최신 코드 반영
echo "🚀 깃허브에서 최신 코드를 가져옵니다..."
git pull origin main

# 2. 공통 설정(Secret) 업데이트
echo "🔐 공통 환경 변수(.env)를 등록 중..."
sudo kubectl delete secret common-env --ignore-not-found
sudo kubectl create secret generic common-env --from-env-file=.env

# 3. 도커 이미지 빌드 및 레지스트리 푸시
echo "📦 각 서비스의 이미지를 빌드하고 레지스트리에 업로드합니다..."

build_and_push() {
    local name=$1
    local path=$2
    local tag=$3
    echo "🗑️  기존 $name 이미지 삭제 중..."
    sudo docker rmi $REGISTRY/$name:$tag 2>/dev/null || true
    echo "🔨 $name 빌드 중..."
    sudo docker build --no-cache -t $REGISTRY/$name:$tag $path
    sudo docker push $REGISTRY/$name:$tag
}

build_and_push "auth-app" "./src/auth-app" "v2"
build_and_push "product-app" "./src/product-app" "v1.1"
build_and_push "worker3" "./src/worker-notion" "latest"

# 4. MariaDB 먼저 배포
echo "📦 MariaDB 인프라를 배포합니다..."
sudo kubectl apply -f ./k3s-manifests/01-db/mariadb-full-setup.yaml
sudo kubectl apply -f ./k3s-manifests/02-apps/chromadb-setup.yaml

# 5. DB가 준비될 때까지 대기
echo "⏳ DB가 활성화될 때까지 기다리는 중..."
sudo kubectl wait --for=condition=ready pod -l app=mariadb --timeout=120s

# 6. Kubernetes 앱 리소스 적용
echo "☸️ Kubernetes 리소스를 배포합니다..."
sed "s|image: .*auth-app:v2|image: $REGISTRY/auth-app:v2|g" ./k3s-manifests/02-apps/deployment-a.yaml | sudo kubectl apply -f -
sed "s|image: .*product-app:v1.1|image: $REGISTRY/product-app:v1.1|g" ./k3s-manifests/02-apps/deployment-b.yaml | sudo kubectl apply -f -
sed "s|image: .*worker3:latest|image: $REGISTRY/worker3:latest|g" ./k3s-manifests/01-db/worker3-deployment.yaml | sudo kubectl apply -f -

# 서비스 적용
echo "🔌 서비스 및 인프라 설정 적용 중..."
sudo kubectl apply -f ./k3s-manifests/02-apps/service-a.yaml
sudo kubectl apply -f ./k3s-manifests/02-apps/service-b.yaml

# 7. Ingress 설정 적용
echo "🌐 Ingress 설정을 적용합니다..."
sudo kubectl delete ingress --all
sudo kubectl apply -f ./k3s-manifests/03-network/ingress.yaml

# 8. 최신 이미지 강제 반영
echo "♻️ 모든 서비스를 최신 이미지로 재시작합니다..."
sudo kubectl rollout restart deployment/face-login-deployment
sudo kubectl rollout restart deployment/product-search-deployment
sudo kubectl rollout restart deployment/worker3-deployment

# 8.5 대시보드 배포
echo "📊 대시보드를 배포합니다..."
bash ~/Docker_project/deploy-dashboard.sh

# 8.6 메트릭 서버 설치
echo "📈 메트릭 서버를 설치합니다..."
sudo kubectl apply -f ./k3s-manifests/04-monitoring/components.yaml
sudo kubectl get pods -n kube-system -l k8s-app=metrics-server

# 8.7 Helm 설치 확인 및 설치
if ! command -v helm &> /dev/null; then
    echo "🔧 Helm이 없습니다. 설치 중..."
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
else
    echo "✅ Helm 이미 설치됨: $(helm version --short)"
fi

# 8.8 Helm 저장소 추가 및 업데이트
echo "📦 Helm 저장소 추가 및 업데이트..."
sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm repo add grafana https://grafana.github.io/helm-charts 2>/dev/null || true
sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm repo update

# 8.9 Loki 설치
echo "📋 Loki 설치 중..."
sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade --install loki grafana/loki \
    --set loki.auth_enabled=false \
    --set deploymentMode=SingleBinary \
    --set loki.commonConfig.replication_factor=1 \
    --set loki.storage.type=filesystem \
    --set loki.useTestSchema=true \
    --set loki.resources.limits.memory=512Mi \
    --set loki.resources.requests.memory=256Mi \
    --set read.replicas=0 \
    --set write.replicas=0 \
    --set backend.replicas=0 \
    --set canary.enabled=false

# 8.10 Promtail 설치
echo "📋 Promtail 설치 중..."
sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade --install promtail grafana/promtail \
    --set "config.clients[0].url=http://loki-gateway/loki/api/v1/push"

# 8.11 k9s 설치
echo "🖥️ k9s 설치 중..."
if ! command -v k9s &> /dev/null; then
    wget -q https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz
    tar -xzf k9s_Linux_amd64.tar.gz
    sudo mv k9s /usr/local/bin/
    rm -f k9s_Linux_amd64.tar.gz
else
    echo "✅ k9s 이미 설치됨"
fi

# k3s kubeconfig 권한 설정 (k9s 접근용)
sudo chmod 644 /etc/rancher/k3s/k3s.yaml

# 8.12 Grafana 설치
echo "📊 Grafana 설치 중 (포트: 31081)..."
sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade --install my-grafana grafana/grafana \
    --set service.type=NodePort \
    --set service.nodePort=31081 \
    --set adminPassword=admin

# 8.13 Prometheus 설치
echo "🔥 Prometheus 설치 중..."
sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
    -n monitoring --create-namespace

# 8.14 Grafana 토큰 자동 발급 및 .env 업데이트
echo "🔑 Grafana 토큰 자동 발급 중..."
sudo kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana --timeout=180s 2>/dev/null || true
sleep 10

GRAFANA_URL="http://$MASTER_IP:31081"

echo "🔗 Loki 데이터소스 추가 중..."
GRAFANA_UID=$(curl -s -X POST "$GRAFANA_URL/api/datasources" \
    -H "Content-Type: application/json" \
    -u admin:admin \
    -d '{"name":"Loki","type":"loki","url":"http://loki-gateway:80","access":"proxy"}' | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('datasource',{}).get('uid','') or d.get('uid',''))" 2>/dev/null || echo "")

echo "🔑 API 토큰 발급 중..."
GRAFANA_TOKEN=$(curl -s -X POST "$GRAFANA_URL/api/auth/keys" \
    -H "Content-Type: application/json" \
    -u admin:admin \
    -d '{"name":"auto-token-'$(date +%s)'","role":"Admin"}' | \
    python3 -c "import sys,json; print(json.load(sys.stdin).get('key',''))" 2>/dev/null || echo "")

# .env 업데이트
sed -i '/^GRAFANA_URL/d' .env
sed -i '/^GRAFANA_TOKEN/d' .env
sed -i '/^GRAFANA_UID/d' .env
echo "GRAFANA_URL=$GRAFANA_URL" >> .env
echo "GRAFANA_TOKEN=$GRAFANA_TOKEN" >> .env
echo "GRAFANA_UID=$GRAFANA_UID" >> .env

echo "✅ Grafana 설정 완료!"
echo "   URL: $GRAFANA_URL"
echo "   UID: $GRAFANA_UID"

# 9. 배포 상태 확인
echo "⏳ 배포 완료! 파드 상태를 확인합니다..."
sleep 10
sudo kubectl get pods -A
sudo kubectl get svc
sudo kubectl get ingress

echo "✅ 모든 작업이 완료되었습니다! 파드들이 Running 상태인지 확인하세요."