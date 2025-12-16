import { THEME_COLORS } from './config.js';
import { getThemesFromCategories, findMainTheme } from './utils.js';

let map;
let allMarkers = [];
let infoWindow;

// [수정] 구글 맵 로드 대기 함수 추가
async function waitForGoogleMaps() {
    // 1. 이미 로드되어 있으면 바로 반환
    if (window.google && window.google.maps) {
        return window.google.maps;
    }
    
    // 2. 아직 안 됐으면 로드될 때까지 대기 (Polling 방식)
    return new Promise((resolve) => {
        const checkInterval = setInterval(() => {
            if (window.google && window.google.maps) {
                clearInterval(checkInterval);
                resolve(window.google.maps);
            }
        }, 100); // 0.1초마다 확인
    });
}

export async function initGoogleMap() {
    // [중요] 구글 맵 객체가 준비될 때까지 기다림
    await waitForGoogleMaps();

    const { Map } = await google.maps.importLibrary("maps");
    map = new Map(document.getElementById("map"), {
        zoom: 10,
        center: { lat: 35.6895, lng: 139.6917 },
        mapId: "2938bb3f7f034d78",
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        gestureHandling: 'greedy'
    });
    infoWindow = new google.maps.InfoWindow();
    addLocationButton();
    return google.maps;
}

// ... (나머지 함수들은 그대로 유지) ...
// addMarkers, filterMapMarkers 등
export function addMarkers(shrines, AdvancedMarkerElement) {
    // ... (기존 코드) ...
    allMarkers.forEach(m => m.map = null);
    allMarkers = [];

    shrines.forEach((shrine) => {
        if (!shrine.lat || !shrine.lng) return;

        const mainTheme = findMainTheme(shrine.categories);
        const borderColor = THEME_COLORS[mainTheme] || THEME_COLORS['default'];

        const markerDiv = document.createElement("div");
        markerDiv.className = 'marker-icon';
        markerDiv.style.cssText = `background-color:${borderColor}; width:32px; height:32px; border-radius:50%; border:3px solid white; box-shadow:0 3px 6px rgba(0,0,0,0.4);`;

        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: shrine.lat, lng: shrine.lng },
            title: shrine.title,
            content: markerDiv,
        });

        marker.themes = getThemesFromCategories(shrine.categories);
        marker.addListener("click", () => showInfoWindow(marker, shrine));
        allMarkers.push(marker);
    });
}

export function filterMapMarkers(selectedTheme) {
    let hasVisibleMarkers = false;
    allMarkers.forEach(marker => {
        const isVisible = (selectedTheme === 'all') || (marker.themes && marker.themes.includes(selectedTheme));
        marker.map = isVisible ? map : null;
        if (isVisible) hasVisibleMarkers = true;
    });
    if (hasVisibleMarkers) updateCameraBounds();
}

function updateCameraBounds() {
    const bounds = new google.maps.LatLngBounds();
    let count = 0;
    allMarkers.forEach(m => { if (m.map) { bounds.extend(m.position); count++; } });
    
    if (count > 0) {
        map.fitBounds(bounds);
        const listener = google.maps.event.addListener(map, "idle", () => {
            if (map.getZoom() > 15) map.setZoom(15);
            google.maps.event.removeListener(listener);
        });
    } else {
        map.setCenter({ lat: 35.6895, lng: 139.6917 });
        map.setZoom(10);
    }
}

function showInfoWindow(marker, shrine) {
    const thumbUrl = shrine.thumbnail || '/static/images/default_thumb.webp';
    const content = `
        <div class="infowindow-content" style="max-width:220px;">
            <a href="${shrine.link}" target="_blank"><img src="${thumbUrl}" style="width:100%; height:120px; object-fit:cover; border-radius:8px; margin-bottom:8px; background:#eee;"></a>
            <h3 style="margin:0 0 5px 0; font-size:16px;">${shrine.title}</h3>
            <div class="info-btn-group" style="display:flex; gap:5px;">
                <a href="https://www.google.com/maps/dir/?api=1&destination=${shrine.lat},${shrine.lng}" target="_blank" class="info-btn dir-btn">📍 길찾기</a>
                <a href="${shrine.link}" class="info-btn blog-btn">상세보기</a>
            </div>
        </div>`;
    infoWindow.setContent(content);
    infoWindow.open(map, marker);
}

function addLocationButton() {
    const btn = document.createElement("button");
    btn.textContent = "🎯 내 위치";
    btn.className = "location-button";
    map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(btn);
    btn.onclick = () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(pos => {
                const p = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                map.setCenter(p); map.setZoom(14);
                new google.maps.marker.AdvancedMarkerElement({ map: map, position: p, title: "내 위치" });
            }, () => alert("위치 정보를 가져올 수 없습니다."));
        }
    };
}