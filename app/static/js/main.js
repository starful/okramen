// main.js - JinjaMap Core Logic

let shrinesData = [];
let map;
let markers = [];
let currentInfoWindow = null;
let isMapLoaded = false;

document.addEventListener('DOMContentLoaded', () => {
    fetchShrines();
    initThemeFilters();
    initOmikuji();
    
    // [수정] 페이지 로드 시 initMap을 직접 호출합니다.
    // (index.html에 Bootstrap Loader가 적용되어 있어야 작동합니다)
    initMap(); 
});

// [1] Fetch Data
async function fetchShrines() {
    try {
        const response = await fetch('/api/shrines');
        const data = await response.json();
        
        // 최신순 정렬
        shrinesData = data.shrines.sort((a, b) => 
            new Date(b.published) - new Date(a.published)
        );

        // 상단 정보 업데이트
        if (data.last_updated) {
            const dateEl = document.getElementById('last-updated-date');
            if(dateEl) dateEl.textContent = data.last_updated;
        }
        if (data.shrines) {
            const totalEl = document.getElementById('total-shrines');
            if(totalEl) totalEl.textContent = data.shrines.length;
        }

        updateCategoryCounts();
        renderCards(shrinesData);

        // 지도 로드 후 데이터가 오면 마커 표시 및 뷰 조정
        if (isMapLoaded) {
            updateMapMarkers(shrinesData);
        }

    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// [2] Google Maps Initialization
// [수정] window 객체 할당 제거, 일반 비동기 함수로 변경
async function initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;

    try {
        // [중요] Bootstrap Loader 덕분에 importLibrary를 즉시 사용할 수 있습니다.
        const { Map } = await google.maps.importLibrary("maps");
        const center = { lat: 36.2048, lng: 138.2529 }; // 일본 중심부

        map = new Map(mapEl, {
            zoom: 5,
            center: center,
            // [중요] 사용자가 생성한 실제 Map ID 적용 (AdvancedMarkerElement 사용 필수)
            mapId: "2938bb3f7f034d78a2dbaf56", 
            disableDefaultUI: false,
            zoomControl: true,
            streetViewControl: false,
            mapTypeControl: false,
        });

        isMapLoaded = true;
        console.log("✅ Map initialized successfully!");

        // 데이터가 이미 로드되었다면 마커 업데이트
        if (shrinesData.length > 0) {
            updateMapMarkers(shrinesData);
        }

    } catch (error) {
        console.error("❌ Map Init Error:", error);
    }
}

// [3] Update Markers (Modern Version with AdvancedMarkerElement)
async function updateMapMarkers(data) {
    if (!map) return;

    // 기존 마커 삭제
    markers.forEach(m => m.map = null);
    markers = [];
    
    if (data.length === 0) {
        return;
    }

    const bounds = new google.maps.LatLngBounds();

    try {
        // [중요] AdvancedMarkerElement 라이브러리 로드
        const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
        const { InfoWindow } = await google.maps.importLibrary("maps");

        data.forEach(shrine => {
            const position = { lat: parseFloat(shrine.lat), lng: parseFloat(shrine.lng) };

            // 커스텀 마커 아이콘 생성 (CSS 스타일 적용됨)
            const markerIcon = document.createElement('div');
            markerIcon.className = 'marker-icon';
            
            // 썸네일 이미지가 있으면 배경으로 설정
            if (shrine.thumbnail) {
                markerIcon.style.backgroundImage = `url(${shrine.thumbnail})`;
                markerIcon.style.backgroundSize = 'cover';
            }

            // 고급 마커 생성
            const marker = new AdvancedMarkerElement({
                map: map,
                position: position,
                title: shrine.title,
                content: markerIcon, // 커스텀 HTML 요소 사용
            });

            marker.addListener('click', () => {
                if (currentInfoWindow) currentInfoWindow.close();

                const onsenTag = shrine.has_onsen 
                    ? '<span class="info-onsen-tag">♨️ Onsen Nearby</span>' 
                    : '';

                const infoContent = `
                    <div class="infowindow-content">
                        <div style="position:relative;">
                            <img src="${shrine.thumbnail}" alt="${shrine.title}" loading="lazy">
                            ${onsenTag}
                        </div>
                        <h3>${shrine.title}</h3>
                        <p>📍 ${shrine.address}</p>
                        <div class="info-btn-group">
                            <a href="${shrine.link}" class="info-btn blog-btn">View Guide</a>
                            <a href="https://www.google.com/maps/dir/?api=1&destination=${shrine.lat},${shrine.lng}" target="_blank" class="info-btn dir-btn">Directions</a>
                        </div>
                    </div>
                `;
                
                const infoWindow = new InfoWindow({ content: infoContent, maxWidth: 250 });
                infoWindow.open(map, marker);
                currentInfoWindow = infoWindow;
            });
            markers.push(marker);

            // 생성된 마커 위치를 경계에 포함
            bounds.extend(position);
        });

        // 모든 마커가 보이도록 뷰 자동 조절
        map.fitBounds(bounds);

    } catch (e) {
        console.error("Marker Error:", e);
    }
}

// [4] Category Counts
function updateCategoryCounts() {
    const counts = { all: shrinesData.length, wealth: 0, love: 0, health: 0, safety: 0, success: 0, history: 0 };
    
    shrinesData.forEach(shrine => {
        if(shrine.categories) {
            shrine.categories.forEach(cat => {
                const key = cat.toLowerCase().trim();
                if (counts.hasOwnProperty(key)) {
                    counts[key]++;
                }
            });
        }
    });

    for (const [key, value] of Object.entries(counts)) {
        const badge = document.getElementById(`count-${key}`);
        if (badge) badge.textContent = value;
    }
}

// [5] Render Cards
function renderCards(data) {
    const listContainer = document.getElementById('shrine-list');
    if(!listContainer) return;

    listContainer.innerHTML = '';
    
    if (data.length === 0) {
        listContainer.innerHTML = '<p style="text-align:center; width:100%; color:#666; margin-top:30px;">No shrines found matching your criteria.</p>';
        return;
    }

    data.forEach(shrine => {
        const pubDate = new Date(shrine.published);
        const now = new Date();
        const diffDays = Math.ceil((now - pubDate) / (1000 * 60 * 60 * 24));
        const isNew = diffDays <= 14; 

        const onsenBadge = shrine.has_onsen 
            ? '<span class="onsen-badge">♨️ Onsen</span>' 
            : '';

        const card = document.createElement('div');
        card.className = 'shrine-card';
        card.innerHTML = `
            <a href="${shrine.link}" class="card-thumb-link">
                ${isNew ? '<span class="new-badge">NEW</span>' : ''}
                ${onsenBadge}
                <img src="${shrine.thumbnail}" alt="${shrine.title}" class="card-thumb" loading="lazy">
            </a>
            <div class="card-content">
                <div class="card-meta">
                    <span>${shrine.categories.join(', ')}</span> • <span>${shrine.published.replace(/-/g, '.')}</span>
                </div>
                <h3 class="card-title"><a href="${shrine.link}">${shrine.title}</a></h3>
                <p class="card-summary">${shrine.summary}</p>
                <div class="card-footer">
                    <a href="${shrine.link}" class="card-btn">Read More &rarr;</a>
                </div>
            </div>`;
        listContainer.appendChild(card);
    });
}

// [6] Filter Logic
function initThemeFilters() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterByTheme(btn.dataset.theme);
        });
    });
}

function filterByTheme(theme) {
    let filtered = shrinesData;

    if (theme !== 'all') {
        filtered = filtered.filter(item => 
            item.categories.some(cat => cat.toLowerCase().trim() === theme.toLowerCase())
        );
    }
    
    renderCards(filtered);
    updateMapMarkers(filtered);
}

// [7] Omikuji (Fortune) Logic
function initOmikuji() {
    const btn = document.getElementById('omikuji-btn');
    const modal = document.getElementById('omikuji-modal');
    const close = document.querySelector('.close-modal');
    const drawBtn = document.getElementById('draw-btn');
    const step1 = document.getElementById('omikuji-step1');
    const step2 = document.getElementById('omikuji-step2');
    
    if(!btn || !modal || !close || !drawBtn || !step1 || !step2) return;

    btn.addEventListener('click', () => { 
        modal.style.display = 'flex'; 
        step1.style.display = 'block'; 
        step2.style.display = 'none'; 
    });

    close.addEventListener('click', () => { modal.style.display = 'none'; });
    window.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });

    drawBtn.addEventListener('click', () => {
        const box = document.getElementById('shaking-box');
        box.style.animation = 'shake 0.5s infinite';
        
        setTimeout(() => { 
            box.style.animation = 'none'; 
            showResult(); 
        }, 1500);
    });

    function showResult() {
        if (shrinesData.length === 0) return;

        const randomShrine = shrinesData[Math.floor(Math.random() * shrinesData.length)];
        const fortuneTypes = ['Great Blessing (Dai-kichi)', 'Blessing (Kichi)', 'Middle Blessing (Chu-kichi)', 'Small Blessing (Sho-kichi)'];
        const randomFortune = fortuneTypes[Math.floor(Math.random() * fortuneTypes.length)];

        step1.style.display = 'none'; 
        step2.style.display = 'block';
        
        document.getElementById('result-title').innerText = randomFortune;
        document.getElementById('result-desc').innerText = `Your lucky spot is:\n${randomShrine.title}`;
        
        const goBtn = document.getElementById('go-map-btn');
        goBtn.innerText = `Explore ${randomShrine.categories[0] || 'Shrine'}`;
        goBtn.onclick = () => { window.location.href = randomShrine.link; };

        if (typeof confetti === 'function') {
            confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
        }
    }
}

const style = document.createElement('style');
style.innerHTML = `@keyframes shake { 0% { transform: translate(1px, 1px) rotate(0deg); } 10% { transform: translate(-1px, -2px) rotate(-1deg); } 20% { transform: translate(-3px, 0px) rotate(1deg); } 30% { transform: translate(3px, 2px) rotate(0deg); } 40% { transform: translate(1px, -1px) rotate(1deg); } 50% { transform: translate(-1px, 2px) rotate(-1deg); } 60% { transform: translate(-3px, 1px) rotate(0deg); } 70% { transform: translate(3px, 1px) rotate(-1deg); } 80% { transform: translate(-1px, -1px) rotate(1deg); } 90% { transform: translate(1px, 2px) rotate(0deg); } 100% { transform: translate(1px, -2px) rotate(-1deg); } }`;
document.head.appendChild(style);