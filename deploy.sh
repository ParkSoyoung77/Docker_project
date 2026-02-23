#!/bin/bash

# 1. 최신 코드 반영
echo "🚀 깃허브에서 최신 코드를 가져옵니다..."
git pull origin main

# 2. 공통 설정(Secret) 업데이트
# 최상위 .env 파일을 Kubernetes Secret으로 등록하여 모든 파드가 공유하게 합니다.
echo "🔐 공통 환경 변수(.env)를 등록 중..."
sudo kubectl delete secret common-env --ignore-not-found
sudo kubectl create secret generic common-env --from-env-file=.env

# 3. 도커 이미지 빌드 (로컬 레지스트리 대신 k3s 내부 이미지 사용을 위해)
# ※ 주의: k3s 환경에 따라 sudo docker 또는 sudo crictl을 사용할 수 있습니다.
echo "📦 각 서비스의 이미지를 빌드합니다..."
sudo docker build -t auth-app:latest ./src/auth-app
sudo docker build -t product-app:latest ./src/product-app

# 4. Kubernetes 리소스 적용
echo "☸️ Kubernetes 리소스를 배포합니다 (Deployments, Services)..."
sudo kubectl apply -f auth-deployment.yaml
sudo kubectl apply -f product-deployment.yaml

# 5. Ingress 설정 적용 (포트 없이 경로로 접속 가능하게 함)
echo "🌐 Ingress 설정을 적용합니다..."
sudo kubectl apply -f ingress.yaml

# 6. 배포 상태 확인
echo "⏳ 배포 완료! 파드 상태를 확인합니다..."
sleep 5
sudo kubectl get pods
sudo kubectl get ingress

echo "✅ 모든 작업이 완료되었습니다. 이제 브라우저에서 VM IP로 접속해 보세요!"