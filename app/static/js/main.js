/**
 * OKRamen - Frontend Engine (Integrated Version)
 * 필터링 + 다국어 + 마커 팝업(섬네일) 기능 통합
 */

let map;
let markers = [];
let allRamens = [];
let currentLang = 'en';
let currentTheme = 'all';
let infoWindow; // 팝업창 객체

// 언어별 카테고리 매핑 (한국어 클릭 시에도 영어 데이터와 매칭되도록 함)
const CATEGORY_MAP = {
    'tonkotsu': { en: 'Tonkotsu', ko: '돈코츠' },
    'shoyu':    { en: 'Shoyu',    ko: '쇼유' },
    'miso':     { en: 'Miso',     ko: '미소' },
    'shio':     { en: 'Shio',     ko: '시오' },
    'chicken':  { en: 'Chicken',  ko: '치킨라멘' },
    'tsukemen': { en: 'Tsukemen', ko: '츠케멘' },
    'vegan':    { en: 'Vegan',    ko: '비건' }
};

async function initMap() {
    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

    // 팝업창(InfoWindow) 초기화
    infoWindow = new google.maps.InfoWindow();

    const mapOptions = {
        center: { lat: 36.5, lng: 138.5 }, // 일본 중앙
        zoom: 6,
        mapId: "OK_RAMEN_MAP_ID", // Google Cloud에서 생성한 Map ID 필요
        disableDefaultUI: false,
    };

    map = new Map(document.getElementById("map"), mapOptions);

    // 서버에서 데이터 가져오기
    try {
        const response = await fetch('/api/ramens');
        const data = await response.json();
        allRamens = data.ramens || [];
        
        // 하단 상태바 업데이트
        document.getElementById('last-updated-date').textContent = data.last_updated;
        updateBadges();
        
        // 첫 화면 렌더링
        render();
    } catch (error) {
        console.error("Data fetch failed:", error);
    }
}

function render() {
    // 언어 및 카테고리에 따른 데이터 필터링
    const filtered = allRamens.filter(item => {
        const langMatch = item.lang === currentLang;
        let themeMatch = true;

        if (currentTheme !== 'all') {
            const targetKeyword = CATEGORY_MAP[currentTheme][currentLang];
            themeMatch = item.categories.includes(targetKeyword);
        }
        return langMatch && themeMatch;
    });

    updateMarkers(filtered);
    updateList(filtered);
    updateActiveButtons();
}

/**
 * 지도 마커 업데이트 (섬네일 팝업 포함)
 */
async function updateMarkers(data) {
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

    // 기존 마커 제거
    markers.forEach(m => m.map = null);
    markers = [];

    const bounds = new google.maps.LatLngBounds();

    data.forEach(item => {
        if (!item.lat || !item.lng) return;

        const pin = new PinElement({
            background: "#e74c3c",
            borderColor: "#c0392b",
            glyphColor: "white",
            scale: 0.8
        });

        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: parseFloat(item.lat), lng: parseFloat(item.lng) },
            title: item.title,
            content: pin.element,
        });

        // 마커 클릭 이벤트: 섬네일 팝업 띄우기
        marker.addListener("click", () => {
            const contentString = `
                <div class="info-window-content">
                    <img src="${item.thumbnail}" alt="${item.title}" style="width:100%; height:120px; object-fit:cover; border-radius:8px;">
                    <div style="padding:10px 0 5px 0;">
                        <h4 style="margin:0 0 5px 0; font-size:14px;">${item.title}</h4>
                        <p style="margin:0 0 10px 0; font-size:12px; color:#666;">${item.address}</p>
                        <a href="${item.link}" style="display:block; text-align:center; background:#e74c3c; color:white; padding:8px; border-radius:5px; text-decoration:none; font-size:12px; font-weight:bold;">View Details →</a>
                    </div>
                </div>
            `;
            infoWindow.setContent(contentString);
            infoWindow.open(map, marker);
        });

        markers.push(marker);
        bounds.extend(marker.position);
    });

    // 마커가 있을 때만 지도 범위 조정
    if (data.length > 0) {
        if (data.length === 1) {
            map.setCenter(markers[0].position);
            map.setZoom(13);
        } else {
            map.fitBounds(bounds);
        }
    }
}

/**
 * 하단 리스트 카드 업데이트
 */
function updateList(data) {
    const listContainer = document.getElementById('ramen-list');
    listContainer.innerHTML = '';

    if (data.length === 0) {
        listContainer.innerHTML = `<p style="grid-column:1/-1; text-align:center; padding:50px;">No ramen shops found.</p>`;
        return;
    }

    data.forEach(item => {
        const card = document.createElement('div');
        card.className = 'onsen-card';
        card.innerHTML = `
            <a href="${item.link}">
                <img src="${item.thumbnail}" class="card-thumb" alt="${item.title}" loading="lazy">
                <div class="card-content">
                    <span class="status-badge" style="margin-bottom:8px; font-size:0.7rem;">
                        ${item.categories.join(' · ')}
                    </span>
                    <h3 style="margin:0 0 10px 0; font-size:1.1rem; line-height:1.3;">${item.title}</h3>
                    <p style="font-size:0.85rem; color:#666; margin-bottom:15px;">${item.summary}</p>
                    <div style="font-size:0.8rem; color:#999;">📍 ${item.address}</div>
                </div>
            </a>
        `;
        listContainer.appendChild(card);
    });

    document.getElementById('total-ramens').textContent = data.length;
}

/**
 * 카테고리 버튼 옆의 숫자(Badge) 업데이트
 */
function updateBadges() {
    const counts = { all: 0, tonkotsu: 0, shoyu: 0, miso: 0, shio: 0, chicken: 0, tsukemen: 0, vegan: 0 };

    allRamens.filter(r => r.lang === currentLang).forEach(item => {
        counts.all++;
        Object.keys(CATEGORY_MAP).forEach(themeKey => {
            const keyword = CATEGORY_MAP[themeKey][currentLang];
            if (item.categories.includes(keyword)) {
                counts[themeKey]++;
            }
        });
    });

    Object.keys(counts).forEach(key => {
        const el = document.getElementById(`count-${key}`);
        if (el) el.textContent = counts[key];
    });
}

/**
 * 현재 활성화된 버튼 UI 표시
 */
function updateActiveButtons() {
    document.querySelectorAll('.theme-button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === currentTheme);
    });
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === currentLang);
    });
}

// 이벤트 바인딩
document.addEventListener('DOMContentLoaded', () => {
    // 카테고리 필터 클릭
    document.querySelector('.theme-filter-buttons').addEventListener('click', (e) => {
        const btn = e.target.closest('.theme-button');
        if (!btn) return;
        currentTheme = btn.dataset.theme;
        render();
    });

    // 언어 토글 클릭
    document.querySelector('.lang-selector').addEventListener('click', (e) => {
        const btn = e.target.closest('.lang-btn');
        if (!btn) return;
        currentLang = btn.dataset.lang;
        updateBadges();
        render();
    });

    initMap();
});