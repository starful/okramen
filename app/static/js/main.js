import { initGoogleMap, addMarkers, filterMapMarkers } from './map-core.js';
import { renderShrineList, updateFilterButtonCounts, initOmikuji } from './ui.js';

let allShrinesData = [];

// [수정 1] window.initMap 대신 일반 비동기 함수로 변경 이름은 runApp 등 자유롭게
async function runApp() {
    try {
        console.log("JinjaMap 시작..."); // 디버깅용 로그

        // 지도 초기화
        const googleMaps = await initGoogleMap();
        const { AdvancedMarkerElement } = await googleMaps.importLibrary("marker");

        // 데이터 가져오기
        const response = await fetch('/api/shrines');
        const jsonData = await response.json();
        
        let lastUpdatedText = '';
        if (jsonData.shrines) {
            allShrinesData = jsonData.shrines;
            lastUpdatedText = jsonData.last_updated || '';
        } else {
            allShrinesData = jsonData;
        }

        // 날짜 표시
        const dateEl = document.getElementById('last-updated');
        if (dateEl && lastUpdatedText) dateEl.textContent = `Last Updated: ${lastUpdatedText}`;

        // 마커 및 리스트 렌더링
        addMarkers(allShrinesData, AdvancedMarkerElement);
        renderShrineList(allShrinesData);
        updateFilterButtonCounts(allShrinesData);
        initOmikuji(filterMapMarkers);

        // 필터 버튼 이벤트 연결
        setupFilterButtons();

        // 로딩 메시지 숨김
        document.getElementById('update-msg')?.style.setProperty('display', 'none');

    } catch (error) {
        console.error("초기화 실패:", error);
    }
}

function setupFilterButtons() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterMapMarkers(btn.dataset.theme);
        });
    });
}

// [수정 2] 파일이 로드되면 즉시 실행
runApp();