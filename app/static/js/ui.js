import { OMIKUJI_RESULTS, CATEGORY_THEME_MAP } from './config.js';
import { getThemesFromCategories } from './utils.js';

// 무한 스크롤 상태 변수
let currentShrinesData = []; // 현재 표시할 전체 데이터
let displayedCount = 0;      // 현재 화면에 그려진 개수
const BATCH_SIZE = 6;        // 한 번에 불러올 개수
let observer;                // 스크롤 감지 객체

// [1] 리스트 렌더링 (초기화 및 스크롤 설정)
export function renderShrineList(shrines) {
    const listContainer = document.getElementById('shrine-list');
    const sentinel = document.getElementById('scroll-sentinel');
    if (!listContainer || !sentinel) return;
    
    // 1. 상태 초기화
    currentShrinesData = shrines;
    displayedCount = 0;
    listContainer.innerHTML = ''; // 기존 리스트 비우기
    
    // 2. 기존 감지기가 있다면 연결 해제 (중복 방지)
    if (observer) observer.disconnect();

    // 3. 첫 번째 배치 로드 (최초 6개)
    loadMoreItems();

    // 4. 스크롤 감지기 설정 (IntersectionObserver)
    observer = new IntersectionObserver((entries) => {
        // 센서(sentinel)가 화면에 보이면 추가 로드
        if (entries[0].isIntersecting) {
            loadMoreItems();
        }
    }, { rootMargin: '100px' }); // 바닥에 닿기 100px 전에 미리 로딩

    observer.observe(sentinel);
}

// [2] 아이템 추가 로드 함수
function loadMoreItems() {
    // 모든 데이터를 다 보여줬으면 더 이상 실행 안 함
    if (displayedCount >= currentShrinesData.length) return;

    const listContainer = document.getElementById('shrine-list');
    const fragment = document.createDocumentFragment();

    // 다음 배치만큼 데이터 잘라내기
    const nextBatch = currentShrinesData.slice(displayedCount, displayedCount + BATCH_SIZE);

    nextBatch.forEach((shrine, index) => {
        // 전체 데이터 기준 인덱스 (NEW 뱃지용)
        const globalIndex = displayedCount + index;
        
        let badgeHtml = globalIndex === 0 ? '<span class="new-badge">NEW</span>' : '';
        const card = document.createElement('div');
        card.className = 'shrine-card';
        
        const thumbUrl = shrine.thumbnail ? shrine.thumbnail : '/static/images/default_thumb.webp';
        const categoryTag = shrine.categories?.[0] ? `<span>🏷️ ${shrine.categories[0]}</span>` : '';
        
        // 카드 HTML 구성 (투명도 애니메이션 추가 style="animation: fadeIn...")
        card.innerHTML = `
            <a href="${shrine.link}" class="card-thumb-link">
                ${badgeHtml}
                <img src="${thumbUrl}" alt="${shrine.title}" class="card-thumb" loading="lazy">
            </a>
            <div class="card-content">
                <h3 class="card-title"><a href="${shrine.link}">${shrine.title}</a></h3>
                <div class="card-meta">📅 ${shrine.published || ''} • ${categoryTag}</div>
                <p class="card-summary">${shrine.summary || ''}</p>
                <div class="card-footer"><a href="${shrine.link}" class="card-btn">더 보기 →</a></div>
            </div>
        `;
        fragment.appendChild(card);
    });

    listContainer.appendChild(fragment);
    
    // 카운트 업데이트
    displayedCount += nextBatch.length;

    // 더 이상 불러올 데이터가 없으면 감지 종료
    if (displayedCount >= currentShrinesData.length) {
        if (observer) observer.disconnect();
    }
}

// [3] 필터 버튼 숫자 업데이트
export function updateFilterButtonCounts(shrines) {
    const counts = { all: shrines.length };
    Object.values(CATEGORY_THEME_MAP).forEach(theme => { if (!counts[theme]) counts[theme] = 0; });

    shrines.forEach(shrine => {
        const themes = new Set(getThemesFromCategories(shrine.categories));
        themes.forEach(theme => { if (counts.hasOwnProperty(theme)) counts[theme]++; });
    });

    document.querySelectorAll('.theme-button').forEach(btn => {
        const theme = btn.dataset.theme;
        if (theme && counts[theme] !== undefined) {
            const textOnly = btn.textContent.split('(')[0].trim();
            btn.textContent = `${textOnly} (${counts[theme]})`;
        }
    });
}

// [4] 오미쿠지 초기화
export function initOmikuji(filterCallback) {
    const modal = document.getElementById('omikuji-modal');
    if (!modal) return;
    
    document.getElementById('omikuji-btn').onclick = () => {
        modal.style.display = 'flex';
        document.getElementById('omikuji-step1').style.display = 'block';
        document.getElementById('omikuji-step2').style.display = 'none';
        document.getElementById('shaking-box')?.classList.remove('shake');
        if (typeof confetti === 'function') confetti({ particleCount: 50, spread: 50, origin: { y: 0.7 } });
    };
    
    document.querySelector('.close-modal').onclick = () => modal.style.display = 'none';
    window.onclick = (e) => { if (e.target == modal) modal.style.display = "none"; };
    
    document.getElementById('draw-btn').onclick = () => {
        const box = document.getElementById('shaking-box');
        box?.classList.add('shake');
        
        setTimeout(() => {
            box?.classList.remove('shake');
            const res = OMIKUJI_RESULTS[Math.floor(Math.random() * OMIKUJI_RESULTS.length)];
            
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
                filterCallback(res.theme); // 지도 필터링 실행
                modal.style.display = 'none';
                document.getElementById("map")?.scrollIntoView({ behavior: "smooth", block: "center" });
            };
            
            document.getElementById('omikuji-step1').style.display = 'none';
            document.getElementById('omikuji-step2').style.display = 'block';
            if (typeof confetti === 'function') confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 } });
        }, 1000);
    };
}