/**
 * JinjaMap - Global Multi-language Core Logic (EN, KO, JA)
 */

let shrinesData = []; // 전체 원본 데이터
let map;
let markers = [];
let currentInfoWindow = null;
let isMapLoaded = false;

// 상태 관리
let currentLang = localStorage.getItem('preferredLang') || 'en'; // 저장된 언어 불러오기
let currentTheme = 'all';

// [1] 다국어 UI 번역 사전
const i18n = {
    en: {
        viewGuide: "View Guide",
        directions: "Directions",
        readMore: "Read More →",
        onsen: "♨️ Onsen Nearby",
        noResult: "No shrines found matching your criteria.",
        luckySpot: "Your lucky spot is:",
        explore: "Explore",
        shrine: "Shrine",
        new: "NEW",
        onsen_short: "Onsen"
    },
    ko: {
        viewGuide: "상세보기",
        directions: "길찾기",
        readMore: "자세히 보기 →",
        onsen: "♨️ 근처 온천 있음",
        noResult: "해당 조건에 맞는 장소가 없습니다.",
        luckySpot: "당신의 행운의 장소는:",
        explore: "둘러보기",
        shrine: "신사",
        new: "신규",
        onsen_short: "온천"
    },
    ja: {
        viewGuide: "詳細を見る",
        directions: "経路案内",
        readMore: "詳しく見る →",
        onsen: "♨️ 近くに温泉あり",
        noResult: "該当する場所がありません。",
        luckySpot: "あなたのラッキースポットは:",
        explore: "探索する",
        shrine: "神社",
        new: "新着",
        onsen_short: "温泉"
    }
};

// [2] 카테고리 매핑 테이블 (다국어 -> 내부 키값)
function getCategoryKey(cat) {
    if (!cat) return 'all';
    const map = {
        "Wealth": "wealth", "재물": "wealth", "金運": "wealth", "商売繁盛": "wealth",
        "Love": "love", "사랑": "love", "연애": "love", "縁結び": "love", "良縁": "love",
        "Health": "health", "건강": "health", "健康": "health", "病気平癒": "health",
        "Safety": "safety", "안전": "safety", "安全": "safety", "交通安全": "safety", "家内安全": "safety",
        "Success": "success", "성공": "success", "학업": "success", "合格": "success", "必勝": "success", "勝利": "success",
        "History": "history", "역사": "history", "歴史": "history", "文化": "history"
    };
    return map[cat] || cat.toLowerCase().trim();
}

// [3] 앱 초기화
document.addEventListener('DOMContentLoaded', () => {
    injectShakeStyle(); // 애니메이션 삽입
    fetchShrines();
    initThemeFilters();
    initLangFilters();
    initOmikuji();
    initMap(); 
});

// [4] 데이터 가져오기
async function fetchShrines() {
    try {
        const response = await fetch('/api/shrines');
        const data = await response.json();
        
        // 최신순 정렬
        shrinesData = data.shrines.sort((a, b) => 
            new Date(b.published) - new Date(a.published)
        );

        if (data.last_updated) {
            const dateEl = document.getElementById('last-updated-date');
            if(dateEl) dateEl.textContent = data.last_updated;
        }

        updateUI(); // 초기 렌더링

    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// [5] 언어 필터 초기화
function initLangFilters() {
    const langBtns = document.querySelectorAll('.lang-btn');
    langBtns.forEach(btn => {
        // 초기 로드 시 활성화 스타일 적용
        if (btn.dataset.lang === currentLang) btn.classList.add('active');

        btn.addEventListener('click', () => {
            langBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentLang = btn.dataset.lang;
            localStorage.setItem('preferredLang', currentLang); // 설정 저장
            updateUI();
        });
    });
}

// [6] 테마 필터 초기화
function initThemeFilters() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTheme = btn.dataset.theme;
            updateUI();
        });
    });
}

// [7] 통합 UI 업데이트 (언어 + 테마 동시 적용)
function updateUI() {
    // 필터링 로직
    const filtered = shrinesData.filter(item => {
        const isCorrectLang = item.lang === currentLang;
        const isCorrectTheme = currentTheme === 'all' || 
            item.categories.some(cat => getCategoryKey(cat) === currentTheme);
        return isCorrectLang && isCorrectTheme;
    });

    updateCategoryCounts(); 
    renderCards(filtered);
    if (isMapLoaded) {
        updateMapMarkers(filtered);
    }

    const totalEl = document.getElementById('total-shrines');
    if(totalEl) totalEl.textContent = filtered.length;
}

// [8] 구글 맵 초기화
async function initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;

    try {
        const { Map } = await google.maps.importLibrary("maps");
        const center = { lat: 36.2048, lng: 138.2529 };

        map = new Map(mapEl, {
            zoom: 5,
            center: center,
            mapId: "2938bb3f7f034d78a2dbaf56", // 기존 Map ID
            disableDefaultUI: false,
            zoomControl: true,
            streetViewControl: false,
            mapTypeControl: false,
        });

        isMapLoaded = true;
        updateUI();

    } catch (error) {
        console.error("❌ Map Init Error:", error);
    }
}

// [9] 마커 업데이트 (Advanced Markers)
async function updateMapMarkers(data) {
    if (!map) return;
    markers.forEach(m => m.map = null);
    markers = [];
    if (data.length === 0) return;

    const bounds = new google.maps.LatLngBounds();

    try {
        const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
        const { InfoWindow } = await google.maps.importLibrary("maps");
        const t = i18n[currentLang];

        data.forEach(shrine => {
            const position = { lat: parseFloat(shrine.lat), lng: parseFloat(shrine.lng) };
            const markerIcon = document.createElement('div');
            markerIcon.className = 'marker-icon';
            if (shrine.thumbnail) {
                markerIcon.style.backgroundImage = `url(${shrine.thumbnail})`;
                markerIcon.style.backgroundSize = 'cover';
            }

            const marker = new AdvancedMarkerElement({
                map: map,
                position: position,
                title: shrine.title,
                content: markerIcon,
            });

            marker.addListener('click', () => {
                if (currentInfoWindow) currentInfoWindow.close();
                const onsenTag = shrine.has_onsen ? `<span class="info-onsen-tag">${t.onsen}</span>` : '';

                const infoContent = `
                    <div class="infowindow-content">
                        <div style="position:relative;">
                            <img src="${shrine.thumbnail}" alt="${shrine.title}" loading="lazy">
                            ${onsenTag}
                        </div>
                        <h3>${shrine.title}</h3>
                        <p>📍 ${shrine.address}</p>
                        <div class="info-btn-group">
                            <a href="${shrine.link}" class="info-btn blog-btn">${t.viewGuide}</a>
                            <a href="https://www.google.com/maps/dir/?api=1&destination=${shrine.lat},${shrine.lng}" target="_blank" class="info-btn dir-btn">${t.directions}</a>
                        </div>
                    </div>`;
                
                const infoWindow = new InfoWindow({ content: infoContent, maxWidth: 250 });
                infoWindow.open(map, marker);
                currentInfoWindow = infoWindow;
            });
            markers.push(marker);
            bounds.extend(position);
        });
        map.fitBounds(bounds);
    } catch (e) { console.error("Marker Error:", e); }
}

// [10] 카운트 배지 업데이트 (현재 언어 기준)
function updateCategoryCounts() {
    const counts = { all: 0, wealth: 0, love: 0, health: 0, safety: 0, success: 0, history: 0 };
    const currentLangData = shrinesData.filter(s => s.lang === currentLang);
    counts.all = currentLangData.length;

    currentLangData.forEach(shrine => {
        if(shrine.categories) {
            shrine.categories.forEach(cat => {
                const key = getCategoryKey(cat);
                if (counts.hasOwnProperty(key)) counts[key]++;
            });
        }
    });

    for (const [key, value] of Object.entries(counts)) {
        const badge = document.getElementById(`count-${key}`);
        if (badge) badge.textContent = value;
    }
}

// [11] 리스트 카드 렌더링
function renderCards(data) {
    const listContainer = document.getElementById('shrine-list');
    if(!listContainer) return;
    listContainer.innerHTML = '';
    const t = i18n[currentLang];
    
    if (data.length === 0) {
        listContainer.innerHTML = `<p style="text-align:center; width:100%; color:#666; margin-top:30px;">${t.noResult}</p>`;
        return;
    }

    data.forEach(shrine => {
        const pubDate = new Date(shrine.published);
        const isNew = (new Date() - pubDate) / (1000 * 60 * 60 * 24) <= 14; 

        const card = document.createElement('div');
        card.className = 'shrine-card';
        card.innerHTML = `
            <a href="${shrine.link}" class="card-thumb-link">
                ${isNew ? `<span class="new-badge">${t.new}</span>` : ''}
                ${shrine.has_onsen ? `<span class="onsen-badge">♨️ ${t.onsen_short}</span>` : ''}
                <img src="${shrine.thumbnail}" alt="${shrine.title}" class="card-thumb" loading="lazy">
            </a>
            <div class="card-content">
                <div class="card-meta">
                    <span>${shrine.categories.join(', ')}</span> • <span>${shrine.published.replace(/-/g, '.')}</span>
                </div>
                <h3 class="card-title"><a href="${shrine.link}">${shrine.title}</a></h3>
                <p class="card-summary">${shrine.summary}</p>
                <div class="card-footer">
                    <a href="${shrine.link}" class="card-btn">${t.readMore}</a>
                </div>
            </div>`;
        listContainer.appendChild(card);
    });
}

// [12] 오미쿠지 로직
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

    drawBtn.addEventListener('click', () => {
        const box = document.getElementById('shaking-box');
        box.style.animation = 'shake 0.5s infinite';
        setTimeout(() => { 
            box.style.animation = 'none'; 
            showResult(); 
        }, 1500);
    });

    function showResult() {
        const langFiltered = shrinesData.filter(s => s.lang === currentLang);
        if (langFiltered.length === 0) return;

        const randomShrine = langFiltered[Math.floor(Math.random() * langFiltered.length)];
        const t = i18n[currentLang];

        const fortunes = {
            en: ['Great Blessing', 'Blessing', 'Small Blessing'],
            ko: ['대길 (大吉)', '길 (吉)', '소길 (小吉)'],
            ja: ['大吉', '吉', '小吉']
        };
        const currentFortunes = fortunes[currentLang] || fortunes.en;
        const randomFortune = currentFortunes[Math.floor(Math.random() * currentFortunes.length)];

        step1.style.display = 'none'; 
        step2.style.display = 'block';
        
        document.getElementById('result-title').innerText = randomFortune;
        document.getElementById('result-desc').innerText = `${t.luckySpot}\n${randomShrine.title}`;
        
        const goBtn = document.getElementById('go-map-btn');
        goBtn.innerText = `${randomShrine.categories[0] || t.shrine} ${t.explore}`;
        goBtn.onclick = () => { window.location.href = randomShrine.link; };

        if (typeof confetti === 'function') {
            confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
        }
    }
}

// [13] 애니메이션 주입
function injectShakeStyle() {
    const style = document.createElement('style');
    style.innerHTML = `@keyframes shake { 0% { transform: translate(1px, 1px) rotate(0deg); } 10% { transform: translate(-1px, -2px) rotate(-1deg); } 20% { transform: translate(-3px, 0px) rotate(1deg); } 30% { transform: translate(3px, 2px) rotate(0deg); } 40% { transform: translate(1px, -1px) rotate(1deg); } 50% { transform: translate(-1px, 2px) rotate(-1deg); } 60% { transform: translate(-3px, 1px) rotate(0deg); } 70% { transform: translate(3px, 1px) rotate(-1deg); } 80% { transform: translate(-1px, -1px) rotate(1deg); } 90% { transform: translate(1px, 2px) rotate(0deg); } 100% { transform: translate(1px, -2px) rotate(-1deg); } }`;
    document.head.appendChild(style);
}

const style = document.createElement('style');
style.innerHTML = `@keyframes shake { 0% { transform: translate(1px, 1px) rotate(0deg); } 10% { transform: translate(-1px, -2px) rotate(-1deg); } 20% { transform: translate(-3px, 0px) rotate(1deg); } 30% { transform: translate(3px, 2px) rotate(0deg); } 40% { transform: translate(1px, -1px) rotate(1deg); } 50% { transform: translate(-1px, 2px) rotate(-1deg); } 60% { transform: translate(-3px, 1px) rotate(0deg); } 70% { transform: translate(3px, 1px) rotate(-1deg); } 80% { transform: translate(-1px, -1px) rotate(1deg); } 90% { transform: translate(1px, 2px) rotate(0deg); } 100% { transform: translate(1px, -2px) rotate(-1deg); } }`;
document.head.appendChild(style);