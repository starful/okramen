/**
 * OKRamen Global Engine
 * Features: Mobile UX Optimized, Multi-language Category Mapping, Advanced Markers
 */

const OKRamenApp = {
    // --- 1. State Management ---
    state: {
        allData: [],        // 서버에서 가져온 전체 데이터
        filteredData: [],   // 필터링된 결과 데이터
        currentLang: 'en',  // 현재 언어 (기본: en)
        currentFlavor: 'all', // 현재 선택된 필터
        map: null,
        markers: [],
        infoWindow: null
    },

    // --- 2. Category Mapping (데이터 속 단어와 버튼 매칭) ---
    // JSON 데이터에 어떤 언어로 적혀있든 버튼과 연결해주는 사전입니다.
    categoryMap: {
        'tonkotsu': ['tonkotsu', '돈코츠', '돼지육수'],
        'shoyu': ['shoyu', '쇼유', '간장'],
        'miso': ['miso', '미소', '된장'],
        'shio': ['shio', '시오', '소금'],
        'chicken': ['chicken', '치킨', '닭육수', '토리파이탄'],
        'tsukemen': ['tsukemen', '츠케멘'],
        'vegan': ['vegan', '비건', '채식']
    },

    // --- 3. Initialization ---
    async init() {
        console.log("🚀 OKRamen Engine Starting...");
        
        // 지도 초기화
        await this.initMap();
        
        // 이벤트 바인딩 (언어/필터 버튼)
        this.bindEvents();
        
        // 데이터 가져오기
        await this.fetchData();
        
        // 초기 렌더링
        this.render();
    },

    // --- 4. Google Maps Setup (Advanced Markers) ---
    async initMap() {
        try {
            const { Map } = await google.maps.importLibrary("maps");
            const el = document.getElementById("map");
            if (!el) return;

            this.state.map = new Map(el, {
                center: { lat: 35.6812, lng: 139.7671 }, // 도쿄역 중심
                zoom: 11,
                mapId: "2938bb3f7f034d7849f653d1", // 제공해주신 지도 ID
                mapTypeControl: false,
                streetViewControl: false,
                fullscreenControl: false
            });

            this.state.infoWindow = new google.maps.InfoWindow();
        } catch (error) {
            console.error("❌ Map Init Error:", error);
        }
    },

    // --- 5. Data Fetching ---
    async fetchData() {
        try {
            const response = await fetch('/api/ramens');
            const json = await response.json();
            this.state.allData = json.ramens || [];
            
            // 푸터(Footer)의 상태바 정보 업데이트
            const totalEl = document.getElementById('total-ramens');
            const dateEl = document.getElementById('last-updated-date');
            if (totalEl) totalEl.innerText = this.state.allData.length;
            if (dateEl) dateEl.innerText = json.last_updated || '-';
            
            console.log("✅ Data Loaded:", this.state.allData.length, "items");
        } catch (e) {
            console.error("❌ API Fetch Error:", e);
        }
    },

    // --- 6. Matching Logic (핵심: 대소문자/언어 무시 매칭) ---
    checkMatch(itemCategories, filterTheme) {
        if (filterTheme === 'all') return true;
        if (!itemCategories || itemCategories.length === 0) return false;

        // 버튼 테마(예: 'shio')에 해당하는 검색 키워드 리스트 가져오기
        const keywords = this.categoryMap[filterTheme] || [filterTheme];

        return itemCategories.some(cat => {
            // 데이터의 카테고리명을 소문자로 바꾸고 공백 제거
            const normalizedCat = cat.toLowerCase().replace(/\s/g, '');
            // 사전의 키워드 중 하나라도 포함되어 있는지 확인
            return keywords.some(k => normalizedCat.includes(k));
        });
    },

    applyFilters() {
        const { allData, currentLang, currentFlavor } = this.state;

        this.state.filteredData = allData.filter(item => {
            const langMatch = item.lang === currentLang;
            const flavorMatch = this.checkMatch(item.categories, currentFlavor);
            return langMatch && flavorMatch;
        });
    },

    // --- 7. Rendering Logic ---
    render() {
        this.applyFilters();
        this.renderList();
        this.renderMarkers();
        this.updateFilterBadges(); // 필터 배지 숫자 갱신
    },

    renderList() {
        const container = document.getElementById('ramen-list');
        if (!container) return;
        
        if (this.state.filteredData.length === 0) {
            container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 80px 20px; color: #888;">
                No Ramen shops found for this category in ${this.state.currentLang.toUpperCase()}.
            </div>`;
            return;
        }

        container.innerHTML = this.state.filteredData.map(item => `
            <article class="onsen-card">
                <a href="${item.link}" class="card-thumb-link">
                    <img src="${item.thumbnail}" class="card-thumb" alt="${item.title}" loading="lazy" 
                         onerror="this.src='https://placehold.co/600x450?text=OKRamen'">
                </a>
                <div class="card-content">
                    <div class="card-meta">📍 ${item.address}</div>
                    <h3 class="card-title"><a href="${item.link}">${item.title}</a></h3>
                    <p class="card-summary">${item.summary}</p>
                    <div class="card-footer">
                        <div class="card-tags">
                            ${item.categories.map(c => `#${c}`).join(' ')}
                        </div>
                        <a href="${item.link}" class="card-btn">Explore →</a>
                    </div>
                </div>
            </article>
        `).join('');
    },

    async renderMarkers() {
        if (!this.state.map) return;

        // 기존 마커 제거
        this.state.markers.forEach(m => m.map = null);
        this.state.markers = [];

        const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

        this.state.filteredData.forEach(item => {
            if (!item.lat || !item.lng) return;

            const pin = new PinElement({
                background: "#e74c3c",
                borderColor: "#ffffff",
                glyphColor: "#ffffff",
            });

            const marker = new AdvancedMarkerElement({
                position: { lat: parseFloat(item.lat), lng: parseFloat(item.lng) },
                map: this.state.map,
                title: item.title,
                content: pin.element
            });

            marker.addListener("click", () => {
                this.state.infoWindow.setContent(`
                    <div style="padding:10px; min-width:160px; color:#333;">
                        <strong style="display:block; margin-bottom:5px;">${item.title}</strong>
                        <a href="${item.link}" style="color:#e74c3c; font-size:12px; font-weight:bold; text-decoration:none;">View Details →</a>
                    </div>
                `);
                this.state.infoWindow.open(this.state.map, marker);
            });

            this.state.markers.push(marker);
        });
    },

    // --- 8. Filter Badge Update (배지 숫자 로직) ---
    updateFilterBadges() {
        // 현재 선택된 언어의 데이터만 기준으로 숫자 계산
        const langData = this.state.allData.filter(i => i.lang === this.state.currentLang);
        
        document.querySelectorAll('.count-badge').forEach(badge => {
            const theme = badge.id.replace('count-', ''); // shio, miso 등 추출
            
            let count = 0;
            if (theme === 'all') {
                count = langData.length;
            } else {
                // 해당 언어 데이터 중 카테고리 매칭되는 것만 카운트
                count = langData.filter(item => this.checkMatch(item.categories, theme)).length;
            }
            
            badge.innerText = count;
        });
    },

    // --- 9. Event Listeners ---
    bindEvents() {
        // 언어 스위처
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const lang = e.target.dataset.lang;
                this.state.currentLang = lang;
                
                document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                
                this.render(); // 화면 갱신 (리스트, 마커, 배지 숫자)
            });
        });

        // 필터 테마 버튼
        document.querySelectorAll('.theme-button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.target.closest('.theme-button');
                const theme = target.dataset.theme;
                
                this.state.currentFlavor = theme;
                
                target.parentElement.querySelectorAll('.theme-button').forEach(b => b.classList.remove('active'));
                target.classList.add('active');
                
                this.render();
            });
        });
    }
};

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    OKRamenApp.init();
});