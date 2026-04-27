#!/bin/bash
# 🍜 OKRamen deployment helper script (option style)

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMMIT_MSG="update: auto-generated ramen & guide contents $(date '+%Y-%m-%d %H:%M') (Admin Sync)"
BUCKET_URL="${BUCKET_URL:-gs://ok-project-assets/okramen}"
IMAGES_DIR="app/static/images"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-starful-258005}"

MODE="full"
DO_GIT=false
DO_CLOUD_DEPLOY=false
CONTENT_LIMIT="${CONTENT_LIMIT:-10}"
GUIDE_LIMIT="${GUIDE_LIMIT:-3}"

CONTENT_DIR="app/content"
GUIDE_DIR="app/content/guides"
R_NEW_COUNT=0
G_NEW_COUNT=0
MISSING=0

print_step() { echo ""; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
print_err()  { echo -e "${RED}  ❌ $1${NC}"; }
print_info() { echo -e "  ℹ️  $1"; }

usage() {
    cat <<'EOF'
Usage: ./deploy.sh [MODE] [OPTIONS]

Modes (default: full)
  --full           Sync images + generate content + image process + build + upload
  --content-only   Generate ramen/guide markdown + build JSON only
  --deploy-only    Trigger Cloud Build deploy only

Options
  --with-git       Commit and push generated changes
  --with-deploy    Trigger deploy after selected mode
  --help           Show this help

Environment overrides
  BUCKET_URL       Default: gs://ok-project-assets/okramen
  GCP_PROJECT_ID   Default: starful-258005
  CONTENT_LIMIT    Default: 10
  GUIDE_LIMIT      Default: 3
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        print_err "Missing required command: $1"
        exit 1
    fi
}

check_env() {
    print_step "STEP 0  |  환경 체크"
    [ ! -f ".env" ] && { print_err ".env 없음"; exit 1; }
    grep -q "GEMINI_API_KEY" .env || { print_err "GEMINI_API_KEY 없음"; exit 1; }
    print_ok ".env / API 키 확인"
}

sync_cloud_images_to_local() {
    print_step "STEP A  |  GCS 최신 이미지 가져오기"
    mkdir -p "$IMAGES_DIR"
    print_info "클라우드($BUCKET_URL) -> 로컬($IMAGES_DIR) 동기화 중..."
    gsutil -m rsync -r "$BUCKET_URL" "$IMAGES_DIR"
    print_ok "최신 이미지 동기화 완료 (관리자 업로드분 보호됨)"
}

generate_content() {
    print_step "STEP B  |  라멘/가이드 컨텐츠 생성"

    local r_before_count=0
    [ -d "$CONTENT_DIR" ] && r_before_count=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
    print_info "생성 전 가게 컨텐츠: ${r_before_count}개"
    python3 script/ramen_generator.py "$CONTENT_LIMIT"
    local r_after_count
    r_after_count=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
    R_NEW_COUNT=$(( r_after_count - r_before_count ))
    print_ok "가게 컨텐츠 생성 완료 (총 ${r_after_count}개, 신규 +${R_NEW_COUNT}개)"

    mkdir -p "$GUIDE_DIR"
    local g_before_count
    g_before_count=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')
    print_info "생성 전 가이드: ${g_before_count}개"
    python3 script/guide_generator.py "$GUIDE_LIMIT"
    local g_after_count
    g_after_count=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')
    G_NEW_COUNT=$(( g_after_count - g_before_count ))
    print_ok "가이드 생성 완료 (총 ${g_after_count}개, 신규 +${G_NEW_COUNT}개)"
}

generate_or_optimize_images() {
    print_step "STEP C  |  라멘 이미지 생성/최적화"
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
        print_ok "모든 라멘 이미지 존재 (또는 관리자 사진) → 생성 스킵"
    else
        print_info "이미지 없는 라멘집: ${MISSING}개 → Imagen 3 생성 시작"
        python3 script/generate_images.py
        print_ok "이미지 생성 완료"
    fi

    print_info "이미지 최적화 중..."
    python3 script/optimize_images.py
    print_ok "이미지 최적화 완료"
}

build_data() {
    print_step "STEP D  |  ramen_data.json 빌드"
    python3 script/build_data.py
    print_ok "데이터 빌드 완료"
}

upload_images_to_gcs() {
    print_step "STEP E  |  GCS 이미지 최종 업로드"
    gsutil -m rsync -r "$IMAGES_DIR" "$BUCKET_URL"
    print_ok "GCS 업로드 완료"
}

git_push_changes() {
    print_step "STEP F  |  GitHub Push"
    git add .
    if ! git diff-index --quiet HEAD --; then
        git commit -m "$COMMIT_MSG"
        git push origin main
        print_ok "GitHub push 완료"
    else
        print_warn "GitHub 변경 사항 없음"
    fi
}

deploy_cloud_run() {
    print_step "STEP G  |  Cloud Build & Deploy"
    gcloud builds submit --project "$GCP_PROJECT_ID"
    print_ok "Cloud Run 배포 완료"
}

for arg in "$@"; do
    case "$arg" in
        --full) MODE="full" ;;
        --content-only) MODE="content-only" ;;
        --deploy-only) MODE="deploy-only" ;;
        --with-git) DO_GIT=true ;;
        --with-deploy) DO_CLOUD_DEPLOY=true ;;
        --help|-h) usage; exit 0 ;;
        *)
            print_err "Unknown argument: $arg"
            usage
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"
START_TIME=$SECONDS

clear
echo ""
echo -e "${BOLD}${CYAN}  🍜  OKRamen 옵션형 배포 파이프라인${NC}"
echo -e "  $(date '+%Y년 %m월 %d일 %H:%M:%S') 시작"
echo ""
print_info "Mode: $MODE"
print_info "Bucket: $BUCKET_URL"
print_info "Project: $GCP_PROJECT_ID"
print_info "Limits: content=${CONTENT_LIMIT}, guide=${GUIDE_LIMIT}"

check_env
require_cmd python3
require_cmd gcloud

case "$MODE" in
    full)
        require_cmd gsutil
        sync_cloud_images_to_local
        generate_content
        generate_or_optimize_images
        build_data
        upload_images_to_gcs
        ;;
    content-only)
        generate_content
        build_data
        ;;
    deploy-only)
        DO_CLOUD_DEPLOY=true
        ;;
esac

if [ "$DO_GIT" = true ]; then
    require_cmd git
    git_push_changes
fi

if [ "$DO_CLOUD_DEPLOY" = true ]; then
    deploy_cloud_run
fi

ELAPSED=$(( SECONDS - START_TIME ))
print_step "DONE  |  최종 요약"
echo -e "${BOLD}${GREEN}  🎉 배포 스크립트 실행 완료${NC}"
echo -e "  ⏱️  총 소요 시간  : $(( ELAPSED / 60 ))분 $(( ELAPSED % 60 ))초"
echo -e "  🍜 신규 가게 추가 : ${R_NEW_COUNT}개"
echo -e "  📖 신규 가이드    : ${G_NEW_COUNT}개"
echo -e "  🖼️  새로 생성된 AI 이미지 : ${MISSING}개"
echo -e "  🌐 라이브 사이트  : https://okramen.net"
echo ""

if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e 'display notification "배포 완료!" with title "OKRamen Deploy"' 2>/dev/null || true
fi