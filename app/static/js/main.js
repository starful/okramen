/**
 * OKRamen Main Engine
 * - Map ID: 2938bb3f7f034d7849f653d1
 * - Advanced Markers: Ramen Photos as Markers
 * - Interaction: Click Marker -> Show InfoWindow -> Go to Detail Page
 * - Filtering: Bilingual Theme & Language Logic
 */

let map;
let markers = [];
let allRamens = [];
let currentLang = 'en';
let currentTheme = 'all';
let infoWindow; // 전역 정보창 (한 번에 하나만 띄우기 위함)

// [매핑] 영문 필터명과 한국어 카테고리명 연결
const categoryMap = {
    'tonkotsu': '돈코츠',
    'shoyu': '쇼유',
    'miso': '미소',
    'shio': '시오',
    'chicken': '치킨라멘',
    'tsukemen': '츠케멘',
    'vegan': '비건'
};

/**
 * 1. 초기 데이터 로드 및 앱 시작
 */
async function initApp() {
    try {
        const response = await fetch('/api/ramens');
        const data = await response.json();
        allRamens = data.ramens || [];
        
        // 푸터 업데이트 정보
        const updatedDate = document.getElementById('last-updated-date');
        if (updatedDate) updatedDate.textContent = data.last_updated;
        
        // 구글 지도 및 UI 초기화
        await initMap();
        updateUI();
    } catch (error) {
        console.error("OKRamen loading failed:", error);
    }
}

/**
 * 2. 구글 지도 초기화 (Advanced Markers 필수 설정)
 */
async function initMap() {
    const { Map } = await google.maps.importLibrary("maps");
    
    map = new Map(document.getElementById("map"), {
        center: { lat: 36.2, lng: 138.2 },
        zoom: 6,
        mapId: "2938bb3f7f034d7849f653d1", // 사용자 전용 Map ID
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
    });

    // 정보창 객체 생성
    infoWindow = new google.maps.InfoWindow();
}

/**
 * 3. 화면 업데이트 통합 함수
 */
async function updateUI() {
    const filtered = getFilteredData();
    
    renderList(filtered);      // 리스트 렌더링
    await renderMarkers(filtered);   // 지도 마커 렌더링
    updateCounts();            // 카테고리 개수 업데이트
}

/**
 * 4. 현재 설정(언어, 테마)에 따른 데이터 필터링
 */
function getFilteredData() {
    return allRamens.filter(item => {
        // 언어 일치 여부
        const langMatch = item.lang === currentLang;
        
        // 테마 일치 여부 (Bilingual 지원)
        let themeMatch = true;
        if (currentTheme !== 'all') {
            const korTarget = categoryMap[currentTheme];
            themeMatch = item.categories.some(cat => 
                cat.toLowerCase() === currentTheme || cat === korTarget
            );
        }
        
        return langMatch && themeMatch;
    });
}

/**
 * 5. 하단 라멘 리스트 렌더링
 */
function renderList(data) {
    const listDiv = document.getElementById('ramen-list');
    listDiv.innerHTML = '';

    if (data.length === 0) {
        listDiv.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 100px 0; color: #999;">
                <p style="font-size: 1.2rem;">🍜 No ramen shops found.</p>
            </div>`;
        return;
    }

    data.forEach(item => {
        const card = document.createElement('div');
        card.className = 'onsen-card';
        card.innerHTML = `
            <a href="${item.link}">
                <img src="${item.thumbnail}" class="card-thumb" alt="${item.title}" loading="lazy">
            </a>
            <div class="card-content">
                <h3 class="card-title"><a href="${item.link}">${item.title}</a></h3>
                <p class="card-summary">${item.summary}</p>
                <div class="card-meta">
                    <span>📍 ${item.address}</span>
                    <span>📅 ${item.published}</span>
                </div>
            </div>
        `;
        listDiv.appendChild(card);
    });
}

/**
 * 6. 지도 위 커스텀 사진 마커 렌더링 및 클릭 이벤트
 */
async function renderMarkers(data) {
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    // 기존 마커 메모리 해제 및 삭제
    markers.forEach(m => m.map = null);
    markers = [];

    const bounds = new google.maps.LatLngBounds();

    data.forEach(item => {
        if (!item.lat || !item.lng) return;

        // 마커용 커스텀 HTML 엘리먼트 (라면 사진 원형)
        const markerTag = document.createElement('div');
        markerTag.className = 'ramen-marker';
        markerTag.innerHTML = `<img src="${item.thumbnail}" alt="${item.title}">`;

        // 고급 마커 생성
        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: parseFloat(item.lat), lng: parseFloat(item.lng) },
            title: item.title,
            content: markerTag,
        });

        // [이벤트] 마커 클릭 시 정보창 띄우기
        marker.addListener('click', () => {
            const btnText = currentLang === 'ko' ? '상세 정보 보기' : 'View Details →';
            
            const infoContent = `
                <div class="info-box-content">
                    <div class="info-box-title">${item.title}</div>
                    <div class="info-box-address">📍 ${item.address}</div>
                    <a href="${item.link}" class="info-box-link">${btnText}</a>
                </div>
            `;
            
            infoWindow.setContent(infoContent);
            infoWindow.open({
                anchor: marker,
                map,
            });
        });

        markers.push(marker);
        bounds.extend(marker.position);
    });

    // 지도 뷰포트 자동 조정
    if (data.length > 0 && map) {
        if (data.length === 1) {
            map.setCenter(markers[0].position);
            map.setZoom(14);
        } else {
            map.fitBounds(bounds, { padding: 80 });
        }
    }
}

/**
 * 7. 카테고리 버튼 배지(숫자) 업데이트
 */
function updateCounts() {
    const langData = allRamens.filter(r => r.lang === currentLang);
    const totalSpan = document.getElementById('total-ramens');
    const allSpan = document.getElementById('count-all');
    
    if (totalSpan) totalSpan.textContent = langData.length;
    if (allSpan) allSpan.textContent = langData.length;

    Object.keys(categoryMap).forEach(key => {
        const kor = categoryMap[key];
        const count = langData.filter(r => 
            r.categories.some(c => c.toLowerCase() === key || c === kor)
        ).length;
        
        const badge = document.getElementById(`count-${key}`);
        if (badge) badge.textContent = count;
    });
}

/**
 * 8. UI 이벤트 리스너 등록
 */

// 언어 전환 버튼
document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentLang = btn.dataset.lang;
        
        // 정보창이 열려있다면 닫기
        if (infoWindow) infoWindow.close();
        
        updateUI();
    });
});

// 테마 필터 버튼
document.querySelectorAll('.theme-button').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.theme-button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTheme = btn.dataset.theme;
        
        // 정보창이 열려있다면 닫기
        if (infoWindow) infoWindow.close();
        
        updateUI();
        
        // 모바일 스크롤 이동 (지도를 가리지 않게 리스트로 이동)
        if (window.innerWidth < 768) {
            const listSection = document.getElementById('list-section');
            if (listSection) listSection.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// 앱 실행
initApp();