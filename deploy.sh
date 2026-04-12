#!/bin/bash
# 🍜 OKRamen 자동 배포 파이프라인 (Imagen 3 이미지 생성 포함)
# 실행: ./deploy.sh

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMMIT_MSG="update: auto-generated ramen contents $(date '+%Y-%m-%d %H:%M')"

print_step() { echo ""; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
print_err()  { echo -e "${RED}  ❌ $1${NC}"; }
print_info() { echo -e "  ℹ️  $1"; }

clear
echo ""
echo -e "${BOLD}${CYAN}  🍜  OKRamen 자동 배포 파이프라인${NC}"
echo -e "  $(date '+%Y년 %m월 %d일 %H:%M:%S') 시작"
echo ""
START_TIME=$SECONDS

# ── STEP 0: 환경 체크 ──────────────────────
print_step "STEP 0 / 5  |  환경 체크"
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

CSV_PATH="script/csv/ramens.csv"
[ ! -f "$CSV_PATH" ] && { print_err "CSV 없음: $CSV_PATH"; exit 1; }
CSV_COUNT=$(( $(wc -l < "$CSV_PATH") - 1 ))
print_ok "라멘 CSV: 총 ${CSV_COUNT}개"

# ── STEP 1: AI 컨텐츠 생성 (Gemini) ────────
print_step "STEP 1 / 5  |  AI 컨텐츠 생성 (Gemini API)"

CONTENT_DIR="app/content"
BEFORE_COUNT=0
[ -d "$CONTENT_DIR" ] && BEFORE_COUNT=$(find "$CONTENT_DIR" -name "*.md" | wc -l | tr -d ' ')
print_info "생성 전 컨텐츠: ${BEFORE_COUNT}개"

python3 script/ramen_generator.py

AFTER_COUNT=$(find "$CONTENT_DIR" -name "*.md" | wc -l | tr -d ' ')
NEW_COUNT=$(( AFTER_COUNT - BEFORE_COUNT ))
print_ok "컨텐츠 생성 완료! (총 ${AFTER_COUNT}개, 신규 +${NEW_COUNT}개)"

# ── STEP 2: AI 이미지 생성 (Imagen 3) ───────
print_step "STEP 2 / 5  |  AI 이미지 생성 (Google Imagen 3)"

# MD 기준으로 이미지 없는 항목 수 확인
IMAGES_DIR="app/static/images"
MISSING=0
if [ -d "$CONTENT_DIR" ]; then
    for md_file in "$CONTENT_DIR"/*.md; do
        [ -f "$md_file" ] || continue
        base=$(basename "$md_file" .md)
        # _ko, _en suffix 제거
        safe=${base%_ko}; safe=${safe%_en}; safe=${safe%_ja}
        if [ ! -f "${IMAGES_DIR}/${safe}.jpg" ] && \
           [ ! -f "${IMAGES_DIR}/${safe}.jpeg" ] && \
           [ ! -f "${IMAGES_DIR}/${safe}.png" ]; then
            MISSING=$((MISSING + 1))
        fi
    done
    # 중복 제거를 위해 2로 나눔 (ko/en 두 파일이 같은 이미지를 가리키므로)
    MISSING=$(( MISSING / 2 ))
fi

if [ "$MISSING" -eq 0 ]; then
    print_ok "모든 이미지 존재 → 스킵"
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

if [ "$NEW_COUNT" -eq 0 ] && [ "$MISSING" -eq 0 ]; then
    print_warn "새로 생성된 컨텐츠/이미지가 없습니다."
    echo ""
    read -p "  그래도 계속 배포하시겠습니까? (y/N): " -n 1 -r
    echo ""
    [[ ! $REPLY =~ ^[Yy]$ ]] && { print_info "취소"; exit 0; }
fi

# ── STEP 3: Git Push ───────────────────────
print_step "STEP 3 / 5  |  GitHub Push"

GIT_STATUS=$(git status --porcelain)
if [ -z "$GIT_STATUS" ]; then
    print_warn "변경 없음 → 건너뜀"
else
    print_info "변경된 파일: $(echo "$GIT_STATUS" | wc -l | tr -d ' ')개"
    git add .
    git commit -m "$COMMIT_MSG"
    git push origin main
    print_ok "GitHub push 완료"
fi

# ── STEP 3.5: GCS 이미지 동기화 ────────────────
print_step "STEP 3.5 | GCS 이미지 업로드"
# 로컬의 images 폴더를 GCS 버킷과 동기화 (새로 생긴 파일만 업로드)
gsutil -m rsync -d app/static/images gs://ok-project-assets/okramen
print_ok "GCS 업로드 완료"

# ── STEP 4: Cloud Build & Cloud Run ───────
print_step "STEP 4 / 5  |  Cloud Build & Cloud Run 배포"
print_info "약 3~5분 소요됩니다..."
echo ""
gcloud builds submit
print_ok "Cloud Run 배포 완료"

# ── STEP 5: 완료 요약 ──────────────────────
print_step "STEP 5 / 5  |  완료 요약"

ELAPSED=$(( SECONDS - START_TIME ))
echo ""
echo -e "${BOLD}${GREEN}  🎉 전체 파이프라인 완료!${NC}"
echo ""
echo -e "  ⏱️  총 소요 시간  : $(( ELAPSED / 60 ))분 $(( ELAPSED % 60 ))초"
echo -e "  🖼️  생성된 이미지 : ${MISSING}개  (약 \$$(echo "scale=2; $MISSING * 0.04" | bc))"
echo -e "  📄 전체 컨텐츠   : ${AFTER_COUNT}개 (신규 +${NEW_COUNT}개)"
echo -e "  🌐 라이브 사이트 : https://okramen.net"
echo ""

osascript -e 'display notification "배포가 완료되었습니다! 🎉" with title "OKRamen 파이프라인"' 2>/dev/null || true
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
