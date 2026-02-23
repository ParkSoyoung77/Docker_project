function toggleDetail(id) {
    const row = document.getElementById('detail-' + id);
    const allPanels = document.querySelectorAll('.detail-panel');
    
    // 다른 패널 닫기 (현업용 인터페이스는 보통 하나만 열리게 함)
    allPanels.forEach(p => {
        if(p.id !== 'detail-' + id) p.style.display = 'none';
    });

    // 선택한 패널 토글
    if (row.style.display === 'none') {
        row.style.display = 'table-row';
    } else {
        row.style.display = 'none';
    }
}