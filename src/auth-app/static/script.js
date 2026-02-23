const video = document.getElementById('video');
const statusMsg = document.getElementById('status'); // HTML의 id가 status라면 그대로 유지
const overlayCanvas = document.getElementById('overlayCanvas');
const ctx = overlayCanvas.getContext('2d');
const startBtn = document.getElementById('startBtn');
const entryBtn = document.getElementById('entryBtn');

// 서버 전송용 프레임을 뽑아낼 보이지 않는 캔버스
const tempCanvas = document.createElement('canvas');
let isAuthenticating = false; // 인증 진행 상태 플래그

/**
 * 1. 시스템 초기화 및 카메라 연결 (인증 시작 버튼 클릭 시)
 */
async function startSystem() {
    try {
        startBtn.style.display = 'none'; // 시작 버튼 숨기기
        statusMsg.innerText = "📷 카메라 연결 시도 중...";
        
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        video.srcObject = stream;

        video.onloadedmetadata = () => {
            video.play();
            // 화면 크기 동기화 (박스 밀림 방지)
            overlayCanvas.width = video.clientWidth;
            overlayCanvas.height = video.clientHeight;
            tempCanvas.width = video.videoWidth;
            tempCanvas.height = video.videoHeight;
            
            isAuthenticating = true; // 인증 시작
            statusMsg.innerText = "🔍 얼굴을 비춰주세요...";
            loop(); 
        };
    } catch (err) {
        statusMsg.innerText = "❌ 에러: 카메라 권한을 확인하세요.";
        startBtn.style.display = 'inline-block';
        console.error(err);
    }
}

/**
 * 2. 실시간 인증 루프 (성공 시 버튼만 표시)
 */
async function loop() {
    if (!isAuthenticating) return; 

    const tCtx = tempCanvas.getContext('2d');
    tCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
    const imageData = tempCanvas.toDataURL('image/jpeg', 0.7);

    try {
        const res = await fetch('/authenticate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });

        const data = await res.json();
        ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        if (data.status === "success") {
            // [수정] 즉시 이동하지 않고 상태만 업데이트
            isAuthenticating = false; 
            statusMsg.innerText = "✅ 인증 성공! 아래 버튼을 클릭하여 입장하세요.";
            
            // 1. [로그인] 혹은 [입장] 버튼을 화면에 표시
            if (entryBtn) {
                entryBtn.style.display = 'inline-block';
            }

            // 2. 얼굴 박스 고정
            drawOverlay(data);
            
            // 3. (옵션) 서버가 준 리다이렉트 경로를 전역 변수나 버튼에 저장해둘 수 있습니다.
            // 여기서는 단순화하여 goProduct 함수에서 처리합니다.
        } else {
            statusMsg.innerText = "🔍 인식 중: 얼굴을 맞춰주세요.";
            requestAnimationFrame(loop);
        }
    } catch (e) {
        console.error("통신 에러:", e);
        if (isAuthenticating) requestAnimationFrame(loop);
    }
}
/**
 * 3. 얼굴 좌표 보정 및 그리기
 */
function drawOverlay(data) {
    const scaleX = video.clientWidth / tempCanvas.width;
    const scaleY = video.clientHeight / tempCanvas.height;

    ctx.strokeStyle = "#00ff00";
    ctx.lineWidth = 3;
    ctx.strokeRect(
        data.bbox.x * scaleX, 
        data.bbox.y * scaleY, 
        data.bbox.w * scaleX, 
        data.bbox.h * scaleY
    );

    ctx.fillStyle = "#00ff00";
    data.points.forEach((p, i) => {
        if (i % 25 === 0) { // 성능을 위해 점 일부만 표시
            ctx.beginPath();
            ctx.arc(p.x * scaleX, p.y * scaleY, 2, 0, 2 * Math.PI);
            ctx.fill();
        }
    });
}

/**
 * 4. [로그인/상품 페이지 입장] 버튼 클릭 시 실행
 */
function goProduct() {
    // [미션 반영] 클릭 시점에 포트를 떼고 Ingress(80) 주소로 이동
    const host = window.location.hostname;
    const redirectPath = "/"; // Ingress에서 설정한 경로
    
    statusMsg.innerText = "🚀 페이지 이동 중...";
    window.location.href = `http://${host}${redirectPath}`;
}

// 브라우저 창 크기 변경 시 캔버스 크기 재조정
window.onresize = () => {
    overlayCanvas.width = video.clientWidth;
    overlayCanvas.height = video.clientHeight;
};