#!/bin/bash
# 🍜 OKRamen 자동 배포 파이프라인 (Ramen + Guide + Imagen 3)
# 실행: ./deploy.sh

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMMIT_MSG="update: auto-generated ramen & guide contents $(date '+%Y-%m-%d %H:%M')"

print_step() { echo ""; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
print_err()  { echo -e "${RED}  ❌ $1${NC}"; }
print_info() { echo -e "  ℹ️  $1"; }

clear
echo ""
echo -e "${BOLD}${CYAN}  🍜  OKRamen 통합 자동 배포 파이프라인${NC}"
echo -e "  $(date '+%Y년 %m월 %d일 %H:%M:%S') 시작"
echo ""
START_TIME=$SECONDS

# ── STEP 0: 환경 체크 ──────────────────────
print_step "STEP 0 / 6  |  환경 체크"
cd "$PROJECT_ROOT"
print_info "프로젝트 경로: $PROJECT_ROOT"

[ ! -f ".env" ] && { print_err ".env 없음"; exit 1; }
print_ok ".env 확인"

grep -q "GEMINI_API_KEY" .env || { print_err "GEMINI_API_KEY 없음"; exit 1; }
print_ok "API 키 확인"

command -v python3 &>/dev/null || { print_err "python3 없음"; exit 1; }
print_ok "Python3: $(python3 --version)"
command -v gcloud  &>/dev/null || { print_err "gcloud 없음"; exit 1; }
print_ok "gcloud: $(gcloud --version | head -1)"
command -v git     &>/dev/null || { print_err "git 없음"; exit 1; }
print_ok "git: $(git --version)"

RAMEN_CSV="script/csv/ramens.csv"
GUIDE_CSV="script/csv/guides.csv"
[ ! -f "$RAMEN_CSV" ] && { print_err "라멘 CSV 없음: $RAMEN_CSV"; exit 1; }
[ ! -f "$GUIDE_CSV" ] && { print_err "가이드 CSV 없음: $GUIDE_CSV"; exit 1; }
print_ok "CSV 파일 확인 완료"

# ── STEP 1: 라멘 가게 컨텐츠 생성 ──────────
print_step "STEP 1 / 6  |  라멘 가게 컨텐츠 생성 (Gemini)"

CONTENT_DIR="app/content"
R_BEFORE_COUNT=0
[ -d "$CONTENT_DIR" ] && R_BEFORE_COUNT=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
print_info "생성 전 가게 컨텐츠: ${R_BEFORE_COUNT}개"

python3 script/ramen_generator.py

R_AFTER_COUNT=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
R_NEW_COUNT=$(( R_AFTER_COUNT - R_BEFORE_COUNT ))
print_ok "가게 컨텐츠 생성 완료! (총 ${R_AFTER_COUNT}개, 신규 +${R_NEW_COUNT}개)"

# ── STEP 2: 라멘 가이드 생성 (신규 추가) ───
print_step "STEP 2 / 6  |  라멘 가이드 생성 (Gemini SEO)"

GUIDE_DIR="app/content/guides"
mkdir -p "$GUIDE_DIR"
G_BEFORE_COUNT=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')
print_info "생성 전 가이드: ${G_BEFORE_COUNT}개"

python3 script/guide_generator.py

G_AFTER_COUNT=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')
G_NEW_COUNT=$(( G_AFTER_COUNT - G_BEFORE_COUNT ))
print_ok "가이드 생성 완료! (총 ${G_AFTER_COUNT}개, 신규 +${G_NEW_COUNT}개)"

# ── STEP 3: AI 이미지 생성 (Imagen 3) ───────
print_step "STEP 3 / 6  |  라멘 이미지 생성 (Google Imagen 3)"

IMAGES_DIR="app/static/images"
MISSING=0
if [ -d "$CONTENT_DIR" ]; then
    for md_file in "$CONTENT_DIR"/*.md; do
        [ -f "$md_file" ] || continue
        base=$(basename "$md_file" .md)
        safe=${base%_ko}; safe=${safe%_en}
        if [ ! -f "${IMAGES_DIR}/${safe}.jpg" ] && \
           [ ! -f "${IMAGES_DIR}/${safe}.jpeg" ] && \
           [ ! -f "${IMAGES_DIR}/${safe}.png" ]; then
            MISSING=$((MISSING + 1))
        fi
    done
    MISSING=$(( MISSING / 2 ))
fi

if [ "$MISSING" -eq 0 ]; then
    print_ok "모든 라멘 이미지 존재 → 스킵"
else
    print_info "이미지 없는 라멘집: ${MISSING}개 → Imagen 3 생성 시작"
    print_info "예상 비용: 약 \$$(echo "scale=2; $MISSING * 0.04" | bc)"
    echo ""
    python3 script/generate_images.py
    print_ok "이미지 생성 완료"
    print_info "이미지 최적화 중..."
    python3 script/optimize_images.py
    print_ok "이미지 최적화 완료"
fi

# 변경 사항 체크 (가게, 가이드, 이미지 모두 확인)
TOTAL_NEW=$(( R_NEW_COUNT + G_NEW_COUNT ))
if [ "$TOTAL_NEW" -eq 0 ] && [ "$MISSING" -eq 0 ]; then
    print_warn "새로 생성된 컨텐츠/이미지가 없습니다."
    echo ""
    read -p "  그래도 계속 배포하시겠습니까? (y/N): " -n 1 -r
    echo ""
    [[ ! $REPLY =~ ^[Yy]$ ]] && { print_info "배포 취소"; exit 0; }
fi

# ── STEP 4: Git Push & 데이터 빌드 ─────────
print_step "STEP 4 / 6  |  데이터 빌드 및 GitHub Push"

print_info "ramen_data.json 빌드 중..."
python3 script/build_data.py

GIT_STATUS=$(git status --porcelain)
if [ -z "$GIT_STATUS" ]; then
    print_warn "GitHub 변경 사항 없음 → 건너뜀"
else
    print_info "변경된 파일: $(echo "$GIT_STATUS" | wc -l | tr -d ' ')개"
    git add .
    git commit -m "$COMMIT_MSG"
    git push origin main
    print_ok "GitHub push 완료"
fi

# ── STEP 5: GCS 이미지 동기화 & 배포 ────────
print_step "STEP 5 / 6  |  GCS 업로드 및 Cloud Run 배포"

print_info "GCS 이미지 동기화 중..."
gsutil -m rsync -d app/static/images gs://ok-project-assets/okramen
print_ok "GCS 업로드 완료"

echo ""
print_info "Cloud Build 시작 (약 3~5분 소요)..."
gcloud builds submit
print_ok "Cloud Run 배포 완료"

# ── STEP 6: 완료 요약 ──────────────────────
print_step "STEP 6 / 6  |  최종 요약"

ELAPSED=$(( SECONDS - START_TIME ))
echo ""
echo -e "${BOLD}${GREEN}  🎉 모든 프로세스가 성공적으로 완료되었습니다!${NC}"
echo ""
echo -e "  ⏱️  총 소요 시간  : $(( ELAPSED / 60 ))분 $(( ELAPSED % 60 ))초"
echo -e "  🍜 신규 가게 추가 : ${R_NEW_COUNT}개 (전체 ${R_AFTER_COUNT}개)"
echo -e "  📖 신규 가이드    : ${G_NEW_COUNT}개 (전체 ${G_AFTER_COUNT}개)"
echo -e "  🖼️  생성된 이미지 : ${MISSING}개  (약 \$$(echo "scale=2; $MISSING * 0.04" | bc))"
echo -e "  🌐 라이브 사이트  : https://okramen.net"
echo ""

# Mac 알림 센터 전송
osascript -e 'display notification "배포 완료! 가게 '"$R_NEW_COUNT"'개, 가이드 '"$G_NEW_COUNT"'개 추가" with title "OKRamen 파이프라인"' 2>/dev/null || true
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""