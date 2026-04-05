/**
 * OKRamen - Frontend Engine
 * Handles Google Maps (Advanced Markers), Multi-language filtering, 
 * and dynamic UI rendering.
 */

let map;
let markers = [];
let allRamens = [];
let currentLang = 'en';
let currentTheme = 'all';

// Language to Category Keyword Mapping
// This ensures that clicking "Tonkotsu" in English also filters "돈코츠" in Korean.
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
    // 1. Initialize Map (Advanced Marker requirements: mapId)
    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

    const mapOptions = {
        center: { lat: 36.5, lng: 138.5 }, // Central Japan
        zoom: 6,
        mapId: "OK_RAMEN_MAP_ID", // Required for Advanced Markers
        disableDefaultUI: false,
        zoomControl: true,
        streetViewControl: false,
        mapTypeControl: false,
    };

    map = new Map(document.getElementById("map"), mapOptions);

    // 2. Fetch Data
    try {
        const response = await fetch('/api/ramens');
        const data = await response.json();
        allRamens = data.ramens || [];
        
        // Update Stats in Footer
        document.getElementById('last-updated-date').textContent = data.last_updated;
        updateBadges();
        
        // 3. Initial Render
        render();
    } catch (error) {
        console.error("Data fetch failed:", error);
    }
}

function render() {
    // Filter data based on Language and Theme
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
 * Update Google Map Markers
 */
async function updateMarkers(data) {
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

    // Clear existing markers
    markers.forEach(m => m.map = null);
    markers = [];

    const bounds = new google.maps.LatLngBounds();

    data.forEach(item => {
        if (!item.lat || !item.lng) return;

        // Custom Pin Style
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

        marker.addListener("click", () => {
            window.location.href = item.link;
        });

        markers.push(marker);
        bounds.extend(marker.position);
    });

    // Auto-zoom if markers exist
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
 * Update the Ramen Card List UI
 */
function updateList(data) {
    const listContainer = document.getElementById('ramen-list');
    listContainer.innerHTML = '';

    if (data.length === 0) {
        listContainer.innerHTML = `<p style="grid-column: 1/-1; text-align: center; padding: 50px;">No ramen shops found in this category.</p>`;
        return;
    }

    data.forEach(item => {
        const card = document.createElement('div');
        card.className = 'onsen-card';
        card.innerHTML = `
            <a href="${item.link}">
                <img src="${item.thumbnail}" class="card-thumb" alt="${item.title}" loading="lazy">
                <div class="card-content">
                    <span class="status-badge" style="margin-bottom: 8px; font-size: 0.7rem;">
                        ${item.categories.join(' · ')}
                    </span>
                    <h3 style="margin: 0 0 10px 0; font-size: 1.1rem; line-height: 1.3;">${item.title}</h3>
                    <p style="font-size: 0.85rem; color: #666; margin-bottom: 15px;">${item.summary}</p>
                    <div style="font-size: 0.8rem; color: #999;">📍 ${item.address}</div>
                </div>
            </a>
        `;
        listContainer.appendChild(card);
    });

    document.getElementById('total-ramens').textContent = data.length;
}

/**
 * Calculate counts for each category badge
 */
function updateBadges() {
    const counts = { all: 0 };
    Object.keys(CATEGORY_MAP).forEach(key => counts[key] = 0);

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

function updateActiveButtons() {
    // Theme buttons
    document.querySelectorAll('.theme-button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === currentTheme);
    });
    // Lang buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === currentLang);
    });
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Theme Filter Click
    document.querySelector('.theme-filter-buttons').addEventListener('click', (e) => {
        const btn = e.target.closest('.theme-button');
        if (!btn) return;
        currentTheme = btn.dataset.theme;
        render();
    });

    // Language Toggle Click
    document.querySelector('.lang-selector').addEventListener('click', (e) => {
        const btn = e.target.closest('.lang-btn');
        if (!btn) return;
        currentLang = btn.dataset.lang;
        updateBadges();
        render();
    });

    initMap();
});