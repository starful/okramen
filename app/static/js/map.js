/**
 * map.js - JinjaMap Main Logic (Bigger Markers Version)
 */

let map;
let allMarkers = [];
let infoWindow;
let allShrinesData = [];

// 카테고리(한글) <-> 테마(영문 코드) 매핑
const CATEGORY_THEME_MAP = {
    '재물': 'wealth', '금전운': 'wealth', '복권': 'wealth',
    '사랑': 'love', '연애': 'love', '인연': 'love', '결혼': 'love',
    '건강': 'health', '치유': 'health',
    '학업': 'study', '합격': 'study',
    '안전': 'safety', '교통안전': 'safety', '액막이': 'safety',
    '성공': 'success', '사업': 'success', '승진': 'success',
    '역사': 'history', '유래': 'history'
};

const THEME_COLORS = {
    'wealth': '#FBC02D', 'love': '#E91E63', 'health': '#2E7D32',
    'study': '#1565C0', 'safety': '#455A64', 'success': '#512DA8',
    'history': '#EF6C00', 'default': '#757575'
};

/**
 * 지도 초기화 (Google Maps API 콜백)
 */
async function initMap() {
    const tokyoCoords = { lat: 35.6895, lng: 139.6917 };

    // Google Maps 라이브러리 로드
    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    map = new Map(document.getElementById("map"), {
        zoom: 10,
        center: tokyoCoords,
        mapId: "2938bb3f7f034d78",
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        gestureHandling: 'greedy'
    });

    infoWindow = new google.maps.InfoWindow();
    addLocationButton();

    // API를 통해 데이터 가져오기
    try {
        const response = await fetch('/api/shrines');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const jsonData = await response.json();
        
        if (Array.isArray(jsonData)) {
            allShrinesData = jsonData;
        } else if (jsonData.shrines) {
            allShrinesData = jsonData.shrines;
        } else {
            allShrinesData = [];
        }

        console.log(`Loaded ${allShrinesData.length} shrines.`);

        // 마커 및 리스트 렌더링
        addMarkers(allShrinesData, AdvancedMarkerElement);
        renderRecentShrines(allShrinesData.slice(0, 8));
        
        updateFilterButtonCounts(allShrinesData);
        setupFilterButtons();
        
        // 초기 로딩 시 모든 마커가 보이도록 카메라 이동
        updateCameraBounds();

        // 로딩 메시지 숨김
        const msgEl = document.getElementById('update-msg');
        if(msgEl) msgEl.style.display = 'none';

    } catch (error) {
        console.error("데이터 로딩 실패:", error);
        const msgEl = document.getElementById('update-msg');
        if(msgEl) {
            msgEl.textContent = '데이터를 불러오는 데 실패했습니다.';
            msgEl.style.display = 'block';
        }
    }
}

/**
 * 마커 추가 함수
 */
function addMarkers(shrines, AdvancedMarkerElement) {
    allMarkers.forEach(m => m.map = null);
    allMarkers = [];

    shrines.forEach((shrine) => {
        if (!shrine.lat || !shrine.lng) return;

        const mainTheme = findMainTheme(shrine.categories);
        const borderColor = THEME_COLORS[mainTheme] || THEME_COLORS['default'];

        const markerContent = document.createElement("div");
        markerContent.className = 'marker-icon';
        markerContent.style.backgroundColor = borderColor;
        
        // [수정됨] 마커 크기 확대 (20px -> 32px)
        markerContent.style.width = '32px';
        markerContent.style.height = '32px';
        markerContent.style.borderRadius = '50%';
        markerContent.style.border = '3px solid white'; // 테두리도 조금 두껍게
        markerContent.style.boxShadow = '0 3px 6px rgba(0,0,0,0.4)'; // 그림자도 조금 더 진하게

        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: shrine.lat, lng: shrine.lng },
            title: shrine.title,
            content: markerContent,
        });

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
    const thumbUrl = shrine.thumbnail ? shrine.thumbnail : '/static/images/default_thumb.webp';
    const detailLink = shrine.link || '#';

    const contentString = `
        <div class="infowindow-content" style="max-width:220px;">
            <a href="${detailLink}" target="_blank">
                <img src="${thumbUrl}" alt="${shrine.title}" 
                     style="width:100%; height:120px; object-fit:cover; border-radius:8px; margin-bottom:8px; background:#eee;">
            </a>
            <h3 style="margin:0 0 5px 0; font-size:16px;">
                <a href="${detailLink}" target="_blank" style="text-decoration:none; color:#333;">${shrine.title}</a>
            </h3>
            <p style="margin:0 0 10px 0; font-size:12px; color:#666;">
                🏷️ ${shrine.categories ? shrine.categories.join(', ') : ''}
            </p>
            <div class="info-btn-group" style="display:flex; gap:5px;">
                <a href="${directionsUrl}" target="_blank" class="info-btn" 
                   style="flex:1; padding:6px; background:#4285F4; color:white; text-align:center; border-radius:4px; text-decoration:none; font-size:12px;">📍 길찾기</a>
                <a href="${detailLink}" class="info-btn" 
                   style="flex:1; padding:6px; background:#fff; border:1px solid #ddd; color:#333; text-align:center; border-radius:4px; text-decoration:none; font-size:12px;">📖 리뷰</a>
            </div>
        </div>
    `;
    infoWindow.setContent(contentString);
    infoWindow.open(map, marker);
}

/**
 * 리스트 렌더링
 */
function renderRecentShrines(shrines) {
    const listContainer = document.getElementById('shrine-list');
    if (!listContainer) return;
    
    listContainer.innerHTML = '';
    const fragment = document.createDocumentFragment();

    shrines.forEach(shrine => {
        const card = document.createElement('div');
        card.className = 'shrine-card';
        
        const thumbUrl = shrine.thumbnail ? shrine.thumbnail : '/static/images/default_thumb.webp';
        const categoryTag = shrine.categories?.[0] ? `<span>🏷️ ${shrine.categories[0]}</span>` : '';
        const detailLink = shrine.link || '#';
        
        card.innerHTML = `
            <a href="${detailLink}" class="card-thumb-link">
                <img src="${thumbUrl}" alt="${shrine.title}" class="card-thumb" loading="lazy">
            </a>
            <div class="card-content">
                <h3 class="card-title"><a href="${detailLink}">${shrine.title}</a></h3>
                <div class="card-meta">📅 ${shrine.published || ''} • ${categoryTag}</div>
                <p class="card-summary">${shrine.summary || ''}</p>
                <a href="${detailLink}" class="card-btn">더 보기 →</a>
            </div>
        `;
        fragment.appendChild(card);
    });

    listContainer.appendChild(fragment);
}

/**
 * 버튼 카운트 업데이트
 */
function updateFilterButtonCounts(shrines) {
    const counts = { all: shrines.length };
    
    Object.values(CATEGORY_THEME_MAP).forEach(theme => {
        if (!counts[theme]) counts[theme] = 0;
    });

    shrines.forEach(shrine => {
        const themes = new Set(getThemesFromCategories(shrine.categories));
        themes.forEach(theme => {
            if (counts.hasOwnProperty(theme)) counts[theme]++;
        });
    });

    document.querySelectorAll('.theme-button').forEach(btn => {
        const theme = btn.dataset.theme;
        if (theme && counts[theme] !== undefined) {
            const textOnly = btn.textContent.split('(')[0].trim();
            btn.textContent = `${textOnly} (${counts[theme]})`;
        }
    });
}

/**
 * 지도 마커 필터링 및 카메라 이동
 */
function filterMapMarkers(selectedTheme) {
    let hasVisibleMarkers = false;

    allMarkers.forEach(marker => {
        let isVisible = false;
        if (selectedTheme === 'all') {
            isVisible = true;
        } else if (marker.themes && marker.themes.includes(selectedTheme)) {
            isVisible = true;
        }
        marker.map = isVisible ? map : null;
        if (isVisible) hasVisibleMarkers = true;
    });

    // 필터링 후 카메라 재조정
    if (hasVisibleMarkers) {
        updateCameraBounds();
    }
}

/**
 * 현재 보이는 마커들에 맞춰 지도 범위 재조정
 */
function updateCameraBounds() {
    const bounds = new google.maps.LatLngBounds();
    let visibleCount = 0;

    allMarkers.forEach(marker => {
        if (marker.map !== null && marker.position) {
            bounds.extend(marker.position);
            visibleCount++;
        }
    });

    if (visibleCount > 0) {
        map.fitBounds(bounds);

        const listener = google.maps.event.addListener(map, "idle", () => {
            if (map.getZoom() > 15) {
                map.setZoom(15);
            }
            google.maps.event.removeListener(listener);
        });
    } else {
        map.setCenter({ lat: 35.6895, lng: 139.6917 });
        map.setZoom(10);
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

function getThemesFromCategories(categories = []) {
    if (!categories) return [];
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
    locationButton.textContent = "🎯 내 위치";
    locationButton.className = "location-button";
    locationButton.style.cssText = "background:white; border:2px solid #ccc; padding:8px; border-radius:4px; margin:10px; cursor:pointer; box-shadow:0 2px 6px rgba(0,0,0,0.3);";

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
        } else {
            alert("브라우저가 위치 정보를 지원하지 않습니다.");
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
        const box = document.getElementById('shaking-box');
        if(box) box.classList.remove('shake');
    };
    
    document.querySelector('.close-modal').onclick = () => modal.style.display = 'none';
    
    const drawBtn = document.getElementById('draw-btn');
    if(drawBtn) {
        drawBtn.onclick = () => {
            const box = document.getElementById('shaking-box');
            if(box) box.classList.add('shake');
            
            setTimeout(() => {
                if(box) box.classList.remove('shake');
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
                    
                    const mapEl = document.getElementById("map");
                    if(mapEl) mapEl.scrollIntoView({ behavior: "smooth", block: "center" });
                };
                
                document.getElementById('omikuji-step1').style.display = 'none';
                document.getElementById('omikuji-step2').style.display = 'block';
            }, 1000);
        };
    }
});