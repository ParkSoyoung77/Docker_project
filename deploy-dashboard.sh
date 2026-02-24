#!/bin/bash
# 파일 위치: ~/Docker_project/deploy.sh

echo " Traefik 대시보드 자동 배포를 시작합니다..."

#  핵심 포인트: YAML 파일들이 있는 하위 폴더 경로를 변수로 지정합니다.
MANIFEST_DIR="./k3s-manifests/03-network"

# 1. 아파치 유틸리티 설치 (htpasswd 용도)
sudo apt-get update && sudo apt-get install -y apache2-utils

# 2. 루트 폴더에 있는 .env 파일 불러오기
if [ -f .env ]; then
  source .env
else
  echo " 현재 폴더에 .env 파일이 없습니다! 파일을 생성해주세요."
  exit 1
fi

# 3. 비밀번호 암호화 및 Secret 생성
sudo kubectl create secret generic traefik-dashboard-auth \
  --from-literal=users="$(htpasswd -nb $DASHBOARD_USER $DASHBOARD_PASS)" \
  -n kube-system \
  --dry-run=client -o yaml | sudo kubectl apply -f -

# 4. 하위 폴더의 YAML 파일들을 지정해서 실행
echo " $MANIFEST_DIR 폴더의 설정 파일들을 적용합니다..."
sudo kubectl apply -f $MANIFEST_DIR/traefik-config.yaml
sudo kubectl apply -f $MANIFEST_DIR/dashboard-setting.yaml

echo " 배포 완료! 어느 환경에서든 <IP 또는 도메인>/dashboard/ 로 접속하세요."
