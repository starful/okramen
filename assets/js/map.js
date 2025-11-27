let map;
let allMarkers = [];
let infoWindow;
let allShrinesData = [];

// 1. 카테고리별 색상 정의
const categoryColors = {
    '재물': '#FBC02D', 
    '연애': '#E91E63', '사랑': '#E91E63',
    '건강': '#2E7D32', 
    '학업': '#1565C0', 
    '안전': '#455A64', 
    '성공': '#512DA8', 
    '역사': '#EF6C00', 
    '기타': '#D32F2F'
};

// 2. 신사에 가장 적합한 카테고리 키 찾기
function findMainCategory(categories) {
    if (!categories || categories.length === 0) return '기타';
    for (const colorKey of Object.keys(categoryColors)) {
        if (colorKey === '기타') continue;
        const match = categories.some(cat => cat.includes(colorKey));
        if (match) return colorKey;
    }
    return '기타';
}

async function initMap() {
    const tokyoCoords = { lat: 35.6895, lng: 139.6917 };
    
    // [중요] 실제 서비스 시 Cloud Console에서 생성한 Map ID로 교체 필요
    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 11,
        center: tokyoCoords,
        mapId: "DEMO_MAP_ID", 
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        options: { gestureHandling: 'greedy' }
    });

    infoWindow = new google.maps.InfoWindow();

    // 내 위치 찾기 버튼
    addLocationButton();

    try {
        const response = await fetch('/api/shrines');
        const jsonData = await response.json();
        allShrinesData = jsonData.shrines ? jsonData.shrines : jsonData;

        if (!Array.isArray(allShrinesData)) return;

        if (jsonData.last_updated) {
            const msgElement = document.getElementById('update-msg');
            if (msgElement) msgElement.textContent = `데이터 업데이트: ${jsonData.last_updated}`;
        }

        addMarkers(allShrinesData);
        
        // [수정] 최신 4개만 표시
        renderRecentShrines(allShrinesData);
        
        setupFilterButtons();
        updateFilterButtonCounts(allShrinesData);

    } catch (error) {
        console.error("초기화 오류:", error);
    }
}

// [추가] 주소 복사 함수
window.copyToClipboard = function(text) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        alert("📋 주소가 복사되었습니다!\n" + text);
    }).catch(err => {
        console.error('복사 실패:', err);
        // 보안 컨텍스트(https)가 아닐 경우 execCommand 폴백
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("Copy");
        textArea.remove();
        alert("📋 주소가 복사되었습니다!\n" + text);
    });
};

function updateFilterButtonCounts(shrines) {
    const themeMap = {
        'wealth': '재물', 'love': '연애', 'health': '건강',
        'study': '학업', 'safety': '안전', 'success': '성공', 'history': '역사'
    };

    const counts = { 'all': shrines.length };
    Object.keys(themeMap).forEach(key => counts[key] = 0);

    shrines.forEach(shrine => {
        if (!shrine.categories) return;
        Object.keys(themeMap).forEach(themeKey => {
            const keyword = themeMap[themeKey];
            if (shrine.categories.some(cat => cat.includes(keyword))) {
                counts[themeKey]++;
            }
        });
    });

    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(btn => {
        const theme = btn.getAttribute('data-theme');
        const count = counts[theme] || 0;
        const originalText = btn.childNodes[0].nodeValue.trim(); 
        btn.textContent = `${originalText} (${count})`;
    });
}

function addMarkers(shrines) {
    allMarkers.forEach(marker => marker.map = null);
    allMarkers = [];

    shrines.forEach((shrine) => {
        if (!shrine.lat || !shrine.lng) return;

        const mainCategoryKey = findMainCategory(shrine.categories);
        const borderColor = categoryColors[mainCategoryKey] || categoryColors['기타'];

        const pinImg = document.createElement("img");
        pinImg.src = "assets/images/marker_torii.png"; 
        
        pinImg.style.width = "40px";
        pinImg.style.height = "40px";
        pinImg.style.borderRadius = "50%";
        pinImg.style.border = `3px solid ${borderColor}`;
        pinImg.style.backgroundColor = "white";
        pinImg.style.boxShadow = "0 3px 6px rgba(0,0,0,0.3)";
        pinImg.style.objectFit = "contain";
        pinImg.style.padding = "2px";

        const marker = new google.maps.marker.AdvancedMarkerElement({
            map: map,
            position: { lat: shrine.lat, lng: shrine.lng },
            title: shrine.title,
            content: pinImg,
        });

        marker.categories = shrine.categories || [];

        // 마커 클릭 시 InfoWindow
        marker.addListener("click", () => {
            const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(shrine.title)}&travelmode=walking`;
            
            // 주소 데이터가 있으면 사용, 없으면 제목 사용
            const copyText = shrine.address ? shrine.address : shrine.title;

            const contentString = `
                <div class="infowindow-content">
                    <img src="${shrine.thumbnail}" alt="${shrine.title}">
                    <h3>${shrine.title}</h3>
                    <p>🏷️ ${shrine.categories.join(', ')}</p>
                    
                    <div class="info-btn-group">
                        <a href="${directionsUrl}" target="_blank" class="info-btn dir-btn">📍 길찾기</a>
                        <a href="${shrine.link}" target="_blank" class="info-btn blog-btn">블로그</a>
                        
                        <!-- [NEW] 주소 복사 버튼 -->
                        <button onclick="copyToClipboard('${copyText}')" class="info-btn copy-btn" title="주소 복사">
                            📋
                        </button>
                    </div>
                </div>
            `;
            infoWindow.setContent(contentString);
            infoWindow.open(map, marker);
        });

        allMarkers.push(marker);
    });
}

function filterMapMarkers(theme) {
    const themeMap = {
        'wealth': '재물', 'love': '연애', 'health': '건강',
        'study': '학업', 'safety': '안전', 'success': '성공', 'history': '역사'
    };

    const targetCategory = themeMap[theme];

    allMarkers.forEach(marker => {
        let isVisible = false;
        if (theme === 'all') {
            isVisible = true;
        } else {
            isVisible = marker.categories.some(cat => cat.includes(targetCategory));
        }
        marker.map = isVisible ? map : null;
    });
}

function addLocationButton() {
    const locationButton = document.createElement("button");
    locationButton.innerHTML = "🎯 내 위치";
    locationButton.style.backgroundColor = "#fff";
    locationButton.style.border = "2px solid #fff";
    locationButton.style.borderRadius = "2px";
    locationButton.style.boxShadow = "0 2px 6px rgba(0,0,0,.3)";
    locationButton.style.color = "rgb(25,25,25)";
    locationButton.style.cursor = "pointer";
    locationButton.style.fontFamily = "Roboto,Arial,sans-serif";
    locationButton.style.fontSize = "14px";
    locationButton.style.lineHeight = "38px";
    locationButton.style.margin = "10px";
    locationButton.style.padding = "0 10px";
    locationButton.style.textAlign = "center";
    
    locationButton.addEventListener("click", () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const pos = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                    };
                    new google.maps.marker.AdvancedMarkerElement({
                        map: map,
                        position: pos,
                        title: "내 위치",
                    });
                    map.setCenter(pos);
                    map.setZoom(14);
                },
                () => { alert("위치 정보를 가져올 수 없습니다."); }
            );
        } else {
            alert("브라우저가 위치 정보를 지원하지 않습니다.");
        }
    });
    map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(locationButton);
}

// [수정] 최신 4개만 렌더링
function renderRecentShrines(shrines) {
    const listContainer = document.getElementById('shrine-list');
    if (!listContainer) return;

    listContainer.innerHTML = ''; 
    const sortedShrines = [...shrines].sort((a, b) => new Date(b.published) - new Date(a.published));
    
    // 0~4 (4개)만 자름
    const recentItems = sortedShrines.slice(0, 4);

    recentItems.forEach(shrine => {
        const categoryTag = shrine.categories && shrine.categories.length > 0 
            ? ` • <span>🏷️ ${shrine.categories[0]}</span>` 
            : '';

        const cardHTML = `
            <div class="shrine-card">
                <a href="${shrine.link}" target="_blank" class="card-thumb-link">
                    <img src="${shrine.thumbnail}" alt="${shrine.title}" class="card-thumb" loading="lazy">
                </a>
                <div class="card-content">
                    <h3 class="card-title">
                        <a href="${shrine.link}" target="_blank">${shrine.title}</a>
                    </h3>
                    <div class="card-meta">
                        <span>📅 ${shrine.published}</span>
                        ${categoryTag}
                    </div>
                    <p class="card-summary">${shrine.summary}</p>
                    <a href="${shrine.link}" target="_blank" class="card-btn">더 보기 →</a>
                </div>
            </div>
        `;
        listContainer.insertAdjacentHTML('beforeend', cardHTML);
    });
}

function setupFilterButtons() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const selectedTheme = btn.getAttribute('data-theme');
            filterMapMarkers(selectedTheme);
        });
    });
}

/* --------------------------------------
   오미쿠지 (운세 뽑기) 로직
-------------------------------------- */
const omikujiResults = [
    { title: "대길 (大吉)", desc: "금전운이 폭발하는 날입니다!💰<br>지금 당장 복권이라도 사야 할 기세!", theme: "wealth", btnText: "💰 재물운 신사 지도 보기", color: "#FBC02D" },
    { title: "중길 (中吉)", desc: "마음이 설레는 인연이 다가옵니다.💘<br>사랑을 쟁취할 준비 되셨나요?", theme: "love", btnText: "💘 연애운 신사 지도 보기", color: "#E91E63" },
    { title: "소길 (小吉)", desc: "건강이 최고입니다.🌿<br>몸과 마음을 힐링하는 시간이 필요해요.", theme: "health", btnText: "🌿 건강기원 신사 지도 보기", color: "#2E7D32" },
    { title: "길 (吉)", desc: "노력한 만큼 성과가 나오는 날!📚<br>학업이나 승진에 좋은 기운이 있어요.", theme: "study", btnText: "🎓 학업/성공 신사 지도 보기", color: "#1565C0" },
    { title: "흉 (凶)", desc: "조금 조심해야 할 시기입니다.🚧<br>신사에서 액운을 씻어내고 보호받으세요!", theme: "safety", btnText: "🛡️ 액막이/안전 신사 지도 보기", color: "#455A64" }
];

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('omikuji-modal');
    const openBtn = document.getElementById('omikuji-btn');
    const closeBtn = document.querySelector('.close-modal');
    const drawBtn = document.getElementById('draw-btn');
    const step1 = document.getElementById('omikuji-step1');
    const step2 = document.getElementById('omikuji-step2');
    const boxImg = document.getElementById('shaking-box');

    openBtn.addEventListener('click', () => {
        modal.style.display = 'flex';
        step1.style.display = 'block';
        step2.style.display = 'none';
        boxImg.classList.remove('shake'); 
    });

    closeBtn.addEventListener('click', () => modal.style.display = 'none');
    window.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });

    drawBtn.addEventListener('click', () => {
        boxImg.classList.add('shake');
        
        setTimeout(() => {
            boxImg.classList.remove('shake');
            
            // [NEW] 폭죽 효과 (Confetti)
            if (typeof confetti === 'function') {
                confetti({
                    particleCount: 150,
                    spread: 70,
                    origin: { y: 0.6 },
                    colors: ['#FBC02D', '#E91E63', '#ffffff']
                });
            }

            const randomResult = omikujiResults[Math.floor(Math.random() * omikujiResults.length)];
            
            document.getElementById('result-title').textContent = randomResult.title;
            document.getElementById('result-title').style.color = randomResult.color;
            document.getElementById('result-desc').innerHTML = randomResult.desc;
            
            const goMapBtn = document.getElementById('go-map-btn');
            goMapBtn.textContent = randomResult.btnText;
            goMapBtn.style.backgroundColor = randomResult.color;
            
            goMapBtn.onclick = () => {
                const buttons = document.querySelectorAll('.theme-button');
                buttons.forEach(b => {
                    b.classList.remove('active');
                    if(b.getAttribute('data-theme') === randomResult.theme) {
                        b.classList.add('active');
                    }
                });
                filterMapMarkers(randomResult.theme);
                modal.style.display = 'none';
                
                // 지도로 스크롤 이동
                document.getElementById("map").scrollIntoView({ behavior: "smooth", block: "center" });
            };

            step1.style.display = 'none';
            step2.style.display = 'block';
            
        }, 1000);
    });
});