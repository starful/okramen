const OKRamenApp = {
    state: {
        allData: [],
        filteredData: [],
        currentLang: 'en',
        currentFlavor: 'all',
        map: null,
        markers: [],
        infoWindow: null
    },

    // 💡 [핵심] 언어/대소문자 상관없이 매칭해주는 사전
    categoryMap: {
        'tonkotsu': ['tonkotsu', '돈코츠', '돼지육수'],
        'shoyu': ['shoyu', '쇼유', '간장'],
        'miso': ['miso', '미소', '된장'],
        'shio': ['shio', '시오', '소금'],
        'chicken': ['chicken', '치킨', '닭육수', '토리파이탄'],
        'tsukemen': ['tsukemen', '츠케멘'],
        'vegan': ['vegan', '비건', '채식']
    },

    async init() {
        console.log("🚀 App Init...");
        await this.initMap();
        this.bindEvents();
        await this.fetchData();
        this.render();
    },

    async initMap() {
        const { Map } = await google.maps.importLibrary("maps");
        this.state.map = new Map(document.getElementById("map"), {
            center: { lat: 35.6812, lng: 139.7671 },
            zoom: 11,
            mapId: "2938bb3f7f034d7849f653d1"
        });
        this.state.infoWindow = new google.maps.InfoWindow();
    },

    async fetchData() {
        try {
            const response = await fetch('/api/ramens');
            const json = await response.json();
            this.state.allData = json.ramens || [];
            document.getElementById('last-updated-date').innerText = json.last_updated || '-';
            document.getElementById('total-ramens').innerText = this.state.allData.length;
        } catch (e) { console.error("❌ Data error", e); }
    },

    // 💡 매칭 검사기
    checkMatch(itemCategories, filterTheme) {
        if (filterTheme === 'all') return true;
        if (!itemCategories) return false;
        
        const keywords = this.categoryMap[filterTheme] || [filterTheme];
        return itemCategories.some(cat => {
            const normalized = cat.toLowerCase().replace(/\s/g, '');
            return keywords.some(k => normalized.includes(k));
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

    render() {
        this.applyFilters();
        this.renderList();
        this.renderMarkers();
        this.updateFilterBadges();
    },

    renderList() {
        const container = document.getElementById('ramen-list');
        if (!container) return;
        container.innerHTML = this.state.filteredData.length > 0 
            ? this.state.filteredData.map(item => this.createCardHTML(item)).join('')
            : `<div style="grid-column:1/-1; text-align:center; padding:50px;">No Results.</div>`;
    },

    createCardHTML(item) {
        return `
            <article class="onsen-card">
                <a href="${item.link}" class="card-thumb-link">
                    <img src="${item.thumbnail}" class="card-thumb" onerror="this.src='https://placehold.co/600x450?text=Ramen'">
                </a>
                <div class="card-content">
                    <div class="card-meta">📍 ${item.address}</div>
                    <h3 class="card-title">${item.title}</h3>
                    <p class="card-summary">${item.summary}</p>
                    <a href="${item.link}" class="card-btn">Explore →</a>
                </div>
            </article>`;
    },

    async renderMarkers() {
        if (!this.state.map) return;
        this.state.markers.forEach(m => m.map = null);
        const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
        
        this.state.filteredData.forEach(item => {
            const pin = new PinElement({ background: "#e74c3c", borderColor: "#fff", glyphColor: "#fff" });
            const marker = new AdvancedMarkerElement({
                position: { lat: parseFloat(item.lat), lng: parseFloat(item.lng) },
                map: this.state.map,
                content: pin.element
            });
            this.state.markers.push(marker);
        });
    },

    // 💡 [핵심] 뱃지 카운트 업데이트 함수
    updateFilterBadges() {
        // 현재 선택된 언어의 데이터만 먼저 필터링
        const langData = this.state.allData.filter(i => i.lang === this.state.currentLang);
        
        document.querySelectorAll('.count-badge').forEach(badge => {
            const theme = badge.id.replace('count-', ''); // shoyu, tonkotsu 등 추출
            
            // 테마별로 데이터 개수 계산
            const count = (theme === 'all') 
                ? langData.length 
                : langData.filter(item => this.checkMatch(item.categories, theme)).length;
            
            badge.innerText = count;
        });
    },

    bindEvents() {
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.state.currentLang = e.target.dataset.lang;
                document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.render();
            });
        });

        document.querySelectorAll('.theme-button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.target.closest('.theme-button');
                this.state.currentFlavor = target.dataset.theme;
                target.parentElement.querySelectorAll('.theme-button').forEach(b => b.classList.remove('active'));
                target.classList.add('active');
                this.render();
            });
        });
    }
};

document.addEventListener('DOMContentLoaded', () => OKRamenApp.init());