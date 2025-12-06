// 전역 변수 선언
let map;
let allMarkers = [];
let infoWindow;
let allShrinesData = [];

// 카테고리 테마 매핑
const CATEGORY_THEME_MAP = {
    '재물': 'wealth',
    '사랑': 'love', '연애': 'love',
    '건강': 'health',
    '학업': 'study',
    '안전': 'safety',
    '성공': 'success',
    '역사': 'history',
};

const THEME_COLORS = {
    'wealth': '#FBC02D', 'love': '#E91E63', 'health': '#2E7D32',
    'study': '#1565C0', 'safety': '#455A64', 'success': '#512DA8',
    'history': '#EF6C00', 'default': '#757575'
};

/**
 * 지도 초기화
 */
async function initMap() {
    const tokyoCoords = { lat: 35.6895, lng: 139.6917 };

    // Google Maps 라이브러리 비동기 로드
    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    map = new Map(document.getElementById("map"), {
        zoom: 11,
        center: tokyoCoords,
        mapId: "2938bb3f7f034d78",
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        gestureHandling: 'greedy'
    });

    infoWindow = new google.maps.InfoWindow();
    addLocationButton();

    try {
        const response = await fetch('/api/shrines');
        const jsonData = await response.json();
        
        // 데이터 호환성 체크 (배열 or 객체)
        if (Array.isArray(jsonData)) {
            allShrinesData = jsonData;
        } else {
            allShrinesData = jsonData.shrines || [];
            if (jsonData.last_updated) {
                document.getElementById('update-msg').textContent = `데이터 업데이트: ${jsonData.last_updated}`;
            }
        }

        // 마커 및 리스트 렌더링
        addMarkers(allShrinesData, AdvancedMarkerElement);
        renderRecentShrines(allShrinesData.slice(0, 4)); // 최신 8개 렌더링
        updateFilterButtonCounts(allShrinesData);
        setupFilterButtons();

    } catch (error) {
        console.error("데이터 로딩 실패:", error);
        document.getElementById('update-msg').textContent = '데이터를 불러오는 데 실패했습니다.';
    }
}

/**
 * 마커 추가 함수
 */
function addMarkers(shrines, AdvancedMarkerElement) {
    // 기존 마커 제거
    allMarkers.forEach(m => m.map = null);
    allMarkers = [];

    shrines.forEach((shrine) => {
        if (!shrine.lat || !shrine.lng) return;

        const mainTheme = findMainTheme(shrine.categories);
        const borderColor = THEME_COLORS[mainTheme] || THEME_COLORS['default'];

        // 커스텀 마커 DOM 요소 생성
        const markerContent = document.createElement("div");
        markerContent.className = 'marker-icon';
        markerContent.style.borderColor = borderColor;

        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: shrine.lat, lng: shrine.lng },
            title: shrine.title,
            content: markerContent,
        });

        // 테마 정보 저장
        marker.themes = getThemesFromCategories(shrine.categories);

        marker.addListener("click", () => showInfoWindow(marker, shrine));
        allMarkers.push(marker);
    });
}

/**
 * 인포윈도우 표시
 */
function showInfoWindow(marker, shrine) {
    const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${shrine.lat},${shrine.lng}&travelmode=walking`;
    
    // [최적화] loading="lazy" 및 width/height 스타일 적용으로 레이아웃 시프트 방지
    const contentString = `
        <div class="infowindow-content">
            <img src="${shrine.thumbnail}" alt="${shrine.title}" loading="lazy" style="background:#eee; min-height:140px;">
            <h3>${shrine.title}</h3>
            <p>🏷️ ${shrine.categories ? shrine.categories.join(', ') : ''}</p>
            <div class="info-btn-group">
                <a href="${directionsUrl}" target="_blank" class="info-btn dir-btn">📍 길찾기</a>
                <a href="${shrine.link}" target="_blank" class="info-btn blog-btn">블로그</a>
            </div>
        </div>
    `;
    infoWindow.setContent(contentString);
    infoWindow.open(map, marker);
}

/**
 * [최적화] 리스트 렌더링 (DocumentFragment + Lazy Loading)
 */
function renderRecentShrines(shrines) {
    const listContainer = document.getElementById('shrine-list');
    if (!listContainer) return;
    
    listContainer.innerHTML = ''; // 초기화

    // [최적화] 가상 DOM 조각을 사용하여 리플로우(Reflow) 방지
    const fragment = document.createDocumentFragment();

    shrines.forEach(shrine => {
        const card = document.createElement('div');
        card.className = 'shrine-card';
        
        const categoryTag = shrine.categories?.[0] ? `• <span>🏷️ ${shrine.categories[0]}</span>` : '';
        
        // [최적화] loading="lazy" 추가
        card.innerHTML = `
            <a href="${shrine.link}" target="_blank" class="card-thumb-link">
                <img src="${shrine.thumbnail}" alt="${shrine.title}" class="card-thumb" loading="lazy">
            </a>
            <div class="card-content">
                <h3 class="card-title"><a href="${shrine.link}" target="_blank">${shrine.title}</a></h3>
                <div class="card-meta"><span>📅 ${shrine.published}</span>${categoryTag}</div>
                <p class="card-summary">${shrine.summary}</p>
                <a href="${shrine.link}" target="_blank" class="card-btn">더 보기 →</a>
            </div>
        `;
        fragment.appendChild(card);
    });

    listContainer.appendChild(fragment);
}

// 유틸리티 및 이벤트 리스너 함수들 (기존 로직 유지)

function updateFilterButtonCounts(shrines) {
    const counts = { all: shrines.length };
    Object.values(CATEGORY_THEME_MAP).forEach(theme => counts[theme] = 0);

    shrines.forEach(shrine => {
        const themes = getThemesFromCategories(shrine.categories);
        new Set(themes).forEach(theme => {
            if (counts.hasOwnProperty(theme)) counts[theme]++;
        });
    });

    document.querySelectorAll('.theme-button').forEach(btn => {
        const theme = btn.dataset.theme;
        const originalText = btn.textContent.split('(')[0].trim();
        btn.textContent = `${originalText} (${counts[theme] || 0})`;
    });
}

function filterMapMarkers(selectedTheme) {
    allMarkers.forEach(marker => {
        const isVisible = (selectedTheme === 'all' || marker.themes.includes(selectedTheme));
        marker.map = isVisible ? map : null;
    });
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

function getThemesFromCategories(categories = []) {
    return categories.map(cat => CATEGORY_THEME_MAP[cat]).filter(Boolean);
}

function findMainTheme(categories = []) {
    for (const cat of categories) {
        const theme = CATEGORY_THEME_MAP[cat];
        if (theme) return theme;
    }
    return 'default';
}

function addLocationButton() {
    const locationButton = document.createElement("button");
    locationButton.innerHTML = "🎯 내 위치";
    locationButton.className = "location-button";
    map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(locationButton);

    locationButton.addEventListener("click", () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const pos = { lat: position.coords.latitude, lng: position.coords.longitude };
                    map.setCenter(pos);
                    map.setZoom(14);
                },
                () => alert("위치 정보를 가져올 수 없습니다.")
            );
        }
    });
}

// 오미쿠지 로직
const omikujiResults = [
    { title: "대길 (大吉)", desc: "금전운이 폭발하는 날!💰", theme: "wealth", btnText: "💰 재물운 신사 지도 보기", color: "#FBC02D" },
    { title: "중길 (中吉)", desc: "좋은 인연이 다가옵니다.💘", theme: "love", btnText: "💘 연애운 신사 지도 보기", color: "#E91E63" },
    { title: "소길 (小吉)", desc: "건강이 최고입니다.🌿", theme: "health", btnText: "🌿 건강기원 신사 지도 보기", color: "#2E7D32" },
    { title: "길 (吉)", desc: "노력한 만큼 성과가 나옵니다.📚", theme: "study", btnText: "🎓 학업/성공 신사 지도 보기", color: "#1565C0" },
    { title: "흉 (凶)", desc: "조심해야 할 시기입니다.🛡️", theme: "safety", btnText: "🛡️ 액막이 신사 지도 보기", color: "#455A64" }
];

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('omikuji-modal');
    if (!modal) return;
    
    document.getElementById('omikuji-btn').onclick = () => {
        modal.style.display = 'flex';
        document.getElementById('omikuji-step1').style.display = 'block';
        document.getElementById('omikuji-step2').style.display = 'none';
        document.getElementById('shaking-box').classList.remove('shake');
    };
    
    document.querySelector('.close-modal').onclick = () => modal.style.display = 'none';
    
    document.getElementById('draw-btn').onclick = () => {
        const box = document.getElementById('shaking-box');
        box.classList.add('shake');
        
        setTimeout(() => {
            box.classList.remove('shake');
            if (typeof confetti === 'function') confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 } });

            const res = omikujiResults[Math.floor(Math.random() * omikujiResults.length)];
            
            document.getElementById('result-title').innerText = res.title;
            document.getElementById('result-title').style.color = res.color;
            document.getElementById('result-desc').innerHTML = res.desc;
            
            const btn = document.getElementById('go-map-btn');
            btn.innerText = res.btnText;
            btn.style.backgroundColor = res.color;
            
            btn.onclick = () => {
                document.querySelectorAll('.theme-button').forEach(b => {
                    b.classList.remove('active');
                    if(b.dataset.theme === res.theme) b.classList.add('active');
                });
                filterMapMarkers(res.theme);
                modal.style.display = 'none';
                document.getElementById("map").scrollIntoView({ behavior: "smooth", block: "center" });
            };
            
            document.getElementById('omikuji-step1').style.display = 'none';
            document.getElementById('omikuji-step2').style.display = 'block';
        }, 1000);
    };
});