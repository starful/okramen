// 라멘 카테고리와 테마 매칭 (데이터베이스의 카테고리 명칭과 일치해야 함)
export const CATEGORY_THEME_MAP = {
    '돈코츠': 'tonkotsu', 'Tonkotsu': 'tonkotsu',
    '쇼유': 'shoyu', 'Shoyu': 'shoyu',
    '미슐랭': 'michelin', 'Michelin': 'michelin',
    '매운맛': 'spicy', 'Spicy': 'spicy',
    '현지인맛집': 'local', 'Local Gem': 'local'
};

// 테마별 포인트 컬러 (CSS 변수와 맞춰도 좋음)
export const THEME_COLORS = {
    'tonkotsu': '#e67e22', // 주황색 (진한 육수)
    'shoyu': '#845c21',    // 갈색 (간장)
    'michelin': '#f1c40f', // 노란색 (별)
    'spicy': '#e74c3c',    // 빨간색 (고추)
    'local': '#2c3e50',    // 차콜색 (로컬 상점)
    'default': '#757575'
};

// (선택 사항) 만약 라멘 추천 기능을 넣는다면 사용할 문구
export const RAMEN_RECOMMENDATIONS = [
    { title: "진한 맛!", desc: "오늘은 진한 돈코츠 어떠신가요?🐷", theme: "tonkotsu", color: "#e67e22" },
    { title: "깔끔한 맛!", desc: "맑은 쇼유 라멘이 당기는 날입니다.🥣", theme: "shoyu", color: "#845c21" },
    { title: "특별한 날!", desc: "미슐랭이 인정한 최고의 한 그릇을 찾아보세요.⭐️", theme: "michelin", color: "#f1c40f" }
];