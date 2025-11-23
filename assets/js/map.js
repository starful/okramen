// 1. 전역 변수
let map;
let geocoder;
let markers = [];

// 2. [핵심] 카테고리 매핑 (블로그 태그 -> 영어 코드)
// 블로그 글 작성 시 '태그'에 아래 한글 단어 중 하나가 포함되면 자동으로 색상이 적용됩니다.
const categoryMap = {
    // 1. 재물 (Gold)
    "재물": "wealth", "금전": "wealth", "사업": "wealth", "로또": "wealth",
    // 2. 사랑 (Pink/Red)
    "사랑": "love", "연애": "love", "인연": "love", "결혼": "love", "커플": "love",
    // 3. 건강 (Green)
    "건강": "health", "치유": "health", "완쾌": "health", "장수": "health",
    // 4. 학업 (Blue)
    "학업": "study", "합격": "study", "시험": "study", "공부": "study",
    // 5. 안전 (Grey)
    "안전": "safety", "교통안전": "safety", "액운": "safety", "보호": "safety",
    // 6. 가정 (Orange)
    "가정": "family", "가족": "family", "순산": "family", "육아": "family",
    // 7. 성공 (Deep Purple)
    "성공": "success", "승진": "success", "승리": "success", "목표": "success",
    // 8. 예술 (Violet)
    "예술": "art", "아트": "art", "음악": "art", "미술": "art", "재능": "art",
    // 9. 휴식 (Teal/Cyan)
    "휴식": "relax", "힐링": "relax", "자연": "relax", "여행": "relax", "산책": "relax",
    // 10. 역사 (Brown)
    "역사": "history", "전통": "history", "문화재": "history", "관광": "history"
};

// 3. 구글 맵 초기화
async function initMap() {
    console.log("Google Maps initMap 시작됨!");

    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
    const { Geocoder } = await google.maps.importLibrary("geocoding");

    const tokyoCenter ={ lat: 36.2048, lng: 138.2529 };

    map = new Map(document.getElementById("map"), {
        zoom: 5,
        center: tokyoCenter,
        mapId: "2938bb3f7f034d78a2dbaf56", // 본인의 Map ID가 있다면 교체하세요.
        mapTypeControl: false,
        streetViewControl: false
    });

    geocoder = new Geocoder();

    fetchBlogPosts(AdvancedMarkerElement, PinElement);
    setupFilterButtons();
}

// 4. 데이터 가져오기
async function fetchBlogPosts(AdvancedMarkerElement, PinElement) {
    const API_ENDPOINT = "/api/shrines";
    try {
        const response = await fetch(API_ENDPOINT);
        const posts = await response.json();
        processBlogData(posts, AdvancedMarkerElement, PinElement);
    } catch (error) {
        console.error("API 호출 실패:", error);
    }
}

// 5. 데이터 처리
async function processBlogData(posts, AdvancedMarkerElement, PinElement) {
    for (const post of posts) {
        if (post.address) {
            // 기본값은 역사(history)
            let matchedTheme = 'history'; 
            
            // 블로그 카테고리와 매핑 확인
            if (post.categories && post.categories.length > 0) {
                for (let cat of post.categories) {
                    if (categoryMap[cat]) {
                        matchedTheme = categoryMap[cat];
                        break; // 첫 번째 일치하는 카테고리 우선
                    }
                }
            }
            
            geocodeAddressAndCreateMarker(post.address, matchedTheme, post, AdvancedMarkerElement, PinElement);
            await new Promise(r => setTimeout(r, 200));
        }
    }
}

// 6. 주소 변환 및 마커 생성
function geocodeAddressAndCreateMarker(address, theme, post, AdvancedMarkerElement, PinElement) {
    geocoder.geocode({ 'address': address }, function(results, status) {
        if (status === 'OK') {
            const location = results[0].geometry.location;
            const shrineData = {
                name: post.title,
                lat: location.lat(),
                lng: location.lng(),
                theme: theme,
                link: post.link,
                desc: post.summary || post.title,
                thumbnail: post.thumbnail
            };
            createMarker(shrineData, AdvancedMarkerElement, PinElement);
        }
    });
}

// 7. 마커 생성 (색상 지정)
function createMarker(shrine, AdvancedMarkerElement, PinElement) {
    // [핵심] 카테고리별 핀 색상 설정
    const colors = {
        wealth: "#FFD700",  // 재물 (황금색)
        love: "#FF4081",    // 사랑 (핫핑크)
        health: "#4CAF50",  // 건강 (초록)
        study: "#2196F3",   // 학업 (파랑)
        safety: "#607D8B",  // 안전 (청회색)
        family: "#FF9800",  // 가정 (주황)
        success: "#673AB7", // 성공 (보라)
        art: "#E91E63",     // 예술 (진분홍)
        relax: "#00BCD4",   // 휴식 (하늘색)
        history: "#795548"  // 역사 (갈색 - 기본값)
    };
    
    const markerColor = colors[shrine.theme] || colors['history'];

    const pin = new PinElement({
        background: markerColor,
        borderColor: "#ffffff",
        glyphColor: "#ffffff"
    });

    const marker = new AdvancedMarkerElement({
        map: map,
        position: { lat: shrine.lat, lng: shrine.lng },
        title: shrine.name,
        content: pin.element
    });

    marker.category = shrine.theme; // 필터링용 태그 저장

    // 인포윈도우 (팝업)
    const infowindow = new google.maps.InfoWindow({
        content: `
            <div class="infowindow-content" style="width:200px; padding:5px;">
                ${shrine.thumbnail ? `<img src="${shrine.thumbnail}" style="width:100%; height:100px; object-fit:contain; background:#f0f0f0; border-radius:4px; margin-bottom:5px;">` : ''}
                <h3 style="font-size:15px; margin-bottom:5px;">${shrine.name}</h3>
                <p style="font-size:12px; color:#888; margin-bottom:8px;">
                    <span style="display:inline-block; padding:2px 6px; background:${markerColor}; color:#fff; border-radius:10px; font-size:10px;">
                        ${getKoreanThemeName(shrine.theme)}
                    </span>
                </p>
                <a href="${shrine.link}" target="_blank" style="display:inline-block; padding:5px 10px; background:#333; color:#fff; text-decoration:none; border-radius:4px; font-size:12px;">상세 보기 ></a>
            </div>
        `
    });

    marker.addListener("click", () => {
        infowindow.open(map, marker);
    });

    markers.push(marker);
}

// 영어 코드를 한글 이름으로 변환하는 헬퍼 함수 (팝업 표시용)
function getKoreanThemeName(theme) {
    const names = {
        wealth: "재물", love: "사랑", health: "건강",
        study: "학업", safety: "안전", family: "가정",
        success: "성공", art: "예술", relax: "휴식", history: "역사"
    };
    return names[theme] || "역사";
}

// 8. 필터 버튼 로직
function setupFilterButtons() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            buttons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            const selectedTheme = button.getAttribute('data-theme');
            markers.forEach(marker => {
                if (selectedTheme === 'all' || marker.category === selectedTheme) {
                    marker.map = map;
                } else {
                    marker.map = null;
                }
            });
        });
    });
}

window.initMap = initMap;