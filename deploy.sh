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

# 4. MariaDB 먼저 배포 (앱보다 DB가 먼저 떠야 함)
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

# 9. 배포 상태 확인
echo "⏳ 배포 완료! 파드 상태를 확인합니다..."
sleep 10
sudo kubectl get pods -o wide
sudo kubectl get svc
sudo kubectl get ingress

echo "✅ 모든 작업이 완료되었습니다! 파드들이 Running 상태인지 확인하세요."
