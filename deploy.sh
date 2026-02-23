#!/bin/bash

# 리눅스 실행 시 발생할 수 있는 줄바꿈 에러 방지
set -e

# 1. 최신 코드 반영
echo "🚀 깃허브에서 최신 코드를 가져옵니다..."
git pull origin main

# 2. 공통 설정(Secret) 업데이트
echo "🔐 공통 환경 변수(.env)를 등록 중..."
sudo kubectl delete secret common-env --ignore-not-found
sudo kubectl create secret generic common-env --from-env-file=.env

# 3. 도커 이미지 빌드
# [수정] YAML에 적힌 이름과 태그(v2, v1)를 그대로 적용합니다.
echo "📦 각 서비스의 이미지를 빌드합니다..."
sudo docker build -t docker.io/library/auth-app:v2 ./src/auth-app
sudo docker build -t docker.io/library/product-app:v1 ./src/product-app

# [추가] 빌드된 이미지를 k3s 내부 저장소로 동기화
# [수정] YAML에 적힌 풀네임을 사용하여 k3s에 주입합니다.
echo "🔄 이미지를 k3s로 동기화 중..."
sudo docker save docker.io/library/auth-app:v2 | sudo k3s ctr images import -
sudo docker save docker.io/library/product-app:v1 | sudo k3s ctr images import -

# 4. Kubernetes 리소스 적용
echo "☸️ Kubernetes 리소스를 배포합니다..."
sudo kubectl apply -f ./k3s-manifests/02-apps/deployment-a.yaml
sudo kubectl apply -f ./k3s-manifests/02-apps/deployment-b.yaml

# 5. Ingress 설정 적용
echo "🌐 Ingress 설정을 적용합니다..."
sudo kubectl apply -f ./ingress.yaml

# 6. 배포 상태 확인
echo "⏳ 배포 완료! 파드 상태를 확인합니다..."
sleep 10
sudo kubectl get pods
sudo kubectl get ingress
sudo kubectl get endpoints

echo "✅ 모든 작업이 완료되었습니다. 이제 브라우저에서 VM IP로 접속해 보세요!"