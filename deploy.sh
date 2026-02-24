#!/bin/bash

set -e

# 1. 최신 코드 반영
echo "🚀 깃허브에서 최신 코드를 가져옵니다..."
git pull origin main

# 2. 공통 설정(Secret) 업데이트
echo "🔐 공통 환경 변수(.env)를 등록 중..."
sudo kubectl delete secret common-env --ignore-not-found
sudo kubectl create secret generic common-env --from-env-file=.env

# 3. 도커 이미지 빌드 (YAML의 image 이름과 태그 반영)
echo "📦 각 서비스의 이미지를 빌드합니다..."
sudo docker build -t docker.io/library/auth-app:v2 ./src/auth-app
sudo docker build -t docker.io/library/product-app:v1 ./src/product-app

# [핵심] 빌드된 이미지를 k3s 내부 저장소로 동기화
echo "🔄 이미지를 k3s로 동기화 중..."
sudo docker save docker.io/library/auth-app:v2 | sudo k3s ctr images import -
sudo docker save docker.io/library/product-app:v1 | sudo k3s ctr images import -

# 4. Kubernetes 리소스 적용
echo "☸️ Kubernetes 리소스를 배포합니다..."
sudo kubectl apply -f ./k3s-manifests/02-apps/deployment-a.yaml
sudo kubectl apply -f ./k3s-manifests/02-apps/deployment-b.yaml

# [핵심] 서비스 파일 적용 (이 부분이 빠져서 안 됐던 겁니다!)
sudo kubectl apply -f ./k3s-manifests/02-apps/service-a.yaml
sudo kubectl apply -f ./k3s-manifests/02-apps/service-b.yaml

# 5. Ingress 설정 적용
echo "🌐 Ingress 설정을 적용합니다..."
# 수정
sudo kubectl delete ingress --all
sudo kubectl apply -f ./k3s-manifests/03-network/ingress.yaml


# 1. MariaDB 배포 (경로 수정: 04-database -> 01-db)
echo "📦 MariaDB 인프라를 배포합니다..."
sudo kubectl apply -f ./k3s-manifests/01-db/mariadb-full-setup.yaml

# 2. DB가 준비될 때까지 대기
echo "⏳ DB가 활성화될 때까지 기다리는 중..."
sudo kubectl wait --for=condition=ready pod -l app=mariadb --timeout=60s

# 3. 테이블 자동 생성 (경로와 무관하게 실행됨)
echo "📋 테이블 구조를 점검합니다..."
# 파드 이름을 정확히 집어내기 위해 -n default(혹은 사용중인 네임스페이스)를 명시하면 더 좋습니다.
MARIADB_POD=$(sudo kubectl get pod -l app=mariadb -o jsonpath='{.items[0].metadata.name}')

sudo kubectl exec -i $MARIADB_POD -- mariadb -u root -p1234 -e "USE shop; CREATE TABLE IF NOT EXISTS products (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255) NOT NULL, category VARCHAR(100), price INT DEFAULT 0, description TEXT, stock INT DEFAULT 0, image_url VARCHAR(255), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"

# 5. Worker3 이미지 빌드 (경로: src/worker-notion)
echo "🏗️ Worker3 배달원 앱 빌드 중..."
sudo docker build -t worker3:latest ./src/worker-notion/

# 6. Worker3 배포
echo "🚀 Worker3 앱 배포 중..."
sudo kubectl apply -f ./k3s-manifests/01-db/worker3-deployment.yaml
sudo docker save worker3:latest | sudo k3s ctr images import -

# 🔄 빌드된 최신 이미지를 컨테이너에 강제 반영 (Rollout Restart)
echo "♻️ 모든 서비스를 최신 이미지로 재시작합니다..."

sudo kubectl rollout restart deployment/face-login-deployment
sudo kubectl rollout restart deployment/product-search-deployment
sudo kubectl rollout restart deployment/worker3-deployment

# 7. 확인
echo "✅ 배포 완료! 상태 확인:"
sudo kubectl get pods -l 'app in (mariadb, worker3)'



# 6. 배포 상태 확인
echo "⏳ 배포 완료! 파드 상태를 확인합니다..."
sleep 10
sudo kubectl get pods
sudo kubectl get svc
sudo kubectl get ingress

echo "✅ 모든 작업이 완료되었습니다!"