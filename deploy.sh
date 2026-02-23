#!/bin/bash

# [수정] 리눅스 실행 시 발생할 수 있는 CRLF(줄바꿈) 에러 방지용 설정
set -e

# 1. 최신 코드 반영
echo "🚀 깃허브에서 최신 코드를 가져옵니다..."
git pull origin main

# 2. 공통 설정(Secret) 업데이트
echo "🔐 공통 환경 변수(.env)를 등록 중..."
sudo kubectl delete secret common-env --ignore-not-found
sudo kubectl create secret generic common-env --from-env-file=.env

# 3. 도커 이미지 빌드
# k3s에서 로컬 이미지를 인식하게 하려면 빌드 후 이미지를 가져오는 과정이 필요할 수 있습니다.
echo "📦 각 서비스의 이미지를 빌드합니다..."
sudo docker build -t auth-app:latest ./src/auth-app
sudo docker build -t product-app:latest ./src/product-app

# 4. Kubernetes 리소스 적용 (정확한 상대 경로 반영)
echo "☸️ Kubernetes 리소스를 배포합니다 (Deployments, Services)..."
# [수정] 말씀하신 02-apps 폴더 경로를 정확히 지정했습니다.
sudo kubectl apply -f ./k3s-manifests/02-apps/deployment-a.yaml
sudo kubectl apply -f ./k3s-manifests/02-apps/deployment-b.yaml

# 5. Ingress 설정 적용 (루트 폴더)
echo "🌐 Ingress 설정을 적용합니다..."
sudo kubectl apply -f ./ingress.yaml

# 6. 배포 상태 확인
echo "⏳ 배포 완료! 파드 상태를 확인합니다..."
sleep 10 # 파드가 생성될 시간을 조금 더 확보합니다.
sudo kubectl get pods
sudo kubectl get ingress
sudo kubectl get endpoints # [추가] 서비스 연결 상태 확인용

echo "✅ 모든 작업이 완료되었습니다. 이제 브라우저에서 VM IP로 접속해 보세요!"