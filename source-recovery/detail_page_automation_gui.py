from __future__ import annotations

import base64
import copy
import itertools
import json
import hashlib
import hmac
import html
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from openpyxl import load_workbook

try:
    import keyring
except Exception:  # pragma: no cover - keeps the GUI usable if keyring is missing
    keyring = None

try:
    import bcrypt
except Exception:  # pragma: no cover - live Naver API upload will report this clearly
    bcrypt = None

try:
    import requests
except Exception:  # pragma: no cover - live marketplace calls will report this clearly
    requests = None


APP_TITLE = "상세페이지 자동화 GUI"
APP_VERSION = "0.1"
DEFAULT_THEME = "dark"
GPT_URL = "https://chatgpt.com/g/g-69ca98c6b4308191abf5d1b33aac6c5e-sangaggeo-sangsepeiji-meikeo-kr"
CHATGPT_HOME_URL = "https://chatgpt.com/"
GPT_NAME = "상세페이지 메이커 KR"
ALI_1688_LOGIN_URL = "https://login.1688.com/member/signin.htm"
GPT_PUBLIC_DESCRIPTION = "상세페이지 섹션 1~10에 설득·입증·구매결정·행동유도까지 통합 설계합니다."
GPT_PROMPT_STARTERS = [
    "좋은 섹션 다 통합해서 짜줘",
    "섹션 1~10까지 설계해줘",
    "히어로 훅 5안도 같이 줘",
    "자동화용 section_key까지 병기해줘",
]

ROOT_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
USER_CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "SangsapageAutomation"
CONFIG_PATH = USER_CONFIG_DIR / "detail_page_gui_config.json"
MARKET_SECRET_FALLBACK_PATH = USER_CONFIG_DIR / "market_secrets.json"
OUTPUT_DIR = Path.home() / "Desktop" / "상세페이지_자동화_결과"
COMPLETED_DIR = OUTPUT_DIR / "완료된폴더"
REQUIRED_SECTION_IMAGE_COUNT = 10
REQUIRED_THUMBNAIL_IMAGE_COUNT = 5
MANUAL_SECTION_BUTTON_COUNT = 10
GPT_ATTACHMENT_IMAGE_LIMIT = 10
GPT_ATTACHMENT_DOMESTIC_IMAGE_LIMIT = 5
GPT_ATTACHMENT_1688_IMAGE_LIMIT = 5
GPT_ATTACHMENT_DOMESTIC_THUMBNAIL_LIMIT = 4
MIN_SOURCE_IMAGE_COUNT = 6
CHATGPT_IMAGE_REQUEST_MAX_ATTEMPTS = 1
CHATGPT_RETRY_GRACE_SECONDS = 1200
CHATGPT_IMAGE_WAIT_TIMEOUT_SECONDS = 180
CHATGPT_THUMBNAIL_ACTIVE_WAIT_EXTENSION_SECONDS = 180
CHATGPT_SECTION_IMAGE_SAVE_DELAY_SECONDS = 180
CHATGPT_SECTION_IMAGE_RELOAD_RETRY_LIMIT = 3
CHATGPT_THUMBNAIL_IMAGE_RETRY_LIMIT = 3
CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS = 210
CHATGPT_SECTION_PLAN_BUSY_MAX_WAIT_SECONDS = 1200
CHATGPT_SECTION_PLAN_STATUS_UPDATE_SECONDS = 1
CHATGPT_SECTION_PLAN_RETRY_WAIT_TIMEOUT_SECONDS = 210
CHATGPT_SECTION_PLAN_MARKER_SETTLE_SECONDS = 180
KEYRING_SERVICE = "detail_page_automation_gui.chatgpt"
MARKET_KEYRING_SERVICE = "detail_page_automation_gui.market"
CODEX_IMAGE_RENDER_MODE = "codex_generated_visuals"
PRODUCTION_RENDER_MODE = "gpt_copy_source_detail_render"
PRODUCTION_RENDERER_MODEL = "source-image-detail-renderer-v3"
LATEST_CODEX_IMAGE_MODEL = "gpt-image-2"
CHATGPT_WEB_IMAGE_MODEL = "chatgpt_web_image_generation"
CHATGPT_IMAGE_MODEL_ALIAS = "chatgpt-image-latest"
LATEST_CODEX_IMAGE_SIZE = "1024x1536"
THUMBNAIL_IMAGE_SIZE = "1000x1000"
THUMBNAIL_STYLE_VERSION = "marketplace-square-real-reference-v10-clean-two-ref-20260525"
DETAIL_PIPELINE_VERSION = "detail-page-first-gpt-plan-native-visuals-20260512d-full-section-prompt"
DETAIL_REVIEW_SECTION_KEY = "review_points"
DETAIL_REVIEW_SECTION_STYLE_VERSION = "masked-review-points-v1-20260513"
MARKET_DRAFT_VERSION = "market-draft-naver-coupang-v2-20260513"
COUPANG_ANIMATED_WEBP_WIDTH = 780
COUPANG_ANIMATED_WEBP_MAX_BYTES = 8_000_000
COUPANG_ANIMATED_WEBP_FRAME_COUNT = 18
COUPANG_ANIMATED_WEBP_FRAME_DURATION_MS = 110
DEFAULT_MARKET_BRAND = "끄롱마제"
DEFAULT_MARKET_MANUFACTURER = "중국OEM"
LEGACY_MARKET_MANUFACTURER = "끄롱마제"
DEFAULT_TARGET_NET_MARGIN_RATE = "20"
DEFAULT_NAVER_FEE_RATE = "10"
DEFAULT_COUPANG_FEE_RATE = "10"
DEFAULT_MARKET_TAX_RATE = "10"
DEFAULT_MARKET_OTHER_FEE_RATE = "0"
DEFAULT_PRICE_ROUND_UNIT = "100"
LOW_COST_DELIVERY_THRESHOLD = 10000
LOW_COST_DELIVERY_FEE = 3000
LEGACY_TARGET_NET_MARGIN_RATE = "25"
LEGACY_NAVER_FEE_RATE = "6.2"
LEGACY_COUPANG_FEE_RATE = "10.8"
COUPANG_PRODUCT_NAME_LIMIT = 100
ENABLE_THUMBNAIL_ONLY_REFRESH = False
BRAND_LOGO_REFERENCE_DIR_NAME = "branded_references"
BRAND_LOGO_MANIFEST_VERSION = "brand-logo-references-v1-20260629"
BRAND_LOGO_FILE_CANDIDATES = (
    USER_CONFIG_DIR / "brand_logo.png",
    Path.home() / "Downloads" / "KakaoTalk_20260609_053054524.png",
)
SECONDARY_1688_USAGE_NOTE = "1688은 상품 이미지/외형/옵션 사진 참고 전용이며 배송·통관·반품·A/S 정책 문구는 사용하지 않음"
DETAIL_COPY_POLICY_MARKERS = (
    "해외직배송",
    "개인통관",
    "개인통관고유부호",
    "통관",
    "반품/교환",
    "반품 / 교환",
    "왕복 해외배송비",
    "국제배송",
    "현지배송",
    "7~13일",
    "주문 확인 후",
    "A/S 제한",
)
NAVER_TOKEN_ENDPOINT = "https://api.commerce.naver.com/external/v1/oauth2/token"
NAVER_PRODUCT_CREATE_ENDPOINT = "https://api.commerce.naver.com/external/v2/products"
NAVER_ORIGIN_PRODUCT_ENDPOINT_TEMPLATE = NAVER_PRODUCT_CREATE_ENDPOINT + "/origin-products/{originProductNo}"
NAVER_IMAGE_UPLOAD_ENDPOINT = "https://api.commerce.naver.com/external/v1/product-images/upload"
NAVER_CATEGORY_LIST_ENDPOINT = "https://api.commerce.naver.com/external/v1/categories"
NAVER_ADDRESSBOOKS_ENDPOINT = "https://api.commerce.naver.com/external/v1/seller/addressbooks-for-page"
NAVER_ORIGIN_AREAS_ENDPOINT = "https://api.commerce.naver.com/external/v1/product-origin-areas"
NAVER_RECOMMEND_TAGS_ENDPOINT = "https://api.commerce.naver.com/external/v2/tags/recommend-tags"
NAVER_ATTRIBUTE_LIST_ENDPOINT = "https://api.commerce.naver.com/external/v1/product-attributes/attributes"
NAVER_ATTRIBUTE_VALUE_LIST_ENDPOINT = "https://api.commerce.naver.com/external/v1/product-attributes/attribute-values"
COUPANG_PRODUCT_CREATE_PATH = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
COUPANG_CATEGORY_RECOMMENDATION_PATH = "/v2/providers/openapi/apis/api/v1/categorization/predict"
COUPANG_CATEGORY_META_PATH_TEMPLATE = (
    "/v2/providers/seller_api/apis/api/v1/marketplace/meta/category-related-metas/display-category-codes/{displayCategoryCode}"
)
COUPANG_OUTBOUND_SHIPPING_PLACES_PATH = "/v2/providers/marketplace_openapi/apis/api/v2/vendor/shipping-place/outbound"
COUPANG_RETURN_SHIPPING_CENTERS_PATH_TEMPLATE = (
    "/v2/providers/openapi/apis/api/v5/vendors/{vendorId}/returnShippingCenters"
)
COUPANG_API_BASE_URL = "https://api-gateway.coupang.com"
AUTO_LOOKUP_PREFIX = "AUTO_LOOKUP_REQUIRED:"
LOCAL_IMAGE_URL_PREFIX = "local-file://"
ENABLE_CHATGPT_WEB_IMAGE_GENERATION = True
REQUIRE_GENERATED_SECTION_IMAGES = True
SECTION_DISPLAY_NAMES = {
    "hero": "히어로",
    "empathy": "공감",
    "solution": "솔루션",
    "benefits": "특징·혜택",
    "how_to_use": "사용법",
    "trust": "신뢰요소",
    "cta": "구매유도",
    DETAIL_REVIEW_SECTION_KEY: "리뷰형 만족 포인트",
}


def slugify(value: str, fallback: str = "detail_page") -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", value.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = cleaned.strip("._")
    return cleaned or fallback


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@dataclass
class ProductBrief:
    product_name: str
    category: str
    platform: str
    target_customer: str
    price_range: str
    tone: str
    product_url: str
    key_features: str
    proof_points: str
    differentiation: str
    usage_context: str
    caution: str
    image_paths: str
    reference_notes: str


@dataclass
class LinkTask:
    row_number: int
    url: str
    secondary_url: str = ""
    status: str = "대기"


@dataclass
class ProductRecord:
    index: int
    url: str
    secondary_url: str
    code: str
    product_name: str
    title: str
    category: str
    price_text: str
    options_text: str
    facts: list[str]
    source_text: str
    image_urls: list[str]
    source_image_paths: list[Path]
    output_dir: Path
    source_payloads: list[dict[str, object]] = field(default_factory=list)


@dataclass
class SectionPlan:
    section_key: str
    section_name: str
    headline: str
    subheadline: str
    body: str
    bullets: list[str]
    image_prompt: str = ""
    overlay_text: str = ""
    source_section_text: str = ""


@dataclass
class RenderResult:
    section_paths: list[Path]
    detail_page_path: Path
    visual_paths: list[Path] = field(default_factory=list)
    render_mode: str = "local_render"
    image_model: str = ""


@dataclass
class ThumbnailResult:
    paths: list[Path]
    prompt_paths: list[Path]
    image_model: str = ""


@dataclass
class MarketProduct:
    code: str
    folder: Path
    product_name: str
    detail_page_path: Path
    thumbnail_paths: list[Path]
    metadata: dict[str, object]
    source: dict[str, object]
    result_text: str
    naver_status: str = "미생성"
    coupang_status: str = "미생성"
    review_status: str = "초안 필요"
    issues: list[str] = field(default_factory=list)


class AutomationStopRequested(RuntimeError):
    pass


class AutomationSkipRequested(RuntimeError):
    pass


class AutomationBrowserDisconnected(RuntimeError):
    pass


class ThumbnailGenerationFailed(RuntimeError):
    pass


class AutomationSignals(QObject):
    status = Signal(str)
    login_status = Signal(str)
    task_status = Signal(int, str)
    result = Signal(str)
    finished = Signal()
    login_finished = Signal()


class DetailPageGui(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.resize(1280, 900)
        self.setMinimumSize(1120, 760)

        self.fields: dict[str, QLineEdit | QTextEdit | QComboBox] = {}
        self.prompt_box = QTextEdit()
        self.result_box = QTextEdit()
        self.link_table = QTableWidget()
        self.link_status_label = QLabel("엑셀을 불러오면 URL 작업 목록이 여기에 표시됩니다.")
        self.main_tabs = QTabWidget()
        self.market_table = QTableWidget()
        self.market_status_label = QLabel("완료폴더를 스캔하면 등록 후보가 여기에 표시됩니다.")
        self.market_preview_label = QLabel("상품을 선택하면 detail_page.png와 썸네일 상태를 표시합니다.")
        self.market_payload_box = QTextEdit()
        self.market_auto_status_label = QLabel("")
        self.market_price_banner_label = QLabel("판매가 산출: 완료폴더를 스캔하고 상품을 선택하면 표시됩니다.")
        self.market_settings_status_label = QLabel("마켓 설정 저장됨")
        self.market_products: list[MarketProduct] = []
        self.current_market_index = -1
        self.market_fields: dict[str, QLineEdit | QComboBox] = {}
        self.market_secret_keys: set[str] = set()
        self.market_resolved_settings: dict[str, str] = {}
        self.login_email_field = QLineEdit()
        self.login_password_field = QLineEdit()
        self.login_status_label = QLabel("1. 로그인으로 자동화 Chrome을 열고 직접 로그인하세요.")
        self.link_tasks: list[LinkTask] = []
        self.current_link_index = -1
        self.current_product_url = ""
        self.excel_path = ""
        self.brand_logo_path = ""
        self.brand_logo_status_label = QLabel("로고 미선택")
        self.automation_running = False
        self.automation_stop_requested = False
        self.automation_skip_requested = False
        self.manual_resume_request: dict[str, object] | None = None
        self.active_manual_resume_request: dict[str, object] | None = None
        self.login_running = False
        self.image_wait_tick = 0
        self.image_wait_timer = QTimer(self)
        self.image_wait_timer.setInterval(5000)
        self.image_wait_timer.timeout.connect(self._refresh_image_wait_animation)
        self.market_autosave_timer = QTimer(self)
        self.market_autosave_timer.setSingleShot(True)
        self.market_autosave_timer.setInterval(900)
        self.market_autosave_timer.timeout.connect(self._autosave_market_settings)
        self.automation_signals = AutomationSignals()
        self.automation_signals.status.connect(self._set_status)
        self.automation_signals.login_status.connect(self._set_login_panel_status)
        self.automation_signals.task_status.connect(self._set_task_status)
        self.automation_signals.result.connect(self._append_result_text)
        self.automation_signals.finished.connect(self._automation_finished)
        self.automation_signals.login_finished.connect(self._login_finished)
        self.theme = DEFAULT_THEME
        self.theme_action: QAction | None = None
        self.theme_btn: QPushButton | None = None
        self._startup_fast_load = True

        self._build_ui()
        self._ensure_output_dirs()
        self._load_config(silent=True)
        self._sync_brand_logo_status_label()
        self._load_market_secrets_from_keyring()
        self._apply_style()
        self._refresh_prompt()
        self._startup_fast_load = False

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(12)
        self.setCentralWidget(root)

        header = self._build_header()
        root_layout.addWidget(header)

        login_panel = self._build_login_panel()
        root_layout.addWidget(login_panel, 0)

        link_panel = self._build_link_panel()
        market_panel = self._build_market_panel()
        self.main_tabs.addTab(link_panel, "URL 작업")
        self.main_tabs.addTab(market_panel, "마켓 등록")
        root_layout.addWidget(self.main_tabs, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("준비됨")

        self._build_menu()
        self._apply_style()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("파일")

        save_action = QAction("입력 저장", self)
        save_action.triggered.connect(self._save_config)
        file_menu.addAction(save_action)

        load_action = QAction("입력 불러오기", self)
        load_action.triggered.connect(lambda: self._load_config(silent=False))
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        excel_action = QAction("엑셀 URL 불러오기", self)
        excel_action.triggered.connect(self._load_excel_links)
        file_menu.addAction(excel_action)

        file_menu.addSeparator()

        exit_action = QAction("닫기", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("보기")
        self.theme_action = QAction("", self)
        self.theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.theme_action)
        self._sync_theme_controls()

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Header")
        layout = QGridLayout(frame)
        layout.setContentsMargins(22, 16, 18, 16)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        title = QLabel(APP_TITLE)
        title.setObjectName("Title")
        subtitle = QLabel(f"연결 GPT: {GPT_NAME}")
        subtitle.setObjectName("Subtitle")
        evidence = QLabel(f"공개 설명: {GPT_PUBLIC_DESCRIPTION}")
        evidence.setObjectName("Evidence")
        evidence.setWordWrap(True)
        starter = QLabel("시작 문구: " + " · ".join(GPT_PROMPT_STARTERS))
        starter.setObjectName("Evidence")
        starter.setWordWrap(True)

        self.theme_btn = QPushButton()
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._sync_theme_controls()

        layout.addWidget(title, 0, 0, 1, 3)
        layout.addWidget(subtitle, 1, 0, 1, 3)
        layout.addWidget(evidence, 2, 0, 1, 3)
        layout.addWidget(starter, 3, 0, 1, 3)
        layout.addWidget(self.theme_btn, 0, 3)
        layout.setColumnStretch(0, 1)

        return frame

    def _build_login_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        title = QLabel("ChatGPT 로그인")
        title.setObjectName("SectionTitle")
        self.login_status_label.setObjectName("LoginStatus")

        login_btn = QPushButton("1. 로그인")
        login_btn.setObjectName("PrimaryButton")
        login_btn.clicked.connect(self._open_manual_login)

        done_btn = QPushButton("2. 로그인 완료")
        done_btn.clicked.connect(self._start_login_check)
        ali_login_btn = QPushButton("1688 로그인")
        ali_login_btn.clicked.connect(self._open_1688_login)
        source_login_btn = QPushButton("상품 URL 로그인")
        source_login_btn.clicked.connect(self._open_selected_product_login)

        layout.addWidget(title, 0, 0)
        layout.addWidget(self.login_status_label, 0, 1, 1, 3)
        layout.addWidget(login_btn, 0, 4)
        layout.addWidget(done_btn, 0, 5)
        layout.addWidget(ali_login_btn, 0, 6)
        layout.addWidget(source_login_btn, 0, 7)
        layout.setColumnStretch(1, 1)

        return panel

    def _build_input_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        section = QLabel("상품 입력")
        section.setObjectName("SectionTitle")
        layout.addWidget(section)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(11)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        layout.addLayout(form)

        self._add_line(form, "product_name", "상품명", "예: 저소음 무선 미니 마사지건")
        self._add_line(form, "category", "카테고리", "예: 생활가전 / 건강용품")
        self._add_combo(
            form,
            "platform",
            "판매처",
            ["쿠팡", "스마트스토어", "자사몰", "오픈마켓", "공통"],
        )
        self._add_line(form, "target_customer", "타겟 고객", "예: 장시간 앉아 일하는 직장인")
        self._add_line(form, "price_range", "가격대", "예: 2만원대")
        self._add_combo(
            form,
            "tone",
            "톤",
            ["신뢰감", "프리미엄", "실용적", "감성적", "직관적"],
        )
        self._add_line(form, "product_url", "상품 URL", "선택 입력")

        self._add_text(form, "key_features", "핵심 특징", "한 줄에 하나씩 적어주세요.")
        self._add_text(form, "proof_points", "입증 요소", "소재, 구성품, 인증, 후기 근거 등")
        self._add_text(form, "differentiation", "차별점", "경쟁 상품 대비 다른 점")
        self._add_text(form, "usage_context", "사용 상황", "언제, 어디서, 누가 쓰는지")
        self._add_text(form, "caution", "금지/주의 표현", "의학적 효능, 과장 수치 등 피할 표현")

        image_row = QHBoxLayout()
        image_box = QLineEdit()
        image_box.setPlaceholderText("제품 이미지 경로. 여러 개는 ; 로 구분합니다.")
        image_box.setMinimumHeight(38)
        self.fields["image_paths"] = image_box
        image_btn = QPushButton("이미지 추가")
        image_btn.clicked.connect(self._pick_images)
        image_row.addWidget(image_box, 1)
        image_row.addWidget(image_btn)
        form.addRow("이미지", image_row)

        self._add_text(form, "reference_notes", "참고 메모", "브랜드 방향, 상세페이지 참고 링크, 구성 요청")

        button_row = QHBoxLayout()
        make_btn = QPushButton("프롬프트 생성")
        make_btn.setObjectName("PrimaryButton")
        make_btn.clicked.connect(self._refresh_prompt)
        save_btn = QPushButton("입력 저장")
        save_btn.clicked.connect(self._save_config)
        load_btn = QPushButton("불러오기")
        load_btn.clicked.connect(lambda: self._load_config(silent=False))
        button_row.addWidget(make_btn)
        button_row.addWidget(save_btn)
        button_row.addWidget(load_btn)
        layout.addLayout(button_row)

        layout.addStretch(1)
        return panel

    def _build_output_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        prompt_header = self._small_header("현재 URL용 프롬프트")
        prompt_actions = QHBoxLayout()
        copy_btn = QPushButton("프롬프트 복사")
        copy_btn.setObjectName("PrimaryButton")
        copy_btn.clicked.connect(self._copy_prompt)
        open_btn = QPushButton("자동화 GPT 열기")
        open_btn.clicked.connect(self._open_gpt)
        prompt_actions.addStretch(1)
        prompt_actions.addWidget(open_btn)
        prompt_actions.addWidget(copy_btn)
        prompt_header.addLayout(prompt_actions)
        layout.addLayout(prompt_header)

        self.prompt_box.setObjectName("TextArea")
        self.prompt_box.setAcceptRichText(False)
        self.prompt_box.setPlaceholderText("엑셀 URL을 열면 해당 URL 기준 프롬프트가 자동으로 생성됩니다.")
        layout.addWidget(self.prompt_box, 2)

        result_header = self._small_header("GPT 결과")
        result_actions = QHBoxLayout()
        save_result_btn = QPushButton("결과 저장")
        save_result_btn.clicked.connect(self._save_result)
        clear_btn = QPushButton("결과 비우기")
        clear_btn.clicked.connect(self.result_box.clear)
        result_actions.addStretch(1)
        result_actions.addWidget(clear_btn)
        result_actions.addWidget(save_result_btn)
        result_header.addLayout(result_actions)
        layout.addLayout(result_header)

        self.result_box.setObjectName("TextArea")
        self.result_box.setAcceptRichText(False)
        self.result_box.setPlaceholderText("GPT가 만든 상세페이지 기획안을 여기에 붙여넣고 저장하세요.")
        layout.addWidget(self.result_box, 1)

        return panel

    def _build_link_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("엑셀 URL 작업 목록")
        title.setObjectName("SectionTitle")
        header_row.addWidget(title)
        header_row.addWidget(self.link_status_label, 1)

        load_btn = QPushButton("엑셀 불러오기")
        load_btn.setObjectName("PrimaryButton")
        load_btn.clicked.connect(self._load_excel_links)
        logo_btn = QPushButton("로고 선택")
        logo_btn.clicked.connect(self._pick_brand_logo)
        selected_btn = QPushButton("선택 링크 열기")
        selected_btn.clicked.connect(self._open_selected_link)
        next_btn = QPushButton("다음 링크 열기")
        next_btn.clicked.connect(self._open_next_link)
        auto_btn = QPushButton("GPT 분석+이미지 생성 실행")
        auto_btn.setObjectName("PrimaryButton")
        auto_btn.clicked.connect(self._start_gpt_analysis)
        stop_btn = QPushButton("현재 작업 중지")
        stop_btn.clicked.connect(self._request_current_task_stop)
        done_btn = QPushButton("현재 완료 표시")
        done_btn.clicked.connect(self._mark_current_done)

        header_row.addWidget(load_btn)
        header_row.addWidget(logo_btn)
        self.brand_logo_status_label.setObjectName("Evidence")
        header_row.addWidget(self.brand_logo_status_label)
        header_row.addWidget(selected_btn)
        header_row.addWidget(next_btn)
        header_row.addWidget(auto_btn)
        header_row.addWidget(stop_btn)
        header_row.addWidget(done_btn)
        layout.addLayout(header_row)

        resume_scroll = QScrollArea()
        resume_scroll.setWidgetResizable(True)
        resume_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        resume_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        resume_scroll.setMinimumHeight(54)
        resume_holder = QWidget()
        resume_row = QHBoxLayout(resume_holder)
        resume_row.setContentsMargins(0, 0, 0, 0)
        resume_row.setSpacing(8)
        resume_label = QLabel("수동 이어하기")
        resume_label.setObjectName("Evidence")
        resume_row.addWidget(resume_label)
        for section_number in range(1, MANUAL_SECTION_BUTTON_COUNT + 1):
            button = QPushButton(f"섹션 {section_number}")
            button.clicked.connect(lambda _=False, n=section_number: self._start_manual_stage("section", n))
            resume_row.addWidget(button)
        merge_btn = QPushButton("합치기")
        merge_btn.clicked.connect(lambda: self._start_manual_stage("merge", 1))
        resume_row.addWidget(merge_btn)
        for thumbnail_number in range(1, REQUIRED_THUMBNAIL_IMAGE_COUNT + 1):
            button = QPushButton(f"썸네일 {thumbnail_number}")
            button.clicked.connect(lambda _=False, n=thumbnail_number: self._start_manual_stage("thumbnail", n))
            resume_row.addWidget(button)
        resume_row.addStretch(1)
        resume_scroll.setWidget(resume_holder)
        layout.addWidget(resume_scroll)

        self.link_table.setColumnCount(5)
        self.link_table.setHorizontalHeaderLabels(["순서", "엑셀 행", "상태", "URL 바로가기", "1688 URL"])
        self.link_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.link_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.link_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.link_table.verticalHeader().setVisible(False)
        self.link_table.setAlternatingRowColors(True)
        self.link_table.setMinimumHeight(155)
        self.link_table.itemDoubleClicked.connect(lambda _: self._open_selected_link())
        header = self.link_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.link_table)

        return panel

    def _build_market_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("마켓 등록")
        title.setObjectName("SectionTitle")
        header_row.addWidget(title)
        header_row.addWidget(self.market_status_label, 1)
        self.market_settings_status_label.setObjectName("Evidence")
        header_row.addWidget(self.market_settings_status_label)

        scan_btn = QPushButton("완료폴더 스캔")
        scan_btn.setObjectName("PrimaryButton")
        scan_btn.clicked.connect(self._scan_completed_market_folder)
        save_market_btn = QPushButton("마켓 설정 저장")
        save_market_btn.setObjectName("PrimaryButton")
        save_market_btn.clicked.connect(self._save_market_settings)
        draft_btn = QPushButton("등록 초안 생성")
        draft_btn.clicked.connect(self._generate_selected_market_draft)
        upload_btn = QPushButton("이미지 업로드 준비")
        upload_btn.clicked.connect(self._prepare_selected_market_upload_manifest)
        merge_detail_btn = QPushButton("상세페이지 합치기")
        merge_detail_btn.clicked.connect(self._merge_selected_completed_sections)
        naver_btn = QPushButton("네이버 등록")
        naver_btn.clicked.connect(lambda: self._publish_selected_market("naver"))
        coupang_btn = QPushButton("쿠팡 등록")
        coupang_btn.clicked.connect(lambda: self._publish_selected_market("coupang"))

        header_row.addWidget(scan_btn)
        header_row.addWidget(save_market_btn)
        header_row.addWidget(draft_btn)
        header_row.addWidget(upload_btn)
        header_row.addWidget(merge_detail_btn)
        header_row.addWidget(naver_btn)
        header_row.addWidget(coupang_btn)
        layout.addLayout(header_row)

        settings_tabs = QTabWidget()
        settings_tabs.setObjectName("MarketSettingsTabs")

        api_tab = QWidget()
        api_grid = QGridLayout(api_tab)
        api_grid.setContentsMargins(10, 10, 10, 10)
        api_grid.setHorizontalSpacing(12)
        api_grid.setVerticalSpacing(8)
        api_help = QLabel(
            "API 키는 저장하면 다음 실행에도 유지됩니다. 쿠팡 vendorId는 Wing OPEN API 화면의 판매자 업체코드입니다."
        )
        api_help.setObjectName("Evidence")
        api_help.setWordWrap(True)
        api_grid.addWidget(api_help, 0, 0, 1, 6)
        self._add_market_line(api_grid, 1, 0, "naver_account_id", "네이버 계정ID", "판매자 계정 ID")
        self._add_market_line(api_grid, 1, 1, "naver_client_id", "네이버 client_id", "커머스 API client_id")
        self._add_market_line(api_grid, 1, 2, "naver_client_secret", "네이버 secret", "keyring 저장", secret=True)
        self._add_market_line(api_grid, 2, 0, "coupang_vendor_id", "쿠팡 vendorId", "Wing OPEN API 업체코드")
        self._add_market_line(api_grid, 2, 1, "coupang_access_key", "쿠팡 access key", "keyring 저장", secret=True)
        self._add_market_line(api_grid, 2, 2, "coupang_secret_key", "쿠팡 secret key", "keyring 저장", secret=True)
        self._add_market_combo(api_grid, 3, 0, "upload_mode", "업로드 모드", ["live"])
        self._add_market_line(api_grid, 3, 1, "coupang_category_recommendation_path", "쿠팡 카테고리API", COUPANG_CATEGORY_RECOMMENDATION_PATH)
        settings_tabs.addTab(api_tab, "API 키")

        basic_tab = QWidget()
        basic_grid = QGridLayout(basic_tab)
        basic_grid.setContentsMargins(10, 10, 10, 10)
        basic_grid.setHorizontalSpacing(12)
        basic_grid.setVerticalSpacing(8)
        basic_help = QLabel("상품명, SEO, 카테고리 후보, 옵션은 URL 수집값과 ChatGPT 결과에서 자동 생성합니다. 비어 있으면 자동값을 씁니다.")
        basic_help.setObjectName("Evidence")
        basic_help.setWordWrap(True)
        basic_grid.addWidget(basic_help, 0, 0, 1, 6)
        self._add_market_line(basic_grid, 1, 0, "naver_category_id", "네이버 카테고리", "비우면 자동 후보")
        self._add_market_line(basic_grid, 1, 1, "coupang_category_id", "쿠팡 카테고리", "비우면 자동 후보")
        self._add_market_line(basic_grid, 1, 2, "sale_price", "공통 수동 판매가", "비우면 수수료/세금 반영 20% 순익 자동 계산")
        self._add_market_line(basic_grid, 2, 0, "stock_quantity", "재고", "기본 100")
        self._add_market_line(basic_grid, 2, 1, "delivery_fee", "배송비", "예: 3000")
        self._add_market_line(basic_grid, 2, 2, "margin_rate", "목표 순익률(%)", "기본 20")
        self._add_market_line(basic_grid, 3, 0, "origin", "원산지", "비우면 중국")
        self._add_market_line(basic_grid, 3, 1, "manufacturer", "제조사", "비우면 중국OEM")
        self._add_market_line(basic_grid, 3, 2, "brand", "브랜드", "비우면 끄롱마제")
        self._add_market_line(basic_grid, 4, 0, "tax_type", "과세", "TAX 또는 FREE")
        self._add_market_line(basic_grid, 4, 1, "as_message", "A/S 문구", "상품 수령 후 판매자 문의")
        self._add_market_line(basic_grid, 4, 2, "naver_as_phone", "A/S 전화", "비우면 live 전 확인")
        self._add_market_line(basic_grid, 5, 0, "naver_sale_price", "네이버 수동 판매가", "비우면 네이버 자동 산출")
        self._add_market_line(basic_grid, 5, 1, "coupang_sale_price", "쿠팡 수동 판매가", "비우면 쿠팡 자동 산출")
        settings_tabs.addTab(basic_tab, "등록 기본값")

        delivery_tab = QWidget()
        delivery_grid = QGridLayout(delivery_tab)
        delivery_grid.setContentsMargins(10, 10, 10, 10)
        delivery_grid.setHorizontalSpacing(12)
        delivery_grid.setVerticalSpacing(8)
        delivery_help = QLabel("출고지/반품지 코드는 계정별 값입니다. API로 못 가져오면 live 등록 전에 이 칸만 채우면 됩니다.")
        delivery_help.setObjectName("Evidence")
        delivery_help.setWordWrap(True)
        delivery_grid.addWidget(delivery_help, 0, 0, 1, 6)
        self._add_market_line(delivery_grid, 1, 0, "outbound_place_code", "출고지 코드", "마켓별 코드")
        self._add_market_line(delivery_grid, 1, 1, "return_center_code", "반품지 코드", "마켓별 코드")
        self._add_market_line(delivery_grid, 1, 2, "naver_delivery_company", "네이버 택배사", "예: CJGLS")
        self._add_market_line(delivery_grid, 2, 0, "naver_origin_area_code", "네이버 원산지코드", "비우면 live 전 확인")
        self._add_market_line(delivery_grid, 2, 1, "coupang_vendor_user_id", "쿠팡 담당자ID", "vendorUserId")
        self._add_market_line(delivery_grid, 2, 2, "coupang_delivery_company_code", "쿠팡 택배사", "예: CJGLS")
        self._add_market_line(delivery_grid, 3, 0, "return_delivery_fee", "반품배송비", "예: 3000")
        self._add_market_line(delivery_grid, 3, 1, "exchange_delivery_fee", "교환배송비", "예: 6000")
        self._add_market_line(delivery_grid, 3, 2, "return_charge_name", "반품 담당자", "예: 고객센터")
        self._add_market_line(delivery_grid, 4, 0, "company_contact_number", "업체 연락처", "예: 010-0000-0000")
        self._add_market_line(delivery_grid, 4, 1, "return_zip_code", "반품 우편번호", "예: 00000")
        self._add_market_line(delivery_grid, 5, 0, "return_address", "반품 주소", "기본 반품지 주소")
        self._add_market_line(delivery_grid, 5, 1, "return_address_detail", "반품 상세주소", "상세주소")
        self._add_market_line(delivery_grid, 6, 0, "naver_delivery_fee", "네이버 배송비", "비우면 공통 배송비")
        self._add_market_line(delivery_grid, 6, 1, "coupang_delivery_fee", "쿠팡 배송비", "비우면 공통 배송비")
        settings_tabs.addTab(delivery_tab, "배송/반품")

        auto_tab = QWidget()
        auto_layout = QVBoxLayout(auto_tab)
        auto_layout.setContentsMargins(10, 10, 10, 10)
        auto_layout.setSpacing(8)
        auto_help = QLabel(
            "옵션은 기본적으로 ownerclan/도매꾹/1688 수집값에서 자동 생성합니다. "
            "상품 페이지에 옵션이 안 잡힌 경우에만 아래 칸에 직접 규칙을 넣습니다."
        )
        auto_help.setObjectName("Evidence")
        auto_help.setWordWrap(True)
        auto_layout.addWidget(auto_help)
        auto_grid = QGridLayout()
        auto_grid.setHorizontalSpacing(12)
        auto_grid.setVerticalSpacing(8)
        self._add_market_line(auto_grid, 0, 0, "market_options_text", "옵션 규칙(선택)", "비우면 URL 수집값 자동 사용")
        self._add_market_line(auto_grid, 0, 1, "option_stock_quantity", "옵션별 재고", "비우면 전체 재고")
        self._add_market_line(auto_grid, 0, 2, "option_price_delta", "옵션 추가금", "예: 50cm=2000")
        self._add_market_line(auto_grid, 1, 0, "naver_fee_rate", "네이버 수수료(%)", "기본 10")
        self._add_market_line(auto_grid, 1, 1, "coupang_fee_rate", "쿠팡 수수료(%)", "기본 10")
        self._add_market_line(auto_grid, 1, 2, "price_round_unit", "판매가 올림 단위", "기본 100")
        self._add_market_line(auto_grid, 2, 0, "base_cost_extra", "추가 원가", "해외배송/포장 등")
        self._add_market_line(auto_grid, 2, 1, "tax_rate", "세금(%)", "기본 10")
        self._add_market_line(auto_grid, 2, 2, "other_fee_rate", "기타비용(%)", "기본 0")
        auto_layout.addLayout(auto_grid)
        self.market_auto_status_label.setObjectName("Evidence")
        self.market_auto_status_label.setWordWrap(True)
        self.market_auto_status_label.setText(
            "자동 산출: SEO 제목, 연관 키워드, 카테고리 후보, 옵션 조합, 상품고시 초안, 이미지 업로드 manifest"
        )
        auto_layout.addWidget(self.market_auto_status_label)
        settings_tabs.addTab(auto_tab, "자동 산출/옵션")

        layout.addWidget(settings_tabs)
        self.market_price_banner_label.setObjectName("Evidence")
        self.market_price_banner_label.setWordWrap(True)
        layout.addWidget(self.market_price_banner_label)

        content_row = QHBoxLayout()
        left_col = QVBoxLayout()
        self.market_table.setColumnCount(8)
        self.market_table.setHorizontalHeaderLabels(
            ["상품코드", "상품명", "상세페이지", "썸네일", "네이버", "쿠팡", "검수", "폴더"]
        )
        self.market_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.market_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.market_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.market_table.verticalHeader().setVisible(False)
        self.market_table.setAlternatingRowColors(True)
        self.market_table.itemSelectionChanged.connect(self._refresh_market_preview)
        market_header = self.market_table.horizontalHeader()
        market_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        market_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        market_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        market_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        market_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        market_header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        market_header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        market_header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        left_col.addWidget(self.market_table, 1)
        content_row.addLayout(left_col, 3)

        right_col = QVBoxLayout()
        preview_title = QLabel("선택 상품 미리보기")
        preview_title.setObjectName("SectionTitle")
        right_col.addWidget(preview_title)
        self.market_preview_label.setObjectName("PreviewImage")
        self.market_preview_label.setMinimumSize(260, 260)
        self.market_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.market_preview_label.setWordWrap(True)
        right_col.addWidget(self.market_preview_label)
        payload_title = QLabel("초안 / payload 미리보기")
        payload_title.setObjectName("SectionTitle")
        right_col.addWidget(payload_title)
        self.market_payload_box.setObjectName("TextArea")
        self.market_payload_box.setAcceptRichText(False)
        self.market_payload_box.setReadOnly(True)
        self.market_payload_box.setMinimumWidth(380)
        right_col.addWidget(self.market_payload_box, 1)
        content_row.addLayout(right_col, 2)
        layout.addLayout(content_row, 1)

        self._apply_market_default_values()
        return panel

    def _add_market_line(
        self,
        grid: QGridLayout,
        row: int,
        column_group: int,
        key: str,
        label: str,
        placeholder: str = "",
        secret: bool = False,
    ) -> None:
        label_widget = QLabel(label)
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setMinimumHeight(36)
        field.setMinimumWidth(180)
        if placeholder:
            label_widget.setToolTip(placeholder)
            field.setToolTip(placeholder)
        field.textEdited.connect(self._mark_market_settings_dirty)
        if secret:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            self.market_secret_keys.add(key)
        self.market_fields[key] = field
        col = column_group * 2
        grid.addWidget(label_widget, row, col)
        grid.addWidget(field, row, col + 1)

    def _add_market_combo(
        self,
        grid: QGridLayout,
        row: int,
        column_group: int,
        key: str,
        label: str,
        values: list[str],
    ) -> None:
        label_widget = QLabel(label)
        combo = QComboBox()
        combo.addItems(values)
        combo.setMinimumHeight(36)
        combo.setMinimumWidth(180)
        combo.currentTextChanged.connect(self._mark_market_settings_dirty)
        self.market_fields[key] = combo
        col = column_group * 2
        grid.addWidget(label_widget, row, col)
        grid.addWidget(combo, row, col + 1)

    def _apply_market_default_values(self) -> None:
        defaults = {
            "stock_quantity": "100",
            "delivery_fee": "0",
            "margin_rate": DEFAULT_TARGET_NET_MARGIN_RATE,
            "origin": "중국",
            "manufacturer": DEFAULT_MARKET_MANUFACTURER,
            "brand": DEFAULT_MARKET_BRAND,
            "tax_type": "TAX",
            "as_message": "상품 수령 후 판매자 문의",
            "upload_mode": "live",
            "return_delivery_fee": "3000",
            "exchange_delivery_fee": "6000",
            "coupang_category_recommendation_path": COUPANG_CATEGORY_RECOMMENDATION_PATH,
            "option_stock_quantity": "100",
            "option_price_delta": "0",
            "naver_fee_rate": DEFAULT_NAVER_FEE_RATE,
            "coupang_fee_rate": DEFAULT_COUPANG_FEE_RATE,
            "price_round_unit": DEFAULT_PRICE_ROUND_UNIT,
            "base_cost_extra": "0",
            "tax_rate": DEFAULT_MARKET_TAX_RATE,
            "other_fee_rate": DEFAULT_MARKET_OTHER_FEE_RATE,
        }
        for key, value in defaults.items():
            if not self._market_field_text(key):
                self._set_market_field_text(key, value)

    def _small_header(self, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        row.addWidget(label)
        return row

    def _add_line(self, form: QFormLayout, key: str, label: str, placeholder: str) -> None:
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setMinimumHeight(38)
        field.textChanged.connect(self._refresh_prompt)
        self.fields[key] = field
        form.addRow(label, field)

    def _add_combo(self, form: QFormLayout, key: str, label: str, values: list[str]) -> None:
        combo = QComboBox()
        combo.addItems(values)
        combo.setMinimumHeight(38)
        combo.currentTextChanged.connect(self._refresh_prompt)
        self.fields[key] = combo
        form.addRow(label, combo)

    def _add_text(self, form: QFormLayout, key: str, label: str, placeholder: str) -> None:
        field = QTextEdit()
        field.setAcceptRichText(False)
        field.setPlaceholderText(placeholder)
        field.setMinimumHeight(74)
        field.setFixedHeight(74)
        field.textChanged.connect(self._refresh_prompt)
        self.fields[key] = field
        form.addRow(label, field)

    def _pick_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "제품 이미지 선택",
            str(Path.home() / "Desktop"),
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*.*)",
        )
        if not files:
            return
        current = self._field_text("image_paths")
        items = [p.strip() for p in re.split(r"[;\n]+", current) if p.strip()]
        items.extend(files)
        self._set_field_text("image_paths", "; ".join(dict.fromkeys(items)))
        self._refresh_prompt()

    def _pick_brand_logo(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "상품에 넣을 브랜드 로고 선택",
            str(Path.home() / "Desktop"),
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*.*)",
        )
        if not file_path:
            return
        source_path = Path(file_path)
        if not self._is_valid_image_file(source_path):
            QMessageBox.warning(self, "로고 선택 실패", "선택한 파일을 이미지로 읽을 수 없습니다.")
            return
        try:
            USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            target_path = USER_CONFIG_DIR / "brand_logo.png"
            from PIL import Image, ImageOps

            with Image.open(source_path) as logo_image:
                logo_image = ImageOps.exif_transpose(logo_image).convert("RGBA")
                logo_image.save(target_path, "PNG")
        except Exception as exc:
            QMessageBox.warning(self, "로고 저장 실패", f"로고를 앱 설정 폴더에 저장하지 못했습니다.\n{exc}")
            return
        self.brand_logo_path = str(target_path)
        self._sync_brand_logo_status_label()
        self._save_config()
        self.statusBar().showMessage(f"브랜드 로고 선택 완료: {target_path}")

    def _sync_brand_logo_status_label(self) -> None:
        label = getattr(self, "brand_logo_status_label", None)
        if not isinstance(label, QLabel):
            return
        logo_path = self._brand_logo_source_path()
        if logo_path is None:
            label.setText("로고 미선택")
        else:
            label.setText(f"로고: {logo_path.name}")

    def _load_excel_links(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "URL 엑셀 선택",
            str(Path.home() / "Desktop"),
            "Excel Files (*.xlsx *.xlsm);;All Files (*.*)",
        )
        if not path:
            return
        try:
            tasks = self._read_excel_url_tasks(Path(path))
        except Exception as exc:
            QMessageBox.warning(self, "엑셀 불러오기 실패", str(exc))
            self.statusBar().showMessage("엑셀 불러오기 실패")
            return
        if not tasks:
            QMessageBox.information(
                self,
                "URL 없음",
                "엑셀에서 http 또는 https로 시작하는 URL을 찾지 못했습니다.",
            )
            return
        self.excel_path = path
        self.link_tasks = tasks
        self.current_link_index = -1
        self._reconcile_link_task_statuses()
        self._refresh_link_table()
        self._save_config()
        self.statusBar().showMessage(f"엑셀 URL {len(tasks)}개를 불러왔습니다.")

    def _read_excel_url_tasks(self, path: Path) -> list[LinkTask]:
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾지 못했습니다: {path}")
        wb = load_workbook(path, read_only=True, data_only=True)
        tasks: list[LinkTask] = []
        seen_urls: set[str] = set()
        matched_header = False
        try:
            for ws in wb.worksheets:
                header_row = None
                url_col = None
                secondary_url_col = None
                for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 20)):
                    for cell in row:
                        header_value = str(cell.value or "")
                        if self._is_1688_url_header(header_value):
                            secondary_url_col = cell.column
                            header_row = header_row or cell.row
                            continue
                        if self._is_excel_url_header(header_value):
                            header_row = cell.row
                            url_col = cell.column
                    if url_col:
                        break
                    if url_col:
                        break
                if not url_col:
                    continue
                matched_header = True
                start_row = (header_row or 1) + 1
                for row_idx in range(start_row, ws.max_row + 1):
                    cell = ws.cell(row=row_idx, column=url_col)
                    url = self._cell_url(cell)
                    if self._is_primary_task_url(url) and url not in seen_urls:
                        secondary_url = ""
                        if secondary_url_col:
                            secondary_url = self._cell_url(ws.cell(row=row_idx, column=secondary_url_col))
                            if not self._is_url(secondary_url):
                                secondary_url = ""
                        tasks.append(LinkTask(row_number=row_idx, url=url, secondary_url=secondary_url))
                        seen_urls.add(url)
            if matched_header:
                return tasks

            for ws in wb.worksheets:
                for row in ws.iter_rows(min_row=1):
                    row_urls = [self._cell_url(cell) for cell in row]
                    row_urls = [url for url in row_urls if self._is_url(url)]
                    if row_urls:
                        primary_url, secondary_url = self._split_row_urls(row_urls)
                        if primary_url and primary_url not in seen_urls:
                            tasks.append(
                                LinkTask(
                                    row_number=row[0].row if row else 0,
                                    url=primary_url,
                                    secondary_url=secondary_url,
                                )
                            )
                            seen_urls.add(primary_url)
                        continue
                    for cell in row:
                        url = self._cell_url(cell)
                        if self._is_primary_task_url(url) and url not in seen_urls:
                            tasks.append(LinkTask(row_number=cell.row, url=url))
                            seen_urls.add(url)
                            break
            return tasks
        finally:
            wb.close()

    def _normalize_excel_header(self, value: str) -> str:
        return re.sub(r"[\s_\-()/]+", "", (value or "").strip()).lower()

    def _is_excel_url_header(self, value: str) -> bool:
        if self._is_url(value):
            return False
        normalized = self._normalize_excel_header(value)
        if not normalized:
            return False
        if any(token in normalized for token in ("이미지", "사진", "썸네일", "thumbnail", "image", "img")):
            return False
        if self._is_1688_url_header(value):
            return False
        exact_matches = {
            "url",
            "url바로가기",
            "url링크",
            "url주소",
            "상품url",
            "상품링크",
            "상품url바로가기",
            "url바로가기링크",
            "링크",
            "바로가기url",
        }
        if normalized in exact_matches:
            return True
        has_url_keyword = any(token in normalized for token in ("url", "링크", "link"))
        has_column_hint = any(token in normalized for token in ("바로가기", "주소", "url", "링크", "link"))
        return has_url_keyword and has_column_hint

    def _is_1688_url_header(self, value: str) -> bool:
        if self._is_url(value):
            return False
        normalized = self._normalize_excel_header(value)
        if not normalized:
            return False
        return "1688" in normalized or "중국" in normalized or "타오바오" in normalized or "alibaba" in normalized

    def _is_1688_url(self, value: str) -> bool:
        lower = (value or "").lower()
        return "1688.com" in lower or "detail.1688.com" in lower or "alibaba.com" in lower

    def _is_direct_image_url(self, value: str) -> bool:
        if not self._is_url(value):
            return False
        parsed = urllib.parse.urlparse(value)
        path = urllib.parse.unquote(parsed.path or "").lower()
        if re.search(r"\.(?:jpg|jpeg|png|gif|webp|bmp|avif)(?:$|[?#])", path):
            return True
        return bool(
            re.search(r"(?:^|[_-])(?:stt|thumb|thumbnail|대표|image|img)[_-]?\d*", path)
            and any(host in (parsed.netloc or "").lower() for host in ("cdn", "image", "img"))
        )

    def _is_primary_task_url(self, value: str) -> bool:
        return self._is_url(value) and not self._is_direct_image_url(value)

    def _split_row_urls(self, urls: list[str]) -> tuple[str, str]:
        if not urls:
            return "", ""
        primary_candidates = [
            url
            for url in urls
            if not self._is_1688_url(url) and self._is_primary_task_url(url)
        ]
        secondary_candidates = [url for url in urls if self._is_1688_url(url)]
        primary_url = primary_candidates[0] if primary_candidates else ""
        secondary_url = ""
        for url in secondary_candidates:
            if url != primary_url:
                secondary_url = url
                break
        if not secondary_url:
            for url in urls:
                if url != primary_url:
                    secondary_url = url
                    break
        return primary_url, secondary_url

    def _cell_url(self, cell) -> str:
        hyperlink = getattr(cell, "hyperlink", None)
        target = getattr(hyperlink, "target", None)
        if target:
            return str(target).strip()
        return str(cell.value or "").strip()

    def _is_url(self, value: str) -> bool:
        return value.startswith("http://") or value.startswith("https://")

    def _stable_url_slug(self, url: str, fallback: str) -> str:
        code_match = re.search(r"selfcode=([^&]+)", url)
        if code_match:
            return slugify(code_match.group(1), fallback)
        parsed = urllib.parse.urlparse(url)
        tail = parsed.path.rstrip("/").split("/")[-1]
        if tail:
            return slugify(tail, fallback)
        return slugify(parsed.netloc or fallback, fallback)

    def _stable_url_suffix(self, url: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered_pairs = [
            (key, value)
            for key, value in pairs
            if key.lower() not in {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
        ]
        canonical_query = urllib.parse.urlencode(sorted(filtered_pairs))
        canonical = urllib.parse.urlunsplit(
            (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, canonical_query, "")
        )
        return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:8]

    def _canonical_task_url(self, url: str | object) -> str:
        text = str(url or "").strip()
        if not text:
            return ""
        parsed = urllib.parse.urlsplit(text)
        pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered_pairs = [
            (key, value)
            for key, value in pairs
            if key.lower() not in {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
        ]
        canonical_query = urllib.parse.urlencode(sorted(filtered_pairs))
        return urllib.parse.urlunsplit(
            (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), canonical_query, "")
        )

    def _task_urls_match(self, left: str | object, right: str | object) -> bool:
        left_key = self._canonical_task_url(left)
        right_key = self._canonical_task_url(right)
        return bool(left_key and right_key and left_key == right_key)

    def _metadata_matches_task_url(
        self,
        metadata: dict[str, object],
        url: str,
        secondary_url: str = "",
    ) -> bool:
        saved_url = str(metadata.get("url") or metadata.get("product_url") or "").strip()
        if not self._task_urls_match(saved_url, url):
            return False
        expected_secondary_url = secondary_url.strip()
        if expected_secondary_url:
            saved_secondary_url = str(metadata.get("secondary_url", "")).strip()
            if not self._task_urls_match(saved_secondary_url, expected_secondary_url):
                return False
        return True

    def _read_output_metadata(self, folder: Path, prefer_completed: bool = True) -> dict[str, object] | None:
        metadata_paths = []
        if prefer_completed:
            metadata_paths.append(COMPLETED_DIR / folder.name / "metadata.json")
        metadata_paths.append(folder / "metadata.json")
        for metadata_path in metadata_paths:
            if not metadata_path.exists():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            if isinstance(metadata, dict):
                return metadata
        return None

    def _legacy_url_output_folder_path(self, index: int, url: str) -> Path:
        base = self._stable_url_slug(url, f"url_{index + 1}")
        return OUTPUT_DIR / f"{index + 1:03d}_{base}"

    def _stable_url_output_folder_path(self, index: int, url: str) -> Path:
        base = self._stable_url_slug(url, f"url_{index + 1}")
        return OUTPUT_DIR / f"{base}_{self._stable_url_suffix(url)}"

    def _url_output_folder_candidates(self, index: int, url: str) -> list[Path]:
        legacy = self._legacy_url_output_folder_path(index, url)
        stable = self._stable_url_output_folder_path(index, url)
        candidates = [stable] if legacy == stable else [stable, legacy]
        base = self._stable_url_slug(url, f"url_{index + 1}")
        for pattern in (f"???_{base}", f"{base}_*"):
            try:
                matches = sorted(
                    (path for path in OUTPUT_DIR.glob(pattern) if path.is_dir()),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )
            except Exception:
                matches = []
            candidates.extend(matches)
        deduped: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            try:
                key = str(candidate.resolve()).lower()
            except Exception:
                key = str(candidate).lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped

    def _ensure_output_dirs(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        COMPLETED_DIR.mkdir(parents=True, exist_ok=True)

    def _metadata_complete(self, metadata: dict[str, object]) -> bool:
        return str(metadata.get("status", "")).strip() == "완료"

    def _valid_section_files(self, sections_dir: Path) -> list[Path]:
        if not sections_dir.exists() or not sections_dir.is_dir():
            return []
        section_files = sorted(sections_dir.glob("section_*.png"))
        if len(section_files) < REQUIRED_SECTION_IMAGE_COUNT:
            return []
        if not all(self._is_valid_image_file(path) for path in section_files):
            return []
        return section_files

    def _valid_thumbnail_files(self, thumbnails_dir: Path) -> list[Path]:
        if not thumbnails_dir.exists() or not thumbnails_dir.is_dir():
            return []
        thumbnail_files = [thumbnails_dir / f"{index}.png" for index in range(1, REQUIRED_THUMBNAIL_IMAGE_COUNT + 1)]
        if not all(self._is_valid_thumbnail_file(path) for path in thumbnail_files):
            return []
        if not self._thumbnail_files_are_visually_distinct(thumbnail_files):
            return []
        return thumbnail_files

    def _task_output_complete(self, index: int, url: str, secondary_url: str = "") -> bool:
        for folder in self._url_output_folder_candidates(index, url):
            detail_page = folder / "detail_page.png"
            sections_dir = folder / "sections"
            thumbnails_dir = folder / "thumbnails"
            metadata_path = folder / "metadata.json"
            if not metadata_path.exists():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not self._metadata_matches_task_url(metadata, url, secondary_url):
                continue
            if not self._metadata_complete(metadata):
                continue
            if metadata.get("pipeline_version") != DETAIL_PIPELINE_VERSION:
                continue
            metadata_sections = metadata.get("sections")
            if not self._metadata_sections_are_clean(metadata_sections):
                continue
            expected_section_count = (
                len(metadata_sections)
                if isinstance(metadata_sections, list) and len(metadata_sections) >= REQUIRED_SECTION_IMAGE_COUNT
                else REQUIRED_SECTION_IMAGE_COUNT
            )
            if not self._copy_manifest_is_valid(folder / "copy_manifest.json"):
                continue
            render_mode = str(metadata.get("render_mode", ""))
            if render_mode not in {CODEX_IMAGE_RENDER_MODE, PRODUCTION_RENDER_MODE}:
                continue
            if REQUIRE_GENERATED_SECTION_IMAGES and render_mode != CODEX_IMAGE_RENDER_MODE:
                continue
            if metadata.get("latest_image_model_target") != LATEST_CODEX_IMAGE_MODEL:
                continue
            image_model = str(metadata.get("image_model", ""))
            if render_mode == CODEX_IMAGE_RENDER_MODE and image_model not in {LATEST_CODEX_IMAGE_MODEL, CHATGPT_WEB_IMAGE_MODEL}:
                continue
            if render_mode == PRODUCTION_RENDER_MODE and image_model != PRODUCTION_RENDERER_MODEL:
                continue
            if REQUIRE_GENERATED_SECTION_IMAGES and render_mode == CODEX_IMAGE_RENDER_MODE:
                generated_paths = [Path(str(path)) for path in metadata.get("generated_visual_paths", []) if str(path).strip()]
                if len(generated_paths) < expected_section_count:
                    continue
                if not all(self._is_valid_generated_visual_file(path) for path in generated_paths):
                    continue
            jobs_path = folder / "codex_image_prompts" / f"imagegen_{LATEST_CODEX_IMAGE_MODEL}_jobs.jsonl"
            if not jobs_path.exists() or jobs_path.stat().st_size <= 0:
                continue
            thumbnail_paths = [Path(str(path)) for path in metadata.get("thumbnail_paths", []) if str(path).strip()]
            if int(metadata.get("thumbnail_count") or 0) != REQUIRED_THUMBNAIL_IMAGE_COUNT:
                continue
            if len(thumbnail_paths) != REQUIRED_THUMBNAIL_IMAGE_COUNT:
                continue
            if metadata.get("thumbnail_style_version") != THUMBNAIL_STYLE_VERSION:
                continue
            if not all(self._is_valid_thumbnail_file(path) for path in thumbnail_paths):
                continue
            if not self._thumbnail_files_are_visually_distinct(thumbnail_paths):
                continue
            completed_dir = COMPLETED_DIR / folder.name
            completed_detail = completed_dir / "detail_page.png"
            completed_thumbnails = [completed_dir / f"{index}.png" for index in range(1, REQUIRED_THUMBNAIL_IMAGE_COUNT + 1)]
            completed_metadata_path = completed_dir / "metadata.json"
            completed_copy_manifest_path = completed_dir / "copy_manifest.json"
            if not self._is_valid_image_file(completed_detail):
                continue
            if not all(self._is_valid_thumbnail_file(path) for path in completed_thumbnails):
                continue
            if not completed_metadata_path.exists():
                continue
            try:
                completed_metadata = json.loads(completed_metadata_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not self._metadata_matches_task_url(completed_metadata, url, secondary_url):
                continue
            if not self._metadata_complete(completed_metadata):
                continue
            completed_sections = completed_metadata.get("sections")
            if not self._metadata_sections_are_clean(completed_sections):
                continue
            completed_expected_section_count = (
                len(completed_sections)
                if isinstance(completed_sections, list) and len(completed_sections) >= REQUIRED_SECTION_IMAGE_COUNT
                else REQUIRED_SECTION_IMAGE_COUNT
            )
            if completed_expected_section_count < expected_section_count:
                continue
            completed_sections_dir = completed_dir / "sections"
            if completed_metadata.get("completed_sections_dir") and len(self._valid_section_files(completed_sections_dir)) < expected_section_count:
                continue
            if not self._copy_manifest_is_valid(completed_copy_manifest_path):
                continue
            if completed_metadata.get("thumbnail_style_version") != THUMBNAIL_STYLE_VERSION:
                continue
            if not self._is_valid_image_file(detail_page):
                continue
            if len(self._valid_section_files(sections_dir)) < expected_section_count:
                continue
            if not self._valid_thumbnail_files(thumbnails_dir):
                continue
            return True
        return False

    def _task_has_partial_output(self, index: int, url: str) -> bool:
        markers = (
            "metadata.json",
            "result.md",
            "source.json",
            "detail_page.png",
            "sections",
            "thumbnails",
            "source_images",
            "codex_image_prompts",
        )
        stable_folder = self._stable_url_output_folder_path(index, url)
        for folder in self._url_output_folder_candidates(index, url):
            if not folder.exists():
                continue
            if folder != stable_folder:
                metadata = self._read_output_metadata(folder)
                if not metadata or not self._metadata_matches_task_url(metadata, url):
                    continue
            for marker in markers:
                path = folder / marker
                if path.exists():
                    return True
        return False

    def _load_existing_detail_for_thumbnail_refresh(
        self,
        index: int,
        url: str,
        secondary_url: str = "",
    ) -> tuple[ProductRecord, list[SectionPlan], RenderResult, str] | None:
        expected_secondary_url = secondary_url.strip()
        for folder in self._url_output_folder_candidates(index, url):
            completed_dir = COMPLETED_DIR / folder.name
            metadata_candidates = [completed_dir / "metadata.json", folder / "metadata.json"]
            metadata: dict[str, object] | None = None
            for metadata_path in metadata_candidates:
                if not metadata_path.exists():
                    continue
                try:
                    candidate = json.loads(metadata_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not self._metadata_matches_task_url(candidate, url, expected_secondary_url):
                    continue
                if (
                    candidate.get("status") == "완료"
                    or candidate.get("sections")
                    or candidate.get("generated_visual_paths")
                    or candidate.get("thumbnail_paths")
                ):
                    metadata = candidate
                    break
            if not metadata:
                continue

            detail_page = folder / "detail_page.png"
            section_paths = self._valid_section_files(folder / "sections")
            visual_paths = sorted((folder / "generated_visuals").glob("section_*.png"))
            visual_paths = [path for path in visual_paths if self._is_valid_generated_visual_file(path)]
            if not self._is_valid_image_file(detail_page) or len(section_paths) < REQUIRED_SECTION_IMAGE_COUNT:
                continue
            if len(visual_paths) < REQUIRED_SECTION_IMAGE_COUNT:
                visual_paths = section_paths

            section_items = metadata.get("sections", [])
            sections: list[SectionPlan] = []
            if isinstance(section_items, list):
                for item in section_items:
                    if not isinstance(item, dict):
                        continue
                    sections.append(
                        SectionPlan(
                            section_key=str(item.get("section_key") or f"section_{len(sections) + 1:02d}"),
                            section_name=str(item.get("section_name") or ""),
                            headline=str(item.get("headline") or ""),
                            subheadline=str(item.get("subheadline") or ""),
                            body=str(item.get("body") or ""),
                            bullets=[str(value) for value in item.get("bullets", []) if str(value).strip()],
                            image_prompt=str(item.get("image_prompt") or ""),
                            overlay_text=str(item.get("overlay_text") or ""),
                            source_section_text=str(item.get("source_section_text") or ""),
                        )
                    )
            if len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
                fallback_keys = list(SECTION_DISPLAY_NAMES.keys())
                product_name = str(metadata.get("product_name") or Path(folder).name)
                sections = [
                    SectionPlan(
                        section_key=fallback_keys[item_index - 1] if item_index <= len(fallback_keys) else f"section_{item_index:02d}",
                        section_name=SECTION_DISPLAY_NAMES.get(
                            fallback_keys[item_index - 1] if item_index <= len(fallback_keys) else "",
                            f"섹션 {item_index}",
                        ),
                        headline=product_name,
                        subheadline="",
                        body="기존 상세페이지와 섹션 이미지를 유지하고 썸네일만 이어서 생성합니다.",
                        bullets=[],
                        image_prompt="",
                        overlay_text="",
                    )
                    for item_index in range(1, REQUIRED_SECTION_IMAGE_COUNT + 1)
                ]

            source_paths: list[Path] = []
            for raw_path in metadata.get("source_image_paths", []):
                path = Path(str(raw_path))
                if self._is_valid_image_file(path):
                    source_paths.append(path)
            for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                source_paths.extend(path for path in (folder / "source_images").rglob(pattern) if self._is_valid_image_file(path))
            deduped_source_paths: list[Path] = []
            seen: set[str] = set()
            for path in source_paths:
                key = str(path.resolve()).lower()
                if key in seen:
                    continue
                seen.add(key)
                deduped_source_paths.append(path)

            product = ProductRecord(
                index=index,
                url=url,
                secondary_url=str(metadata.get("secondary_url") or secondary_url).strip(),
                code=str(metadata.get("code") or slugify(Path(folder).name)),
                product_name=str(metadata.get("product_name") or Path(folder).name),
                title=str(metadata.get("product_name") or Path(folder).name),
                category=str(metadata.get("category") or ""),
                price_text=str(metadata.get("price_text") or ""),
                options_text=str(metadata.get("options_text") or ""),
                facts=[str(value) for value in metadata.get("facts", []) if str(value).strip()] if isinstance(metadata.get("facts", []), list) else [],
                source_text="",
                image_urls=[],
                source_image_paths=deduped_source_paths,
                output_dir=folder,
                source_payloads=self._image_only_source_payloads(metadata.get("source_payloads", [])) if isinstance(metadata.get("source_payloads", []), list) else [],
            )
            render_result = RenderResult(
                section_paths=section_paths,
                detail_page_path=detail_page,
                visual_paths=visual_paths,
                render_mode=str(metadata.get("render_mode") or CODEX_IMAGE_RENDER_MODE),
                image_model=str(metadata.get("image_model") or CHATGPT_WEB_IMAGE_MODEL),
            )
            result_text = ""
            for result_path in (completed_dir / "result.md", folder / "result.md"):
                if result_path.exists():
                    try:
                        result_text = result_path.read_text(encoding="utf-8")
                        break
                    except Exception:
                        continue
            return product, sections, render_result, result_text
        return None

    def _regenerate_existing_thumbnails_only(
        self,
        index: int,
        url: str,
        secondary_url: str,
        run_stamp: str,
        page,
        progress_callback=None,
    ) -> tuple[Path, ThumbnailResult] | None:
        loaded = self._load_existing_detail_for_thumbnail_refresh(index, url, secondary_url)
        if not loaded:
            return None
        product, sections, render_result, result_text = loaded
        try:
            thumbnail_result = self._generate_thumbnail_images(
                product,
                sections,
                run_stamp,
                page=page,
                progress_callback=progress_callback,
            )
        except Exception:
            raise
        saved_path = self._save_detail_page_result(
            product,
            "[썸네일 v2 재생성]\n기존 상세페이지와 섹션 PNG는 유지하고, 상품 참고 이미지를 첨부해 정사각 쇼핑몰 썸네일 5장만 다시 생성했습니다.",
            result_text,
            sections,
            render_result,
            run_stamp,
            thumbnail_result,
        )
        return saved_path, thumbnail_result

    def _normalize_loaded_task_status(self, status: str) -> str:
        text = str(status or "").strip()
        if not text:
            return "대기"
        stale_markers = (
            "GPT 답변",
            "답변대기",
            "GPT 기획 재시도",
            "기획 재시도",
            "GPT 기획 분석",
            "기획 분석",
            "GPT 기획 분석중",
            "GPT 기획 요청",
            "GPT 기획 재사용",
            "기존 GPT 기획 재사용",
            "답변 대기",
            "GPT 답변 대기",
            "상품이미지 렌더중",
            "섹션 이미지 생성중",
            "ChatGPT 이미지 생성중",
            "이미지 감시",
            "썸네일 생성중",
            "썸네일 재시도",
            "진행중",
            "열림",
            "재작업 필요",
        )
        if any(marker in text for marker in stale_markers):
            return "대기"
        if "부터 재시작" in text:
            return "대기"
        if "부터 시작" in text:
            return "대기"
        return text

    def _reconcile_link_task_statuses(self) -> bool:
        changed = False
        terminal_incomplete_statuses = {"대기"}
        for index, task in enumerate(self.link_tasks):
            normalized = self._normalize_loaded_task_status(task.status)
            if normalized != task.status:
                task.status = normalized
                changed = True
            if self._task_output_complete(index, task.url, task.secondary_url):
                if task.status != "완료":
                    task.status = "완료"
                    changed = True
                continue
            if "실패" in task.status:
                task.status = "대기"
                changed = True
                continue
            if task.status == "대기" and self._task_has_partial_output(index, task.url):
                continue
            if (
                task.status == "완료"
                or task.status in {"진행중", "열림"}
                or self._is_image_wait_status(task.status)
                or ("완료" in task.status and task.status != "완료")
                or task.status not in terminal_incomplete_statuses
            ):
                task.status = "대기"
                changed = True
        return changed

    def _refresh_link_table(self, validate_outputs: bool = True) -> None:
        complete_cache: dict[int, bool] = {}

        def completed(index: int, task: LinkTask) -> bool:
            if not validate_outputs:
                return task.status == "완료"
            if index not in complete_cache:
                complete_cache[index] = self._task_output_complete(index, task.url, task.secondary_url)
            return complete_cache[index]

        self.link_table.setRowCount(len(self.link_tasks))
        for index, task in enumerate(self.link_tasks):
            completion_state = completed(index, task) if task.status == "완료" else None
            display_status = self._display_task_status(index, task, completion_state)
            values = [str(index + 1), str(task.row_number), display_status, task.url, task.secondary_url]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col < 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.link_table.setItem(index, col, item)
        if self.current_link_index >= 0 and self.current_link_index < len(self.link_tasks):
            self.link_table.selectRow(self.current_link_index)
        pending = sum(1 for task in self.link_tasks if task.status == "대기")
        failed = sum(1 for task in self.link_tasks if "실패" in task.status)
        done = sum(
            1
            for index, task in enumerate(self.link_tasks)
            if task.status == "완료" and completed(index, task)
        )
        stale = sum(
            1
            for index, task in enumerate(self.link_tasks)
            if validate_outputs and task.status == "완료" and not completed(index, task)
        )
        opened = sum(1 for task in self.link_tasks if task.status in {"열림", "진행중"})
        image_wait = sum(1 for task in self.link_tasks if self._is_image_wait_status(task.status))
        secondary_count = sum(1 for task in self.link_tasks if task.secondary_url.strip())
        if self.link_tasks:
            name = Path(self.excel_path).name if self.excel_path else "엑셀"
            self.link_status_label.setText(
                f"{name} · 전체 {len(self.link_tasks)}개 · 1688 {secondary_count}개 · 대기 {pending + stale} · 실패 {failed} · 열림 {opened} · 이미지대기 {image_wait} · 완료 {done}"
            )
        else:
            self.link_status_label.setText("엑셀을 불러오면 URL 작업 목록이 여기에 표시됩니다.")
        self._sync_image_wait_timer()

    def _display_task_status(self, index: int, task: LinkTask, completion_state: bool | None = None) -> str:
        status = self._normalize_loaded_task_status(task.status)
        if status == "완료" and completion_state is False:
            return "대기"
        if status == "완료" and completion_state is None and not self._task_output_complete(index, task.url, task.secondary_url):
            return "대기"
        if status.startswith("썸네일 생성중"):
            return status
        if not self._is_image_wait_status(status):
            return status
        count = self._generated_visual_count(index, task.url)
        dots = "." * ((self.image_wait_tick % 3) + 1)
        return f"이미지 생성중 {count}장 {dots}"

    def _is_image_wait_status(self, status: str) -> bool:
        return (
            status.startswith("ChatGPT 이미지 생성중")
            or status.startswith("썸네일 생성중")
            or status.startswith("상품이미지 렌더중")
            or status.startswith("이미지 생성 대기")
            or status.startswith("Codex 이미지 대기")
            or status.startswith("이미지 감시")
        )

    def _generated_visual_count(self, index: int, url: str) -> int:
        for folder in self._url_output_folder_candidates(index, url):
            visual_dir = folder / "generated_visuals"
            if not visual_dir.exists():
                continue
            files = [
                path
                for path in visual_dir.glob("section_*.png")
                if path.exists() and path.stat().st_size > 0
            ]
            if files:
                return len(files)
        return 0

    def _sync_image_wait_timer(self) -> None:
        has_waiting = any(self._is_image_wait_status(task.status) for task in self.link_tasks)
        if has_waiting and not self.image_wait_timer.isActive():
            self.image_wait_timer.start()
        elif not has_waiting and self.image_wait_timer.isActive():
            self.image_wait_timer.stop()

    def _refresh_image_wait_animation(self) -> None:
        if not any(self._is_image_wait_status(task.status) for task in self.link_tasks):
            self.image_wait_timer.stop()
            return
        self.image_wait_tick += 1
        waiting_parts = []
        for index, task in enumerate(self.link_tasks):
            if self._is_image_wait_status(task.status):
                waiting_parts.append(f"{index + 1}번 {self._generated_visual_count(index, task.url)}장")
        self._refresh_link_table()
        if waiting_parts:
            dots = "." * ((self.image_wait_tick % 3) + 1)
            self.statusBar().showMessage(f"섹션 이미지 생성 상태 확인 중 {dots} " + " · ".join(waiting_parts))

    def _selected_link_index(self) -> int:
        rows = self.link_table.selectionModel().selectedRows() if self.link_table.selectionModel() else []
        if not rows:
            return -1
        return rows[0].row()

    def _start_manual_stage(self, stage: str, number: int = 1) -> None:
        if self.automation_running:
            QMessageBox.information(self, "실행 중", "먼저 현재 작업 중지를 누르고 멈춘 뒤 다시 시작하세요.")
            return
        index = self._selected_link_index()
        if index < 0:
            index = self.current_link_index if 0 <= self.current_link_index < len(self.link_tasks) else -1
        if index < 0 or index >= len(self.link_tasks):
            QMessageBox.information(self, "선택 필요", "먼저 이어서 작업할 URL 행을 선택하세요.")
            return
        try:
            number = max(1, int(number or 1))
        except Exception:
            number = 1
        if stage == "section" and number > MANUAL_SECTION_BUTTON_COUNT:
            stage = "merge"
            number = 1
        labels = {
            "section": f"섹션 {number}",
            "merge": "합치기",
            "thumbnail": f"썸네일 {number}",
        }
        self.manual_resume_request = {
            "task_index": index,
            "stage": stage,
            "number": number,
        }
        self.link_tasks[index].status = "대기"
        self.current_link_index = index
        self._save_config()
        self._refresh_link_table()
        self.statusBar().showMessage(f"{index + 1}번 URL {labels.get(stage, '선택 지점')}부터 이어서 실행합니다.")
        self._start_gpt_analysis(use_manual_resume=True)

    def _open_selected_link(self) -> None:
        index = self._selected_link_index()
        if index < 0:
            QMessageBox.information(self, "선택 필요", "먼저 열 URL 행을 선택하세요.")
            return
        self._open_link_task(index)

    def _open_next_link(self) -> None:
        if not self.link_tasks:
            QMessageBox.information(self, "목록 없음", "먼저 엑셀을 불러오세요.")
            return
        start = self.current_link_index + 1
        for index in range(start, len(self.link_tasks)):
            if self.link_tasks[index].status != "완료":
                self._open_link_task(index)
                return
        QMessageBox.information(self, "완료", "더 열 대기 URL이 없습니다.")

    def _open_link_task(self, index: int) -> None:
        task = self.link_tasks[index]
        if self.current_link_index >= 0 and self.current_link_index < len(self.link_tasks):
            previous = self.link_tasks[self.current_link_index]
            if previous.status == "진행중":
                previous.status = "열림"
        task.status = "진행중"
        self.current_link_index = index
        self.current_product_url = task.url
        self._set_field_text("product_url", task.url)
        self._refresh_prompt()
        self._refresh_link_table()
        self._save_config()
        self._open_url_in_automation_browser(task.url, f"{index + 1}번 엑셀 URL을 자동화 브라우저에서 열었습니다.")

    def _mark_current_done(self) -> None:
        index = self.current_link_index
        if index < 0:
            index = self._selected_link_index()
        if index < 0 or index >= len(self.link_tasks):
            QMessageBox.information(self, "선택 필요", "완료 처리할 URL을 선택하세요.")
            return
        self.link_tasks[index].status = "완료"
        self.current_link_index = index
        self._refresh_link_table()
        self._save_config()
        self.statusBar().showMessage(f"{index + 1}번 URL을 완료 처리했습니다.")

    def _market_field_text(self, key: str) -> str:
        field = self.market_fields.get(key)
        if isinstance(field, QLineEdit):
            return field.text().strip()
        if isinstance(field, QComboBox):
            return field.currentText().strip()
        return ""

    def _set_market_field_text(self, key: str, value: str) -> None:
        field = self.market_fields.get(key)
        if isinstance(field, QLineEdit):
            if self._is_auto_lookup_value(value):
                field.setText("")
                return
            field.setText(value)
        elif isinstance(field, QComboBox):
            index = field.findText(value)
            if index >= 0:
                field.setCurrentIndex(index)

    def _set_market_setting_value(self, key: str, value: str | object) -> bool:
        cleaned = str(value or "").strip()
        if not cleaned or self._is_auto_lookup_value(cleaned):
            return False
        current = str(self.market_resolved_settings.get(key) or "").strip()
        ui_value = self._market_field_text(key)
        transient_auto_keys = {"naver_category_id", "coupang_category_id"}
        if key in transient_auto_keys and not ui_value:
            if current == cleaned:
                return False
            self.market_resolved_settings[key] = cleaned
            return True
        if key in self.market_fields and key not in self.market_secret_keys:
            if ui_value == cleaned:
                return False
            self._set_market_field_text(key, cleaned)
            return True
        if current == cleaned:
            return False
        self.market_resolved_settings[key] = cleaned
        return True

    def _mark_market_settings_dirty(self) -> None:
        self.market_settings_status_label.setText("마켓 설정 수정됨 - 자동 저장 대기")
        self.market_autosave_timer.start()

    def _autosave_market_settings(self) -> None:
        try:
            self._write_config_file(save_secrets=False)
        except Exception as exc:
            self.market_settings_status_label.setText(f"마켓 설정 자동 저장 실패: {exc}")
            return
        self.market_settings_status_label.setText("마켓 설정 자동 저장됨")

    def _market_settings_data(self, include_secrets: bool = False) -> dict[str, str]:
        data: dict[str, str] = {
            key: value
            for key, value in self.market_resolved_settings.items()
            if str(value or "").strip() and not self._is_auto_lookup_value(value)
        }
        for key in self.market_fields:
            if key in self.market_secret_keys and not include_secrets:
                continue
            value = self._market_field_text(key)
            if value or key not in data:
                data[key] = value
        if not data.get("stock_quantity"):
            data["stock_quantity"] = "100"
        if not data.get("delivery_fee"):
            data["delivery_fee"] = "0"
        if not data.get("margin_rate"):
            data["margin_rate"] = DEFAULT_TARGET_NET_MARGIN_RATE
        data["origin"] = self._normalize_market_origin(data.get("origin", "")) or "중국"
        data["manufacturer"] = self._normalize_market_manufacturer(data.get("manufacturer", "")) or DEFAULT_MARKET_MANUFACTURER
        if not data.get("brand"):
            data["brand"] = DEFAULT_MARKET_BRAND
        if not data.get("tax_type"):
            data["tax_type"] = "TAX"
        if not data.get("as_message"):
            data["as_message"] = "상품 수령 후 판매자 문의"
        if not data.get("upload_mode"):
            data["upload_mode"] = "live"
        defaults = {
            "naver_as_phone": AUTO_LOOKUP_PREFIX + "seller_as_phone",
            "naver_delivery_company": AUTO_LOOKUP_PREFIX + "naver_delivery_company",
            "naver_origin_area_code": AUTO_LOOKUP_PREFIX + "naver_origin_area_code",
            "coupang_vendor_user_id": AUTO_LOOKUP_PREFIX + "coupang_vendor_user_id",
            "coupang_delivery_company_code": AUTO_LOOKUP_PREFIX + "coupang_delivery_company_code",
            "return_delivery_fee": "3000",
            "exchange_delivery_fee": "6000",
            "return_charge_name": AUTO_LOOKUP_PREFIX + "return_charge_name",
            "company_contact_number": AUTO_LOOKUP_PREFIX + "company_contact_number",
            "return_zip_code": AUTO_LOOKUP_PREFIX + "return_zip_code",
            "return_address": AUTO_LOOKUP_PREFIX + "return_address",
            "return_address_detail": AUTO_LOOKUP_PREFIX + "return_address_detail",
            "coupang_category_recommendation_path": COUPANG_CATEGORY_RECOMMENDATION_PATH,
            "option_stock_quantity": "100",
            "option_price_delta": "0",
            "naver_fee_rate": DEFAULT_NAVER_FEE_RATE,
            "coupang_fee_rate": DEFAULT_COUPANG_FEE_RATE,
            "price_round_unit": DEFAULT_PRICE_ROUND_UNIT,
            "base_cost_extra": "0",
            "tax_rate": DEFAULT_MARKET_TAX_RATE,
            "other_fee_rate": DEFAULT_MARKET_OTHER_FEE_RATE,
        }
        for key, value in defaults.items():
            if not data.get(key):
                data[key] = value
        return data

    def _market_settings_for_config(self) -> dict[str, str]:
        transient_auto_keys = {"naver_category_id", "coupang_category_id"}
        data: dict[str, str] = {
            key: value
            for key, value in self.market_resolved_settings.items()
            if str(value or "").strip()
            and not self._is_auto_lookup_value(value)
            and key not in self.market_secret_keys
            and key not in transient_auto_keys
        }
        for key in self.market_fields:
            if key in self.market_secret_keys:
                continue
            value = self._market_field_text(key)
            if self._is_auto_lookup_value(value):
                continue
            data[key] = value
        return data

    def _market_secret_field_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key in self.market_secret_keys:
            value = self._market_field_text(key)
            if value:
                values[key] = value
        return values

    def _save_market_secrets_fallback(self, values: dict[str, str]) -> bool:
        if not values:
            return False
        existing = self._read_json_file(MARKET_SECRET_FALLBACK_PATH)
        merged = {str(key): str(value) for key, value in existing.items() if str(value or "").strip()}
        merged.update(values)
        MARKET_SECRET_FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        MARKET_SECRET_FALLBACK_PATH.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True

    def _load_market_secret_fallback(self, key: str) -> str:
        data = self._read_json_file(MARKET_SECRET_FALLBACK_PATH)
        return str(data.get(key) or "").strip()

    def _save_market_secrets_to_keyring(self, show_message: bool = False) -> bool:
        values = self._market_secret_field_values()
        if not values:
            return False
        if keyring is None:
            try:
                return self._save_market_secrets_fallback(values)
            except Exception as exc:
                if show_message:
                    QMessageBox.warning(self, "저장 불가", f"API 비밀값 보조 저장에 실패했습니다.\n{exc}")
                return False
        saved_any = False
        fallback_values: dict[str, str] = {}
        for key, value in values.items():
            try:
                keyring.set_password(MARKET_KEYRING_SERVICE, key, value)
                saved_any = True
            except Exception:
                fallback_values[key] = value
        if fallback_values:
            try:
                saved_any = self._save_market_secrets_fallback(fallback_values) or saved_any
            except Exception as exc:
                if show_message:
                    QMessageBox.warning(self, "저장 불가", f"API 비밀값 보조 저장에 실패했습니다.\n{exc}")
                return saved_any
        return saved_any

    def _load_market_secrets_from_keyring(self) -> None:
        for key in self.market_secret_keys:
            field = self.market_fields.get(key)
            if not isinstance(field, QLineEdit) or field.text().strip():
                continue
            value = ""
            if keyring is not None:
                try:
                    value = keyring.get_password(MARKET_KEYRING_SERVICE, key) or ""
                except Exception:
                    value = ""
            if not value:
                value = self._load_market_secret_fallback(key)
            if value:
                field.setText(value)

    def _save_market_settings(self) -> None:
        self._save_market_secrets_to_keyring(show_message=True)
        self._save_config()
        self.market_settings_status_label.setText("마켓 설정 저장됨")
        QMessageBox.information(self, "저장 완료", "마켓 설정을 저장했습니다. API 비밀값도 저장합니다.")

    def _persist_market_settings_silent(self) -> None:
        self._write_config_file()
        self.market_settings_status_label.setText("마켓 설정 저장됨")

    def _scan_completed_market_folder(self, select_index: int | None = None, select_code: str = "") -> None:
        self._ensure_output_dirs()
        self.market_products = self._load_completed_market_products()
        if self.market_products:
            if select_code:
                matched_index = next((index for index, product in enumerate(self.market_products) if product.code == select_code), -1)
                select_index = matched_index if matched_index >= 0 else select_index
            if select_index is None:
                select_index = self.current_market_index if 0 <= self.current_market_index < len(self.market_products) else 0
            self.current_market_index = max(0, min(int(select_index), len(self.market_products) - 1))
        else:
            self.current_market_index = -1
        self._refresh_market_table()
        if self.market_products:
            self.market_table.selectRow(self.current_market_index)
        self._refresh_market_preview()

    def _load_completed_market_products(self) -> list[MarketProduct]:
        products: list[MarketProduct] = []
        if not COMPLETED_DIR.exists():
            return products
        for folder in sorted(path for path in COMPLETED_DIR.iterdir() if path.is_dir()):
            products.append(self._market_product_from_completed_folder(folder))
        return products

    def _market_product_from_completed_folder(self, folder: Path) -> MarketProduct:
        metadata = self._read_json_file(folder / "metadata.json")
        source = self._read_json_file(folder / "source.json")
        result_path = folder / "result.md"
        result_text = result_path.read_text(encoding="utf-8", errors="ignore") if result_path.exists() else ""
        product_name = (
            str(metadata.get("product_name") or "")
            or str(source.get("product_name") or "")
            or str(source.get("title") or "")
            or folder.name
        ).strip()
        detail_page = folder / "detail_page.png"
        thumbnail_paths = [folder / f"{index}.png" for index in range(1, REQUIRED_THUMBNAIL_IMAGE_COUNT + 1)]
        issues = self._market_asset_issues(detail_page, thumbnail_paths, metadata)
        naver_status, coupang_status, review_status = self._market_status_from_files(folder, issues)
        return MarketProduct(
            code=folder.name,
            folder=folder,
            product_name=product_name,
            detail_page_path=detail_page,
            thumbnail_paths=thumbnail_paths,
            metadata=metadata,
            source=source,
            result_text=result_text,
            naver_status=naver_status,
            coupang_status=coupang_status,
            review_status=review_status,
            issues=issues,
        )

    def _market_asset_issues(
        self,
        detail_page: Path,
        thumbnail_paths: list[Path],
        metadata: dict[str, object],
    ) -> list[str]:
        issues: list[str] = []
        if not self._is_valid_image_file(detail_page):
            issues.append("detail_page.png 없음 또는 손상")
        valid_thumbs = [path for path in thumbnail_paths if self._is_valid_thumbnail_file(path)]
        if len(valid_thumbs) != REQUIRED_THUMBNAIL_IMAGE_COUNT:
            issues.append(f"썸네일 1000x1000 PNG {len(valid_thumbs)}/{REQUIRED_THUMBNAIL_IMAGE_COUNT}")
        sections_dir_raw = str(metadata.get("completed_sections_dir") or "").strip()
        sections_dir = Path(sections_dir_raw) if sections_dir_raw else detail_page.parent / "sections"
        if sections_dir_raw or sections_dir.exists():
            valid_sections = [
                path
                for path in sorted(sections_dir.glob("section_*.png"))
                if self._is_valid_image_file(path)
            ]
            if len(valid_sections) < REQUIRED_SECTION_IMAGE_COUNT:
                issues.append(f"완료폴더 섹션 PNG {len(valid_sections)}/{REQUIRED_SECTION_IMAGE_COUNT}")
        if not self._metadata_complete(metadata):
            issues.append("metadata.json 상태가 완료가 아님")
        return issues

    def _market_status_from_files(self, folder: Path, issues: list[str]) -> tuple[str, str, str]:
        market_dir = folder / "market"
        publish_result_path = market_dir / "publish_result.json"
        publish_result = self._read_json_file(publish_result_path)
        naver_payload = market_dir / "naver_payload.json"
        coupang_payload = market_dir / "coupang_payload.json"
        naver_status = self._single_market_status(publish_result, "naver", naver_payload, publish_result_path)
        coupang_status = self._single_market_status(publish_result, "coupang", coupang_payload, publish_result_path)
        if issues:
            review_status = "검수 필요"
        elif naver_payload.exists() or coupang_payload.exists():
            review_status = "등록 초안 검수"
        else:
            review_status = "초안 필요"
        return naver_status, coupang_status, review_status

    def _single_market_status(
        self,
        publish_result: dict[str, object],
        key: str,
        payload_path: Path,
        publish_result_path: Path,
    ) -> str:
        raw = publish_result.get(key) if isinstance(publish_result, dict) else None
        if isinstance(raw, dict):
            status = str(raw.get("status") or "").strip()
            if status:
                if status == "live 실패" and payload_path.exists() and publish_result_path.exists():
                    try:
                        if payload_path.stat().st_mtime > publish_result_path.stat().st_mtime:
                            return "재시도 필요"
                    except OSError:
                        pass
                return status
        return "초안 생성" if payload_path.exists() else "미생성"

    def _refresh_market_table(self) -> None:
        self.market_table.setRowCount(len(self.market_products))
        for row, product in enumerate(self.market_products):
            values = [
                product.code,
                product.product_name,
                "정상" if self._is_valid_image_file(product.detail_page_path) else "없음",
                f"{len([path for path in product.thumbnail_paths if self._is_valid_thumbnail_file(path)])}/5",
                product.naver_status,
                product.coupang_status,
                product.review_status,
                str(product.folder),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in {0, 2, 3, 4, 5, 6}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.market_table.setItem(row, col, item)
        ready = sum(1 for product in self.market_products if not product.issues)
        needs_review = sum(1 for product in self.market_products if product.issues)
        self.market_status_label.setText(
            f"완료폴더 {COMPLETED_DIR} · 전체 {len(self.market_products)}개 · 등록 가능 {ready} · 검수 필요 {needs_review}"
        )

    def _selected_market_index(self) -> int:
        rows = self.market_table.selectionModel().selectedRows() if self.market_table.selectionModel() else []
        if not rows:
            return -1
        return rows[0].row()

    def _selected_market_product(self) -> MarketProduct | None:
        index = self._selected_market_index()
        if index < 0:
            index = self.current_market_index
        if index < 0 or index >= len(self.market_products):
            return None
        self.current_market_index = index
        return self.market_products[index]

    def _merge_selected_completed_sections(self) -> None:
        product = self._selected_market_product()
        if product is None:
            QMessageBox.information(self, "선택 필요", "먼저 완료폴더를 스캔하고 상품을 선택하세요.")
            return
        sections_dir = product.folder / "sections"
        section_paths = self._valid_section_files(sections_dir)
        if len(section_paths) < REQUIRED_SECTION_IMAGE_COUNT:
            QMessageBox.warning(
                self,
                "합치기 불가",
                f"완료폴더 섹션 이미지가 부족합니다.\n{sections_dir}\n현재 {len(section_paths)}/{REQUIRED_SECTION_IMAGE_COUNT}장",
            )
            return
        target_detail = product.folder / "detail_page.png"
        try:
            self._merge_section_images(section_paths, target_detail, width=860)
            if not self._is_valid_image_file(target_detail):
                raise RuntimeError(f"합본 파일 검증 실패: {target_detail}")
            metadata_path = product.folder / "metadata.json"
            metadata = self._read_json_file(metadata_path)
            metadata["detail_page_path"] = str(target_detail)
            metadata["completed_detail_page_path"] = str(target_detail)
            metadata["section_paths"] = [str(path) for path in section_paths]
            metadata["sections_merged_at"] = datetime.now().isoformat(timespec="seconds")
            self._write_json_file(metadata_path, metadata)
        except Exception as exc:
            QMessageBox.warning(self, "합치기 실패", str(exc))
            return
        self.statusBar().showMessage(f"상세페이지 합치기 완료: {target_detail}")
        QMessageBox.information(self, "합치기 완료", f"완료폴더 섹션 이미지를 다시 합쳤습니다.\n\n{target_detail}")
        self._scan_completed_market_folder(select_index=self.current_market_index)

    def _refresh_market_preview(self) -> None:
        product = self._selected_market_product()
        if product is None:
            self.market_preview_label.setPixmap(QPixmap())
            self.market_preview_label.setText("완료폴더를 스캔한 뒤 상품을 선택하세요.")
            self.market_payload_box.setPlainText("")
            self.market_price_banner_label.setText("판매가 산출: 완료폴더를 스캔하고 상품을 선택하면 표시됩니다.")
            self.market_auto_status_label.setText(
                "자동 산출: SEO 제목, 연관 키워드, 카테고리 후보, 옵션 조합, 상품고시 초안, 이미지 업로드 manifest"
            )
            return
        preview_path = product.thumbnail_paths[0] if self._is_valid_image_file(product.thumbnail_paths[0]) else product.detail_page_path
        pixmap = QPixmap(str(preview_path))
        if not pixmap.isNull():
            self.market_preview_label.setPixmap(
                pixmap.scaled(260, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self.market_preview_label.setPixmap(QPixmap())
            self.market_preview_label.setText("미리보기 이미지를 열지 못했습니다.")
        market_dir = product.folder / "market"
        naver_payload = self._read_json_file(market_dir / "naver_payload.json")
        coupang_payload = self._read_json_file(market_dir / "coupang_payload.json")
        seo_keywords = self._read_json_file(market_dir / "seo_keywords.json")
        preview = {
            "상품코드": product.code,
            "상품명": product.product_name,
            "상세페이지": str(product.detail_page_path),
            "썸네일": [str(path) for path in product.thumbnail_paths],
            "검수이슈": product.issues,
            "네이버초안": "있음" if naver_payload else "없음",
            "쿠팡초안": "있음" if coupang_payload else "없음",
        }
        if naver_payload:
            preview["네이버_SEO"] = naver_payload.get("_draft", {}).get("seo_title", "")
        if coupang_payload:
            preview["쿠팡_상품명"] = coupang_payload.get("sellerProductName", "")
        if seo_keywords:
            preview["연관키워드"] = seo_keywords.get("related_keywords", [])
            preview["카테고리후보"] = seo_keywords.get("category_candidates", [])
        pricing_preview = self._market_pricing_preview(product)
        preview["가격산출"] = pricing_preview
        pricing_text = self._market_pricing_banner_text(pricing_preview)
        option_plan = self._market_option_plan(product)
        option_count = len(option_plan.get("options", [])) if isinstance(option_plan, dict) else 0
        option_groups = option_plan.get("option_groups", []) if isinstance(option_plan, dict) else []
        option_names = [
            str(group.get("name") or "")
            for group in option_groups
            if isinstance(group, dict) and str(group.get("name") or "").strip()
        ]
        option_source = "직접 입력값" if self._market_field_text("market_options_text") else "URL 수집값 자동"
        self.market_price_banner_label.setText(pricing_text)
        self.market_auto_status_label.setText(
            f"{pricing_text}\n옵션 산출: {option_source} · 옵션그룹 {', '.join(option_names) if option_names else '기본'} · 조합 {option_count}개"
        )
        self.market_payload_box.setPlainText(json.dumps(preview, ensure_ascii=False, indent=2))

    def _read_json_file(self, path: Path) -> dict[str, object]:
        if not path.exists() or not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_json_file(self, path: Path, data: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_market_draft_bundle(
        self,
        product: MarketProduct,
        live_platforms: set[str] | None = None,
    ) -> dict[str, object]:
        live_targets = {platform for platform in (live_platforms or set()) if platform in {"naver", "coupang"}}
        for platform in sorted(live_targets):
            self._prepare_market_live_requirements(product, platform)
        draft = self._build_market_draft_bundle(product, include_coupang_animated_webp="coupang" in live_targets)
        if live_targets:
            draft = self._apply_live_ready_market_draft(product, draft, live_targets)
        market_dir = product.folder / "market"
        self._write_json_file(market_dir / "naver_payload.json", draft["naver_payload"])
        self._write_json_file(market_dir / "coupang_payload.json", draft["coupang_payload"])
        self._write_json_file(market_dir / "upload_manifest.json", draft["upload_manifest"])
        self._write_json_file(market_dir / "seo_keywords.json", draft["seo_keywords"])
        self._write_json_file(market_dir / "market_option_plan.json", draft["market_option_plan"])
        self._write_json_file(market_dir / "registration_plan.json", draft["registration_plan"])
        (market_dir / "naver_market_prompt.txt").write_text(str(draft["naver_chatgpt_prompt"]), encoding="utf-8")
        (market_dir / "coupang_market_prompt.txt").write_text(str(draft["coupang_chatgpt_prompt"]), encoding="utf-8")
        (market_dir / "chatgpt_market_prompt.txt").write_text(str(draft["chatgpt_prompt"]), encoding="utf-8")
        return draft

    def _apply_live_ready_market_draft(
        self,
        product: MarketProduct,
        draft: dict[str, object],
        live_platforms: set[str],
    ) -> dict[str, object]:
        settings = self._market_settings_data(include_secrets=True)
        copy_data = self._build_market_copy(product)
        seo_keywords_raw = draft.get("seo_keywords")
        seo_keywords: dict[str, object] = dict(seo_keywords_raw) if isinstance(seo_keywords_raw, dict) else {}

        if "naver" in live_platforms:
            payload = draft.get("naver_payload")
            if isinstance(payload, dict):
                prepared = self._live_ready_market_payload("naver", dict(payload), settings)
                prompt = self._build_naver_market_chatgpt_prompt(product, copy_data, prepared)
                draft["naver_payload"] = prepared
                draft["naver_chatgpt_prompt"] = prompt
                seo_keywords["naver_chatgpt_prompt"] = prompt
                seo_keywords["naver_chatgpt_seo_prompt"] = copy_data.get("naver_chatgpt_seo_prompt", "")
                seo_keywords["naver_search_tags"] = copy_data.get("naver_search_tags", [])

        if "coupang" in live_platforms:
            payload = draft.get("coupang_payload")
            if isinstance(payload, dict):
                prepared = self._live_ready_market_payload("coupang", dict(payload), settings)
                prompt = self._build_coupang_market_chatgpt_prompt(product, copy_data, prepared)
                draft["coupang_payload"] = prepared
                draft["coupang_chatgpt_prompt"] = prompt
                seo_keywords["coupang_chatgpt_prompt"] = prompt
                seo_keywords["coupang_chatgpt_seo_prompt"] = copy_data.get("coupang_chatgpt_seo_prompt", "")
                seo_keywords["coupang_search_tags"] = copy_data.get("coupang_search_tags", [])

        draft["seo_keywords"] = seo_keywords
        naver_prompt = str(draft.get("naver_chatgpt_prompt") or "")
        coupang_prompt = str(draft.get("coupang_chatgpt_prompt") or "")
        draft["chatgpt_prompt"] = self._build_market_chatgpt_prompt(product, copy_data, naver_prompt, coupang_prompt)
        return draft

    def _live_ready_market_payload(
        self,
        platform: str,
        payload: dict[str, object],
        settings: dict[str, str],
    ) -> dict[str, object]:
        draft_info = payload.get("_draft")
        stripped = self._strip_draft_keys(copy.deepcopy(payload))
        prepared = dict(stripped) if isinstance(stripped, dict) else {}
        if platform == "naver":
            prepared = self._prepare_naver_live_payload(prepared, settings)
        elif platform == "coupang":
            category_meta = self._fetch_coupang_category_meta(prepared.get("displayCategoryCode"), settings)
            prepared = self._apply_coupang_category_meta(prepared, category_meta)
            prepared["requested"] = True
            if prepared.get("manufacturer") and not prepared.get("manufacture"):
                prepared["manufacture"] = prepared.get("manufacturer")
            prepared.pop("manufacturer", None)
        if isinstance(draft_info, dict):
            prepared["_draft"] = draft_info
        return prepared

    def _format_won(self, value: object) -> str:
        if isinstance(value, (int, float)):
            amount = int(round(value))
        else:
            amount = self._positive_int(value)
        return f"{amount:,}원" if amount else "0원"

    def _market_pricing_preview(self, product: MarketProduct) -> dict[str, object]:
        settings = self._market_settings_data(include_secrets=False)
        naver = self._market_pricing_plan(product, settings, "naver")
        coupang = self._market_pricing_plan(product, settings, "coupang")
        result = {
            "원가": self._format_won(naver.get("total_cost", 0)),
            "네이버판매가": self._format_won(naver.get("sale_price", 0)),
            "쿠팡판매가": self._format_won(coupang.get("sale_price", 0)),
            "마진율": f"{naver.get('target_net_margin_rate', 0)}%",
            "네이버수수료": f"{naver.get('fee_rate', 0)}%",
            "쿠팡수수료": f"{coupang.get('fee_rate', 0)}%",
            "부가세": f"{naver.get('tax_rate', 0)}%",
            "네이버예상순익": self._format_won(naver.get("estimated_net_profit", 0)),
            "쿠팡예상순익": self._format_won(coupang.get("estimated_net_profit", 0)),
            "정책": naver.get("pricing_policy", ""),
        }

        return result

    def _market_pricing_banner_text(self, pricing: dict[str, object]) -> str:
        return (
            "판매가 산출: "
            f"원가 {pricing.get('원가', '0원')} · "
            f"네이버 {pricing.get('네이버판매가', '0원')} · "
            f"쿠팡 {pricing.get('쿠팡판매가', '0원')} · "
            f"기준 마진 {pricing.get('마진율', '0%')} · "
            f"네이버 수수료 {pricing.get('네이버수수료', '0%')} · "
            f"쿠팡 수수료 {pricing.get('쿠팡수수료', '0%')} · "
            f"부가세 {pricing.get('부가세', '10%')}"
        )

    def _generate_selected_market_draft(self) -> None:
        product = self._selected_market_product()
        if product is None:
            QMessageBox.information(self, "선택 필요", "먼저 완료폴더를 스캔하고 상품을 선택하세요.")
            return
        self._persist_market_settings_silent()
        draft = self._write_market_draft_bundle(product, {"naver", "coupang"})
        market_dir = product.folder / "market"
        naver_pricing = draft["naver_payload"].get("_draft", {}).get("pricing", {}) if isinstance(draft.get("naver_payload"), dict) else {}
        coupang_pricing = draft["coupang_payload"].get("_draft", {}).get("pricing", {}) if isinstance(draft.get("coupang_payload"), dict) else {}
        pricing_text = self._market_pricing_banner_text(
            {
                "원가": self._format_won(naver_pricing.get("total_cost", 0)),
                "네이버판매가": self._format_won(naver_pricing.get("sale_price", 0)),
                "쿠팡판매가": self._format_won(coupang_pricing.get("sale_price", 0)),
                "마진율": f"{naver_pricing.get('target_net_margin_rate', 0)}%",
                "네이버수수료": f"{naver_pricing.get('fee_rate', 0)}%",
                "쿠팡수수료": f"{coupang_pricing.get('fee_rate', 0)}%",
                "부가세": f"{naver_pricing.get('tax_rate', 0)}%",
            }
        )
        self.market_price_banner_label.setText(pricing_text)
        self.statusBar().showMessage(f"등록 초안 생성 완료: {market_dir}")
        QMessageBox.information(
            self,
            "초안 생성 완료",
            f"네이버/쿠팡 등록 초안을 만들었습니다.\n\n{pricing_text}\n\n{market_dir}",
        )
        self._scan_completed_market_folder()

    def _prepare_selected_market_upload_manifest(self) -> None:
        product = self._selected_market_product()
        if product is None:
            QMessageBox.information(self, "선택 필요", "먼저 완료폴더를 스캔하고 상품을 선택하세요.")
            return
        self._persist_market_settings_silent()
        manifest = self._build_upload_manifest(product)
        self._write_json_file(product.folder / "market" / "upload_manifest.json", manifest)
        self.statusBar().showMessage("이미지 업로드 준비 manifest를 갱신했습니다.")
        QMessageBox.information(
            self,
            "업로드 준비 완료",
            "로컬 이미지 목록과 마켓 업로드 대상 파일을 정리했습니다.\n"
            "live 등록 버튼을 누르면 네이버 이미지 업로드 API로 HTTPS URL을 자동 발급하고 payload에 반영합니다.",
        )
        self._scan_completed_market_folder()

    def _publish_selected_market(self, platform: str) -> None:
        if platform not in {"naver", "coupang"}:
            QMessageBox.warning(self, "등록 차단", "네이버 등록 또는 쿠팡 등록을 따로 실행하세요.")
            return
        start_index = self._selected_market_index()
        if start_index < 0:
            start_index = self.current_market_index
        if start_index < 0 or start_index >= len(self.market_products):
            QMessageBox.information(self, "선택 필요", "먼저 완료폴더를 스캔하고 상품을 선택하세요.")
            return
        self._persist_market_settings_silent()
        platforms = [platform]
        products = self.market_products[start_index:]
        first_product = products[0]
        pricing_text = self._market_pricing_banner_text(self._market_pricing_preview(first_product))
        platform_label = "네이버" if platform == "naver" else "쿠팡"
        answer = QMessageBox.question(
            self,
            "실제 API 등록 확인",
            f"{platform_label} live API 등록을 선택 상품부터 아래로 {len(products)}개 이어서 진행할까요?\n\n"
            f"첫 상품 기준: {pricing_text}\n\n"
            "이미 live 완료된 마켓은 건너뛰고, 실패한 상품은 기록한 뒤 다음 상품으로 계속 진행합니다.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            self.market_auto_status_label.setText(f"등록 취소: {platform_label} live 등록을 시작하지 않았습니다.")
            return

        batch_summary: list[tuple[MarketProduct, dict[str, object]]] = []
        has_problem = False
        for offset, product in enumerate(products, start=start_index):
            self.current_market_index = offset
            self.market_table.selectRow(offset)
            QApplication.processEvents()
            publish_result_path = product.folder / "market" / "publish_result.json"
            publish_result = self._read_json_file(publish_result_path)
            self.market_auto_status_label.setText(
                f"live 등록 진행 {offset - start_index + 1}/{len(products)} · {product.code}"
            )
            for target in platforms:
                existing = publish_result.get(target) if isinstance(publish_result, dict) else None
                existing_status = str(existing.get("status") or "") if isinstance(existing, dict) else ""
                if self._market_publish_succeeded(existing_status):
                    continue
                result = self._attempt_market_publish(product, target, ask_confirmation=False, show_messages=False)
                publish_result[target] = result
                if not self._market_publish_succeeded(str(result.get("status") or "")) or self._market_publish_warning_text(result):
                    has_problem = True
                self._write_json_file(publish_result_path, publish_result)
                QApplication.processEvents()
            batch_summary.append((product, {key: publish_result.get(key) for key in platforms}))

        next_index = min(start_index + len(products), max(len(self.market_products) - 1, 0))
        self._scan_completed_market_folder(select_index=next_index)
        self._show_market_batch_publish_summary(platforms, batch_summary, has_problem)

    def _show_market_publish_summary(
        self,
        product: MarketProduct,
        platforms: list[str],
        publish_result: dict[str, object],
    ) -> None:
        lines = [f"상품코드: {product.code}", f"상품명: {product.product_name}", ""]
        has_problem = False
        for platform in platforms:
            raw_result = publish_result.get(platform)
            result = raw_result if isinstance(raw_result, dict) else {}
            line = self._market_publish_result_line(platform, result)
            lines.append(line)
            status = str(result.get("status") or "")
            if not self._market_publish_succeeded(status) or self._market_publish_warning_text(result):
                has_problem = True
        message = "\n".join(lines)
        self.market_auto_status_label.setText("등록 완료 요약\n" + message)
        self.market_payload_box.setPlainText(json.dumps({key: publish_result.get(key) for key in platforms}, ensure_ascii=False, indent=2))
        if has_problem:
            QMessageBox.warning(self, "등록 결과 확인", message)
        else:
            QMessageBox.information(self, "등록 완료", message)

    def _show_market_batch_publish_summary(
        self,
        platforms: list[str],
        batch_summary: list[tuple[MarketProduct, dict[str, object]]],
        has_problem: bool,
    ) -> None:
        lines = [f"처리 상품: {len(batch_summary)}개", ""]
        for product, result_by_platform in batch_summary[:30]:
            status_parts = []
            for platform in platforms:
                result = result_by_platform.get(platform)
                result_dict = result if isinstance(result, dict) else {}
                status_parts.append(self._market_publish_result_line(platform, result_dict))
            lines.append(f"{product.code}: " + " / ".join(status_parts))
        if len(batch_summary) > 30:
            lines.append(f"...외 {len(batch_summary) - 30}개")
        message = "\n".join(lines)
        self.market_auto_status_label.setText("등록 완료 요약\n" + message)
        self.market_payload_box.setPlainText(
            json.dumps(
                [
                    {"product_code": product.code, **{key: result_by_platform.get(key) for key in platforms}}
                    for product, result_by_platform in batch_summary
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        if has_problem:
            QMessageBox.warning(self, "등록 결과 확인", message)
        else:
            QMessageBox.information(self, "등록 완료", message)

    def _market_publish_succeeded(self, status: str) -> bool:
        text = str(status or "").strip()
        return text.startswith("live 완료") or text.startswith("live 수정 완료")

    def _market_publish_result_line(self, platform: str, result: dict[str, object]) -> str:
        label = "네이버" if platform == "naver" else "쿠팡" if platform == "coupang" else platform
        status = str(result.get("status") or "결과 없음")
        product_no = str(result.get("product_no") or "").strip()
        parts = [f"{label}: {status}"]
        if product_no and product_no.upper() != "ERROR":
            parts.append(f"상품번호 {product_no}")
        warning = self._market_publish_warning_text(result)
        if warning:
            parts.append(f"확인 필요: {warning}")
        return " / ".join(parts)

    def _market_publish_warning_text(self, result: dict[str, object]) -> str:
        response = result.get("response")
        if not isinstance(response, dict):
            return ""
        error_items = response.get("errorItems")
        details = str(response.get("details") or "").strip()
        message = str(response.get("message") or "").strip()
        if error_items or details:
            return self._clip_text(details or message or "응답에 확인 항목이 있습니다.", 260)
        return ""

    def _attempt_market_publish(
        self,
        product: MarketProduct,
        platform: str,
        ask_confirmation: bool = True,
        show_messages: bool = True,
    ) -> dict[str, object]:
        mode = self._force_live_market_upload_mode()
        try:
            self._write_market_draft_bundle(product)
        except Exception as exc:
            if show_messages:
                QMessageBox.warning(self, "초안 생성 실패", f"{platform} 등록 전 초안 갱신에 실패했습니다.\n\n{exc}")
            return {
                "status": "초안 생성 실패",
                "mode": mode,
                "error": str(exc),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        try:
            self._write_market_draft_bundle(product, {platform})
        except Exception as exc:
            if show_messages:
                QMessageBox.warning(self, "live 조회 실패", f"{platform} 등록 전 자동 조회에 실패했습니다.\n\n{exc}")
            return {
                "status": "live 조회 실패",
                "mode": mode,
                "error": str(exc),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        issues = self._market_publish_blockers(product, platform)
        if issues:
            if show_messages:
                QMessageBox.warning(
                    self,
                    "등록 차단",
                    f"{platform} 등록을 막았습니다.\n\n" + "\n".join(f"- {issue}" for issue in issues),
                )
            return {
                "status": "검수 필요",
                "mode": mode,
                "blocked_issues": issues,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        if ask_confirmation:
            pricing_text = self._market_pricing_banner_text(self._market_pricing_preview(product))
            answer = QMessageBox.question(
                self,
                "실제 API 등록 확인",
                f"{platform} live API로 실제 상품 등록을 실행할까요?\n"
                f"{pricing_text}\n"
                "저장된 API 키, 카테고리, 출고지/반품지, 이미지 업로드 결과를 사용합니다.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return {
                    "status": "사용자 취소",
                    "mode": mode,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
        return self._attempt_live_market_publish(product, platform)

    def _force_live_market_upload_mode(self) -> str:
        mode = (self._market_field_text("upload_mode") or "").strip().lower()
        if mode != "live":
            self._set_market_field_text("upload_mode", "live")
            self._persist_market_settings_silent()
            self.statusBar().showMessage("마켓 등록은 실제 API 호출용 live 모드로 실행합니다.")
        return "live"

    def _prepare_market_live_requirements(self, product: MarketProduct, platform: str) -> None:
        category_key = "naver_category_id" if platform == "naver" else "coupang_category_id"
        if not self._market_field_text(category_key):
            self.market_resolved_settings.pop(category_key, None)
        settings = self._market_settings_data(include_secrets=True)
        changed = False
        if platform == "naver":
            changed = self._ensure_naver_live_settings(product, settings) or changed
        elif platform == "coupang":
            changed = self._ensure_coupang_live_settings(product, settings) or changed
        if changed:
            self._persist_market_settings_silent()

    def _ensure_naver_live_settings(self, product: MarketProduct, settings: dict[str, str]) -> bool:
        changed = False
        category_code = self._effective_category_code(product, "naver", settings)
        if self._is_auto_lookup_value(category_code):
            resolved_category = self._resolve_naver_category_id(product, settings)
            resolved_key = self._product_category_setting_key(product, "naver_category_id")
            if resolved_category and self.market_resolved_settings.get(resolved_key) != resolved_category:
                self.market_resolved_settings[resolved_key] = resolved_category
                changed = True
            settings = self._market_settings_data(include_secrets=True)
        outbound_code = self._effective_location_code(settings, "naver", "outbound")
        return_code = self._effective_location_code(settings, "naver", "return")
        if (
            self._is_auto_lookup_value(outbound_code)
            or self._is_auto_lookup_value(return_code)
            or any(
                self._is_auto_lookup_value(settings.get(key, ""))
                for key in ("naver_as_phone", "company_contact_number", "return_zip_code", "return_address", "return_address_detail")
            )
        ):
            changed = self._resolve_naver_address_settings(settings) or changed
            settings = self._market_settings_data(include_secrets=True)
        current_origin = self._normalize_market_origin(settings.get("origin", "")) or "중국"
        if self._clean_market_field_text(settings.get("origin", "")) != current_origin:
            changed = self._set_market_setting_value("origin", current_origin) or changed
            settings = self._market_settings_data(include_secrets=True)
        origin_area_code = str(settings.get("naver_origin_area_code") or "").strip()
        if not origin_area_code or self._is_auto_lookup_value(origin_area_code):
            changed = self._set_market_setting_value("naver_origin_area_code", self._resolve_naver_origin_area_code(settings)) or changed
            settings = self._market_settings_data(include_secrets=True)
        source_origin = self._market_source_origin(product)
        if source_origin:
            if self._normalize_market_origin(settings.get("origin", "")) != source_origin:
                changed = self._set_market_setting_value("origin", source_origin) or changed
                settings = self._market_settings_data(include_secrets=True)
                resolved_origin_code = self._resolve_naver_origin_area_code(settings, force_lookup=True)
                if resolved_origin_code and str(settings.get("naver_origin_area_code") or "").strip() != resolved_origin_code:
                    changed = self._set_market_setting_value("naver_origin_area_code", resolved_origin_code) or changed
                    settings = self._market_settings_data(include_secrets=True)
            else:
                origin_area_code = str(settings.get("naver_origin_area_code") or "").strip()
                if not origin_area_code or self._is_auto_lookup_value(origin_area_code):
                    resolved_origin_code = self._resolve_naver_origin_area_code(settings)
                    if resolved_origin_code and str(settings.get("naver_origin_area_code") or "").strip() != resolved_origin_code:
                        changed = self._set_market_setting_value("naver_origin_area_code", resolved_origin_code) or changed
                        settings = self._market_settings_data(include_secrets=True)
        if self._is_auto_lookup_value(settings.get("naver_delivery_company", "")):
            changed = self._set_market_setting_value("naver_delivery_company", "CJGLS") or changed
        settings = self._market_settings_data(include_secrets=True)
        if self._is_auto_lookup_value(settings.get("naver_as_phone", "")):
            phone = settings.get("company_contact_number") or ""
            if phone and not self._is_auto_lookup_value(phone) and re.search(r"\d{2,}", str(phone)):
                changed = self._set_market_setting_value("naver_as_phone", phone) or changed
        return changed

    def _ensure_coupang_live_settings(self, product: MarketProduct, settings: dict[str, str]) -> bool:
        changed = False
        category_code = self._effective_category_code(product, "coupang", settings)
        if self._is_auto_lookup_value(category_code):
            resolved_category = self._resolve_coupang_category_id(product, settings)
            resolved_key = self._product_category_setting_key(product, "coupang_category_id")
            if resolved_category and self.market_resolved_settings.get(resolved_key) != resolved_category:
                self.market_resolved_settings[resolved_key] = resolved_category
                changed = True
            settings = self._market_settings_data(include_secrets=True)
        vendor_user_id = str(settings.get("coupang_vendor_user_id") or "").strip()
        outbound_code = self._effective_location_code(settings, "coupang", "outbound")
        return_code = self._effective_location_code(settings, "coupang", "return")
        if (
            not vendor_user_id
            or self._is_auto_lookup_value(vendor_user_id)
            or self._is_auto_lookup_value(outbound_code)
            or self._invalid_coupang_location_code("outbound", outbound_code)
        ):
            changed = self._resolve_coupang_existing_product_settings(settings) or changed
            settings = self._market_settings_data(include_secrets=True)
            outbound_code = self._effective_location_code(settings, "coupang", "outbound")
            return_code = self._effective_location_code(settings, "coupang", "return")
        if self._is_auto_lookup_value(outbound_code) or self._invalid_coupang_location_code("outbound", outbound_code):
            changed = self._resolve_coupang_outbound_settings(settings) or changed
            settings = self._market_settings_data(include_secrets=True)
        if self._is_auto_lookup_value(return_code) or self._invalid_coupang_location_code("return", return_code) or any(
            self._is_auto_lookup_value(settings.get(key, ""))
            for key in ("return_charge_name", "company_contact_number", "return_zip_code", "return_address", "return_address_detail")
        ):
            changed = self._resolve_coupang_return_settings(settings) or changed
            settings = self._market_settings_data(include_secrets=True)
        if self._is_auto_lookup_value(settings.get("coupang_delivery_company_code", "")):
            changed = self._set_market_setting_value("coupang_delivery_company_code", "CJGLS") or changed
        return changed

    def _naver_get_json(self, endpoint: str, settings: dict[str, str], params: dict[str, object] | None = None) -> object:
        if requests is None:
            raise RuntimeError("requests 패키지가 없어 네이버 조회를 할 수 없습니다.")
        token = self._naver_access_token(settings)
        response = requests.get(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
            timeout=60,
        )
        body = self._safe_response_json(response)
        if response.status_code >= 400:
            raise RuntimeError(f"네이버 조회 실패 {response.status_code}: {response.text[:1000]}")
        return body

    def _naver_response_rows(self, value: object) -> list[dict[str, object]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            for key in ("data", "contents", "content"):
                rows = value.get(key)
                if isinstance(rows, list):
                    return [item for item in rows if isinstance(item, dict)]
        return []

    def _prepare_naver_live_payload(
        self,
        payload: dict[str, object],
        settings: dict[str, str],
    ) -> dict[str, object]:
        prepared = copy.deepcopy(payload)
        origin_product = prepared.get("originProduct")
        if not isinstance(origin_product, dict):
            return prepared
        detail_attribute = origin_product.get("detailAttribute")
        if not isinstance(detail_attribute, dict):
            return prepared
        seo_info = detail_attribute.get("seoInfo")
        if not isinstance(seo_info, dict):
            seo_info = {}
        seller_tags = self._naver_live_seller_tags(seo_info.get("sellerTags"), origin_product, settings)
        if seller_tags:
            seo_info["sellerTags"] = seller_tags
        else:
            seo_info.pop("sellerTags", None)
        detail_attribute["seoInfo"] = seo_info
        detail_attribute["originAreaInfo"] = self._naver_live_origin_area_info(
            detail_attribute.get("originAreaInfo"),
            settings,
        )
        detail_attribute.pop("productAttributes", None)
        product_attributes = self._naver_live_product_attributes(origin_product, settings)
        if product_attributes:
            detail_attribute["productAttributes"] = product_attributes
        origin_product["detailAttribute"] = detail_attribute
        prepared["originProduct"] = origin_product
        return prepared

    def _naver_live_origin_area_info(
        self,
        origin_area_info: object,
        settings: dict[str, str],
    ) -> dict[str, object]:
        info = dict(origin_area_info) if isinstance(origin_area_info, dict) else {}
        content = (
            self._normalize_market_origin(info.get("content", ""))
            or self._normalize_market_origin(settings.get("origin", ""))
            or "\uc911\uad6d"
        )
        origin_code = str(info.get("originAreaCode") or "").strip()
        expected_origin_codes = {
            "\uc911\uad6d": "0200037",
            "\ub300\ud55c\ubbfc\uad6d": "0200014",
        }
        expected_origin_code = expected_origin_codes.get(content)
        if not origin_code or self._is_auto_lookup_value(origin_code):
            origin_code = self._naver_origin_area_code_for_origin(content, settings)
        if expected_origin_code and origin_code != expected_origin_code:
            origin_code = expected_origin_code
        if self._is_auto_lookup_value(origin_code):
            origin_code = self._resolve_naver_origin_area_code({**settings, "origin": content})
        info["originAreaCode"] = origin_code
        info["content"] = content
        info.setdefault("plural", False)
        if content != "\ub300\ud55c\ubbfc\uad6d" and not str(info.get("importer") or "").strip():
            info["importer"] = (
                self._clean_market_field_text(settings.get("manufacturer", ""))
                or self._clean_market_field_text(settings.get("brand", ""))
                or "\ud310\ub9e4\uc790 \ud655\uc778"
            )
        return info

    def _naver_live_seller_tags(
        self,
        seller_tags: object,
        origin_product: dict[str, object],
        settings: dict[str, str],
    ) -> list[dict[str, object]]:
        candidates: list[str] = []
        if isinstance(seller_tags, list):
            for tag in seller_tags:
                if isinstance(tag, dict):
                    candidates.append(str(tag.get("text") or ""))
                else:
                    candidates.append(str(tag or ""))
        if len([item for item in candidates if str(item or "").strip()]) < 5:
            candidates.extend(self._naver_tag_candidates_from_origin_product(origin_product))
        result: list[dict[str, object]] = []
        seen: set[str] = set()
        for candidate in candidates:
            tag_text = re.sub(r"[^가-힣A-Za-z0-9]", "", str(candidate or "")).strip()
            if not (2 <= len(tag_text) <= 20):
                continue
            key = tag_text.lower()
            if key in seen:
                continue
            seen.add(key)
            recommended = self._naver_recommended_tag(tag_text, settings)
            if recommended:
                result.append(recommended)
            else:
                result.append({"text": tag_text})
            if len(result) >= 10:
                break
        return result

    def _naver_tag_candidates_from_origin_product(self, origin_product: dict[str, object]) -> list[str]:
        text = " ".join(
            self._market_visible_copy_text(value)
            for value in (
                origin_product.get("name"),
                origin_product.get("detailContent"),
            )
        )
        tokens = [
            re.sub(r"[^가-힣A-Za-z0-9]", "", token)
            for token in re.split(r"\s+|,|/|>|\\|\\||·|ㆍ|-|_", text)
        ]
        blocked = {
            "끄롱마제", "중국OEM", "상품", "상품명", "핵심", "문제", "상세", "참조", "도매꾹",
            "온채널", "생활용품", "인테리어", "씻은", "돌려", "더해", "보관할",
            "매번", "불편했던", "상황", "고민했다면", "이제", "으로", "확인된", "기능", "장면", "맞춘",
        }
        return [token for token in tokens if 2 <= len(token) <= 20 and token not in blocked]

    def _naver_recommended_tag(self, tag_text: str, settings: dict[str, str]) -> dict[str, object]:
        cache: dict[str, dict[str, object] | None] = getattr(self, "_naver_recommend_tag_cache", {})
        cache_key = tag_text.lower()
        if cache_key in cache:
            cached = cache[cache_key]
            return dict(cached) if isinstance(cached, dict) else {}
        try:
            body = self._naver_get_json(NAVER_RECOMMEND_TAGS_ENDPOINT, settings, {"keyword": tag_text})
            rows = self._naver_response_rows(body)
        except Exception:
            rows = []
        normalized = re.sub(r"[^가-힣A-Za-z0-9]", "", tag_text).lower()
        picked: dict[str, object] | None = None
        for row in rows:
            row_text = str(row.get("text") or "").strip()
            row_key = re.sub(r"[^가-힣A-Za-z0-9]", "", row_text).lower()
            if row_key == normalized:
                picked = row
                break
        result: dict[str, object] = {}
        if isinstance(picked, dict) and picked.get("code") and picked.get("text"):
            result = {"code": int(picked["code"]), "text": str(picked["text"])}
        cache[cache_key] = result or None
        self._naver_recommend_tag_cache = cache
        return result

    def _naver_category_attributes(self, category_id: str, settings: dict[str, str]) -> list[dict[str, object]]:
        cache: dict[str, list[dict[str, object]]] = getattr(self, "_naver_attribute_cache", {})
        if category_id in cache:
            return cache[category_id]
        try:
            body = self._naver_get_json(NAVER_ATTRIBUTE_LIST_ENDPOINT, settings, {"categoryId": category_id})
            rows = self._naver_response_rows(body)
        except Exception:
            rows = []
        cache[category_id] = rows
        self._naver_attribute_cache = cache
        return rows

    def _naver_category_attribute_values(self, category_id: str, settings: dict[str, str]) -> list[dict[str, object]]:
        cache: dict[str, list[dict[str, object]]] = getattr(self, "_naver_attribute_value_cache", {})
        if category_id in cache:
            return cache[category_id]
        try:
            body = self._naver_get_json(NAVER_ATTRIBUTE_VALUE_LIST_ENDPOINT, settings, {"categoryId": category_id})
            rows = self._naver_response_rows(body)
        except Exception:
            rows = []
        cache[category_id] = rows
        self._naver_attribute_value_cache = cache
        return rows

    def _naver_live_product_attributes(
        self,
        origin_product: dict[str, object],
        settings: dict[str, str],
    ) -> list[dict[str, object]]:
        category_id = str(origin_product.get("leafCategoryId") or "").strip()
        if not category_id:
            return []
        attributes = self._naver_category_attributes(category_id, settings)
        values = self._naver_category_attribute_values(category_id, settings)
        values_by_seq: dict[int, list[dict[str, object]]] = {}
        for row in values:
            seq = self._positive_int(row.get("attributeSeq", ""))
            value_seq = self._positive_int(row.get("attributeValueSeq", ""))
            if seq and value_seq:
                values_by_seq.setdefault(seq, []).append(row)
        text = self._naver_product_attribute_text(origin_product)
        selected: list[dict[str, object]] = []
        seen: set[tuple[int, int]] = set()
        sorted_attributes = sorted(
            attributes,
            key=lambda row: 0 if str(row.get("attributeType") or "").upper() == "PRIMARY" else 1,
        )
        for attribute in sorted_attributes:
            if len(selected) >= 5:
                break
            seq = self._positive_int(attribute.get("attributeSeq", ""))
            if not seq:
                continue
            if str(attribute.get("attributeClassificationType") or "").upper() == "RANGE":
                continue
            choice = self._naver_select_attribute_value(attribute, values_by_seq.get(seq, []), text)
            if not choice:
                continue
            value_seq = self._positive_int(choice.get("attributeValueSeq", ""))
            if not value_seq or (seq, value_seq) in seen:
                continue
            seen.add((seq, value_seq))
            selected.append({"attributeSeq": seq, "attributeValueSeq": value_seq})
        if selected:
            return selected
        for attribute in sorted_attributes:
            seq = self._positive_int(attribute.get("attributeSeq", ""))
            name = str(attribute.get("attributeName") or "")
            if not seq or name not in {"구성", "종류", "형태"}:
                continue
            for value in values_by_seq.get(seq, []):
                value_text = str(value.get("minAttributeValue") or value.get("maxAttributeValue") or "")
                if value_text in {"본품", "기본", "일반"} or value_text:
                    value_seq = self._positive_int(value.get("attributeValueSeq", ""))
                    if value_seq:
                        return [{"attributeSeq": seq, "attributeValueSeq": value_seq}]
        return []

    def _naver_product_attribute_text(self, origin_product: dict[str, object]) -> str:
        detail_attribute = origin_product.get("detailAttribute")
        notice = detail_attribute.get("productInfoProvidedNotice") if isinstance(detail_attribute, dict) else {}
        option_info = detail_attribute.get("optionInfo") if isinstance(detail_attribute, dict) else {}
        parts = [
            origin_product.get("name"),
            origin_product.get("detailContent"),
            json.dumps(notice, ensure_ascii=False) if isinstance(notice, dict) else "",
            json.dumps(option_info, ensure_ascii=False) if isinstance(option_info, dict) else "",
        ]
        return self._market_visible_copy_text(" ".join(str(part or "") for part in parts))

    def _naver_select_attribute_value(
        self,
        attribute: dict[str, object],
        values: list[dict[str, object]],
        text: str,
    ) -> dict[str, object]:
        if not values:
            return {}
        name = str(attribute.get("attributeName") or "")
        normalized_text = self._normalize_text_key(text)
        best: tuple[int, dict[str, object]] = (0, {})
        for value in values:
            value_text = str(value.get("minAttributeValue") or value.get("maxAttributeValue") or "").strip()
            if not value_text:
                continue
            score = 0
            if value_text and value_text in text and (not re.fullmatch(r"\d+", value_text) or "단수" in name):
                score += 20
            value_key = self._normalize_text_key(value_text)
            if value_key and value_key in normalized_text and (not re.fullmatch(r"\d+", value_text) or "단수" in name):
                score += 12
            if "구성" in name and value_text == "본품":
                score += 8
            if "구성" in name and "리필" in text and "리필" in value_text:
                score += 20
            if "색상" in name or "컬러" in name:
                color_terms = ("블랙", "화이트", "그레이", "브라운", "베이지", "핑크", "블루", "레드", "옐로우", "그린", "민트", "네이비", "투명")
                if any(term in text and term in value_text for term in color_terms):
                    score += 20
            if "재질" in name:
                material_pairs = {
                    "원목": ("원목", "우드", "목재"),
                    "플라스틱": ("플라스틱", "PP", "PVC"),
                    "철제": ("철제", "스틸", "금속"),
                    "스테인리스스틸": ("스텐", "스테인리스", "스테인레스"),
                    "알루미늄": ("알루미늄",),
                    "면": ("면", "코튼"),
                    "실리콘": ("실리콘",),
                }
                for target, terms in material_pairs.items():
                    if target in value_text and any(term in text for term in terms):
                        score += 20
            if "단수" in name:
                match = re.search(r"(\d+)\s*단", text)
                if match and match.group(1) in value_text:
                    score += 25
            if "형태" in name:
                shape_pairs = {
                    "스탠드형": ("스탠드", "입식"),
                    "벽걸이형": ("벽걸이", "벽면"),
                    "폴딩형": ("접이", "접이식", "폴딩"),
                    "코너형": ("코너",),
                    "조절형": ("조절",),
                }
                for target, terms in shape_pairs.items():
                    if target in value_text and any(term in text for term in terms):
                        score += 20
            if score > best[0]:
                best = (score, value)
        if best[0] > 0:
            return best[1]
        if "구성" in name:
            for value in values:
                if str(value.get("minAttributeValue") or "") == "본품":
                    return value
        return {}

    def _coupang_get_json(self, path: str, settings: dict[str, str], params: dict[str, object] | None = None) -> object:
        if requests is None:
            raise RuntimeError("requests 패키지가 없어 쿠팡 조회를 할 수 없습니다.")
        query = urllib.parse.urlencode(params or {}, doseq=True)
        headers = self._coupang_hmac_headers("GET", path, query, "", settings)
        url = COUPANG_API_BASE_URL + path + (f"?{query}" if query else "")
        response = requests.get(
            url,
            headers={**headers, "Content-Type": "application/json;charset=UTF-8"},
            timeout=60,
        )
        body = self._safe_response_json(response)
        if response.status_code >= 400:
            raise RuntimeError(f"쿠팡 조회 실패 {response.status_code}: {response.text[:1000]}")
        return body

    def _coupang_post_json(self, path: str, settings: dict[str, str], payload: dict[str, object]) -> object:
        if requests is None:
            raise RuntimeError("requests 패키지가 없어 쿠팡 조회를 할 수 없습니다.")
        body_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        headers = self._coupang_hmac_headers("POST", path, "", body_text, settings)
        url = COUPANG_API_BASE_URL + path
        response = requests.post(
            url,
            headers={**headers, "Content-Type": "application/json;charset=UTF-8"},
            data=body_text.encode("utf-8"),
            timeout=60,
        )
        body = self._safe_response_json(response)
        if response.status_code >= 400:
            raise RuntimeError(f"쿠팡 조회 실패 {response.status_code}: {response.text[:1000]}")
        return body

    def _resolve_naver_category_id(self, product: MarketProduct, settings: dict[str, str]) -> str:
        queries = self._naver_category_lookup_queries(product)
        errors: list[str] = []
        for query in queries:
            for params in ({"name": query}, {"last": "true", "name": query}):
                try:
                    body = self._naver_get_json(NAVER_CATEGORY_LIST_ENDPOINT, settings, params)
                    rows = self._rank_naver_category_rows(body, query, product)
                    for row in rows:
                        code = self._first_code_value(
                            row,
                            ("leafCategoryId", "wholeCategoryId", "categoryId", "id", "code"),
                        )
                        if code and not self._is_auto_lookup_value(code):
                            return code
                except Exception as exc:
                    errors.append(str(exc))
        raise RuntimeError("네이버 카테고리 자동 조회 실패: " + " / ".join(errors[-3:]))

    def _resolve_coupang_category_id(self, product: MarketProduct, settings: dict[str, str]) -> str:
        queries = self._category_lookup_queries(product)
        path = settings.get("coupang_category_recommendation_path") or COUPANG_CATEGORY_RECOMMENDATION_PATH
        errors: list[str] = []
        for query in queries:
            payload = {
                "productName": query,
                "productDescription": self._plain_text_excerpt(product.result_text, 1000),
                "brand": self._clean_market_field_text(settings.get("brand", "")) or DEFAULT_MARKET_BRAND,
                "sellerSkuCode": product.code,
            }
            for body_payload in (payload, {"productName": query, "sellerSkuCode": product.code}):
                try:
                    body = self._coupang_post_json(path, settings, body_payload)
                    rows = self._rank_lookup_rows(body, query, self._infer_market_category_text(product))
                    for row in rows:
                        code = self._first_code_value(
                            row,
                            ("displayCategoryCode", "predictedCategoryId", "categoryId", "categoryCode"),
                        )
                        if self._looks_like_coupang_display_category_code(code):
                            return code
                except Exception as exc:
                    errors.append(str(exc))
        raise RuntimeError("쿠팡 카테고리 자동 조회 실패: " + " / ".join(errors[-3:]))

    def _looks_like_coupang_display_category_code(self, value: str | object) -> bool:
        code = self._clean_market_field_text(value)
        return bool(re.fullmatch(r"\d{5,12}", code))

    def _resolve_naver_address_settings(self, settings: dict[str, str]) -> bool:
        errors: list[str] = []
        for params in ({"page": 1, "size": 100}, {"page": 0, "size": 100}, {}):
            try:
                body = self._naver_get_json(NAVER_ADDRESSBOOKS_ENDPOINT, settings, params)
                rows = [row for row in self._iter_json_dicts(body) if self._first_code_value(row, ("addressBookNo", "addressBookId", "addressId", "id", "placeId"))]
                if not rows:
                    continue
                outbound = self._pick_address_row(rows, "outbound") or rows[0]
                ret = self._pick_address_row(rows, "return") or outbound
                changed = False
                outbound_code = self._first_code_value(outbound, ("addressBookNo", "addressBookId", "addressId", "id", "placeId"))
                return_code = self._first_code_value(ret, ("addressBookNo", "addressBookId", "addressId", "id", "placeId"))
                changed = self._set_market_setting_value("naver_outbound_place_code", outbound_code) or changed
                changed = self._set_market_setting_value("naver_return_center_code", return_code) or changed
                changed = self._set_market_setting_value("outbound_place_code", outbound_code) or changed
                changed = self._set_market_setting_value("return_center_code", return_code) or changed
                changed = self._fill_contact_address_values(ret) or changed
                phone = self._first_text_value(
                    ret,
                    ("phoneNumber", "phoneNumber1", "phoneNumber2", "telNo", "telephoneNumber", "mobileNumber", "contactNumber"),
                )
                if phone:
                    changed = self._set_market_setting_value("naver_as_phone", phone) or changed
                return changed
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError("네이버 주소록 자동 조회 실패: " + " / ".join(errors[-3:]))

    def _resolve_coupang_outbound_settings(self, settings: dict[str, str]) -> bool:
        body = self._coupang_get_json(
            COUPANG_OUTBOUND_SHIPPING_PLACES_PATH,
            settings,
            {"pageNum": 1, "pageSize": 50},
        )
        rows = [
            row
            for row in self._iter_json_dicts(body)
            if self._first_code_value(row, ("outboundShippingPlaceCode", "shippingPlaceCode", "placeCode"))
        ]
        if not rows:
            raise RuntimeError(f"쿠팡 출고지 조회 응답에서 코드를 찾지 못했습니다: {body}")
        row = rows[0]
        code = self._first_code_value(row, ("outboundShippingPlaceCode", "shippingPlaceCode", "placeCode"))
        changed = self._set_market_setting_value("coupang_outbound_place_code", code)
        changed = self._set_market_setting_value("outbound_place_code", code) or changed
        return changed

    def _resolve_coupang_return_settings(self, settings: dict[str, str]) -> bool:
        vendor_id = str(settings.get("coupang_vendor_id") or "").strip()
        if not vendor_id:
            raise RuntimeError("쿠팡 반품지 조회에는 vendorId가 필요합니다.")
        path = COUPANG_RETURN_SHIPPING_CENTERS_PATH_TEMPLATE.format(vendorId=urllib.parse.quote(vendor_id, safe=""))
        body = self._coupang_get_json(path, settings)
        rows = [
            row
            for row in self._iter_json_dicts(body)
            if self._first_code_value(row, ("returnCenterCode", "returnShippingCenterCode", "centerCode"))
        ]
        if not rows:
            raise RuntimeError(f"쿠팡 반품지 조회 응답에서 코드를 찾지 못했습니다: {body}")
        row = rows[0]
        code = self._first_code_value(row, ("returnCenterCode", "returnShippingCenterCode", "centerCode"))
        changed = self._set_market_setting_value("coupang_return_center_code", code)
        changed = self._set_market_setting_value("return_center_code", code) or changed
        changed = self._fill_contact_address_values(row) or changed
        return changed

    def _resolve_coupang_existing_product_settings(self, settings: dict[str, str]) -> bool:
        vendor_id = str(settings.get("coupang_vendor_id") or "").strip()
        if not vendor_id:
            raise RuntimeError("쿠팡 기존 상품 조회에는 vendorId가 필요합니다.")
        body = self._coupang_get_json(
            COUPANG_PRODUCT_CREATE_PATH,
            settings,
            {"vendorId": vendor_id, "maxPerPage": 10},
        )
        product_ids = [
            self._first_code_value(row, ("sellerProductId",))
            for row in self._iter_json_dicts(body)
        ]
        errors: list[str] = []
        for seller_product_id in [item for item in product_ids if item][:5]:
            try:
                detail = self._coupang_get_json(f"{COUPANG_PRODUCT_CREATE_PATH}/{seller_product_id}", settings)
            except Exception as exc:
                errors.append(str(exc))
                continue
            row = detail.get("data") if isinstance(detail, dict) and isinstance(detail.get("data"), dict) else detail
            if not isinstance(row, dict):
                continue
            changed = False
            vendor_user_id = self._first_text_value(row, ("vendorUserId", "vendorUserID", "userId"))
            outbound_code = self._first_code_value(row, ("outboundShippingPlaceCode", "shippingPlaceCode", "placeCode"))
            if vendor_user_id:
                changed = self._set_market_setting_value("coupang_vendor_user_id", vendor_user_id) or changed
            if outbound_code:
                changed = self._set_market_setting_value("coupang_outbound_place_code", outbound_code) or changed
            if changed:
                return True
        reason = " / ".join(errors[-3:]) if errors else "기존 승인 상품 상세에서 vendorUserId/outboundShippingPlaceCode를 찾지 못했습니다."
        raise RuntimeError("쿠팡 기존 상품 자동 조회 실패: " + reason)

    def _resolve_naver_origin_area_code(self, settings: dict[str, str], force_lookup: bool = False) -> str:
        origin = self._normalize_market_origin(settings.get("origin", "")) or "중국"
        configured_code = str(settings.get("naver_origin_area_code") or "").strip()
        if configured_code and not self._is_auto_lookup_value(configured_code) and not force_lookup:
            return configured_code
        if origin == "중국":
            return "0200037"
        if origin == "대한민국":
            return "0200014"
        errors: list[str] = []
        for params in ({"name": origin}, {"searchKeyword": origin}, {}):
            try:
                body = self._naver_get_json(NAVER_ORIGIN_AREAS_ENDPOINT, settings, params)
                rows = self._rank_lookup_rows(body, origin, origin)
                for row in rows:
                    code = self._first_code_value(row, ("originAreaCode", "originAreaId", "areaCode", "code", "id"))
                    if code:
                        text = self._row_text(row)
                        if origin in text or origin == "중국":
                            return code
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError("네이버 원산지 코드 자동 조회 실패: " + " / ".join(errors[-3:]))

    def _naver_origin_area_code_for_origin(self, origin: str | object, settings: dict[str, str]) -> str:
        normalized_origin = self._normalize_market_origin(origin) or "중국"
        if normalized_origin == "중국":
            return "0200037"
        if normalized_origin == "대한민국":
            return "0200014"
        configured_code = str(settings.get("naver_origin_area_code") or "").strip()
        if configured_code and not self._is_auto_lookup_value(configured_code):
            return configured_code
        return AUTO_LOOKUP_PREFIX + "naver_origin_area_code"

    def _category_lookup_queries(self, product: MarketProduct) -> list[str]:
        values = [
            self._market_seo_title(product.product_name, self._infer_market_category_text(product)),
            product.product_name,
            self._infer_market_category_text(product),
            *self._product_core_terms(product),
            *self._market_keyword_expansions(product, self._infer_market_category_text(product))[:8],
        ]
        if self._is_camping_hook_product(product):
            values = [
                "캠핑 고리 후크 스트랩",
                "캠핑 후크",
                "캠핑 스트랩 고리",
                "카라비너 캠핑용품",
                *values,
            ]
        cleaned: list[str] = []
        for value in values:
            text = re.sub(r"\s+", " ", str(value or "")).strip()
            text = re.sub(r"[|].*$", "", text).strip()
            if 2 <= len(text) <= 80:
                cleaned.append(text)
        return self._dedupe_text_items(cleaned)[:12]

    def _naver_category_lookup_queries(self, product: MarketProduct) -> list[str]:
        base = self._category_lookup_queries(product)
        if self._is_baby_chair_product(product):
            preferred = [
                "유아동 유아가구 유아식탁의자",
                "유아식탁의자",
                "아기 식탁의자",
                "하이체어",
                "유아용 식탁의자",
                "유아의자",
            ]
            return self._dedupe_text_items([*preferred, *base])[:16]
        if not self._is_storage_shelf_product(product):
            return base
        preferred = [
            "가구/인테리어 수납가구 선반",
            "수납가구 선반",
            "이동식 수납 선반",
            "수납 선반",
            "트롤리 선반",
            "다용도 선반",
            "선반",
        ]
        return self._dedupe_text_items([*preferred, *base])[:16]

    def _is_storage_shelf_product(self, product: MarketProduct) -> bool:
        source = product.source if isinstance(product.source, dict) else {}
        metadata = product.metadata if isinstance(product.metadata, dict) else {}
        blob = " ".join(
            str(item or "")
            for item in (
                product.code,
                product.product_name,
                metadata.get("product_name"),
                metadata.get("category"),
                source.get("title"),
                source.get("product_name"),
                source.get("category"),
                source.get("options_text"),
                " ".join(str(item or "") for item in source.get("facts", []) if isinstance(source.get("facts", []), list)),
                self._market_clean_product_source_text(source.get("text"))[:3000],
            )
        )
        negative = ("팔찌", "암밴드", "밴드", "목줄", "리드줄", "고양이", "반바지", "바지", "의류", "두건", "커튼", "커텐", "블라인드", "가림막", "린넨", "집게")
        strong_positive = ("수납선반", "이동식 선반", "트롤리", "수납랙", "선반랙", "카트", "협탁", "책장")
        if any(term in blob for term in negative) and not any(term in blob for term in strong_positive):
            return False
        positive = (*strong_positive, "수납", "선반", "랙", "사이드", "스낵")
        return not self._is_baby_chair_product(product) and any(term in blob for term in positive)

    def _is_baby_chair_product(self, product: MarketProduct) -> bool:
        blob = self._market_primary_text_blob(product)
        positive = ("유아식탁의자", "아기 식탁의자", "아기식탁의자", "유아용 식탁의자", "하이체어", "유아이유식의자")
        return any(term in blob for term in positive)

    def _is_camping_hook_product(self, product: MarketProduct) -> bool:
        blob = f"{product.product_name} {self._market_primary_text_blob(product)}".lower()
        camping_terms = ("캠핑", "감성캠핑", "캠핑용품")
        hook_terms = ("고리", "후크", "스트랩", "카라비너", "걸이")
        return any(term in blob for term in camping_terms) and any(term in blob for term in hook_terms)

    def _rank_naver_category_rows(self, value: object, query: str, product: MarketProduct) -> list[dict[str, object]]:
        rows = list(self._iter_json_dicts(value))
        storage_product = self._is_storage_shelf_product(product)
        baby_chair_product = self._is_baby_chair_product(product)
        query_terms = [term for term in re.split(r"\s+|/|>|,", f"{query} {self._infer_market_category_text(product)}") if len(term) >= 2]
        positive_terms = ("가구/인테리어", "수납가구", "수납", "선반", "트롤리", "랙", "카트", "다용도")
        baby_positive_terms = ("유아동", "유아가구", "유아식탁의자", "유아", "아기", "식탁의자", "하이체어", "의자")
        baby_wrong_terms = ("수납", "선반", "트롤리", "랙", "카트", "침구", "소파")
        wrong_terms = (
            "소파",
            "가죽소파",
            "패브릭소파",
            "리클라이너",
            "베개",
            "침대",
            "침구",
            "커튼",
            "카페트",
            "러그",
            "의자",
            "식탁",
        )

        def score(row: dict[str, object]) -> int:
            text = self._row_text(row)
            if baby_chair_product and any(term in text for term in baby_wrong_terms):
                return -10000
            if storage_product and any(term in text for term in wrong_terms):
                return -10000
            total = 0
            for term in query_terms:
                if term and term in text:
                    total += 3
            if storage_product:
                for term in positive_terms:
                    if term in text:
                        total += 8
                if "수납가구" in text and "선반" in text:
                    total += 30
                if "가구/인테리어" in text:
                    total += 6
            if baby_chair_product:
                for term in baby_positive_terms:
                    if term in text:
                        total += 8
                if "유아" in text and "식탁의자" in text:
                    total += 35
            if any(str(row.get(key, "")).lower() in {"true", "y", "1", "last", "leaf"} for key in ("last", "leaf", "leafCategory", "lastCategory")):
                total += 5
            if self._first_code_value(row, ("leafCategoryId", "wholeCategoryId", "categoryId", "id", "code")):
                total += 1
            return total

        return [row for row in sorted(rows, key=score, reverse=True) if score(row) > -10000]

    def _rank_lookup_rows(self, value: object, query: str, category_hint: str = "") -> list[dict[str, object]]:
        rows = list(self._iter_json_dicts(value))
        query_terms = [term for term in re.split(r"\s+|/|>|,", f"{query} {category_hint}") if len(term) >= 2]

        def score(row: dict[str, object]) -> int:
            text = self._row_text(row)
            total = 0
            for term in query_terms:
                if term and term in text:
                    total += 4
            if any(str(row.get(key, "")).lower() in {"true", "y", "1", "last", "leaf"} for key in ("last", "leaf", "leafCategory", "lastCategory")):
                total += 5
            if self._first_code_value(row, ("leafCategoryId", "displayCategoryCode", "wholeCategoryId", "categoryId", "id", "code")):
                total += 1
            return total

        return sorted(rows, key=score, reverse=True)

    def _iter_json_dicts(self, value: object):
        if isinstance(value, dict):
            yield value
            for item in value.values():
                yield from self._iter_json_dicts(item)
        elif isinstance(value, list):
            for item in value:
                yield from self._iter_json_dicts(item)

    def _row_text(self, row: dict[str, object]) -> str:
        parts: list[str] = []
        for value in row.values():
            if isinstance(value, (str, int, float)):
                parts.append(str(value))
            elif isinstance(value, list):
                parts.extend(str(item) for item in value if isinstance(item, (str, int, float)))
        return " ".join(parts)

    def _first_text_value(self, row: dict[str, object], keys: tuple[str, ...]) -> str:
        lookup = {str(key).lower(): key for key in row}
        for key in keys:
            raw_key = lookup.get(key.lower())
            if raw_key is None:
                continue
            value = str(row.get(raw_key) or "").strip()
            if value and not self._is_auto_lookup_value(value):
                return value
        return ""

    def _first_code_value(self, row: dict[str, object], keys: tuple[str, ...]) -> str:
        value = self._first_text_value(row, keys)
        if value:
            return re.sub(r"\.0$", "", value)
        return ""

    def _pick_address_row(self, rows: list[dict[str, object]], kind: str) -> dict[str, object] | None:
        hints = ("출고", "발송", "배송", "ship", "outbound") if kind == "outbound" else ("반품", "교환", "return", "claim")
        for row in rows:
            text = self._row_text(row).lower()
            if any(hint.lower() in text for hint in hints):
                return row
        return None

    def _fill_contact_address_values(self, row: dict[str, object]) -> bool:
        candidates = [row]
        addresses = row.get("placeAddresses")
        if isinstance(addresses, list):
            candidates.extend(item for item in addresses if isinstance(item, dict))

        def first(keys: tuple[str, ...]) -> str:
            for candidate in candidates:
                value = self._first_text_value(candidate, keys)
                if value:
                    return value
            return ""

        changed = False
        changed = self._set_market_setting_value(
            "return_charge_name",
            first(("returnChargeName", "chargeName", "managerName", "receiverName", "shippingPlaceName", "name")),
        ) or changed
        changed = self._set_market_setting_value(
            "company_contact_number",
            first(("companyContactNumber", "phoneNumber", "phoneNumber1", "phoneNumber2", "telNo", "telephoneNumber", "mobileNumber", "contactNumber")),
        ) or changed
        changed = self._set_market_setting_value(
            "return_zip_code",
            first(("returnZipCode", "zipCode", "zipcode", "postalCode", "postCode")),
        ) or changed
        changed = self._set_market_setting_value(
            "return_address",
            first(("returnAddress", "address", "roadNameAddress", "baseAddress", "address1")),
        ) or changed
        changed = self._set_market_setting_value(
            "return_address_detail",
            first(("returnAddressDetail", "addressDetail", "detailAddress", "address2")),
        ) or changed
        return changed

    def _attempt_live_market_publish(self, product: MarketProduct, platform: str) -> dict[str, object]:
        started_at = datetime.now().isoformat(timespec="seconds")
        try:
            existing_product_no = self._existing_market_product_no(product, platform)
            self._prepare_market_live_requirements(product, platform)
            settings = self._market_settings_data(include_secrets=True)
            image_refs = self._ensure_market_http_image_refs(
                product,
                settings,
                include_coupang_animated_webp=platform == "coupang",
            )
            draft = self._write_market_draft_bundle(product, {platform})
            if platform == "naver":
                payload = draft["naver_payload"]
                if not self._market_image_refs_are_http(image_refs):
                    raise RuntimeError("네이버 이미지 URL이 HTTPS로 준비되지 않았습니다.")
                result = self._post_naver_product(payload, settings, existing_product_no)
            else:
                payload = draft["coupang_payload"]
                if not self._market_image_refs_are_http(image_refs):
                    raise RuntimeError("쿠팡 vendorPath에 넣을 HTTPS 이미지 URL이 준비되지 않았습니다.")
                result = self._post_coupang_product(payload, settings, existing_product_no)
            result.update({"mode": "live", "started_at": started_at, "updated_at": datetime.now().isoformat(timespec="seconds")})
            return result
        except Exception as exc:
            return {
                "status": "live 실패",
                "mode": "live",
                "error": str(exc),
                "started_at": started_at,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }

    def _existing_market_product_no(self, product: MarketProduct, platform: str) -> str:
        publish_result = self._read_json_file(product.folder / "market" / "publish_result.json")
        existing = publish_result.get(platform) if isinstance(publish_result, dict) else None
        if not isinstance(existing, dict):
            return ""
        if str(existing.get("status") or "").startswith("live"):
            product_no = str(existing.get("product_no") or "").strip()
            if product_no and product_no.upper() != "ERROR":
                return product_no
        return ""

    def _market_api_runtime_issues(self, platform: str) -> list[str]:
        issues: list[str] = []
        if requests is None:
            issues.append("requests 패키지 필요")
        if platform == "naver" and bcrypt is None:
            issues.append("네이버 인증용 bcrypt 패키지 필요")
        return issues

    def _ensure_market_http_image_refs(
        self,
        product: MarketProduct,
        settings: dict[str, str],
        include_coupang_animated_webp: bool = False,
    ) -> dict[str, object]:
        upload_manifest = self._build_upload_manifest(
            product,
            include_coupang_animated_webp=include_coupang_animated_webp,
        )
        existing_manifest = self._read_json_file(product.folder / "market" / "upload_manifest.json")
        existing_refs = self._market_image_references(product, existing_manifest) if existing_manifest else {}
        if existing_refs and self._market_image_refs_are_http(existing_refs):
            merged_manifest = self._merge_fresh_coupang_animated_webp(upload_manifest, existing_manifest)
            return self._market_image_references(product, merged_manifest)
        image_refs = self._market_image_references(product, upload_manifest)
        if self._market_image_refs_are_http(image_refs):
            return image_refs
        uploaded_urls = self._naver_upload_product_images(product, settings, upload_manifest)
        upload_manifest["uploaded_image_urls"] = uploaded_urls
        upload_manifest["upload_status"] = "naver_uploaded"
        upload_manifest["uploaded_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_json_file(product.folder / "market" / "upload_manifest.json", upload_manifest)
        return self._market_image_references(product, upload_manifest)

    def _naver_access_token(self, settings: dict[str, str]) -> str:
        if requests is None:
            raise RuntimeError("requests 패키지가 없어 네이버 토큰을 받을 수 없습니다.")
        if bcrypt is None:
            raise RuntimeError("bcrypt 패키지가 없어 네이버 client_secret_sign을 만들 수 없습니다.")
        client_id = str(settings.get("naver_client_id") or "").strip()
        client_secret = str(settings.get("naver_client_secret") or "").strip()
        if not client_id or not client_secret:
            raise RuntimeError("네이버 client_id/client_secret이 필요합니다.")
        timestamp = str(int(time.time() * 1000))
        password = f"{client_id}_{timestamp}".encode("utf-8")
        hashed = bcrypt.hashpw(password, client_secret.encode("utf-8"))
        client_secret_sign = base64.b64encode(hashed).decode("utf-8")
        response = requests.post(
            NAVER_TOKEN_ENDPOINT,
            data={
                "client_id": client_id,
                "timestamp": timestamp,
                "client_secret_sign": client_secret_sign,
                "grant_type": "client_credentials",
                "type": "SELF",
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"네이버 토큰 실패 {response.status_code}: {response.text[:500]}")
        payload = response.json()
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise RuntimeError(f"네이버 토큰 응답에 access_token 없음: {payload}")
        return token

    def _naver_upload_product_images(
        self,
        product: MarketProduct,
        settings: dict[str, str],
        upload_manifest: dict[str, object],
    ) -> dict[str, str]:
        if requests is None:
            raise RuntimeError("requests 패키지가 없어 이미지를 업로드할 수 없습니다.")
        token = self._naver_access_token(settings)
        local_images = upload_manifest.get("local_images", [])
        if not isinstance(local_images, list) or not local_images:
            raise RuntimeError("업로드할 이미지 목록이 없습니다.")
        upload_items = self._prepare_naver_upload_images(product, local_images)
        upload_manifest["prepared_local_images"] = upload_items
        files: list[tuple[str, tuple[str, object, str]]] = []
        opened_files = []
        try:
            for item in upload_items:
                if not isinstance(item, dict):
                    continue
                path = Path(str(item.get("upload_path") or item.get("path") or ""))
                if not self._is_valid_image_file(path):
                    raise RuntimeError(f"업로드 이미지 없음 또는 손상: {path}")
                mime = mimetypes.guess_type(str(path))[0] or "image/png"
                handle = path.open("rb")
                opened_files.append(handle)
                files.append(("imageFiles", (str(item.get("upload_name") or item.get("target_name") or path.name), handle, mime)))
            response = requests.post(
                NAVER_IMAGE_UPLOAD_ENDPOINT,
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                timeout=120,
            )
        finally:
            for handle in opened_files:
                try:
                    handle.close()
                except Exception:
                    pass
        if response.status_code >= 400:
            raise RuntimeError(f"네이버 이미지 업로드 실패 {response.status_code}: {response.text[:700]}")
        urls = self._collect_uploaded_image_urls(response.json())
        if len(urls) < len(upload_items):
            raise RuntimeError(f"네이버 이미지 업로드 URL 부족: {len(urls)}/{len(upload_items)}")
        return {
            str(item.get("target_name") or f"image_{index}.png"): urls[index]
            for index, item in enumerate(upload_items)
            if isinstance(item, dict) and index < len(urls)
        }

    def _prepare_naver_upload_images(self, product: MarketProduct, local_images: list[object]) -> list[dict[str, object]]:
        try:
            from PIL import Image, ImageOps
        except Exception as exc:
            raise RuntimeError(f"Pillow 패키지가 없어 네이버 업로드용 이미지 압축을 할 수 없습니다: {exc}")

        prepared_dir = product.folder / "market" / "upload_images"
        prepared_dir.mkdir(parents=True, exist_ok=True)
        prepared: list[dict[str, object]] = []
        total_bytes = 0
        for index, raw_item in enumerate(local_images, start=1):
            if not isinstance(raw_item, dict):
                continue
            source_path = Path(str(raw_item.get("path") or ""))
            if not self._is_valid_image_file(source_path):
                raise RuntimeError(f"업로드 이미지 없음 또는 손상: {source_path}")
            target_name = str(raw_item.get("target_name") or source_path.name)
            role = str(raw_item.get("role") or "")
            budget = 3_200_000 if role == "detail_page" else 850_000
            upload_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(target_name).stem) + ".jpg"
            upload_path = prepared_dir / upload_name
            self._write_upload_safe_jpeg(source_path, upload_path, budget, Image, ImageOps)
            size = upload_path.stat().st_size
            total_bytes += size
            item = dict(raw_item)
            item.update(
                {
                    "upload_path": str(upload_path),
                    "upload_name": upload_name,
                    "upload_size": size,
                    "upload_mime": "image/jpeg",
                }
            )
            prepared.append(item)
        if total_bytes > 9_500_000:
            raise RuntimeError(f"네이버 이미지 업로드 준비 용량이 아직 큽니다: {total_bytes} bytes")
        return prepared

    def _write_upload_safe_jpeg(self, source_path: Path, output_path: Path, budget: int, image_module: object, image_ops_module: object) -> None:
        with image_module.open(source_path) as image:
            image = image_ops_module.exif_transpose(image)
            if image.mode not in {"RGB", "L"}:
                background = image_module.new("RGB", image.size, (255, 255, 255))
                if "A" in image.getbands():
                    background.paste(image, mask=image.getchannel("A"))
                else:
                    background.paste(image)
                image = background
            else:
                image = image.convert("RGB")

            max_width = 860 if image.height > image.width else 1000
            working = image
            for scale in (1.0, 0.92, 0.84, 0.76, 0.68, 0.6):
                width = min(max_width, int(image.width * scale))
                if width <= 0:
                    continue
                height = max(1, int(image.height * (width / image.width)))
                working = image.resize((width, height), image_module.Resampling.LANCZOS) if (width, height) != image.size else image
                for quality in (88, 82, 76, 70, 64, 58, 52):
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    working.save(output_path, format="JPEG", quality=quality, optimize=True, progressive=True)
                    if output_path.stat().st_size <= budget:
                        return
            working.save(output_path, format="JPEG", quality=48, optimize=True, progressive=True)

    def _collect_uploaded_image_urls(self, value: object) -> list[str]:
        urls: list[str] = []
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in {"url", "imageurl", "image_url"} and self._is_http_url(item):
                    urls.append(str(item))
                else:
                    urls.extend(self._collect_uploaded_image_urls(item))
        elif isinstance(value, list):
            for item in value:
                urls.extend(self._collect_uploaded_image_urls(item))
        elif self._is_http_url(value):
            urls.append(str(value))
        return self._dedupe_text_items(urls)

    def _post_naver_product(
        self,
        payload: dict[str, object],
        settings: dict[str, str],
        existing_product_no: str = "",
    ) -> dict[str, object]:
        if requests is None:
            raise RuntimeError("requests 패키지가 없어 네이버 상품 등록을 호출할 수 없습니다.")
        token = self._naver_access_token(settings)
        payload = self._strip_draft_keys(payload)
        payload = self._prepare_naver_live_payload(payload, settings)
        is_update = bool(str(existing_product_no or "").strip())
        endpoint = (
            NAVER_ORIGIN_PRODUCT_ENDPOINT_TEMPLATE.format(
                originProductNo=urllib.parse.quote(str(existing_product_no).strip(), safe="")
            )
            if is_update
            else NAVER_PRODUCT_CREATE_ENDPOINT
        )
        response = requests.request(
            "PUT" if is_update else "POST",
            endpoint,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        body = self._safe_response_json(response)
        if is_update and response.status_code == 404 and "삭제된 상품" in str(response.text):
            response = requests.post(
                NAVER_PRODUCT_CREATE_ENDPOINT,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            body = self._safe_response_json(response)
            is_update = False
        for _ in range(3):
            if response.status_code < 400:
                break
            retry_payload = copy.deepcopy(payload)
            retry_origin = retry_payload.get("originProduct", {})
            retry_detail = retry_origin.get("detailAttribute", {}) if isinstance(retry_origin, dict) else {}
            changed = False
            if isinstance(retry_detail, dict) and self._is_naver_restricted_seller_tags_error(response):
                retry_seo = retry_detail.get("seoInfo", {})
                if not isinstance(retry_seo, dict):
                    retry_seo = {}
                current_tags = retry_seo.get("sellerTags")
                invalid_tags = self._naver_invalid_seller_tag_texts(response)
                filtered_tags = self._naver_filter_seller_tags(current_tags, invalid_tags)
                if filtered_tags != current_tags:
                    if filtered_tags:
                        retry_seo["sellerTags"] = filtered_tags
                    else:
                        retry_seo.pop("sellerTags", None)
                    retry_detail["seoInfo"] = retry_seo
                    changed = True
            if isinstance(retry_detail, dict) and self._is_naver_product_attributes_error(response):
                if "productAttributes" in retry_detail:
                    retry_detail.pop("productAttributes", None)
                    changed = True
            if not changed:
                break
            response = requests.request(
                "PUT" if is_update else "POST",
                endpoint if is_update else NAVER_PRODUCT_CREATE_ENDPOINT,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=retry_payload,
                timeout=60,
            )
            body = self._safe_response_json(response)
            payload = retry_payload
        if is_update and response.status_code >= 400 and self._is_naver_unchangeable_category_error(response):
            response = requests.post(
                NAVER_PRODUCT_CREATE_ENDPOINT,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            body = self._safe_response_json(response)
            is_update = False
            fallback = "recreated_due_to_unchangeable_category"
        else:
            fallback = ""
        if response.status_code >= 400:
            action = "수정" if is_update else "등록"
            raise RuntimeError(f"네이버 상품 {action} 실패 {response.status_code}: {response.text[:1000]}")
        product_no = self._extract_product_no(body) or str(existing_product_no or "").strip()
        result = {
            "status": "live 수정 완료" if is_update else "live 완료",
            "platform": "naver",
            "http_status": response.status_code,
            "product_no": product_no,
            "response": body,
        }
        if fallback:
            result["fallback"] = fallback
            result["replaced_product_no"] = str(existing_product_no or "").strip()
        return result

    def _is_naver_restricted_seller_tags_error(self, response: object) -> bool:
        try:
            text = str(getattr(response, "text", "") or "")
        except Exception:
            text = ""
        if (
            "Restricted.sellerTags" in text
            or "NotValid.recommendTags.text" in text
            or "태그로 등록할 수 없는" in text
            or "sellerTags" in text and "등록불가" in text
        ):
            return True
        try:
            body = self._safe_response_json(response)
        except Exception:
            body = None
        invalid = body.get("invalidInputs", []) if isinstance(body, dict) else []
        if isinstance(invalid, list):
            for item in invalid:
                if not isinstance(item, dict):
                    continue
                if str(item.get("type") or "") == "Restricted.sellerTags":
                    return True
                if str(item.get("type") or "") == "NotValid.recommendTags.text":
                    return True
                if "sellerTags" in str(item.get("name") or "") and "등록불가" in str(item.get("message") or ""):
                    return True
        return False

    def _naver_invalid_seller_tag_texts(self, response: object) -> set[str]:
        try:
            body = self._safe_response_json(response)
        except Exception:
            body = {}
        invalid: set[str] = set()
        invalid_inputs = body.get("invalidInputs", []) if isinstance(body, dict) else []
        if isinstance(invalid_inputs, list):
            for item in invalid_inputs:
                if not isinstance(item, dict):
                    continue
                message = str(item.get("message") or "")
                for pattern in (
                    r"태그명:\s*([^)]+)",
                    r"등록불가인\s*단어\(([^)]+)\)",
                    r"등록\s*불가\s*단어\(([^)]+)\)",
                    r"단어\(([^)]+)\)",
                ):
                    match = re.search(pattern, message)
                    if match:
                        invalid.update(tag.strip() for tag in re.split(r",|/", match.group(1)) if tag.strip())
        return {re.sub(r"[^가-힣A-Za-z0-9]", "", tag).lower() for tag in invalid if tag}

    def _naver_filter_seller_tags(self, seller_tags: object, invalid_tags: set[str]) -> list[dict[str, object]]:
        if not isinstance(seller_tags, list):
            return []
        if not invalid_tags:
            return []
        filtered: list[dict[str, object]] = []
        for tag in seller_tags:
            text = str(tag.get("text") if isinstance(tag, dict) else tag or "")
            key = re.sub(r"[^가-힣A-Za-z0-9]", "", text).lower()
            if key and key not in invalid_tags:
                filtered.append(dict(tag) if isinstance(tag, dict) else {"text": text})
        return filtered[:10]

    def _is_naver_product_attributes_error(self, response: object) -> bool:
        try:
            text = str(getattr(response, "text", "") or "")
        except Exception:
            text = ""
        if "productAttributes" in text or "attributeSeq" in text or "attributeValueSeq" in text:
            return True
        body = self._safe_response_json(response)
        invalid = body.get("invalidInputs", []) if isinstance(body, dict) else []
        if isinstance(invalid, list):
            for item in invalid:
                if not isinstance(item, dict):
                    continue
                joined = " ".join(str(item.get(key) or "") for key in ("name", "type", "message"))
                if "productAttributes" in joined or "attributeSeq" in joined or "attributeValueSeq" in joined:
                    return True
        return False

    def _is_naver_unchangeable_category_error(self, response: object) -> bool:
        try:
            text = str(getattr(response, "text", "") or "")
        except Exception:
            text = ""
        if "NotChangable.product.category.id" in text or "대분류는 변경할 수 없습니다" in text:
            return True
        body = self._safe_response_json(response)
        invalid = body.get("invalidInputs", []) if isinstance(body, dict) else []
        if isinstance(invalid, list):
            for item in invalid:
                if not isinstance(item, dict):
                    continue
                if str(item.get("type") or "") == "NotChangable.product.category.id":
                    return True
                if "대분류는 변경할 수 없습니다" in str(item.get("message") or ""):
                    return True
        return False

    def _post_coupang_product(
        self,
        payload: dict[str, object],
        settings: dict[str, str],
        existing_product_no: str = "",
    ) -> dict[str, object]:
        if requests is None:
            raise RuntimeError("requests 패키지가 없어 쿠팡 상품 등록을 호출할 수 없습니다.")
        category_meta = self._fetch_coupang_category_meta(payload.get("displayCategoryCode"), settings)
        payload = self._apply_coupang_category_meta(payload, category_meta)
        create_payload = copy.deepcopy(payload)
        is_update = bool(str(existing_product_no or "").strip())
        if is_update:
            payload = self._prepare_coupang_update_payload(payload, str(existing_product_no), settings)
        # Live publish must request Coupang approval regardless of a saved draft/template state.
        payload["requested"] = True
        if payload.get("manufacturer") and not payload.get("manufacture"):
            payload["manufacture"] = payload.get("manufacturer")
        payload.pop("manufacturer", None)
        payload = self._strip_draft_keys(payload)
        path = COUPANG_PRODUCT_CREATE_PATH
        method = "PUT" if is_update else "POST"
        request_fn = requests.put if is_update else requests.post

        def send_payload(current_payload: dict[str, object]) -> tuple[object, object]:
            body = json.dumps(current_payload, ensure_ascii=False, separators=(",", ":"))
            headers = self._coupang_hmac_headers(method, path, "", body, settings)
            response = request_fn(
                COUPANG_API_BASE_URL + path,
                headers={**headers, "Content-Type": "application/json;charset=UTF-8"},
                data=body.encode("utf-8"),
                timeout=60,
            )
            return response, self._safe_response_json(response)

        response, response_body = send_payload(payload)
        minimum_price_adjustment: dict[str, object] | None = None
        if response.status_code < 400 and self._coupang_response_is_error(response_body):
            minimum_price = self._coupang_minimum_sale_price(response_body)
            if minimum_price:
                adjusted_payload, adjusted_items = self._coupang_payload_with_minimum_item_price(payload, minimum_price)
                if adjusted_items:
                    payload = adjusted_payload
                    response, response_body = send_payload(payload)
                    minimum_price_adjustment = {
                        "minimum_sale_price": minimum_price,
                        "adjusted_items": adjusted_items,
                    }
        if response.status_code >= 400:
            if is_update and self._is_deleted_coupang_product_error(response_body, response.text):
                recreated = self._post_coupang_product(create_payload, settings, "")
                recreated["fallback"] = "deleted_existing_product_recreated"
                recreated["replaced_product_no"] = str(existing_product_no)
                return recreated
            action = "수정" if is_update else "등록"
            raise RuntimeError(f"쿠팡 상품 {action} 실패 {response.status_code}: {response.text[:1000]}")
        if self._coupang_response_is_error(response_body):
            if is_update and self._is_deleted_coupang_product_error(response_body, response.text):
                recreated = self._post_coupang_product(create_payload, settings, "")
                recreated["fallback"] = "deleted_existing_product_recreated"
                recreated["replaced_product_no"] = str(existing_product_no)
                return recreated
            action = "수정" if is_update else "등록"
            raise RuntimeError(
                f"쿠팡 상품 {action} 실패 "
                f"{response.status_code}: {json.dumps(response_body, ensure_ascii=False)[:1500]}"
            )
        item_price_updates = self._update_coupang_live_item_prices(payload, settings) if is_update else []
        result = {
            "status": "live 수정 완료" if is_update else "live 완료",
            "platform": "coupang",
            "http_status": response.status_code,
            "product_no": str(existing_product_no) if is_update else self._extract_product_no(response_body),
            "requested": True,
            "item_price_updates": item_price_updates,
            "response": response_body,
        }
        if minimum_price_adjustment:
            result["minimum_price_adjustment"] = minimum_price_adjustment
        return result

    def _update_coupang_live_item_prices(
        self,
        payload: dict[str, object],
        settings: dict[str, str],
    ) -> list[dict[str, object]]:
        updates: list[dict[str, object]] = []
        items = payload.get("items", [])
        if not isinstance(items, list):
            return updates
        for item in items:
            if not isinstance(item, dict):
                continue
            vendor_item_id = self._first_code_value(item, ("vendorItemId",))
            sale_price = self._positive_int(item.get("salePrice", ""))
            original_price = self._positive_int(item.get("originalPrice", "")) or sale_price
            if not vendor_item_id or not sale_price:
                continue
            price_path = f"/v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/{vendor_item_id}/prices/{sale_price}"
            price_response = self._coupang_put_empty(
                price_path,
                settings,
                {"forceSalePriceUpdate": "true"},
            )
            update: dict[str, object] = {
                "vendorItemId": vendor_item_id,
                "salePrice": sale_price,
                "price_response": price_response,
            }
            if original_price:
                original_path = f"/v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/{vendor_item_id}/original-prices/{original_price}"
                update["originalPrice"] = original_price
                update["original_price_response"] = self._coupang_put_empty(original_path, settings)
            updates.append(update)
        return updates

    def _coupang_put_empty(
        self,
        path: str,
        settings: dict[str, str],
        params: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if requests is None:
            raise RuntimeError("requests 패키지가 없어 쿠팡 수정 API를 호출할 수 없습니다.")
        query = urllib.parse.urlencode(params or {}, doseq=True)
        headers = self._coupang_hmac_headers("PUT", path, query, "", settings)
        url = COUPANG_API_BASE_URL + path + (f"?{query}" if query else "")
        response = requests.put(
            url,
            headers={**headers, "Content-Type": "application/json;charset=UTF-8"},
            timeout=60,
        )
        body = self._safe_response_json(response)
        if response.status_code >= 400 or self._coupang_response_is_error(body):
            raise RuntimeError(f"쿠팡 아이템 수정 실패 {response.status_code}: {json.dumps(body, ensure_ascii=False)[:1000]}")
        return body

    def _is_deleted_coupang_product_error(self, body: object, text: str = "") -> bool:
        haystack = text
        if isinstance(body, dict):
            haystack += " " + json.dumps(body, ensure_ascii=False)
        return "이미 삭제된 상품" in haystack or "deleted product" in haystack.lower()

    def _prepare_coupang_update_payload(
        self,
        payload: dict[str, object],
        existing_product_no: str,
        settings: dict[str, str],
    ) -> dict[str, object]:
        updated = copy.deepcopy(payload)
        updated["sellerProductId"] = int(existing_product_no) if str(existing_product_no).isdigit() else existing_product_no
        try:
            detail = self._coupang_get_json(f"{COUPANG_PRODUCT_CREATE_PATH}/{existing_product_no}", settings)
        except Exception:
            return updated
        existing = detail.get("data") if isinstance(detail, dict) and isinstance(detail.get("data"), dict) else detail
        if not isinstance(existing, dict):
            return updated
        existing_category = self._first_code_value(existing, ("displayCategoryCode", "categoryCode"))
        if existing_category:
            updated["displayCategoryCode"] = int(existing_category) if str(existing_category).isdigit() else existing_category
        existing_items = existing.get("items", [])
        if not isinstance(existing_items, list):
            existing_items = []
        by_sku: dict[str, dict[str, object]] = {}
        by_name: dict[str, dict[str, object]] = {}
        for item in existing_items:
            if not isinstance(item, dict):
                continue
            sku = str(item.get("externalVendorSku") or "").strip()
            name = str(item.get("itemName") or "").strip()
            if sku:
                by_sku[sku] = item
            if name:
                by_name[name] = item
        for item in updated.get("items", []):
            if not isinstance(item, dict):
                continue
            existing_item = by_sku.get(str(item.get("externalVendorSku") or "").strip()) or by_name.get(str(item.get("itemName") or "").strip())
            if not isinstance(existing_item, dict):
                continue
            seller_item_id = self._first_code_value(existing_item, ("sellerProductItemId", "id"))
            vendor_item_id = self._first_code_value(existing_item, ("vendorItemId",))
            if seller_item_id:
                item["sellerProductItemId"] = int(seller_item_id) if str(seller_item_id).isdigit() else seller_item_id
            if vendor_item_id:
                item["vendorItemId"] = int(vendor_item_id) if str(vendor_item_id).isdigit() else vendor_item_id
        return updated

    def _coupang_response_is_error(self, body: object) -> bool:
        if not isinstance(body, dict):
            return False
        code = str(body.get("code") or "").strip().upper()
        if code and code not in {"SUCCESS", "OK", "200"}:
            return True
        message = body.get("message")
        if isinstance(message, list) and message:
            return True
        if isinstance(message, str) and code not in {"SUCCESS", "OK", "200"} and message.strip():
            return True
        data = body.get("data")
        if isinstance(data, dict):
            data_code = str(data.get("code") or "").strip().upper()
            if data_code and data_code not in {"SUCCESS", "OK", "200"}:
                return True
        return False

    def _coupang_minimum_sale_price(self, body: object) -> int:
        if not isinstance(body, dict):
            return 0
        text = json.dumps(body, ensure_ascii=False)
        if "최소" not in text or "가격" not in text:
            return 0
        matches = re.findall(r"최소\s*설정\s*가격은\s*([\d,]+)\s*원", text)
        prices = [self._positive_int(match) for match in matches]
        prices = [price for price in prices if price > 0]
        return max(prices) if prices else 0

    def _coupang_payload_with_minimum_item_price(
        self,
        payload: dict[str, object],
        minimum_price: int,
    ) -> tuple[dict[str, object], int]:
        adjusted = copy.deepcopy(payload)
        items = adjusted.get("items", [])
        if not isinstance(items, list):
            return adjusted, 0
        adjusted_count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            sale_price = self._positive_int(item.get("salePrice", ""))
            if not sale_price or sale_price >= minimum_price:
                continue
            item["salePrice"] = minimum_price
            original_price = self._positive_int(item.get("originalPrice", ""))
            item["originalPrice"] = max(original_price, minimum_price)
            adjusted_count += 1
        return adjusted, adjusted_count

    def _fetch_coupang_category_meta(self, display_category_code: object, settings: dict[str, str]) -> dict[str, object]:
        code = str(display_category_code or "").strip()
        if not code or self._is_auto_lookup_value(code):
            raise RuntimeError("쿠팡 live 등록 전 displayCategoryCode 확정이 필요합니다.")
        path = COUPANG_CATEGORY_META_PATH_TEMPLATE.format(displayCategoryCode=urllib.parse.quote(code, safe=""))
        headers = self._coupang_hmac_headers("GET", path, "", "", settings)
        response = requests.get(
            COUPANG_API_BASE_URL + path,
            headers={**headers, "Content-Type": "application/json;charset=UTF-8"},
            timeout=60,
        )
        body = self._safe_response_json(response)
        if response.status_code >= 400:
            raise RuntimeError(f"쿠팡 카테고리 메타 조회 실패 {response.status_code}: {response.text[:1000]}")
        return body

    def _apply_coupang_category_meta(self, payload: dict[str, object], category_meta: dict[str, object]) -> dict[str, object]:
        attribute_specs = self._coupang_category_attribute_specs(category_meta)
        spec_by_name = self._coupang_attribute_specs_by_name(attribute_specs)
        allowed_names = {str(spec.get("name") or "") for spec in attribute_specs if str(spec.get("name") or "")}
        required_names = self._coupang_required_attribute_names(category_meta)
        purchase_names = self._coupang_purchase_attribute_names(attribute_specs, required_names)
        items = payload.get("items", [])
        if not isinstance(items, list):
            return payload
        for item in items:
            if not isinstance(item, dict):
                continue
            item["notices"] = self._coupang_notices_from_category_meta(item, payload, category_meta)
            item.pop("barcode", None)
            item["emptyBarcode"] = True
            item["emptyBarcodeReason"] = "상품에 바코드가 없음"
            attrs = item.get("attributes", [])
            if not isinstance(attrs, list):
                attrs = []
            required_for_item = self._coupang_required_names_for_item(required_names, attribute_specs, item, payload) if required_names else []
            required_set = set(required_for_item)
            if required_names or allowed_names:
                attrs = self._normalize_coupang_purchase_attributes(attrs, required_set, allowed_names, purchase_names)
                self._remove_coupang_unselected_group_attributes(attrs, attribute_specs, required_set)
            present = {
                str(attr.get("attributeTypeName") or "")
                for attr in attrs
                if isinstance(attr, dict)
            }
            for required_name in required_for_item:
                if required_name in present:
                    continue
                fallback_value = self._coupang_required_attribute_fallback(required_name, item, payload, spec_by_name.get(required_name))
                exposed = "EXPOSED" if required_name in purchase_names else "NONE"
                attrs.append({"attributeTypeName": required_name, "attributeValueName": fallback_value, "exposed": exposed})
                present.add(required_name)
            for spec in attribute_specs:
                if not self._should_autofill_coupang_attribute_spec(spec, required_set):
                    continue
                name = str(spec.get("name") or "").strip()
                if not name or name in present:
                    continue
                fallback_value = self._coupang_required_attribute_fallback(name, item, payload, spec)
                exposed = "EXPOSED" if name in purchase_names else "NONE"
                attrs.append({"attributeTypeName": name, "attributeValueName": fallback_value, "exposed": exposed})
                present.add(name)
            self._sanitize_coupang_required_attributes(attrs, item, payload, attribute_specs)
            self._normalize_coupang_number_attribute_values(attrs, attribute_specs)
            item["attributes"] = attrs
        self._ensure_coupang_purchase_options_distinct(payload, allowed_names, purchase_names)
        self._validate_coupang_purchase_options(payload, allowed_names)
        return payload

    def _normalize_coupang_purchase_attributes(
        self,
        attrs: list[object],
        required_names: set[str],
        allowed_names: set[str] | None = None,
        purchase_names: set[str] | None = None,
    ) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        allowed_names = allowed_names or set()
        purchase_names = purchase_names or set()
        for attr in attrs:
            if not isinstance(attr, dict):
                continue
            name = str(attr.get("attributeTypeName") or "").strip()
            value = str(attr.get("attributeValueName") or "").strip()
            if not name or not value:
                continue
            if allowed_names and name in {"옵션", "옵션명"} and name not in allowed_names:
                continue
            copied = dict(attr)
            current_exposed = str(copied.get("exposed") or "").upper() == "EXPOSED"
            can_expose = not allowed_names or name in allowed_names
            copied["exposed"] = (
                "EXPOSED"
                if name in purchase_names or (can_expose and (current_exposed or name in self._coupang_variant_attribute_names()))
                else "NONE"
            )
            normalized.append(copied)
        return normalized

    def _coupang_variant_attribute_names(self) -> set[str]:
        return {"옵션", "옵션명", "색상", "컬러", "사이즈", "규격", "크기", "종류", "타입", "디자인"}

    def _coupang_numeric_attribute_name(self, name: str | object) -> bool:
        text = self._normalize_text_key(str(name or ""))
        if any(token in text for token in ("여부", "가능", "유무")):
            return False
        return any(
            token in text
            for token in (
                "수량",
                "개수",
                "용량",
                "중량",
                "무게",
                "단수",
                "단 수",
                "길이",
                "가로",
                "세로",
                "높이",
                "너비",
                "폭",
                "두께",
            )
        )

    def _should_autofill_coupang_attribute_spec(
        self,
        spec: dict[str, object],
        required_names: set[str],
    ) -> bool:
        if not isinstance(spec, dict):
            return False
        name = str(spec.get("name") or "").strip()
        if not name or name in required_names:
            return False
        if name in self._coupang_variant_attribute_names():
            return False
        data_type = str(spec.get("data_type") or "").upper()
        input_type = str(spec.get("input_type") or "").upper()
        if data_type in {"CODE", "NONE"}:
            return False
        if "인증" in name or "안전확인" in name or name.startswith("[KCs"):
            return False
        if input_type and input_type not in {"INPUT", "SELECT"}:
            return False
        if data_type and data_type not in {"STRING", "NUMBER"}:
            return False
        return bool(input_type or data_type)

    def _sanitize_coupang_required_attributes(
        self,
        attrs: list[dict[str, object]],
        item: dict[str, object],
        payload: dict[str, object],
        attribute_specs: list[dict[str, object]] | None = None,
    ) -> None:
        spec_by_name = self._coupang_attribute_specs_by_name(attribute_specs or [])
        for attr in attrs:
            if not isinstance(attr, dict):
                continue
            name = str(attr.get("attributeTypeName") or "").strip()
            value = str(attr.get("attributeValueName") or "").strip()
            if not name:
                continue
            spec = spec_by_name.get(name)
            if not value:
                attr["attributeValueName"] = self._coupang_required_attribute_fallback(name, item, payload, spec)
                value = str(attr.get("attributeValueName") or "").strip()
            if self._coupang_option_text_has_unavailable_marker(value):
                cleaned = self._clean_coupang_option_text(name, value)
                attr["attributeValueName"] = cleaned or self._coupang_required_attribute_fallback(name, item, payload, spec)
                value = str(attr.get("attributeValueName") or "").strip()
            if self._coupang_numeric_attribute_name(name) and (
                not re.search(r"\d", value) or "상세 조건 확인" in value
            ):
                attr["attributeValueName"] = self._coupang_required_attribute_fallback(name, item, payload, spec)
                value = str(attr.get("attributeValueName") or "").strip()
            attr["attributeValueName"] = self._coerce_coupang_attribute_value_to_spec(name, value, item, payload, spec)

    def _normalize_coupang_number_attribute_values(
        self,
        attrs: list[dict[str, object]],
        attribute_specs: list[dict[str, object]],
    ) -> None:
        number_names = {
            str(spec.get("name") or "")
            for spec in attribute_specs
            if str(spec.get("data_type") or "").upper() == "NUMBER"
        }
        if not number_names:
            return
        for attr in attrs:
            if not isinstance(attr, dict):
                continue
            name = str(attr.get("attributeTypeName") or "").strip()
            if name not in number_names:
                continue
            value = str(attr.get("attributeValueName") or "").strip()
            match = re.search(r"\d+(?:\.\d+)?", value)
            if match:
                attr["attributeValueName"] = match.group(0)

    def _coupang_attribute_specs_by_name(self, attribute_specs: list[dict[str, object]]) -> dict[str, dict[str, object]]:
        by_name: dict[str, dict[str, object]] = {}
        for spec in attribute_specs:
            if not isinstance(spec, dict):
                continue
            name = str(spec.get("name") or "").strip()
            if name and name not in by_name:
                by_name[name] = spec
        return by_name

    def _coupang_spec_input_values(self, spec: dict[str, object] | None) -> list[str]:
        values = spec.get("input_values", []) if isinstance(spec, dict) else []
        if not isinstance(values, list):
            return []
        return [str(value or "").strip() for value in values if str(value or "").strip()]

    def _select_coupang_input_value(
        self,
        name: str,
        item: dict[str, object],
        payload: dict[str, object],
        input_values: list[str],
    ) -> str:
        if not input_values:
            return ""
        haystack = f"{item.get('itemName') or ''} {payload.get('sellerProductName') or ''} {payload.get('displayProductName') or ''}"
        normalized_haystack = self._normalize_text_key(haystack)
        normalized_name = self._normalize_text_key(name)
        for value in input_values:
            if self._normalize_text_key(value) and self._normalize_text_key(value) in normalized_haystack:
                return value
        preferred_by_name: list[str] = []
        if "사용연령" in name or "연령" in name:
            preferred_by_name = ["전연령", "14세 이상", "성인", "아동"]
        elif "분리" in name or "일체" in name:
            preferred_by_name = ["일체형", "분리형"]
        elif "본품" in name or "리필" in name:
            preferred_by_name = ["본품", "본품/리필", "리필"]
        elif "조립" in name:
            preferred_by_name = ["조립 필수", "조립식", "조립 필요", "조립 필수 아님", "비조립식"]
        elif "재질" in name or "소재" in name:
            if any(token in normalized_haystack for token in ("wood", "원목", "목재", "우드")):
                preferred_by_name = ["목재", "우드", "원목"]
            elif any(token in normalized_haystack for token in ("metal", "철", "금속", "스틸", "강철")):
                preferred_by_name = ["금속", "강철", "철사"]
            else:
                preferred_by_name = ["플라스틱", "목재", "금속"]
        elif "색상계열" in name:
            preferred_by_name = ["멀티(혼합)컬러", "블랙계열", "화이트계열", "그레이계열", "브라운계열"]
        elif "손잡이" in name:
            preferred_by_name = ["손잡이 있음", "손잡이 없음"]
        elif "향기" in name:
            preferred_by_name = ["무향", "무향료"]
        elif "제형" in name:
            preferred_by_name = ["기타", "스프레이형", "액상형"]
        elif "해당" in normalized_name or "전용" in name:
            preferred_by_name = ["해당없음", "없음", "사용안함"]
        for preferred in preferred_by_name:
            preferred_key = self._normalize_text_key(preferred)
            for value in input_values:
                value_key = self._normalize_text_key(value)
                if preferred_key and (preferred_key == value_key or preferred_key in value_key or value_key in preferred_key):
                    return value
        for value in input_values:
            if "해당없음" in value:
                return value
        return input_values[0]

    def _coerce_coupang_attribute_value_to_spec(
        self,
        name: str,
        value: str,
        item: dict[str, object],
        payload: dict[str, object],
        spec: dict[str, object] | None,
    ) -> str:
        input_values = self._coupang_spec_input_values(spec)
        if input_values:
            value_key = self._normalize_text_key(value)
            for allowed in input_values:
                allowed_key = self._normalize_text_key(allowed)
                if value_key and allowed_key and (value_key == allowed_key or value_key in allowed_key or allowed_key in value_key):
                    return allowed
            return self._select_coupang_input_value(name, item, payload, input_values)
        data_type = str(spec.get("data_type") or "").upper() if isinstance(spec, dict) else ""
        if data_type == "NUMBER" or self._coupang_numeric_attribute_name(name):
            match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
            if match:
                return match.group(0)
            fallback = self._coupang_required_attribute_fallback(name, item, payload, None)
            match = re.search(r"\d+(?:\.\d+)?", str(fallback or ""))
            return match.group(0) if match else "1"
        if not str(value or "").strip() or "상세 조건 확인" in str(value or ""):
            return self._coupang_required_attribute_fallback(name, item, payload, None)
        return str(value or "").strip()

    def _coupang_exposed_attribute_combo(self, item: dict[str, object]) -> tuple[tuple[str, str], ...]:
        attrs = item.get("attributes", [])
        if not isinstance(attrs, list):
            return tuple()
        combo: list[tuple[str, str]] = []
        for attr in attrs:
            if not isinstance(attr, dict):
                continue
            if str(attr.get("exposed") or "").upper() != "EXPOSED":
                continue
            name = str(attr.get("attributeTypeName") or "").strip()
            value = str(attr.get("attributeValueName") or "").strip()
            if name and value:
                combo.append((name, value))
        return tuple(combo)

    def _ensure_coupang_item_exposed_option(
        self,
        item: dict[str, object],
        index: int,
        used_values: set[str],
        attribute_name: str = "옵션",
    ) -> None:
        attrs = item.get("attributes", [])
        if not isinstance(attrs, list):
            attrs = []
        option_value = self._clean_coupang_option_text(attribute_name, item.get("itemName")) or f"{attribute_name} {index}"
        if option_value in used_values:
            option_value = f"{option_value} {index}"
        used_values.add(option_value)
        for attr in attrs:
            if isinstance(attr, dict) and str(attr.get("attributeTypeName") or "").strip() == attribute_name:
                attr["attributeValueName"] = option_value
                attr["exposed"] = "EXPOSED"
                item["attributes"] = attrs
                return
        attrs.insert(0, {"attributeTypeName": attribute_name, "attributeValueName": option_value, "exposed": "EXPOSED"})
        item["attributes"] = attrs

    def _ensure_coupang_purchase_options_distinct(
        self,
        payload: dict[str, object],
        allowed_names: set[str] | None = None,
        purchase_names: set[str] | None = None,
    ) -> None:
        items = payload.get("items", [])
        if not isinstance(items, list) or len(items) <= 1:
            return
        combos = [
            self._coupang_exposed_attribute_combo(item)
            for item in items
            if isinstance(item, dict)
        ]
        if not combos:
            return
        if all(combo and combos.count(combo) == 1 for combo in combos):
            return
        allowed_names = allowed_names or set()
        purchase_names = purchase_names or set()
        fallback_order = ("색상", "사이즈", "종류", "타입", "규격", "크기", "디자인", "옵션")
        candidate_names = [
            name
            for name in fallback_order
            if (not allowed_names or name in allowed_names)
            and (not purchase_names or name in purchase_names or name == "옵션")
        ]
        if not candidate_names:
            return
        attribute_name = candidate_names[0]
        used_values: set[str] = set()
        for index, item in enumerate(items, start=1):
            if isinstance(item, dict):
                self._ensure_coupang_item_exposed_option(item, index, used_values, attribute_name)

    def _validate_coupang_purchase_options(
        self,
        payload: dict[str, object],
        allowed_names: set[str] | None = None,
    ) -> None:
        items = payload.get("items", [])
        if not isinstance(items, list):
            return
        allowed_names = allowed_names or set()
        seen: set[tuple[tuple[str, str], ...]] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            attrs = item.get("attributes", [])
            if not isinstance(attrs, list):
                continue
            for attr in attrs:
                if not isinstance(attr, dict):
                    continue
                name = str(attr.get("attributeTypeName") or "").strip()
                value = str(attr.get("attributeValueName") or "").strip()
                if (
                    allowed_names
                    and str(attr.get("exposed") or "").upper() == "EXPOSED"
                    and name in {"옵션", "옵션명"}
                    and name not in allowed_names
                ):
                    raise RuntimeError(f"쿠팡 카테고리에서 허용하지 않는 구매옵션명: {name}")
                if self._coupang_numeric_attribute_name(name) and (
                    not re.search(r"\d", value) or "상세 조건 확인" in value
                ):
                    raise RuntimeError(f"쿠팡 숫자형 속성 값 확인 필요: {name}={value}")
                if self._coupang_option_text_has_unavailable_marker(value):
                    raise RuntimeError(f"쿠팡 판매불가 옵션 값 확인 필요: {name}={value}")
            combo = self._coupang_exposed_attribute_combo(item)
            if len(items) > 1:
                if not combo:
                    raise RuntimeError("쿠팡 구매옵션 노출값이 없어 다중 옵션 등록을 막았습니다.")
                if combo in seen:
                    raise RuntimeError(f"쿠팡 구매옵션 조합 중복 확인 필요: {combo}")
                seen.add(combo)

    def _coupang_notice_categories(self, category_meta: object) -> list[dict[str, object]]:
        categories: list[dict[str, object]] = []
        if isinstance(category_meta, dict):
            for key, value in category_meta.items():
                if str(key).lower() == "noticecategories" and isinstance(value, list):
                    categories.extend(item for item in value if isinstance(item, dict))
                else:
                    categories.extend(self._coupang_notice_categories(value))
        elif isinstance(category_meta, list):
            for item in category_meta:
                categories.extend(self._coupang_notice_categories(item))
        return categories

    def _coupang_preferred_notice_category(self, category_meta: dict[str, object]) -> dict[str, object] | None:
        categories = self._coupang_notice_categories(category_meta)
        if not categories:
            return None
        for category in categories:
            name = str(category.get("noticeCategoryName") or category.get("categoryName") or "")
            if "가구" in name:
                return category
        return categories[0]

    def _coupang_notices_from_category_meta(
        self,
        item: dict[str, object],
        payload: dict[str, object],
        category_meta: dict[str, object],
    ) -> list[dict[str, str]]:
        category = self._coupang_preferred_notice_category(category_meta)
        if not category:
            return item.get("notices", []) if isinstance(item.get("notices"), list) else []
        category_name = str(category.get("noticeCategoryName") or category.get("categoryName") or "").strip()
        details = category.get("noticeCategoryDetailNames") or category.get("details") or category.get("noticeCategoryDetails")
        if not isinstance(details, list):
            details = []
        notices: list[dict[str, str]] = []
        for detail in details:
            if isinstance(detail, dict):
                detail_name = str(
                    detail.get("noticeCategoryDetailName")
                    or detail.get("name")
                    or detail.get("detailName")
                    or ""
                ).strip()
                required = str(detail.get("required") or detail.get("mandatory") or "").upper()
                if required and required not in {"MANDATORY", "REQUIRED", "Y", "TRUE", "1"}:
                    continue
            else:
                detail_name = str(detail or "").strip()
            if not detail_name:
                continue
            notices.append(
                {
                    "noticeCategoryName": category_name,
                    "noticeCategoryDetailName": detail_name,
                    "content": self._coupang_notice_content(detail_name, item, payload),
                }
            )
        return notices or (item.get("notices", []) if isinstance(item.get("notices"), list) else [])

    def _coupang_notice_content(self, detail_name: str, item: dict[str, object], payload: dict[str, object]) -> str:
        name = str(detail_name or "")
        normalized = self._normalize_text_key(name)
        product_name = str(item.get("itemName") or payload.get("generalProductName") or payload.get("displayProductName") or "상품 상세페이지 참조")
        manufacturer = str(payload.get("manufacturer") or "기타")
        origin = self._attribute_value(item, ("원산지", "제조국", "제조국(원산지)")) or "중국"
        color = self._attribute_value(item, ("색상", "컬러")) or "우드톤"
        material = self._attribute_value(item, ("가구/홈 재질", "재질", "주요 소재")) or "목재형 소재"
        if "품명" in name or "모델" in name:
            return self._clip_text(product_name, 100)
        if "kc" in normalized or "인증" in name:
            return str(payload.get("_kcCertificationText") or "관련 법령에 따름")
        if "색상" in name or "컬러" in name:
            return color
        if "구성품" in name:
            return "본품"
        if "소재" in name or "재질" in name:
            return material
        if "제조자" in name or "수입자" in name or "제조사" in name:
            return manufacturer
        if "제조국" in name or "원산지" in name:
            return origin
        if "크기" in name or "치수" in name or "사이즈" in name:
            return self._attribute_value(item, ("사이즈", "규격", "크기")) or "상세페이지 참조"
        if "재공급" in name or "리퍼브" in name:
            return "해당사항 없음"
        if "배송" in name or "설치" in name:
            return "배송비 무료, 설치비 없음"
        if "품질보증" in name or "보증" in name:
            return "관련 법 및 소비자분쟁해결기준에 따름"
        if "a/s" in normalized or "as" in normalized or "책임자" in name or "전화번호" in name:
            return str(payload.get("companyContactNumber") or "판매자 문의")
        return "상세페이지 참조"

    def _attribute_value(self, item: dict[str, object], names: tuple[str, ...]) -> str:
        attrs = item.get("attributes", [])
        if not isinstance(attrs, list):
            return ""
        for attr in attrs:
            if not isinstance(attr, dict):
                continue
            attr_name = str(attr.get("attributeTypeName") or "")
            if attr_name in names:
                value = str(attr.get("attributeValueName") or "").strip()
                if value:
                    return value
        return ""

    def _coupang_category_attribute_specs(self, value: object) -> list[dict[str, object]]:
        specs: list[dict[str, object]] = []
        if isinstance(value, dict):
            lower_keys = {str(key).lower(): key for key in value}
            name_key = lower_keys.get("attributetypename")
            if not name_key and (
                "exposed" in lower_keys
                or "groupnumber" in lower_keys
                or "inputtype" in lower_keys
                or "basicunit" in lower_keys
                or "usableunits" in lower_keys
            ):
                name_key = lower_keys.get("name")
            if name_key:
                name = str(value.get(name_key) or "").strip()
                if name:
                    required_raw = str(value.get(lower_keys.get("required", ""), "")).upper() if lower_keys.get("required") else ""
                    exposed_raw = str(value.get(lower_keys.get("exposed", ""), "")).upper() if lower_keys.get("exposed") else ""
                    group_number = str(value.get(lower_keys.get("groupnumber", ""), "")).strip() if lower_keys.get("groupnumber") else ""
                    specs.append(
                        {
                            "name": name,
                            "required": required_raw in {"MANDATORY", "REQUIRED", "Y", "TRUE", "1"},
                            "exposed": exposed_raw,
                            "group_number": group_number,
                            "data_type": str(value.get(lower_keys.get("datatype", ""), "")).upper() if lower_keys.get("datatype") else "",
                            "input_type": str(value.get(lower_keys.get("inputtype", ""), "")).upper() if lower_keys.get("inputtype") else "",
                            "input_values": value.get(lower_keys.get("inputvalues", ""), []) if lower_keys.get("inputvalues") else [],
                            "basic_unit": str(value.get(lower_keys.get("basicunit", ""), "")).strip() if lower_keys.get("basicunit") else "",
                            "usable_units": value.get(lower_keys.get("usableunits", ""), []) if lower_keys.get("usableunits") else [],
                        }
                    )
            for item in value.values():
                specs.extend(self._coupang_category_attribute_specs(item))
        elif isinstance(value, list):
            for item in value:
                specs.extend(self._coupang_category_attribute_specs(item))
        deduped: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for spec in specs:
            key = (str(spec.get("name") or ""), str(spec.get("group_number") or ""))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(spec)
        return deduped

    def _coupang_required_attribute_names(self, value: object) -> list[str]:
        names = [
            str(spec.get("name") or "").strip()
            for spec in self._coupang_category_attribute_specs(value)
            if spec.get("required") and str(spec.get("name") or "").strip()
        ]
        return self._dedupe_text_items(names)[:30]

    def _coupang_purchase_attribute_names(
        self,
        attribute_specs: list[dict[str, object]],
        required_names: list[str],
    ) -> set[str]:
        required_set = set(required_names)
        names = {
            str(spec.get("name") or "")
            for spec in attribute_specs
            if str(spec.get("exposed") or "").upper() == "EXPOSED"
        }
        for name in required_set:
            if name in {"색상", "컬러", "사이즈"}:
                names.add(name)
        return {name for name in names if name}

    def _coupang_required_names_for_item(
        self,
        required_names: list[str],
        attribute_specs: list[dict[str, object]],
        item: dict[str, object],
        payload: dict[str, object],
    ) -> list[str]:
        selected = list(required_names)
        groups: dict[str, list[str]] = {}
        for spec in attribute_specs:
            if not spec.get("required"):
                continue
            group_number = str(spec.get("group_number") or "").strip()
            if not group_number or group_number.upper() in {"NONE", "0", "NULL"}:
                continue
            name = str(spec.get("name") or "").strip()
            if name:
                groups.setdefault(group_number, []).append(name)
        for names in groups.values():
            group_names = [name for name in self._dedupe_text_items(names) if name in selected]
            if len(group_names) <= 1:
                continue
            choice = self._coupang_group_attribute_choice(group_names, item, payload)
            selected = [name for name in selected if name not in group_names or name == choice]
        return self._dedupe_text_items(selected)

    def _coupang_group_attribute_choice(
        self,
        names: list[str],
        item: dict[str, object],
        payload: dict[str, object],
    ) -> str:
        haystack = f"{item.get('itemName') or ''} {payload.get('sellerProductName') or ''} {payload.get('displayProductName') or ''}"
        if any("용량" in name for name in names) and re.search(r"\d+(?:\.\d+)?\s*(ml|mL|ML|l|L|리터)", haystack):
            return next(name for name in names if "용량" in name)
        if any(("중량" in name or "무게" in name) for name in names) and re.search(r"\d+(?:\.\d+)?\s*(kg|KG|g|G)", haystack):
            return next(name for name in names if "중량" in name or "무게" in name)
        for preferred in ("개당 수량", "수량", "개당 용량", "개당 중량"):
            if preferred in names:
                return preferred
        return names[0]

    def _remove_coupang_unselected_group_attributes(
        self,
        attrs: list[dict[str, object]],
        attribute_specs: list[dict[str, object]],
        selected_required_names: set[str],
    ) -> None:
        grouped_required_names = {
            str(spec.get("name") or "")
            for spec in attribute_specs
            if spec.get("required")
            and str(spec.get("group_number") or "").strip()
            and str(spec.get("group_number") or "").strip().upper() not in {"NONE", "0", "NULL"}
        }
        if not grouped_required_names:
            return
        attrs[:] = [
            attr
            for attr in attrs
            if not isinstance(attr, dict)
            or str(attr.get("attributeTypeName") or "") not in grouped_required_names
            or str(attr.get("attributeTypeName") or "") in selected_required_names
        ]

    def _coupang_required_attribute_fallback(
        self,
        name: str,
        item: dict[str, object],
        payload: dict[str, object],
        spec: dict[str, object] | None = None,
    ) -> str:
        input_values = self._coupang_spec_input_values(spec)
        if input_values:
            return self._select_coupang_input_value(name, item, payload, input_values)
        normalized = self._normalize_text_key(name)
        item_name = str(item.get("itemName") or "")
        payload_name = str(payload.get("sellerProductName") or payload.get("displayProductName") or "")
        if "브랜드" in name or "brand" in normalized:
            return str(payload.get("brand") or "브랜드 없음")
        if "제조" in name or "maker" in normalized or "manufacturer" in normalized:
            return str(payload.get("manufacturer") or "기타")
        if name == "Variation MPN":
            return str(item.get("externalVendorSku") or item.get("modelNo") or "VAR-001")
        if name == "Parent MPN":
            return str(item.get("modelNo") or payload.get("sellerProductName") or "PARENT-001")[:100]
        if name == "GTIN":
            return "없음"
        if "모델" in name or "model" in normalized:
            return str(item.get("modelNo") or "기본")
        if "수량" in name or "개수" in name:
            return "1개"
        if "용량" in name:
            match = re.search(r"(\d+(?:\.\d+)?)\s*(ml|mL|ML|l|L|리터)", f"{item_name} {payload_name}")
            if match:
                unit = match.group(2)
                unit = "ml" if unit.lower() == "ml" else ("L" if unit.lower() == "l" or unit == "리터" else unit)
                return f"{match.group(1)}{unit}"
            return "1ml"
        if "중량" in name or "무게" in name:
            match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|KG|g|G)", f"{item_name} {payload_name}")
            if match:
                unit = match.group(2).lower()
                return f"{match.group(1)}{unit}"
            return "1g"
        if "색상" in name or "컬러" in name or "color" in normalized:
            for attr in item.get("attributes", []):
                if isinstance(attr, dict) and str(attr.get("attributeTypeName") or "") in {"색상", "컬러"}:
                    cleaned = self._clean_coupang_option_text("색상", attr.get("attributeValueName"))
                    if cleaned:
                        return cleaned
            cleaned_name = self._clean_coupang_option_text("색상", item_name)
            if cleaned_name and not re.fullmatch(r"\d+", cleaned_name) and not cleaned_name.startswith("옵션"):
                return cleaned_name
            return "혼합색상"
        if "단 수" in name or "단수" in name:
            match = re.search(r"(\d+)\s*단", item_name)
            return f"{match.group(1)}단" if match else "1단"
        if "사용연령" in name or "연령" in name:
            return "전연령"
        if "분리" in name or "일체" in name:
            return "일체형"
        if "본품" in name or "리필" in name:
            return "본품"
        if "조립" in name:
            return "조립 필수"
        if "재질" in name or "소재" in name:
            haystack = f"{item_name} {payload_name}"
            if re.search(r"원목|목재|우드", haystack):
                return "목재"
            if re.search(r"금속|철|스틸|강철", haystack):
                return "금속"
            if re.search(r"플라스틱|PVC|실리콘", haystack, flags=re.IGNORECASE):
                return "플라스틱"
            return "기타"
        if "용도" in name:
            return "일반용"
        if "구성" in name or "구성 요소" in name:
            return "본품"
        if "스타일" in name or "형태" in name:
            return "기본형"
        if "권장" in name or "표면" in name:
            return "일반 표면"
        if "가능" in name or "여부" in name or "유무" in name:
            return "해당없음"
        if "전용" in name:
            return "해당없음"
        if "향기" in name:
            return "무향"
        if "제형" in name:
            return "기타"
        if any(token in name for token in ("길이", "너비", "높이", "폭", "가로", "세로", "두께")):
            match = re.search(r"(\d+(?:\.\d+)?)\s*(cm|CM|mm|MM|m|M)", f"{item_name} {payload_name}")
            if match:
                return f"{match.group(1)}{match.group(2).lower()}"
            return "1cm"
        if "사이즈" in name or "크기" in name or "size" in normalized:
            for attr in item.get("attributes", []):
                if isinstance(attr, dict) and str(attr.get("attributeTypeName") or "") in {"사이즈", "규격", "크기"}:
                    return str(attr.get("attributeValueName") or "기본")
            if item_name and not item_name.startswith("옵션"):
                return item_name
            return "기본"
        if self._coupang_numeric_attribute_name(name):
            return "1"
        return "상세 조건 확인"

    def _coupang_hmac_headers(
        self,
        method: str,
        path: str,
        query: str,
        body: str,
        settings: dict[str, str],
    ) -> dict[str, str]:
        access_key = str(settings.get("coupang_access_key") or "").strip()
        secret_key = str(settings.get("coupang_secret_key") or "").strip()
        if not access_key or not secret_key:
            raise RuntimeError("쿠팡 access_key/secret_key가 필요합니다.")
        signed_date = datetime.utcnow().strftime("%y%m%dT%H%M%SZ")
        message = signed_date + method.upper() + path + query
        signature = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
        authorization = (
            f"CEA algorithm=HmacSHA256, access-key={access_key}, "
            f"signed-date={signed_date}, signature={signature}"
        )
        return {"Authorization": authorization, "X-EXTENDED-TIMEOUT": "90000"}

    def _safe_response_json(self, response: object) -> dict[str, object]:
        try:
            data = response.json()
            return data if isinstance(data, dict) else {"data": data}
        except Exception:
            return {"text": str(getattr(response, "text", ""))}

    def _strip_draft_keys(self, value: object) -> object:
        if isinstance(value, dict):
            return {
                key: self._strip_draft_keys(item)
                for key, item in value.items()
                if not str(key).startswith("_")
            }
        if isinstance(value, list):
            return [self._strip_draft_keys(item) for item in value]
        return value

    def _extract_product_no(self, body: object) -> str:
        if isinstance(body, dict):
            data_value = body.get("data")
            if isinstance(data_value, (int, float)) and str(data_value).strip():
                return str(data_value)
            if isinstance(data_value, str) and re.fullmatch(r"\d+", data_value.strip()):
                return data_value.strip()
            for key in ("productNo", "product_no", "originProductNo", "sellerProductId", "sellerProductItemId", "vendorItemId", "itemId"):
                value = body.get(key)
                if str(value or "").strip():
                    return str(value)
            for item in body.values():
                found = self._extract_product_no(item)
                if found:
                    return found
        if isinstance(body, list):
            for item in body:
                found = self._extract_product_no(item)
                if found:
                    return found
        return ""

    def _market_publish_blockers(self, product: MarketProduct, platform: str) -> list[str]:
        issues = list(product.issues)
        market_dir = product.folder / "market"
        payload_name = "naver_payload.json" if platform == "naver" else "coupang_payload.json"
        payload = self._read_json_file(market_dir / payload_name)
        if not payload:
            issues.append(f"{payload_name} 없음. 먼저 등록 초안을 생성하세요.")
        publish_result = self._read_json_file(market_dir / "publish_result.json")
        existing = publish_result.get(platform) if isinstance(publish_result, dict) else None
        if (
            isinstance(existing, dict)
            and str(existing.get("status") or "").startswith("live")
            and str(existing.get("product_no") or "").strip()
            and str(existing.get("product_no") or "").strip().upper() != "ERROR"
        ):
            if platform not in {"coupang", "naver"}:
                issues.append(f"{platform} 상품번호가 이미 저장되어 있어 중복 등록을 막았습니다.")
        sale_price = self._effective_sale_price(product, platform)
        if sale_price <= 0:
            issues.append("판매가가 비어 있거나 숫자가 아닙니다.")
        if self._is_baby_chair_product(product) and not self._market_kc_certification_number(product):
            issues.append("KC 인증번호 필요: 어린이제품/유아식탁의자 live 등록 전 실제 인증번호를 확인하세요.")
        settings = self._market_settings_data(include_secrets=True)
        if not self._positive_int(settings.get("stock_quantity", "") or "100"):
            issues.append("재고 수량이 비어 있거나 숫자가 아닙니다.")
        image_refs = self._market_image_references(product)
        mode = settings.get("upload_mode") or "live"
        if platform == "naver":
            category_code = self._effective_category_code(product, "naver", settings)
            outbound_code = self._effective_location_code(settings, "naver", "outbound")
            return_code = self._effective_location_code(settings, "naver", "return")
            if mode == "live" and self._is_auto_lookup_value(category_code):
                issues.append("네이버 카테고리는 자동 후보만 있습니다. live 전 leafCategoryId API 조회/확정이 필요합니다.")
            if mode == "live" and (self._is_auto_lookup_value(outbound_code) or self._is_auto_lookup_value(return_code)):
                issues.append("네이버 출고지/반품지 코드는 자동 후보 상태입니다. live 전 판매자 주소 코드 조회가 필요합니다.")
            if mode == "live":
                issues.extend(self._market_api_runtime_issues("naver"))
                for key in ("naver_account_id", "naver_client_id", "naver_client_secret"):
                    if not settings.get(key):
                        issues.append(f"{key} 필요")
                for key in ("naver_as_phone", "naver_delivery_company", "naver_origin_area_code"):
                    value = str(settings.get(key) or "").strip()
                    if not value or self._is_auto_lookup_value(value):
                        issues.append(f"{key} 저장값 필요")
        if platform == "coupang":
            category_code = self._effective_category_code(product, "coupang", settings)
            outbound_code = self._effective_location_code(settings, "coupang", "outbound")
            return_code = self._effective_location_code(settings, "coupang", "return")
            if mode == "live" and self._is_auto_lookup_value(category_code):
                issues.append("쿠팡 카테고리는 자동 후보만 있습니다. live 전 displayCategoryCode API 조회/확정이 필요합니다.")
            if mode == "live" and (self._is_auto_lookup_value(outbound_code) or self._is_auto_lookup_value(return_code)):
                issues.append("쿠팡 출고지/반품지 코드는 자동 후보 상태입니다. live 전 판매자 배송지 코드 조회가 필요합니다.")
            if mode == "live" and not self._market_image_refs_are_http(image_refs):
                for key in ("naver_account_id", "naver_client_id", "naver_client_secret"):
                    if not settings.get(key):
                        issues.append("쿠팡 local-file 이미지는 네이버 이미지 업로드로 HTTPS URL을 만든 뒤 vendorPath에 넣어야 합니다.")
                        break
            if mode == "live":
                issues.extend(self._market_api_runtime_issues("coupang"))
                for key in ("coupang_vendor_id", "coupang_access_key", "coupang_secret_key"):
                    if not settings.get(key):
                        issues.append(f"{key} 필요")
                for key in (
                    "coupang_vendor_user_id",
                    "coupang_delivery_company_code",
                    "return_charge_name",
                    "company_contact_number",
                    "return_zip_code",
                    "return_address",
                    "return_address_detail",
                ):
                    value = str(settings.get(key) or "").strip()
                    if not value or self._is_auto_lookup_value(value):
                        issues.append(f"{key} 저장값 필요")
        copy_text = self._market_publish_copy_text(payload, platform)
        issues.extend(self._market_forbidden_copy_issues(copy_text))
        issues.extend(self._market_payload_required_issues(payload, platform))
        return self._dedupe_text_items(issues)

    def _market_registration_noise_issues(self, label: str, value: object) -> list[str]:
        text = str(value or "")
        if not text:
            return []
        noise_terms = (
            "공급사의 인기상품",
            "인기상품 더보기",
            "상품상세 더보기",
            "마무리하세요",
            "인사이트 얻기",
            "돈버는 쇼핑",
            "도매꾹",
            "양우산",
            "치매",
        )
        return [f"{label} 오염 확인 필요: {term}" for term in noise_terms if term in text]

    def _market_payload_required_issues(self, payload: dict[str, object], platform: str) -> list[str]:
        if not isinstance(payload, dict):
            return ["등록 payload가 비어 있습니다."]
        issues: list[str] = []
        if platform == "naver":
            origin_product = payload.get("originProduct")
            if not isinstance(origin_product, dict):
                return ["네이버 originProduct payload가 비어 있습니다."]
            for key, label in (("name", "네이버 상품명"), ("detailContent", "네이버 상세설명")):
                if not str(origin_product.get(key) or "").strip():
                    issues.append(f"{label} 누락")
            if self._positive_int(origin_product.get("salePrice")) <= 0:
                issues.append("네이버 판매가 누락")
            images = origin_product.get("images")
            representative = images.get("representativeImage") if isinstance(images, dict) else None
            if not isinstance(representative, dict) or not str(representative.get("url") or "").strip():
                issues.append("네이버 대표이미지 누락")
            detail_attribute = origin_product.get("detailAttribute")
            if not isinstance(detail_attribute, dict):
                return issues + ["네이버 detailAttribute 누락"]
            origin_info = detail_attribute.get("originAreaInfo")
            if isinstance(origin_info, dict):
                origin_content = self._normalize_market_origin(origin_info.get("content", ""))
                origin_code = str(origin_info.get("originAreaCode") or "").strip()
                expected_origin_codes = {"중국": "0200037", "대한민국": "0200014"}
                expected_origin_code = expected_origin_codes.get(origin_content)
                if expected_origin_code and origin_code != expected_origin_code:
                    issues.append(f"네이버 원산지코드 불일치: {origin_content}={expected_origin_code}")
            seo_info = detail_attribute.get("seoInfo")
            if not isinstance(seo_info, dict) or not str(seo_info.get("pageTitle") or "").strip():
                issues.append("네이버 SEO pageTitle 누락")
            if not isinstance(seo_info, dict) or not str(seo_info.get("metaDescription") or "").strip():
                issues.append("네이버 SEO metaDescription 누락")
            if isinstance(seo_info, dict):
                page_title = str(seo_info.get("pageTitle") or "")
                meta_description = str(seo_info.get("metaDescription") or "")
                issues.extend(self._market_registration_noise_issues("네이버 SEO 제목", page_title))
                issues.extend(self._market_registration_noise_issues("네이버 SEO 설명", meta_description))
                if len(page_title) > 70:
                    issues.append("네이버 SEO pageTitle 70자 초과")
                if len(meta_description) > 160:
                    issues.append("네이버 SEO metaDescription 160자 초과")
            seller_tags = seo_info.get("sellerTags") if isinstance(seo_info, dict) else None
            if not isinstance(seller_tags, list) or not seller_tags:
                issues.append("네이버 SEO 태그 누락")
            elif len(seller_tags) != len({str(tag.get("text") if isinstance(tag, dict) else tag) for tag in seller_tags}):
                issues.append("네이버 SEO 태그 중복")
            if isinstance(seller_tags, list):
                for tag in seller_tags:
                    tag_text = str(tag.get("text") if isinstance(tag, dict) else tag)
                    issues.extend(self._market_registration_noise_issues("네이버 SEO 태그", tag_text))
            option_info = detail_attribute.get("optionInfo")
            combinations = option_info.get("optionCombinations") if isinstance(option_info, dict) else None
            if not isinstance(combinations, list) or not combinations:
                issues.append("네이버 옵션 조합 누락")
            else:
                for index, option in enumerate(combinations, start=1):
                    if not isinstance(option, dict):
                        issues.append(f"네이버 {index}번째 옵션 형식 오류")
                        continue
                    manager_code = str(option.get("sellerManagerCode") or "")
                    if not manager_code:
                        issues.append(f"네이버 {index}번째 옵션 관리코드 누락")
                    elif len(manager_code) > 20:
                        issues.append(f"네이버 {index}번째 옵션 관리코드 20자 초과")
                    if not any(str(option.get(f"optionName{group_index}") or "").strip() for group_index in range(1, 4)):
                        issues.append(f"네이버 {index}번째 옵션명 누락")
                    for group_index in range(1, 4):
                        issues.extend(self._market_registration_noise_issues(f"네이버 {index}번째 옵션명", option.get(f"optionName{group_index}")))
            payload_name = str(origin_product.get("name") or "")
            if any(term in payload_name for term in ("커튼", "커텐", "가림막", "블라인드", "린넨", "집게")):
                payload_text = json.dumps(payload, ensure_ascii=False)
                if "이동식 수납선반" in payload_text:
                    issues.append("네이버 상품속성 오염 확인 필요: 이동식 수납선반")
        elif platform == "coupang":
            for key, label in (
                ("sellerProductName", "쿠팡 상품명"),
                ("displayProductName", "쿠팡 노출상품명"),
                ("generalProductName", "쿠팡 일반상품명"),
                ("displayCategoryCode", "쿠팡 카테고리"),
            ):
                if not str(payload.get(key) or "").strip():
                    issues.append(f"{label} 누락")
            for key, label in (
                ("sellerProductName", "쿠팡 상품명"),
                ("displayProductName", "쿠팡 노출상품명"),
                ("generalProductName", "쿠팡 일반상품명"),
            ):
                if len(str(payload.get(key) or "")) > COUPANG_PRODUCT_NAME_LIMIT:
                    issues.append(f"{label} {COUPANG_PRODUCT_NAME_LIMIT}자 초과")
            items = payload.get("items")
            if not isinstance(items, list) or not items:
                return issues + ["쿠팡 옵션 item 누락"]
            for index, item in enumerate(items, start=1):
                if not isinstance(item, dict):
                    issues.append(f"쿠팡 {index}번째 item 형식 오류")
                    continue
                if not str(item.get("itemName") or "").strip():
                    issues.append(f"쿠팡 {index}번째 옵션명 누락")
                if self._positive_int(item.get("salePrice")) <= 0:
                    issues.append(f"쿠팡 {index}번째 판매가 누락")
                if not item.get("images"):
                    issues.append(f"쿠팡 {index}번째 이미지 누락")
                if not item.get("notices"):
                    issues.append(f"쿠팡 {index}번째 상품고시 누락")
                if not item.get("attributes"):
                    issues.append(f"쿠팡 {index}번째 속성 누락")
                if not item.get("contents"):
                    issues.append(f"쿠팡 {index}번째 상세내용 누락")
                if not item.get("searchTags"):
                    issues.append(f"쿠팡 {index}번째 검색태그 누락")
                elif isinstance(item.get("searchTags"), list):
                    tags = [str(tag or "") for tag in item.get("searchTags", [])]
                    if len(tags) > 20:
                        issues.append(f"쿠팡 {index}번째 검색태그 20개 초과")
                    if len(tags) != len(set(tags)):
                        issues.append(f"쿠팡 {index}번째 검색태그 중복")
                    for tag in tags:
                        issues.extend(self._market_registration_noise_issues(f"쿠팡 {index}번째 검색태그", tag))
                attributes = item.get("attributes")
                if isinstance(attributes, list):
                    for attr in attributes:
                        if isinstance(attr, dict):
                            issues.extend(self._market_registration_noise_issues(f"쿠팡 {index}번째 속성", attr.get("attributeValueName")))
            payload_name = " ".join(str(payload.get(key) or "") for key in ("sellerProductName", "displayProductName", "generalProductName"))
            if any(term in payload_name for term in ("커튼", "커텐", "가림막", "블라인드", "린넨", "집게")):
                payload_text = json.dumps(payload, ensure_ascii=False)
                if "이동식 수납선반" in payload_text:
                    issues.append("쿠팡 상품속성 오염 확인 필요: 이동식 수납선반")
        return issues

    def _market_publish_copy_text(self, payload: dict[str, object], platform: str) -> str:
        if not isinstance(payload, dict):
            return ""
        fields: list[str] = []
        if platform == "naver":
            origin_product = payload.get("originProduct")
            if isinstance(origin_product, dict):
                fields.extend(
                    str(origin_product.get(key) or "")
                    for key in (
                        "name",
                        "detailContent",
                    )
                )
                detail_attribute = origin_product.get("detailAttribute")
                if isinstance(detail_attribute, dict):
                    seller_code = detail_attribute.get("sellerCodeInfo")
                    if isinstance(seller_code, dict):
                        fields.append(str(seller_code.get("sellerManagementCode") or ""))
                    seo_info = detail_attribute.get("seoInfo")
                    if isinstance(seo_info, dict):
                        fields.extend(str(seo_info.get(key) or "") for key in ("pageTitle", "metaDescription"))
                        seller_tags = seo_info.get("sellerTags")
                        if isinstance(seller_tags, list):
                            for tag in seller_tags:
                                if isinstance(tag, dict):
                                    fields.append(str(tag.get("text") or ""))
                                else:
                                    fields.append(str(tag or ""))
        elif platform == "coupang":
            fields.extend(
                str(payload.get(key) or "")
                for key in (
                    "sellerProductName",
                    "displayProductName",
                    "generalProductName",
                )
            )
            for item in payload.get("items") or []:
                if isinstance(item, dict):
                    fields.extend(
                        str(item.get(key) or "")
                        for key in (
                            "itemName",
                            "noticeProductName",
                            "contents",
                        )
                    )
        else:
            fields.extend(str(value) for value in payload.values() if isinstance(value, str))
        cleaned_fields = [self._market_visible_copy_text(field) for field in fields]
        return "\n".join(field for field in cleaned_fields if field.strip())

    def _market_visible_copy_text(self, value: object) -> str:
        text = str(value or "")
        if "<" in text and ">" in text:
            text = re.sub(r"<[^>]*>", " ", text)
            text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _build_market_draft_bundle(
        self,
        product: MarketProduct,
        include_coupang_animated_webp: bool = False,
    ) -> dict[str, object]:
        settings = self._market_settings_data(include_secrets=False)
        copy = self._build_market_copy(product)
        upload_manifest = self._build_upload_manifest(
            product,
            include_coupang_animated_webp=include_coupang_animated_webp,
        )
        existing_manifest = self._read_json_file(product.folder / "market" / "upload_manifest.json")
        if existing_manifest and self._market_image_refs_are_http(self._market_image_references(product, existing_manifest)):
            upload_manifest = self._merge_fresh_coupang_animated_webp(upload_manifest, existing_manifest)
        image_refs = self._market_image_references(product, upload_manifest)
        naver_payload = self._build_naver_payload(product, copy, settings, image_refs)
        coupang_payload = self._build_coupang_payload(product, copy, settings, image_refs)
        naver_prompt = self._build_naver_market_chatgpt_prompt(product, copy, naver_payload)
        coupang_prompt = self._build_coupang_market_chatgpt_prompt(product, copy, coupang_payload)
        naver_pricing = naver_payload.get("_draft", {}).get("pricing", {}) if isinstance(naver_payload.get("_draft"), dict) else {}
        coupang_pricing = coupang_payload.get("_draft", {}).get("pricing", {}) if isinstance(coupang_payload.get("_draft"), dict) else {}
        return {
            "naver_payload": naver_payload,
            "coupang_payload": coupang_payload,
            "upload_manifest": upload_manifest,
            "pricing_plan": {
                "product_code": product.code,
                "product_name": product.product_name,
                "source_price": self._market_source_cost(product),
                "target_net_margin_rate": naver_pricing.get("target_net_margin_rate", self._percent_number(settings.get("margin_rate"), float(DEFAULT_TARGET_NET_MARGIN_RATE))),
                "tax_rate": naver_pricing.get("tax_rate", self._percent_number(settings.get("tax_rate"), float(DEFAULT_MARKET_TAX_RATE))),
                "other_fee_rate": naver_pricing.get("other_fee_rate", self._percent_number(settings.get("other_fee_rate"), float(DEFAULT_MARKET_OTHER_FEE_RATE))),
                "naver": naver_pricing,
                "coupang": coupang_pricing,
                "notes": [
                    "수동 판매가가 비어 있으면 수집 원가와 추가 원가에 원가 기준 목표 순이익, 플랫폼 수수료, 세금, 기타비용을 반영해 자동 산출합니다.",
                    "기본값은 원가 기준 순이익 20%, 세금 10%, 기타비용 0%, 네이버/쿠팡 수수료 10%, 100원 단위 올림입니다.",
                ],
            },
            "seo_keywords": {
                "product_code": product.code,
                "product_name": product.product_name,
                "seo_title": copy.get("seo_title", ""),
                "naver_seo_title": copy.get("naver_seo_title", ""),
                "coupang_seo_title": copy.get("coupang_seo_title", ""),
                "category_text": copy.get("category_text", ""),
                "category_candidates": copy.get("category_candidates", []),
                "keywords": copy.get("keywords", []),
                "naver_keywords": copy.get("naver_keywords", []),
                "coupang_keywords": copy.get("coupang_keywords", []),
                "related_keywords": copy.get("related_keywords", []),
                "search_tags": copy.get("search_tags", []),
                "naver_search_tags": copy.get("naver_search_tags", []),
                "coupang_search_tags": copy.get("coupang_search_tags", []),
                "chatgpt_fallback_prompt": copy.get("chatgpt_seo_prompt", ""),
                "naver_chatgpt_seo_prompt": copy.get("naver_chatgpt_seo_prompt", ""),
                "coupang_chatgpt_seo_prompt": copy.get("coupang_chatgpt_seo_prompt", ""),
                "naver_chatgpt_prompt": naver_prompt,
                "coupang_chatgpt_prompt": coupang_prompt,
                "options": copy.get("options", []),
                "option_groups": copy.get("option_groups", []),
            },
            "market_option_plan": {
                "product_code": product.code,
                "product_name": product.product_name,
                "options": copy.get("options", []),
                "option_groups": copy.get("option_groups", []),
                "naver_strategy": "originProduct.optionInfo.optionCombinationGroupNames + optionCombinations",
                "coupang_strategy": "seller-products.items[] per option with option attributes",
            },
            "registration_plan": {
                "draft_version": MARKET_DRAFT_VERSION,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "product_code": product.code,
                "product_name": product.product_name,
                "steps": [
                    "등록 버튼 실행 시 최신 SEO 제목, 검색 태그, 옵션 payload 자동 갱신",
                    "live 등록 중 네이버 이미지 업로드 API로 1.png~5.png와 detail_page.png HTTPS URL 발급",
                    "네이버/쿠팡 payload에 발급된 이미지 URL 자동 반영",
                    "판매가는 수집 원가에 플랫폼 수수료 10%, 세금 10%, 목표 순익률 20%를 반영해 자동 산출",
                    "저장된 카테고리 코드와 출고지/반품지 코드를 사용해 실제 API 호출",
                    "성공 응답의 상품번호를 publish_result.json에 저장해 중복 등록 방지",
                ],
                "required_user_saved_values": self._market_required_live_setting_keys(),
            },
            "naver_chatgpt_prompt": naver_prompt,
            "coupang_chatgpt_prompt": coupang_prompt,
            "chatgpt_prompt": self._build_market_chatgpt_prompt(product, copy, naver_prompt, coupang_prompt),
        }

    def _merge_fresh_coupang_animated_webp(
        self,
        fresh_manifest: dict[str, object],
        existing_manifest: dict[str, object],
    ) -> dict[str, object]:
        merged = dict(fresh_manifest)
        animated_webp = fresh_manifest.get("coupang_animated_webp")
        if isinstance(animated_webp, dict):
            merged["coupang_animated_webp"] = animated_webp
        else:
            merged.pop("coupang_animated_webp", None)
        return merged

    def _build_coupang_animated_webp_asset(self, product: MarketProduct) -> dict[str, object]:
        animated_dir = product.folder / "market" / "animated_webp"
        animated_dir.mkdir(parents=True, exist_ok=True)
        target = animated_dir / "coupang_feature.webp"
        public_url = self._coupang_animated_webp_public_url(product)
        source_path = self._coupang_animated_webp_source_image(product)
        result: dict[str, object] = {
            "role": "coupang_animated_webp",
            "target_name": target.name,
            "local_path": str(target),
            "public_url": public_url,
            "width": COUPANG_ANIMATED_WEBP_WIDTH,
            "max_bytes": COUPANG_ANIMATED_WEBP_MAX_BYTES,
            "inserted_in_payload": False,
            "notes": [
                "Generated as a Coupang-only animated WebP detail asset.",
                "It is not uploaded through the Naver JPEG image upload flow.",
                "Write a public HTTPS URL to market/coupang_animated_webp_url.txt to insert it into Coupang live HTML.",
            ],
        }
        if source_path is None:
            result["status"] = "source_missing"
            result["public_url"] = ""
            result["inserted_in_payload"] = False
            return result
        result["source_path"] = str(source_path)
        if self._is_valid_animated_webp_file(target):
            result["status"] = "ready"
            result["inserted_in_payload"] = bool(public_url)
            result["size"] = target.stat().st_size
            return result
        try:
            self._write_coupang_animated_webp(source_path, target)
        except Exception as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
            result["public_url"] = ""
            result["inserted_in_payload"] = False
            return result
        result["status"] = "ready" if self._is_valid_animated_webp_file(target) else "invalid"
        result["inserted_in_payload"] = bool(public_url) and result["status"] == "ready"
        if result["status"] != "ready":
            result["public_url"] = ""
        result["size"] = target.stat().st_size if target.exists() else 0
        return result

    def _coupang_animated_webp_source_image(self, product: MarketProduct) -> Path | None:
        for path in product.thumbnail_paths:
            if self._is_valid_thumbnail_file(path):
                return path
        if self._is_valid_image_file(product.detail_page_path):
            return product.detail_page_path
        return None

    def _coupang_animated_webp_public_url(self, product: MarketProduct) -> str:
        url_file = product.folder / "market" / "coupang_animated_webp_url.txt"
        if not url_file.exists() or not url_file.is_file():
            return ""
        try:
            url = re.sub(r"\s+", "", url_file.read_text(encoding="utf-8")).strip()
        except Exception:
            return ""
        return url if self._is_https_webp_url(url) else ""

    def _write_coupang_animated_webp(self, source_path: Path, target: Path) -> None:
        from PIL import Image, ImageOps

        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            base = self._fit_animated_webp_frame(image, COUPANG_ANIMATED_WEBP_WIDTH)
        frame_count = max(8, COUPANG_ANIMATED_WEBP_FRAME_COUNT)
        frames = []
        for index in range(frame_count):
            phase = index / max(1, frame_count - 1)
            wave = 1.0 - abs(phase * 2.0 - 1.0)
            scale = 1.0 + wave * 0.055
            frame = self._zoom_animated_webp_frame(base, scale)
            # Prevent low-detail images from being collapsed into one static WebP frame.
            marker = 248 if index % 2 else 255
            for x in range(frame.width - 2, frame.width):
                for y in range(frame.height - 2, frame.height):
                    frame.putpixel((x, y), (marker, marker, marker))
            frames.append(frame)
        target.parent.mkdir(parents=True, exist_ok=True)
        for quality, step in ((82, 1), (74, 1), (66, 2), (58, 2), (50, 3)):
            selected = frames[::step]
            if len(selected) < 2:
                selected = frames[:2]
            selected[0].save(
                target,
                format="WEBP",
                save_all=True,
                append_images=selected[1:],
                duration=COUPANG_ANIMATED_WEBP_FRAME_DURATION_MS * step,
                loop=0,
                quality=quality,
                method=6,
            )
            if target.stat().st_size <= COUPANG_ANIMATED_WEBP_MAX_BYTES:
                return

    def _fit_animated_webp_frame(self, image, width: int):
        from PIL import Image, ImageOps

        target_size = (width, width)
        fitted = ImageOps.contain(image, target_size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        canvas.paste(fitted, ((width - fitted.width) // 2, (width - fitted.height) // 2))
        return canvas

    def _zoom_animated_webp_frame(self, image, scale: float):
        from PIL import Image

        width, height = image.size
        scaled_width = max(width, int(width * scale))
        scaled_height = max(height, int(height * scale))
        resized = image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        left = max(0, (scaled_width - width) // 2)
        top = max(0, (scaled_height - height) // 2)
        return resized.crop((left, top, left + width, top + height))

    def _is_valid_animated_webp_file(self, path: Path) -> bool:
        if not path.exists() or path.suffix.lower() != ".webp" or path.stat().st_size <= 0:
            return False
        if path.stat().st_size > COUPANG_ANIMATED_WEBP_MAX_BYTES:
            return False
        try:
            from PIL import Image

            with Image.open(path) as image:
                return bool(getattr(image, "is_animated", False)) and int(getattr(image, "n_frames", 1)) >= 2 and image.width <= COUPANG_ANIMATED_WEBP_WIDTH
        except Exception:
            return False

    def _build_upload_manifest(
        self,
        product: MarketProduct,
        include_coupang_animated_webp: bool = False,
    ) -> dict[str, object]:
        local_images = [
            {"role": "representative", "path": str(product.thumbnail_paths[0]), "target_name": "1.png"},
            *[
                {"role": "optional", "path": str(path), "target_name": f"{index}.png"}
                for index, path in enumerate(product.thumbnail_paths[1:], start=2)
            ],
            {"role": "detail_page", "path": str(product.detail_page_path), "target_name": "detail_page.png"},
        ]
        existing_manifest = self._read_json_file(product.folder / "market" / "upload_manifest.json")
        animated_webp = None
        if include_coupang_animated_webp:
            animated_webp = self._build_coupang_animated_webp_asset(product)
        existing_urls = existing_manifest.get("uploaded_image_urls", {}) if isinstance(existing_manifest, dict) else {}
        if not isinstance(existing_urls, dict):
            existing_urls = {}

        def uploaded_url_for(item: dict[str, str]) -> str:
            target_name = str(item["target_name"])
            existing = str(existing_urls.get(target_name) or "").strip()
            if self._is_http_url(existing):
                return existing
            return self._local_file_url(Path(str(item["path"])))

        uploaded_image_urls = {
            item["target_name"]: uploaded_url_for(item)
            for item in local_images
        }
        all_http = all(self._is_http_url(value) for value in uploaded_image_urls.values())
        return {
            "draft_version": MARKET_DRAFT_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "product_code": product.code,
            "product_name": product.product_name,
            "naver_image_upload_endpoint": NAVER_IMAGE_UPLOAD_ENDPOINT,
            "local_images": local_images,
            **({"coupang_animated_webp": animated_webp} if isinstance(animated_webp, dict) else {}),
            "uploaded_image_urls": uploaded_image_urls,
            "upload_status": str(existing_manifest.get("upload_status") or "naver_uploaded") if all_http else "local_paths_ready",
            **({"uploaded_at": existing_manifest.get("uploaded_at")} if all_http and existing_manifest.get("uploaded_at") else {}),
            "notes": [
                "초안에는 빈 칸을 만들지 않기 위해 local-file URL을 넣습니다.",
                "live 등록 전에는 네이버 이미지 업로드 API 결과의 HTTPS URL로 자동 교체되어야 합니다.",
            ],
        }

    def _market_required_live_setting_keys(self) -> list[str]:
        return [
            "naver_account_id",
            "naver_client_id",
            "naver_client_secret",
            "naver_category_id",
            "naver_as_phone",
            "naver_delivery_company",
            "naver_origin_area_code",
            "coupang_vendor_id",
            "coupang_access_key",
            "coupang_secret_key",
            "coupang_category_id",
            "coupang_vendor_user_id",
            "coupang_delivery_company_code",
            "outbound_place_code",
            "return_center_code",
            "return_charge_name",
            "company_contact_number",
            "return_zip_code",
            "return_address",
            "return_address_detail",
        ]

    def _local_file_url(self, path: Path) -> str:
        return LOCAL_IMAGE_URL_PREFIX + path.resolve().as_posix()

    def _market_image_references(
        self,
        product: MarketProduct,
        upload_manifest: dict[str, object] | None = None,
    ) -> dict[str, object]:
        manifest = upload_manifest or self._read_json_file(product.folder / "market" / "upload_manifest.json")
        uploaded_urls = manifest.get("uploaded_image_urls", {}) if isinstance(manifest, dict) else {}
        if not isinstance(uploaded_urls, dict):
            uploaded_urls = {}

        def ref(path: Path, target_name: str, role: str) -> dict[str, str]:
            url = str(uploaded_urls.get(target_name) or "").strip() or self._local_file_url(path)
            return {
                "role": role,
                "target_name": target_name,
                "url": url,
                "local_path": str(path),
            }

        optional = [
            ref(path, f"{index}.png", "optional")
            for index, path in enumerate(product.thumbnail_paths[1:], start=2)
        ]
        detail = ref(product.detail_page_path, "detail_page.png", "detail_page")
        animated_webp_manifest = manifest.get("coupang_animated_webp", {}) if isinstance(manifest, dict) else {}
        animated_webp: dict[str, str] = {}
        if isinstance(animated_webp_manifest, dict) and animated_webp_manifest:
            animated_path = Path(str(animated_webp_manifest.get("local_path") or product.folder / "market" / "animated_webp" / "coupang_feature.webp"))
            animated_url = str(animated_webp_manifest.get("public_url") or animated_webp_manifest.get("url") or "").strip()
            animated_status = str(animated_webp_manifest.get("status") or "")
            public_url = animated_url if animated_status == "ready" and self._is_https_webp_url(animated_url) else ""
            animated_webp = {
                "role": "coupang_animated_webp",
                "target_name": str(animated_webp_manifest.get("target_name") or "coupang_feature.webp"),
                "url": animated_url if self._is_http_url(animated_url) else self._local_file_url(animated_path),
                "public_url": public_url,
                "local_path": str(animated_path),
                "status": animated_status,
                "inserted_in_payload": str(bool(public_url)),
            }
        return {
            "representative": ref(product.thumbnail_paths[0], "1.png", "representative"),
            "optional": optional,
            "detail_page": detail,
            "coupang_animated_webp": animated_webp,
            "all": [ref(product.thumbnail_paths[0], "1.png", "representative"), *optional, detail],
        }

    def _is_http_url(self, value: str | object) -> bool:
        text = str(value or "").strip().lower()
        return text.startswith("http://") or text.startswith("https://")

    def _is_https_url(self, value: str | object) -> bool:
        return str(value or "").strip().lower().startswith("https://")

    def _is_https_webp_url(self, value: str | object) -> bool:
        text = str(value or "").strip()
        try:
            parsed = urllib.parse.urlsplit(text)
        except Exception:
            return False
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return False
        if parsed.username or parsed.password:
            return False
        host = parsed.hostname.strip().lower().rstrip(".")
        if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
            return False
        try:
            import ipaddress

            ip = ipaddress.ip_address(host)
            if not ip.is_global:
                return False
        except ValueError:
            if "." not in host:
                return False
        path = parsed.path
        return path.lower().endswith(".webp")

    def _market_image_refs_are_http(self, image_refs: dict[str, object]) -> bool:
        refs = image_refs.get("all", []) if isinstance(image_refs, dict) else []
        if not isinstance(refs, list) or not refs:
            return False
        urls = [str(item.get("url") or "") for item in refs if isinstance(item, dict)]
        return bool(urls) and all(self._is_http_url(url) for url in urls)

    def _is_auto_lookup_value(self, value: str | object) -> bool:
        return str(value or "").strip().startswith(AUTO_LOOKUP_PREFIX)

    def _market_text_blob(self, product: MarketProduct) -> str:
        chunks = [
            product.product_name,
            product.result_text,
            json.dumps(product.metadata, ensure_ascii=False),
            json.dumps(product.source, ensure_ascii=False),
        ]
        return "\n".join(str(chunk) for chunk in chunks if str(chunk or "").strip())

    def _market_clean_product_source_text(self, text: str | object) -> str:
        cleaned = str(text or "")
        if not cleaned:
            return ""
        for marker in (
            "공급사의 인기상품 더보기",
            "공급사의 인기상품",
            "묶음배송 가능상품",
            "공급사정보 자세히보기",
            "인기상품 더보기",
        ):
            index = cleaned.find(marker)
            if index >= 0:
                cleaned = cleaned[:index]
                break
        return cleaned

    def _market_primary_text_blob(self, product: MarketProduct) -> str:
        source_facts = product.source.get("facts", []) if isinstance(product.source, dict) else []
        metadata_facts = product.metadata.get("facts", []) if isinstance(product.metadata, dict) else []
        chunks: list[str] = [
            product.product_name,
            str(product.source.get("title") or "") if isinstance(product.source, dict) else "",
            str(product.source.get("product_name") or "") if isinstance(product.source, dict) else "",
            str(product.source.get("category") or "") if isinstance(product.source, dict) else "",
            str(product.metadata.get("product_name") or "") if isinstance(product.metadata, dict) else "",
            str(product.metadata.get("category") or "") if isinstance(product.metadata, dict) else "",
        ]
        if isinstance(source_facts, list):
            chunks.extend(str(item or "") for item in source_facts[:20])
        if isinstance(metadata_facts, list):
            chunks.extend(str(item or "") for item in metadata_facts[:20])
        text = self._market_clean_product_source_text(product.source.get("text")) if isinstance(product.source, dict) else ""
        for label in (
            "품명 및 모델명",
            "KC 인증정보",
            "크기, 중량",
            "색상",
            "재질",
            "사용연령",
            "제조자",
            "제조국",
            "원산지",
        ):
            value = self._market_source_field(product, (label,))
            if value:
                chunks.append(f"{label} {value}")
        if text:
            product_title = re.sub(r"\|.*$", "", product.product_name).strip()
            if product_title:
                start = text.find(product_title)
                if start >= 0:
                    chunks.append(text[start : start + 2500])
        return "\n".join(str(chunk) for chunk in chunks if str(chunk or "").strip())

    def _infer_market_category_text(self, product: MarketProduct) -> str:
        candidates = [
            str(product.metadata.get("category") or ""),
            str(product.source.get("category") or ""),
            str(product.metadata.get("category_text") or ""),
        ]
        for payload in product.metadata.get("source_payloads", []):
            if isinstance(payload, dict):
                candidates.extend([str(payload.get("category") or ""), str(payload.get("breadcrumb") or "")])
        for payload in product.source.get("source_payloads", []):
            if isinstance(payload, dict):
                candidates.extend([str(payload.get("category") or ""), str(payload.get("breadcrumb") or "")])
        blob = self._market_primary_text_blob(product)
        for line in blob.splitlines():
            if "▷" in line or ">" in line:
                cleaned = self._clean_detail_copy_text(line)
                if 3 <= len(cleaned) <= 120:
                    candidates.append(cleaned)
        cleaned_candidates: list[str] = []
        for value in candidates:
            cleaned = self._clean_market_field_text(value)
            if not cleaned:
                continue
            cleaned = cleaned.replace("▷", ">")
            cleaned = re.sub(r"\s*>\s*", " > ", cleaned).strip(" >")
            if cleaned:
                cleaned_candidates.append(cleaned)
        cleaned_candidates = self._dedupe_text_items(cleaned_candidates)
        guessed = self._guess_market_category_text(product)
        if guessed == "스포츠/레저 > 스포츠잡화" and self._is_safety_reflection_product(product):
            return guessed
        if guessed:
            if cleaned_candidates and self._market_category_is_generic(cleaned_candidates[0]):
                return guessed
            if not cleaned_candidates:
                return guessed
        if cleaned_candidates:
            return cleaned_candidates[0]
        if guessed:
            return guessed
        return "생활/주방 > 생활용품"

    def _market_category_is_generic(self, category: str | object) -> bool:
        text = self._normalize_text_key(str(category or ""))
        generic = {
            self._normalize_text_key("생활/주방 > 생활용품"),
            self._normalize_text_key("생활/주방 생활용품"),
            self._normalize_text_key("생활용품"),
            self._normalize_text_key("기타"),
        }
        return text in generic or text.endswith(self._normalize_text_key("> 생활용품"))

    def _is_safety_reflection_product(self, product: MarketProduct) -> bool:
        blob = f"{product.product_name} {self._market_primary_text_blob(product)}".lower()
        return any(
            keyword in blob
            for keyword in (
                "반사",
                "형광",
                "야광",
                "빛반사",
                "안전밴드",
                "안전조끼",
                "반사조끼",
                "발목각반",
                "반사 각반",
                "각반",
                "암밴드",
                "발목밴드",
                "안전용품",
                "프레임보호",
            )
        )

    def _guess_market_category_text(self, product: MarketProduct) -> str:
        source = product.source if isinstance(product.source, dict) else {}
        metadata = product.metadata if isinstance(product.metadata, dict) else {}
        source_facts = source.get("facts", []) if isinstance(source.get("facts", []), list) else []
        metadata_facts = metadata.get("facts", []) if isinstance(metadata.get("facts", []), list) else []
        blob = " ".join(
            str(item or "")
            for item in (
                product.product_name,
                source.get("title"),
                source.get("product_name"),
                source.get("category"),
                source.get("options_text"),
                metadata.get("product_name"),
                metadata.get("category"),
                metadata.get("options_text"),
                " ".join(str(item or "") for item in source_facts[:20]),
                " ".join(str(item or "") for item in metadata_facts[:20]),
            )
        ).lower()
        rules = [
            (("유아식탁의자", "아기 식탁의자", "아기식탁의자", "하이체어", "유아용 식탁의자", "유아이유식의자"), "유아동 > 유아가구 > 유아식탁의자"),
            (("유아의자", "아기의자", "어린이의자", "키즈의자"), "유아동 > 유아가구 > 유아의자"),
            (("고양이", "목줄", "리드줄", "초크체인"), "생활/건강 > 반려동물 > 고양이용품"),
            (("캠핑고리", "감성캠핑 스트랩", "캠핑 스트랩", "캠핑 후크", "다용도 고리", "카라비너"), "스포츠/레저 > 캠핑 > 캠핑소품"),
            (("led 경량 스포츠 팔찌", "발광 팔찌", "스포츠 팔찌", "암밴드", "러닝 밴드"), "스포츠/레저 > 스포츠잡화"),
            (("반사밴드", "반사 밴드", "반사조끼", "형광조끼", "야광조끼", "안전엑스밴드", "발목각반", "안전발목밴드", "프레임보호 스티커", "반사 각반", "각반"), "스포츠/레저 > 스포츠잡화"),
            (("야간 안전", "빛반사", "반사판", "안전 스트랩", "형광 팔찌", "야광 안전"), "스포츠/레저 > 스포츠잡화"),
            (("책상", "서재", "책장", "선반", "수납", "테이블"), "가구/인테리어 > 수납가구"),
            (("의자", "스툴", "체어"), "가구/인테리어 > 의자"),
            (("침구", "이불", "베개", "매트리스"), "가구/인테리어 > 침구"),
            (("주방", "냄비", "팬", "식기", "컵", "조리"), "생활/주방 > 주방용품"),
            (("욕실", "샤워", "수건", "화장실"), "생활/주방 > 욕실용품"),
            (("조명", "무드등", "램프", "전구"), "가구/인테리어 > 조명"),
            (("거울", "행거", "옷걸이", "의류수납"), "가구/인테리어 > 인테리어소품"),
        ]
        for keywords, category in rules:
            if any(keyword in blob for keyword in keywords):
                return category
        return ""

    def _market_source_field(self, product: MarketProduct, labels: tuple[str, ...]) -> str:
        text = str(product.source.get("text") or "") if isinstance(product.source, dict) else ""
        if not text:
            return ""
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:：\t ]+\s*(.+?)(?=\n[가-힣A-Za-z0-9 /·()]+(?:\t|[:：])|\r?\n|$)"
            match = re.search(pattern, text)
            if match:
                cleaned = self._clean_market_field_text(match.group(1))
                if cleaned:
                    return cleaned
        return ""

    def _clean_market_field_text(self, value: str | object) -> str:
        text = self._clean_detail_copy_text(str(value or ""))
        text = re.sub(r"\s+", " ", text).strip(" -_/|·")
        noisy = {
            "상세페이지 참조",
            "상세설명참조",
            "상품 상세정보에 별도",
            "상세정보 별도표기",
            "별도표기",
            "판매자 연락처 참고",
            "확인 필요",
            "-",
            ".",
            "없음",
            "기타",
            "브랜드 없음",
            "none",
            "null",
        }
        return "" if text.lower() in noisy else text

    def _normalize_market_manufacturer(self, value: str | object) -> str:
        text = self._clean_market_field_text(value)
        compact = re.sub(r"[^0-9A-Za-z가-힣]", "", text).lower()
        blocked = {
            "",
            re.sub(r"[^0-9A-Za-z가-힣]", "", DEFAULT_MARKET_BRAND).lower(),
            re.sub(r"[^0-9A-Za-z가-힣]", "", LEGACY_MARKET_MANUFACTURER).lower(),
            "상세설명참조",
            "상세페이지참조",
            "상품상세정보에별도",
            "상세정보별도표기",
            "별도표기",
            "판매자연락처참고",
            "판매자확인",
        }
        if compact in blocked:
            return ""
        if any(noise in compact for noise in ("협력사", "사입", "이거찜")):
            return ""
        return text

    def _normalize_market_origin(self, value: str | object) -> str:
        text = self._clean_market_field_text(value)
        if not text:
            return ""
        if any(token in text for token in ("상세정보", "관련 연락처", "판매자 연락처", "마무리하세요", "별도표기")):
            return ""
        if "국산" in text:
            return "대한민국"
        if text in {"수입산", "해외", "아시아", "해외직구", "수입"}:
            return ""
        countries = (
            "중국",
            "대한민국",
            "한국",
            "베트남",
            "일본",
            "미국",
            "대만",
            "태국",
            "인도",
            "인도네시아",
            "말레이시아",
            "필리핀",
            "캄보디아",
            "방글라데시",
            "파키스탄",
            "터키",
            "이탈리아",
            "프랑스",
            "독일",
            "스페인",
        )
        for country in countries:
            if country in text:
                return "대한민국" if country == "한국" else country
        parts = [part.strip() for part in re.split(r"[|>/,]", text) if part.strip()]
        if len(parts) == 1 and 2 <= len(parts[0]) <= 20:
            return parts[0]
        return ""

    def _plain_text_excerpt(self, value: str | object, limit: int = 1000) -> str:
        text = self._clean_detail_copy_text(str(value or ""))
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"[#*_>`|]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[: max(0, limit)]

    def _market_effective_value(
        self,
        product: MarketProduct,
        settings: dict[str, str],
        key: str,
        fallback: str,
    ) -> str:
        setting_value = self._clean_market_field_text(settings.get(key, ""))
        if key == "origin":
            setting_value = self._normalize_market_origin(setting_value)
        if key == "manufacturer":
            setting_value = self._normalize_market_manufacturer(setting_value)
        if setting_value:
            return setting_value
        blob = self._market_text_blob(product)
        patterns = {
            "origin": [
                r"원산지\s*[:：]?\s*([가-힣A-Za-z0-9 /·_-]{2,40}?)(?=\s*(?:제조사|수입사|브랜드|모델명|[\"',}\]]|$))",
                r"제조국\s*[:：]?\s*([가-힣A-Za-z0-9 /·_-]{2,40}?)(?=\s*(?:제조사|수입사|브랜드|모델명|[\"',}\]]|$))",
            ],
            "manufacturer": [
                r"제조사\s*[:：]?\s*([가-힣A-Za-z0-9 /·_-]{2,40}?)(?=\s*(?:원산지|제조국|수입사|브랜드|모델명|[\"',}\]]|$))",
                r"수입사\s*[:：]?\s*([가-힣A-Za-z0-9 /·_-]{2,40}?)(?=\s*(?:원산지|제조국|제조사|브랜드|모델명|[\"',}\]]|$))",
            ],
            "brand": [r"브랜드\s*[:：]?\s*([가-힣A-Za-z0-9 /·_-]{2,40}?)(?=\s*(?:원산지|제조국|제조사|수입사|모델명|[\"',}\]]|$))"],
        }
        for pattern in patterns.get(key, []):
            cleaned = ""
            match = re.search(pattern, blob)
            if match:
                cleaned = self._clean_market_field_text(match.group(1))
                if key == "manufacturer":
                    cleaned = self._normalize_market_manufacturer(cleaned)
            if cleaned:
                return cleaned
        return fallback

    def _market_source_origin(self, product: MarketProduct) -> str:
        for labels in (("원산지",), ("제조국", "제조국 또는 원산지")):
            origin = self._normalize_market_origin(self._market_source_field(product, labels))
            if origin:
                return origin
        return ""

    def _effective_category_code(
        self,
        product: MarketProduct,
        platform: str,
        settings: dict[str, str],
    ) -> str:
        key = "naver_category_id" if platform == "naver" else "coupang_category_id"
        ui_configured = self._clean_market_field_text(self._market_field_text(key))
        product_resolved = self._clean_market_field_text(settings.get(self._product_category_setting_key(product, key), ""))
        configured = ui_configured or product_resolved or self._clean_market_field_text(settings.get(key, ""))
        if key in {"naver_category_id", "coupang_category_id"} and not ui_configured:
            configured = product_resolved
        if configured:
            if platform == "coupang" and not self._looks_like_coupang_display_category_code(configured):
                return f"{AUTO_LOOKUP_PREFIX}{platform}_category:{self._infer_market_category_text(product)}"
            return configured
        category_text = self._infer_market_category_text(product)
        return f"{AUTO_LOOKUP_PREFIX}{platform}_category:{category_text}"

    def _product_category_setting_key(self, product: MarketProduct, key: str) -> str:
        product_code = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(product.code or "").strip()) or "product"
        return f"{product_code}:{key}"

    def _effective_location_code(
        self,
        settings: dict[str, str],
        platform: str,
        kind: str,
    ) -> str:
        primary_key = "outbound_place_code" if kind == "outbound" else "return_center_code"
        specific_key = f"{platform}_outbound_place_code" if kind == "outbound" else f"{platform}_return_center_code"
        configured = self._clean_market_field_text(settings.get(specific_key, ""))
        if not configured and platform != "coupang":
            configured = self._clean_market_field_text(settings.get(primary_key, ""))
        if configured:
            return configured
        return f"{AUTO_LOOKUP_PREFIX}{platform}_{kind}_code"

    def _invalid_coupang_location_code(self, kind: str, code: str | object) -> bool:
        text = self._clean_market_field_text(code)
        if not text or self._is_auto_lookup_value(text):
            return True
        if not re.fullmatch(r"\d+", text):
            return True
        number = int(text)
        # Coupang API should not receive HTTP status codes or Naver address ids here.
        if number in {200, 201, 400, 401, 403, 404, 500}:
            return True
        if kind == "return" and number < 1_000_000:
            return True
        if kind == "outbound" and number < 10_000:
            return True
        return False

    def _build_market_copy(self, product: MarketProduct) -> dict[str, object]:
        metadata = product.metadata
        sections = metadata.get("sections", [])
        category = self._infer_market_category_text(product)
        headlines: list[str] = []
        if isinstance(sections, list):
            for section in sections:
                if not isinstance(section, dict):
                    continue
                for key in ("headline", "subheadline", "body"):
                    value = str(section.get(key) or "").strip()
                    if value:
                        headlines.append(self._clean_detail_copy_text(value))
        facts = [str(value).strip() for value in metadata.get("facts", []) if str(value).strip()] if isinstance(metadata.get("facts", []), list) else []
        summary_items = self._dedupe_text_items(headlines + facts)
        seo_title = self._strip_external_brand_terms(
            self._market_seo_title(product.product_name, category),
            product,
            DEFAULT_MARKET_BRAND,
        )
        keywords = self._filter_external_brand_items(self._market_keywords(product, category, summary_items), product, DEFAULT_MARKET_BRAND)
        related_keywords = self._filter_external_brand_items(
            self._market_related_keywords(product, category, summary_items),
            product,
            DEFAULT_MARKET_BRAND,
        )
        naver_keywords = self._platform_market_keywords(product, category, keywords, related_keywords, "naver")
        coupang_keywords = self._platform_market_keywords(product, category, keywords, related_keywords, "coupang")
        naver_seo_title = self._platform_market_seo_title(product, category, seo_title, naver_keywords, "naver")
        coupang_seo_title = self._platform_market_seo_title(product, category, seo_title, coupang_keywords, "coupang")
        category_candidates = self._market_category_candidates(product, category, related_keywords)
        search_tags = self._market_search_tag_candidates(
            {
                "seo_title": seo_title,
                "category_text": category,
                "keywords": keywords,
                "related_keywords": related_keywords,
            },
            product,
            DEFAULT_MARKET_BRAND,
            limit=20,
        )
        naver_search_tags = self._market_search_tag_candidates(
            {
                "seo_title": naver_seo_title,
                "category_text": category,
                "keywords": naver_keywords,
                "related_keywords": related_keywords,
            },
            product,
            DEFAULT_MARKET_BRAND,
            include_brand=False,
            limit=7,
        )
        coupang_search_tags = self._market_search_tag_candidates(
            {
                "seo_title": coupang_seo_title,
                "category_text": category,
                "keywords": coupang_keywords,
                "related_keywords": related_keywords,
            },
            product,
            DEFAULT_MARKET_BRAND,
            include_brand=True,
            limit=20,
        )
        seo_summary = self._market_seo_summary(product, category, summary_items, related_keywords)
        naver_summary = self._market_seo_summary(product, category, summary_items, naver_keywords)
        option_plan = self._market_option_plan(product)
        return {
            "seo_title": seo_title,
            "naver_seo_title": naver_seo_title,
            "coupang_seo_title": coupang_seo_title,
            "keywords": keywords,
            "naver_keywords": naver_keywords,
            "coupang_keywords": coupang_keywords,
            "related_keywords": related_keywords,
            "search_tags": search_tags,
            "naver_search_tags": naver_search_tags,
            "coupang_search_tags": coupang_search_tags,
            "category_candidates": category_candidates,
            "options": option_plan["options"],
            "option_groups": option_plan["option_groups"],
            "category_text": category,
            "summary": seo_summary,
            "naver_summary": naver_summary,
            "notice": summary_items[:8],
            "as_message": self._market_field_text("as_message") or "상품 수령 후 판매자 문의",
            "chatgpt_seo_prompt": self._build_market_seo_fallback_prompt(product, category, summary_items),
            "naver_chatgpt_seo_prompt": self._build_platform_market_seo_fallback_prompt(product, category, summary_items, "naver"),
            "coupang_chatgpt_seo_prompt": self._build_platform_market_seo_fallback_prompt(product, category, summary_items, "coupang"),
        }

    def _platform_market_keywords(
        self,
        product: MarketProduct,
        category: str,
        keywords: list[str],
        related_keywords: list[str],
        platform: str,
    ) -> list[str]:
        seeds = [
            *related_keywords,
            *keywords,
            *self._market_keyword_expansions(product, category),
            *self._product_core_terms(product),
        ]
        if platform == "naver":
            seeds.extend(re.split(r"\s+|>|/|,", category or ""))
            limit = 30
        else:
            seeds.insert(0, DEFAULT_MARKET_BRAND)
            seeds.extend(re.findall(r"[가-힣A-Za-z0-9]{2,20}", product.product_name or ""))
            limit = 40
        cleaned = [
            self._normalize_market_keyword(seed)
            for seed in seeds
            if self._normalize_market_keyword(seed)
        ]
        return self._filter_external_brand_items(self._dedupe_text_items(cleaned), product, DEFAULT_MARKET_BRAND)[:limit]

    def _platform_market_seo_title(
        self,
        product: MarketProduct,
        category: str,
        base_title: str,
        platform_keywords: list[str],
        platform: str,
    ) -> str:
        title = self._clean_detail_copy_text(base_title or product.product_name)
        title = self._strip_external_brand_terms(title, product, DEFAULT_MARKET_BRAND)
        title = self._clean_market_title_text(title)
        title = re.sub(r"\s+", " ", title).strip(" -_/|·")
        category_tail = category.split(">")[-1].split("/")[-1].strip() if category else ""
        title_keyword_pool = [
            *self._product_core_terms(product),
        ]
        extras = []
        if category_tail and category_tail not in title and self._market_title_extra_allowed(category_tail):
            extras.append(category_tail)
        extras.extend(
            keyword
            for keyword in title_keyword_pool
            if keyword and keyword not in title and self._market_title_extra_allowed(keyword)
        )
        if platform == "naver":
            limit = 92
            extras = extras[:4]
        else:
            limit = COUPANG_PRODUCT_NAME_LIMIT - len(DEFAULT_MARKET_BRAND) - 1
            extras = extras[:6]
        combined = " ".join(self._dedupe_text_items([title, *extras])).strip()
        return self._clip_text(combined or title or product.product_name, max(20, limit))

    def _clean_market_title_text(self, value: str | object) -> str:
        text = str(value or "")
        for noise in ("온채널", "마무리하세요", "생활용품", "상품군", "기타"):
            text = text.replace(noise, " ")
        text = re.sub(r"\bdetail\s*php\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\b[0-9a-f]{6,}\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\b[A-Za-z]*\d+[A-Za-z0-9]*\b", " ", text)
        text = re.sub(r"[가-힣A-Za-z0-9]+(?:하세요|두세요|됩니다|입니다|합니다|납니다|보세요|주세요)\b", " ", text)
        return re.sub(r"\s+", " ", text).strip(" -_/|·")

    def _market_title_extra_allowed(self, value: str | object) -> bool:
        text = self._normalize_market_keyword(value)
        if not text:
            return False
        lowered = text.lower()
        if text in {DEFAULT_MARKET_BRAND, "생활용품", "주방", "가구", "인테리어", "기타", "상품군", "제품", "용품"}:
            return False
        if any(noise in lowered for noise in ("detailphp", "온채널", "마무리하세요")):
            return False
        return True

    def _market_seo_title(self, product_name: str, category: str) -> str:
        base = re.sub(r"[|].*$", "", product_name)
        for noise in ("돈버는 쇼핑 도매꾹", "도매꾹", "돈버는 쇼핑", "꾹AI", "온채널"):
            base = base.replace(noise, " ")
        for noise in ("최저가", "무료배송"):
            base = base.replace(noise, " ")
        base = re.sub(r"https?://\S+", " ", base)
        base = re.sub(r"\s+", " ", base).strip(" -_/|")
        if category:
            tail = category.split(">")[-1].split("/")[-1].strip()
            if tail and tail not in base:
                base = f"{base} {tail}"
        return base[:100]

    def _market_keywords(self, product: MarketProduct, category: str, items: list[str]) -> list[str]:
        raw = [product.product_name, category, *items[:8], *self._product_core_terms(product)]
        tokens: list[str] = []
        for text in raw:
            for part in re.split(r"[\s,/|>·()_\-\[\]]+", str(text)):
                part = self._normalize_market_keyword(part)
                if part:
                    tokens.append(part)
        tokens.extend(self._market_keyword_expansions(product, category))
        return self._dedupe_text_items(tokens)[:30]

    def _product_core_terms(self, product: MarketProduct) -> list[str]:
        blob = self._market_primary_text_blob(product)
        terms: list[str] = []
        for pattern in [
            r"([가-힣A-Za-z0-9]+(?:식탁의자|유아의자|아기의자|하이체어|공부의자))",
            r"([가-힣A-Za-z0-9]+(?:선반|책상|책장|수납장|행거|거울|조명|테이블|의자|스툴|서랍장|트롤리))",
            r"([0-9]+단\s*[가-힣A-Za-z0-9]+)",
            r"([가-힣A-Za-z]+형\s*[가-힣A-Za-z0-9]+)",
        ]:
            terms.extend(match.group(1).strip() for match in re.finditer(pattern, blob))
        return self._dedupe_text_items(terms)

    def _normalize_market_keyword(self, value: str | object) -> str:
        text = self._clean_detail_copy_text(str(value or ""))
        text = re.sub(r"[^0-9A-Za-z가-힣+]+", "", text)
        if not 2 <= len(text) <= 20:
            return ""
        if re.fullmatch(r"\d+", text):
            return ""
        if text in {"최저가", "무료배송"}:
            return ""
        if re.search(r"(하세요|두세요|됩니다|입니다|합니다|납니다|보세요|주세요)$", text):
            return ""
        blocked = {
            "상품", "상세", "페이지", "이미지", "옵션", "확인", "구매", "판매자", "무료", "배송",
            "돈버는", "도매꾹", "쇼핑", "꾹AI", "상품번호", "브랜드", "전체", "목록",
            "온채널", "마무리하세요", "참고", "detailphp",
        }
        lowered = text.lower()
        if text in blocked or any(noise in lowered for noise in ("detailphp", "마무리하세요", "온채널")):
            return ""
        if re.fullmatch(r"[0-9a-f]{6,}", lowered) or re.fullmatch(r"[a-z]*\d+[a-z0-9]*", lowered):
            return ""
        return text

    def _market_keyword_expansions(self, product: MarketProduct, category: str) -> list[str]:
        blob = f"{product.product_name} {category} {self._market_primary_text_blob(product)}".lower()
        expansions: list[str] = []
        keyword_sets = [
            (("캠핑고리", "감성캠핑", "캠핑 후크", "캠핑 스트랩", "카라비너"), [
                "캠핑고리", "캠핑후크", "캠핑스트랩", "캠핑용품", "카라비너",
                "감성캠핑", "텐트고리", "다용도고리", "아웃도어소품",
            ]),
            (("반사", "형광", "야광", "안전", "암밴드", "각반", "발목밴드", "반사조끼", "안전조끼", "빛반사"), [
                "반사밴드", "야간안전", "안전밴드", "형광밴드", "반사스트랩", "야간운동",
                "러닝밴드", "자전거안전", "작업안전", "발목밴드", "암밴드", "안전조끼",
            ]),
            (("유아식탁의자", "아기식탁의자", "아기 식탁의자", "하이체어", "유아용 식탁의자"), [
                "유아식탁의자", "아기식탁의자", "하이체어", "아기의자", "유아의자",
                "원목식탁의자", "접이식식탁의자", "이유식의자", "어린이의자", "베이비체어",
            ]),
            (("선반", "폴딩", "접이", "수납", "랙", "트롤리"), [
                "접이식선반", "폴딩선반", "수납선반", "이동식선반", "다용도선반", "주방선반",
                "베란다선반", "틈새수납", "공간활용", "철제선반", "정리선반", "바퀴선반",
            ]),
            (("책상", "책장", "서재", "원목", "h형", "h형"), [
                "원목책상", "H형책상", "책상책장", "서재책상", "수납책상", "공부책상",
                "홈오피스책상", "학생책상", "책장일체형책상", "공간활용책상",
            ]),
            (("거울", "전신거울", "행거"), [
                "전신거울", "인테리어거울", "스탠드거울", "드레스룸", "현관거울", "공간연출",
            ]),
            (("조명", "램프", "무드등", "캔들"), [
                "무드등", "인테리어조명", "감성조명", "침실조명", "테이블조명", "집들이선물",
            ]),
            (("주방", "냄비", "팬", "식기", "조리"), [
                "주방용품", "살림템", "신혼집", "정리용품", "실용아이템", "집들이선물",
            ]),
        ]
        for triggers, values in keyword_sets:
            if any(trigger in blob for trigger in triggers):
                expansions.extend(values)
        if not expansions:
            expansions.extend(["생활용품", "인테리어소품", "공간활용", "실용템", "집들이선물"])
        return self._dedupe_text_items(expansions)

    def _market_related_keywords(self, product: MarketProduct, category: str, items: list[str]) -> list[str]:
        raw = [*self._market_keywords(product, category, items), *self._market_keyword_expansions(product, category)]
        title_terms = self._product_core_terms(product)
        raw.extend(title_terms)
        return self._dedupe_text_items(raw)[:35]

    def _market_category_candidates(
        self,
        product: MarketProduct,
        category: str,
        related_keywords: list[str],
    ) -> list[dict[str, str]]:
        blob = f"{product.product_name} {category}".lower()
        candidates: list[dict[str, str]] = []
        rules = [
            (("캠핑고리", "감성캠핑", "캠핑 후크", "캠핑 스트랩", "다용도 고리", "카라비너"), ("스포츠/레저 > 캠핑 > 캠핑소품", "스포츠/레저 > 캠핑용품")),
            (("반사", "형광", "야광", "안전", "암밴드", "각반", "발목밴드", "반사조끼", "안전조끼", "빛반사"), ("스포츠/레저 > 스포츠잡화", "스포츠/레저 > 스포츠잡화")),
            (("유아식탁의자", "아기식탁의자", "하이체어", "유아용 식탁의자"), ("유아동 > 유아가구 > 유아식탁의자", "출산/유아동 > 유아동가구 > 유아식탁의자")),
            (("고양이", "목줄", "리드줄", "초크체인"), ("생활/건강 > 반려동물 > 고양이용품", "반려/애완용품 > 고양이용품")),
            (("발광 팔찌", "스포츠 팔찌", "암밴드", "러닝 밴드", "두건/밴드"), ("스포츠/레저 > 스포츠잡화", "스포츠/레저 > 스포츠잡화")),
            (("선반", "수납", "랙"), ("가구/인테리어 > 수납가구 > 선반", "가구 > 수납가구 > 선반/랙")),
            (("책상", "서재", "공부"), ("가구/인테리어 > 서재/사무용가구 > 책상", "가구 > 책상")),
            (("거울",), ("가구/인테리어 > 인테리어소품 > 거울", "가구 > 거울")),
            (("조명", "램프"), ("가구/인테리어 > 조명 > 스탠드", "홈데코 > 조명")),
            (("주방", "식기"), ("생활/주방 > 주방용품", "주방용품")),
        ]
        for triggers, (naver_text, coupang_text) in rules:
            if any(trigger in blob for trigger in triggers):
                candidates.append({"platform": "naver", "category_text": naver_text, "source": "local_keyword_rule"})
                candidates.append({"platform": "coupang", "category_text": coupang_text, "source": "local_keyword_rule"})
        if not candidates:
            candidates.append({"platform": "naver", "category_text": category or "생활/주방 > 생활용품", "source": "fallback"})
            candidates.append({"platform": "coupang", "category_text": category or "생활용품", "source": "fallback"})
        return candidates

    def _market_seo_summary(
        self,
        product: MarketProduct,
        category: str,
        items: list[str],
        related_keywords: list[str],
    ) -> str:
        core = ", ".join(related_keywords[:5])
        base = " ".join(items[:2]).strip()
        product_name = self._strip_external_brand_terms(product.product_name, product, DEFAULT_MARKET_BRAND)
        product_name = re.sub(r"\|.*$", "", product_name).strip()
        if base:
            return f"{product_name}은(는) {category} 상품으로, {core} 중심 검색어에 맞춰 구성했습니다. {base}"
        return f"{product_name}은(는) {category} 상품으로, {core} 중심의 쇼핑 검색 노출을 고려해 구성했습니다."

    def _market_option_plan(self, product: MarketProduct) -> dict[str, object]:
        settings = self._market_settings_data(include_secrets=False)
        manual = str(settings.get("market_options_text") or "").strip()
        groups = []
        option_rows: list[dict[str, object]] = []
        if manual and not self._is_auto_lookup_value(manual):
            groups = self._parse_market_option_groups(manual)
            if self._option_groups_are_noise(groups):
                groups = []
        if not groups:
            option_rows = self._market_source_option_rows(product)
            if option_rows:
                groups = self._option_rows_to_option_groups(option_rows)
            else:
                groups = self._market_source_option_groups(product)
        if self._option_groups_are_noise(groups):
            groups = []
        if not groups:
            groups = self._infer_market_option_groups(product)
        if not groups:
            groups = [{"name": "옵션", "values": ["기본"]}]
        groups = self._normalize_option_groups(groups)[:3]
        if not groups:
            groups = [self._fallback_market_option_group(product)]
        combinations = self._build_option_combinations(groups)
        stock = self._positive_int(settings.get("option_stock_quantity", "")) or self._positive_int(settings.get("stock_quantity", "")) or 100
        price_delta_map = self._parse_option_price_delta(settings.get("option_price_delta", ""))
        group_names = [str(group.get("name") or "") for group in groups if isinstance(group, dict)]
        option_row_by_value_key = {
            self._normalize_text_key(str(row.get("value") or "")): row
            for row in option_rows
            if isinstance(row, dict) and str(row.get("value") or "").strip()
        }
        option_row_by_combo_key: dict[str, dict[str, object]] = {}
        for row in option_rows:
            if not isinstance(row, dict):
                continue
            row_values = row.get("option_values")
            if not isinstance(row_values, dict):
                continue
            cleaned_values: dict[str, str] = {}
            for raw_name, raw_value in row_values.items():
                name = self._normalize_option_group_name(str(raw_name or "옵션"))
                value = self._clean_option_text(raw_value)
                if name and value:
                    cleaned_values[name] = value
            combo_values = tuple(cleaned_values.get(name, "") for name in group_names)
            if combo_values and all(combo_values):
                option_row_by_combo_key[self._normalize_text_key("|".join(combo_values))] = row
        options = []
        for index, values in enumerate(combinations, start=1):
            label = " / ".join(f"{group['name']}:{value}" for group, value in zip(groups, values))
            combo_key = self._normalize_text_key("|".join(values))
            row_match = option_row_by_combo_key.get(combo_key) or next(
                (
                    option_row_by_value_key.get(self._normalize_text_key(value))
                    for value in values
                    if option_row_by_value_key.get(self._normalize_text_key(value))
                ),
                {},
            )
            option_delta = sum(price_delta_map.get(value, 0) for value in values)
            if isinstance(row_match, dict) and not self._positive_int(row_match.get("source_price", "")):
                option_delta += self._positive_int(row_match.get("price_delta", ""))
            option_stock = self._positive_int(row_match.get("stock_quantity", "")) or stock
            option_values = {
                str(group["name"]): value
                for group, value in zip(groups, values)
            }
            option_payload = {
                "index": index,
                "label": label or "기본",
                "option_values": option_values,
                "stock_quantity": option_stock,
                "price_delta": option_delta,
                "seller_sku": f"{slugify(product.code).upper()}-{index:03d}",
            }
            source_price = self._positive_int(row_match.get("source_price", "")) if isinstance(row_match, dict) else 0
            if source_price:
                option_payload["source_price"] = source_price
                option_payload["source_option_code"] = str(row_match.get("code") or "")
            options.append(option_payload)
        return {
            "option_groups": groups,
            "options": options or [
                {
                    "index": 1,
                    "label": "기본",
                    "option_values": {"옵션": "기본"},
                    "stock_quantity": stock,
                    "price_delta": 0,
                    "seller_sku": f"{slugify(product.code).upper()}-001",
                }
            ],
        }

    def _fallback_market_option_group(self, product: MarketProduct) -> dict[str, object]:
        if self._is_safety_reflection_product(product):
            return {"name": "옵션", "values": ["기본"]}
        option_blob = self._market_source_options_text(product)
        if re.search(r"색상|컬러", option_blob):
            return {"name": "옵션", "values": ["기본"]}
        if re.search(r"사이즈|규격|크기", option_blob):
            return {"name": "옵션", "values": ["기본"]}
        return {"name": "옵션", "values": ["단일상품"]}

    def _market_source_option_rows(self, product: MarketProduct) -> list[dict[str, object]]:
        stored_rows: list[dict[str, object]] = []
        for candidate in (
            product.metadata.get("option_rows") if isinstance(product.metadata, dict) else None,
            product.source.get("option_rows") if isinstance(product.source, dict) else None,
        ):
            if isinstance(candidate, list):
                stored_rows.extend(row for row in candidate if isinstance(row, dict))
        for payload in [*product.metadata.get("source_payloads", []), *product.source.get("source_payloads", [])]:
            if isinstance(payload, dict) and isinstance(payload.get("option_rows"), list):
                stored_rows.extend(row for row in payload.get("option_rows", []) if isinstance(row, dict))
        popup_text = str(product.source.get("option_popup_text") or product.metadata.get("option_popup_text") or "")
        rows = self._parse_domeggook_option_rows(popup_text) if popup_text else []
        if not rows:
            rows = stored_rows
        if not rows:
            url = str(product.source.get("url") or product.metadata.get("url") or "")
            popup_text = self._fetch_domeggook_option_popup_text(url)
            rows = self._parse_domeggook_option_rows(popup_text)
        cleaned: list[dict[str, object]] = []
        seen: set[str] = set()
        for row in rows:
            group_name = self._normalize_option_group_name(str(row.get("group_name") or "옵션"))
            raw_option_values = row.get("option_values")
            option_values: dict[str, str] = {}
            if isinstance(raw_option_values, dict):
                for raw_name, raw_value in raw_option_values.items():
                    name = self._normalize_option_group_name(str(raw_name or "옵션"))
                    value = self._clean_option_text(raw_value)
                    if name and value and self._normalize_text_key(value) not in {self._normalize_text_key(name), self._normalize_text_key("옵션")}:
                        option_values[name] = value
            value = self._clean_option_text(row.get("value"))
            if option_values:
                value = " / ".join(f"{name}:{option_values[name]}" for name in option_values)
            if not value:
                continue
            if self._normalize_text_key(value) in {self._normalize_text_key(group_name), self._normalize_text_key("옵션")}:
                continue
            key = self._normalize_text_key(f"{group_name}:{value}:{row.get('code') or ''}")
            if key in seen:
                continue
            seen.add(key)
            cleaned_row = {
                "code": str(row.get("code") or ""),
                "group_name": group_name,
                "value": value,
                "source_price": self._positive_int(row.get("source_price", "")),
                "price_delta": self._positive_int(row.get("price_delta", "")),
                "stock_quantity": self._positive_int(row.get("stock_quantity", "")),
                "source": str(row.get("source") or ""),
            }
            if option_values:
                cleaned_row["option_values"] = option_values
            cleaned.append(cleaned_row)
        return cleaned[:300]

    def _option_rows_to_option_groups(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        if not rows:
            return []
        grouped: dict[str, list[str]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            option_values = row.get("option_values")
            if not isinstance(option_values, dict):
                continue
            for raw_name, raw_value in option_values.items():
                name = self._normalize_option_group_name(str(raw_name or "옵션"))
                value = self._clean_option_text(raw_value)
                if not name or not value:
                    continue
                grouped.setdefault(name, []).append(value)
        if grouped:
            groups: list[dict[str, object]] = []
            for name, values in grouped.items():
                deduped = self._dedupe_text_items(values)
                if deduped:
                    groups.append({"name": name, "values": deduped[:30]})
            if groups:
                return groups[:3]
        group_name = self._normalize_option_group_name(str(rows[0].get("group_name") or "옵션"))
        values = self._dedupe_text_items(
            [
                self._clean_option_text(row.get("value"))
                for row in rows
                if isinstance(row, dict) and str(row.get("value") or "").strip()
            ]
        )
        return [{"name": group_name, "values": values[:30]}] if values else []

    def _market_source_option_groups(self, product: MarketProduct) -> list[dict[str, object]]:
        for candidate in self._market_source_option_candidates(product):
            groups = self._parse_market_option_groups(candidate)
            if groups and not self._option_groups_are_noise(groups):
                return groups
        return self._infer_market_option_groups(product)

    def _option_groups_are_noise(self, groups: list[dict[str, object]]) -> bool:
        normalized = self._normalize_option_groups(groups)
        if not normalized:
            return True
        noise_words = (
            "랭킹",
            "점수",
            "추천",
            "상품번호",
            "도움말",
            "검색필터",
            "도매꾹",
            "돈버는",
            "http",
            "url",
        )
        meaningful = 0
        for group in normalized:
            name = str(group.get("name") or "")
            values = [str(value or "") for value in group.get("values", []) if str(value or "").strip()]
            if any(word.lower() in name.lower() for word in noise_words):
                return True
            for value in values:
                lower = value.lower()
                if any(word.lower() in lower for word in noise_words):
                    return True
                if value not in {"기본", "선택", name} and not re.fullmatch(r"\d+", value):
                    meaningful += 1
        return meaningful == 0

    def _infer_market_option_groups(self, product: MarketProduct) -> list[dict[str, object]]:
        blob = self._market_primary_text_blob(product)
        compact = re.sub(r"\s+", "", blob)
        lower_name = str(product.product_name or "").lower()
        groups: list[dict[str, object]] = []
        if self._is_baby_chair_product(product):
            color = self._market_source_field(product, ("색상", "컬러")) or "원목색"
            return [{"name": "색상", "values": [color]}]
        if self._is_safety_reflection_product(product):
            return [{"name": "옵션", "values": ["기본"]}]
        shelf_like = self._is_storage_shelf_product(product)
        if shelf_like or any(keyword in lower_name for keyword in ("trolley", "rack", "shelf")):
            groups.append({"name": "단수", "values": ["2단", "3단"]})
            groups.append({"name": "폭", "values": ["35cm", "50cm"]})
            if "서랍" in blob or "오픈" in blob or shelf_like:
                groups.append({"name": "형태", "values": ["오픈형", "서랍형"]})
            return groups[:3]
        size_values: list[str] = []
        if re.search(r"35\s*cm|35센치|35폭", compact, re.IGNORECASE):
            size_values.append("35cm")
        if re.search(r"50\s*cm|50센치|50폭", compact, re.IGNORECASE):
            size_values.append("50cm")
        if size_values:
            groups.append({"name": "사이즈", "values": self._dedupe_text_items(size_values)})
        return groups[:3]

    def _market_source_option_candidates(self, product: MarketProduct) -> list[str]:
        candidates = [
            str(product.metadata.get("options_text") or ""),
            str(product.source.get("options_text") or ""),
            str(product.metadata.get("option_text") or ""),
            str(product.source.get("option_text") or ""),
        ]
        for payload in product.metadata.get("source_payloads", []):
            if isinstance(payload, dict):
                candidates.append(str(payload.get("options_text") or ""))
                candidates.append(str(payload.get("option_text") or ""))
                candidates.append(self._market_clean_product_source_text(payload.get("text"))[:3000])
        for payload in product.source.get("source_payloads", []):
            if isinstance(payload, dict):
                candidates.append(str(payload.get("options_text") or ""))
                candidates.append(str(payload.get("option_text") or ""))
                candidates.append(self._market_clean_product_source_text(payload.get("text"))[:3000])
        candidates.extend([product.result_text, self._market_primary_text_blob(product)[:5000]])
        return [candidate for candidate in candidates if candidate.strip()]

    def _market_source_options_text(self, product: MarketProduct) -> str:
        chunks = [
            str(product.metadata.get("options_text") or ""),
            str(product.source.get("options_text") or ""),
            str(product.metadata.get("option_text") or ""),
            str(product.source.get("option_text") or ""),
        ]
        for payload in product.metadata.get("source_payloads", []):
            if isinstance(payload, dict):
                chunks.append(str(payload.get("options_text") or ""))
                chunks.append(self._market_clean_product_source_text(payload.get("text"))[:3000])
        for payload in product.source.get("source_payloads", []):
            if isinstance(payload, dict):
                chunks.append(str(payload.get("options_text") or ""))
                chunks.append(self._market_clean_product_source_text(payload.get("text"))[:3000])
        chunks.extend([product.result_text, self._market_primary_text_blob(product)[:5000]])
        return "\n".join(chunk for chunk in chunks if chunk.strip())

    def _parse_market_option_groups(self, text: str | object) -> list[dict[str, object]]:
        raw = str(text or "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            groups = self._option_groups_from_json(parsed)
            if groups:
                return groups
        except Exception:
            pass
        groups: list[dict[str, object]] = []
        for chunk in re.split(r"[;\n]+", raw):
            chunk = chunk.strip()
            if not chunk:
                continue
            match = re.match(r"([가-힣A-Za-z0-9 _/\-]{1,20})\s*[:=：]\s*(.+)", chunk)
            if not match:
                continue
            name = self._clean_option_text(match.group(1)) or "옵션"
            values = self._split_option_values(match.group(2))
            if values:
                groups.append({"name": name, "values": values})
        if groups:
            return groups
        for name in ("색상", "컬러", "사이즈", "규격", "크기", "구성", "단수"):
            pattern = rf"{name}\s*[:=：]\s*([가-힣A-Za-z0-9 /,|·+\-~]{1,120})"
            values: list[str] = []
            for match in re.finditer(pattern, raw):
                values.extend(self._split_option_values(match.group(1)))
            values = self._dedupe_text_items(values)
            if values:
                groups.append({"name": "색상" if name == "컬러" else name, "values": values})
        return groups

    def _option_groups_from_json(self, parsed: object) -> list[dict[str, object]]:
        groups: list[dict[str, object]] = []
        if isinstance(parsed, dict):
            parsed = parsed.get("groups") or parsed.get("option_groups") or parsed
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    values = value if isinstance(value, list) else self._split_option_values(value)
                    groups.append({"name": self._clean_option_text(key) or "옵션", "values": values})
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "name" in item:
                    values = item.get("values") or item.get("items") or []
                    if not isinstance(values, list):
                        values = self._split_option_values(values)
                    groups.append({"name": self._clean_option_text(item.get("name")) or "옵션", "values": values})
                elif isinstance(item, dict):
                    for key, value in item.items():
                        values = value if isinstance(value, list) else self._split_option_values(value)
                        groups.append({"name": self._clean_option_text(key) or "옵션", "values": values})
        return groups

    def _split_option_values(self, value: str | object) -> list[str]:
        text = str(value or "")
        parts = re.split(r"\s*(?:\||,|/|·|ㆍ|、|，|\\n)\s*", text)
        cleaned = [self._clean_option_text(part) for part in parts]
        return self._dedupe_text_items([part for part in cleaned if 1 <= len(part) <= 30])[:30]

    def _clean_option_text(self, value: str | object) -> str:
        text = self._clean_detail_copy_text(str(value or ""))
        delivery_noises = (
            "배송비",
            "묶음배송",
            "출고지",
            "반품",
            "교환",
            "제주도",
            "도서산간",
            "상품정보를 확인",
            "배송비 별도",
            "공급사",
            "등급",
            "멤버십",
            "비상주 오피스",
        )
        if any(noise in text for noise in delivery_noises):
            return ""
        if any(
            noise in text
            for noise in (
                "꾹AI",
                "상품번호",
                "도매꾹",
                "돈버는 쇼핑",
                "브랜드",
                "랭킹",
                "점수",
                "도움말",
                "검색필터",
            )
        ):
            return ""
        for phrase in (
            "마무리하세요.",
            "마무리하세요",
            "옵션선택",
            "전체옵션보기",
            "상품상세 더보기",
            "상품상세더보기",
            "인사이트 얻기",
        ):
            text = text.replace(phrase, " ")
        if re.fullmatch(r"\d[\d,]*\s*점", text.strip()):
            return ""
        if text.strip() in {"추천", "기본", "선택"}:
            return ""
        if self._is_url(text):
            return ""
        text = re.sub(r"(선택|옵션|필수|선택형|추가금|품절)\s*", "", text).strip(" :-_/|")
        text = re.sub(r"\s+", " ", text)
        return text[:30].strip()

    def _coupang_option_text_has_unavailable_marker(self, value: str | object) -> bool:
        text = str(value or "")
        return any(marker in text for marker in ("판매종료", "일시품절", "품절"))

    def _clean_coupang_option_text(self, name: str | object, value: str | object) -> str:
        text = str(value or "")
        text = re.sub(r"\s*\(?\s*(판매종료|일시품절|품절)\s*\)?", "", text)
        cleaned = self._clean_option_text(text)
        if not cleaned:
            return ""
        name_key = self._normalize_text_key(str(name or ""))
        if any(token in name_key for token in ("색상", "컬러", "color")):
            colors = [
                "라이트그레이",
                "다크그레이",
                "혼합색상",
                "연그레이",
                "진그레이",
                "화이트",
                "블랙",
                "그레이",
                "베이지",
                "브라운",
                "네이비",
                "카키",
                "그린",
                "레드",
                "오렌지",
                "옐로",
                "블루",
                "퍼플",
                "핑크",
                "실버",
                "투명",
            ]
            matches = [(cleaned.rfind(color), color) for color in colors if color in cleaned]
            if matches:
                matches.sort()
                return matches[-1][1]
        return cleaned

    def _coupang_option_is_unavailable(self, option: dict[str, object]) -> bool:
        if not isinstance(option, dict):
            return False
        if self._coupang_option_text_has_unavailable_marker(option.get("label")):
            return True
        values = option.get("option_values", {})
        if isinstance(values, dict):
            return any(self._coupang_option_text_has_unavailable_marker(value) for value in values.values())
        return False

    def _normalize_option_groups(self, groups: list[dict[str, object]]) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        seen_names: set[str] = set()
        for index, group in enumerate(groups, start=1):
            name = self._clean_option_text(group.get("name", "")) or f"옵션{index}"
            name = self._normalize_option_group_name(name)
            if name in seen_names:
                name = f"{name}{index}"
            values = group.get("values", [])
            if not isinstance(values, list):
                values = self._split_option_values(values)
            values = self._dedupe_text_items([self._clean_option_text(value) for value in values if str(value).strip()])
            if not values:
                continue
            seen_names.add(name)
            normalized.append({"name": name[:25], "values": values[:30]})
        return normalized

    def _normalize_option_group_name(self, name: str) -> str:
        raw = str(name or "").strip()
        lower_raw = raw.lower().replace("_", " ").strip()
        if lower_raw in {"option", "options", "option name"}:
            return "옵션"
        if lower_raw in {"color", "colour"}:
            return "색상"
        if lower_raw in {"size"}:
            return "사이즈"
        if raw in {"옵션", "옵션명"} or re.fullmatch(r"옵션\s*\d*", raw):
            return "옵션"
        text = self._clean_option_text(name)
        if "컬러" in text or "색상" in text:
            return "색상"
        if "사이즈" in text or "규격" in text or "크기" in text:
            return "사이즈"
        if "구성" in text:
            return "구성"
        if "단수" in text:
            return "단수"
        return text or "옵션"

    def _build_option_combinations(self, groups: list[dict[str, object]]) -> list[tuple[str, ...]]:
        value_lists = [list(group.get("values", [])) for group in groups if isinstance(group.get("values", []), list)]
        if not value_lists:
            return [("기본",)]
        combinations = list(itertools.product(*value_lists))
        return combinations[:300] if combinations else [("기본",)]

    def _parse_option_price_delta(self, value: str | object) -> dict[str, int]:
        text = str(value or "").strip()
        if not text or text == "0":
            return {}
        result: dict[str, int] = {}
        for chunk in re.split(r"[;\n,]+", text):
            match = re.match(r"(.+?)\s*[:=]\s*([+-]?\d[\d,]*)", chunk.strip())
            if not match:
                continue
            key = self._clean_option_text(match.group(1))
            amount = int(match.group(2).replace(",", ""))
            if key:
                result[key] = amount
        return result

    def _build_market_seo_fallback_prompt(
        self,
        product: MarketProduct,
        category: str,
        items: list[str],
    ) -> str:
        return (
            "아래 상품의 마켓별 SEO를 네이버와 쿠팡 기준으로 따로 제안해줘.\n"
            "네이버는 판매자 태그/상품속성 안정성을 우선하고, 쿠팡은 구매옵션/카테고리 메타값 안정성을 우선해줘.\n"
            "확실하지 않은 코드는 단정하지 말고 후보명만 적어줘.\n\n"
            f"상품명: {product.product_name}\n"
            f"카테고리 추정: {category}\n"
            f"수집 요약: {' / '.join(items[:8])}\n"
        )

    def _build_platform_market_seo_fallback_prompt(
        self,
        product: MarketProduct,
        category: str,
        items: list[str],
        platform: str,
    ) -> str:
        common = (
            f"상품명: {product.product_name}\n"
            f"카테고리 추정: {category}\n"
            f"수집 요약: {' / '.join(items[:8])}\n"
            "확실하지 않은 값은 단정하지 말고 '확인 필요'로 표시.\n"
        )
        if platform == "naver":
            return (
                "네이버 스마트스토어 등록용 SEO/속성만 제안해줘.\n"
                "쿠팡 기준은 섞지 마.\n"
                "출력 항목: 네이버 상품명, Page Title, Meta description, 판매자 태그 10개 이하, 상품속성 후보.\n"
                "판매자 태그는 2~20자 한글/영문/숫자만 사용하고 브랜드명, 공급사명, 최저가, 무료배송, 추천, 랭킹, 과장/금지 표현, 문장형 단어는 제외.\n"
                "상품속성은 실제 상품 정보에서 확인되는 값만 후보로 적고, 모르면 확인 필요로 둬.\n\n"
                f"{common}"
            )
        return (
            "쿠팡 등록용 SEO/옵션/카테고리 메타값만 제안해줘.\n"
            "네이버 판매자 태그 기준은 섞지 마.\n"
            "출력 항목: 쿠팡 상품명, 검색태그 20개 이하, 필수 구매옵션 후보, 필수 속성 후보, 카테고리 후보.\n"
            "색상/사이즈/수량/개당 수량/개당 용량/개당 중량 같은 쿠팡 필수값은 실제 정보 기준으로 채우고, 확인 불가하면 기본/혼합색상/1개처럼 안전한 기본값 후보를 표시.\n"
            "품절/판매종료 옵션, 무관한 자유 옵션명, 과장/금지 표현은 제외.\n\n"
            f"{common}"
        )

    def _build_naver_payload(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        settings: dict[str, str],
        image_refs: dict[str, object],
    ) -> dict[str, object]:
        pricing = self._market_pricing_plan(product, settings, "naver")
        sale_price = int(pricing.get("sale_price") or 0)
        stock_quantity = self._positive_int(settings.get("stock_quantity", "")) or 100
        representative = image_refs.get("representative", {}) if isinstance(image_refs.get("representative"), dict) else {}
        optional_refs = image_refs.get("optional", []) if isinstance(image_refs.get("optional"), list) else []
        detail_ref = image_refs.get("detail_page", {}) if isinstance(image_refs.get("detail_page"), dict) else {}
        category_code = self._effective_category_code(product, "naver", settings)
        outbound_code = self._effective_location_code(settings, "naver", "outbound")
        return_code = self._effective_location_code(settings, "naver", "return")
        origin = self._market_source_origin(product) or self._market_effective_value(product, settings, "origin", "중국")
        manufacturer = self._market_effective_value(product, settings, "manufacturer", DEFAULT_MARKET_MANUFACTURER)
        brand = self._market_effective_value(product, settings, "brand", DEFAULT_MARKET_BRAND)
        copy = dict(copy)
        naver_product_title = self._naver_product_title(product, copy, brand)
        copy["naver_product_title"] = naver_product_title
        naver_search_info = {"brandName": brand, "manufacturerName": manufacturer}
        extra_detail_attributes = self._naver_extra_detail_attributes(product, copy, manufacturer)
        extra_search_info = extra_detail_attributes.pop("naverShoppingSearchInfo", {})
        if isinstance(extra_search_info, dict):
            naver_search_info.update(extra_search_info)
        product_attributes = extra_detail_attributes.pop("productAttributes", [])
        importer = manufacturer if self._clean_market_field_text(manufacturer) else "판매자 확인"
        delivery_fee = self._platform_delivery_fee(settings, "naver")
        return_fee = self._positive_int(settings.get("return_delivery_fee", "")) or 3000
        exchange_fee = self._positive_int(settings.get("exchange_delivery_fee", "")) or max(return_fee * 2, 6000)
        as_phone = self._market_setting_or_auto(settings, "naver_as_phone", "seller_as_phone")
        origin_area_code = self._naver_origin_area_code_for_origin(origin, settings)
        delivery_company = self._market_setting_or_auto(settings, "naver_delivery_company", "naver_delivery_company")
        optional_images = [
            {
                "url": str(item.get("url") or self._local_file_url(product.thumbnail_paths[index])),
                "_localPath": str(item.get("local_path") or product.thumbnail_paths[index]),
            }
            for index, item in enumerate(optional_refs, start=1)
        ]
        return {
            "_draft": {
                "draft_only": True,
                "draft_version": MARKET_DRAFT_VERSION,
                "seo_title": naver_product_title,
                "keywords": copy.get("naver_keywords", copy["keywords"]),
                "related_keywords": copy.get("naver_keywords", copy.get("related_keywords", [])),
                "seller_tags": copy.get("naver_search_tags", []),
                "category_candidates": copy.get("category_candidates", []),
                "image_refs": image_refs,
                "pricing": pricing,
                "category_auto_text": copy.get("category_text", ""),
                "validation_required": [
                    "AUTO_LOOKUP 값은 live 업로드 전 API 조회 결과 또는 저장 설정으로 교체",
                    "local-file 이미지는 live 등록 시 네이버 이미지 업로드 API HTTPS URL로 자동 교체",
                ],
            },
            "originProduct": {
                "statusType": "SALE",
                "saleType": "NEW",
                "leafCategoryId": category_code,
                "name": naver_product_title,
                "detailContent": self._market_detail_html(product, str(detail_ref.get("url") or "")),
                "images": {
                    "representativeImage": {
                        "url": str(representative.get("url") or self._local_file_url(product.thumbnail_paths[0])),
                        "_localPath": str(representative.get("local_path") or product.thumbnail_paths[0]),
                    },
                    "optionalImages": optional_images or [
                        {
                            "url": str(representative.get("url") or self._local_file_url(product.thumbnail_paths[0])),
                            "_localPath": str(representative.get("local_path") or product.thumbnail_paths[0]),
                        }
                    ],
                },
                "salePrice": sale_price,
                "stockQuantity": stock_quantity,
                "deliveryInfo": {
                    "deliveryType": "DELIVERY",
                    "deliveryAttributeType": "NORMAL",
                    "deliveryCompany": delivery_company,
                    "deliveryFee": {
                        "deliveryFeeType": "FREE" if delivery_fee == 0 else "PAID",
                        "baseFee": delivery_fee,
                        "deliveryFeePayType": "PREPAID",
                    },
                    "outboundLocationId": outbound_code,
                    "returnLocationId": return_code,
                    "claimDeliveryInfo": {
                        "returnDeliveryCompanyPriorityType": "PRIMARY",
                        "returnDeliveryFee": return_fee,
                        "exchangeDeliveryFee": exchange_fee,
                        "shippingAddressId": outbound_code,
                        "returnAddressId": return_code,
                    },
                },
                "detailAttribute": {
                    "naverShoppingSearchInfo": naver_search_info,
                    "minorPurchasable": True,
                    "afterServiceInfo": {
                        "afterServiceTelephoneNumber": as_phone,
                        "afterServiceGuideContent": str(copy["as_message"]),
                    },
                    "originAreaInfo": {"originAreaCode": origin_area_code, "content": origin, "importer": importer},
                    "manufacturer": manufacturer,
                    "brand": brand,
                    "taxType": settings.get("tax_type", "TAX"),
                    "unitCapacity": {"unitPriceYn": False},
                    "seoInfo": self._naver_seo_info(copy, product, brand),
                    "sellerCodeInfo": {"sellerManagementCode": product.code},
                    "optionInfo": self._naver_option_info(copy, product, settings, sale_price),
                    "productInfoProvidedNotice": self._naver_product_notice(product, copy, manufacturer, origin),
                    **({"productAttributes": product_attributes} if product_attributes else {}),
                    **extra_detail_attributes,
                },
            },
            "smartstoreChannelProduct": {
                "naverShoppingRegistration": True,
                "channelProductDisplayStatusType": "ON",
            },
        }

    def _naver_seo_info(
        self,
        copy: dict[str, object],
        product: MarketProduct,
        brand: str,
    ) -> dict[str, object]:
        title = self._naver_product_title(product, copy, brand)
        summary = str(copy.get("naver_summary") or copy.get("summary") or "")
        if not summary:
            keywords = copy.get("naver_keywords", copy.get("related_keywords", []))
            if isinstance(keywords, list):
                summary = " ".join(str(item or "") for item in keywords[:8])
        summary = re.sub(r'[\\*?"<>]', " ", summary or title)
        summary = self._strip_external_brand_terms(summary, product, brand)
        for noise in ("돈버는 쇼핑 도매꾹", "돈버는 쇼핑", "도매꾹"):
            summary = summary.replace(noise, " ")
        for noise in ("최저가", "무료배송"):
            summary = summary.replace(noise, " ")
        summary = re.sub(r"\|\s*", " ", summary)
        summary = re.sub(r",\s*,+", ",", summary)
        summary = re.sub(r"\s+", " ", summary).strip()
        return {
            "pageTitle": self._clip_text(title, 70),
            "metaDescription": self._clip_text(summary, 160),
            "sellerTags": self._naver_seller_tags(copy, product, brand),
        }

    def _naver_extra_detail_attributes(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        manufacturer: str,
    ) -> dict[str, object]:
        if not self._is_baby_chair_product(product):
            return {}
        source_title = self._market_source_field(product, ("품명 및 모델명", "품명", "모델명")) or copy.get("naver_product_title") or product.product_name
        certification_number = self._market_kc_certification_number(product)
        company_name = self._market_source_field(product, ("제조자", "제조사", "수입자")) or manufacturer
        result: dict[str, object] = {
            "naverShoppingSearchInfo": {"modelName": self._clip_text(source_title, 100)},
            "productAttributes": self._naver_baby_chair_product_attributes(product),
        }
        if certification_number:
            result["productCertificationInfos"] = [
                {
                    "certificationInfoId": 1042,
                    "certificationKindType": "CHILD_CERTIFICATION",
                    "name": "[어린이제품]공급자적합성확인_국가인증",
                    "certificationNumber": certification_number,
                    "certificationMark": True,
                    "companyName": company_name,
                }
            ]
            result["certificationTargetExcludeContent"] = {
                "childCertifiedProductExclusionYn": False,
            }
        return result

    def _naver_baby_chair_product_attributes(self, product: MarketProduct) -> list[dict[str, int]]:
        blob = self._market_text_blob(product)
        attributes: list[dict[str, int]] = []
        seen: set[tuple[int, int]] = set()

        def append(attribute_seq: int, value_seq: int) -> None:
            key = (attribute_seq, value_seq)
            if key in seen:
                return
            seen.add(key)
            attributes.append({"attributeSeq": attribute_seq, "attributeValueSeq": value_seq})

        append(10012826, 10678483)  # 종류: 유아식탁의자
        append(10012827, 10678486)  # 구성: 의자
        if any(term in blob for term in ("식판", "트레이")):
            append(10012827, 10678487)  # 구성: 식판
        if "안전가드" in blob:
            append(10012827, 10673605)  # 구성: 안전가드
        if "안전벨트" in blob or "벨트" in blob:
            append(10012827, 10678489)  # 구성: 안전벨트
        if "발받침" in blob:
            append(10012827, 10678490)  # 구성: 발받침
        if "접이" in blob:
            append(10012828, 10028652)  # 특징: 접이식
        if any(term in blob for term in ("원목", "목재", "나무", "우드")):
            append(10025794, 10031941)  # 프레임소재: 원목
        if "A형" in blob or "A형 다리" in blob:
            append(10039938, 10791284)  # 형태: A형
        return attributes

    def _extract_kc_certification_number(self, value: str | object) -> str:
        text = str(value or "").upper()
        patterns = [
            r"\b[A-Z]{1,3}\d{2,}[A-Z0-9-]{3,}\b",
            r"\b[A-Z]{1,3}\d{3,}[A-Z0-9]*-\d{3,}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    def _market_kc_certification_text(self, product: MarketProduct) -> str:
        return self._market_source_field(product, ("KC 인증정보", "어린이제품 인증", "인증/허가 사항", "인증정보"))

    def _market_kc_certification_number(self, product: MarketProduct) -> str:
        return self._extract_kc_certification_number(self._market_kc_certification_text(product))

    def _naver_product_title(self, product: MarketProduct, copy: dict[str, object], brand: str) -> str:
        brand = self._clean_market_field_text(brand) or DEFAULT_MARKET_BRAND
        title = str(copy.get("naver_seo_title") or copy.get("seo_title") or product.product_name or "").strip()
        title = re.sub(r"\|.*$", "", title)
        title = re.sub(r"\b\d{6,}\b\s*랭킹점수\s*:\s*\d+점", " ", title)
        for noise in ("돈버는 쇼핑 도매꾹", "도매꾹", "상품번호", "랭킹점수", "브랜드 없음", "추천"):
            title = title.replace(noise, " ")
        for noise in ("최저가", "무료배송"):
            title = title.replace(noise, " ")
        title = self._clean_detail_copy_text(title)
        title = re.sub(r"\s+", " ", title).strip(" -_/|·")
        if not title:
            title = self._market_seo_title(product.product_name, self._infer_market_category_text(product))
        title = re.sub(r"\b소파\b", "거실", title)
        title = self._strip_external_brand_terms(title, product, brand)
        title = re.sub(rf"^(?:{re.escape(brand)}\s*)+", "", title).strip()
        title = f"{brand} {title}".strip()
        return self._clip_text(title, 100)

    def _coupang_product_title(self, product: MarketProduct, copy: dict[str, object], brand: str) -> str:
        brand = self._clean_market_field_text(brand) or DEFAULT_MARKET_BRAND
        title = str(copy.get("coupang_seo_title") or copy.get("seo_title") or product.product_name or "").strip()
        title = re.sub(r"\|.*$", "", title)
        title = re.sub(r"\b\d{6,}\b\s*랭킹점수\s*:\s*\d+점", " ", title)
        for noise in ("돈버는 쇼핑 도매꾹", "도매꾹", "상품번호", "랭킹점수", "브랜드 없음", "추천"):
            title = title.replace(noise, " ")
        for noise in ("최저가", "무료배송"):
            title = title.replace(noise, " ")
        title = self._clean_detail_copy_text(title)
        title = re.sub(r"\s+", " ", title).strip(" -_/|·")
        if not title:
            title = self._market_seo_title(product.product_name, self._infer_market_category_text(product))
        title = re.sub(r"\b소파\b", "거실", title)
        title = self._strip_external_brand_terms(title, product, brand)
        title = re.sub(rf"^(?:{re.escape(brand)}\s*)+", "", title).strip()
        title = f"{brand} {title}".strip()
        return self._clip_text(title, COUPANG_PRODUCT_NAME_LIMIT)

    def _external_brand_terms(self, product: MarketProduct, brand: str) -> list[str]:
        own_brand = re.sub(r"[^가-힣A-Za-z0-9]", "", str(brand or ""))
        candidates: list[str] = []
        for value in (
            product.product_name,
            str(product.metadata.get("product_name") or "") if isinstance(product.metadata, dict) else "",
            str(product.source.get("product_name") or "") if isinstance(product.source, dict) else "",
            str(product.source.get("title") or "") if isinstance(product.source, dict) else "",
        ):
            for match in re.finditer(r"\[([^\[\]]{2,30})\]", str(value or "")):
                term = self._clean_detail_copy_text(match.group(1))
                normalized = re.sub(r"[^가-힣A-Za-z0-9]", "", term)
                if term and normalized and normalized != own_brand:
                    candidates.append(term)
        if self._is_baby_chair_product(product):
            candidates.extend(["베이비캠프", "베이스캠프"])
        return self._dedupe_text_items(candidates)

    def _strip_external_brand_terms(self, value: str | object, product: MarketProduct, brand: str) -> str:
        text = str(value or "")
        for term in self._external_brand_terms(product, brand):
            if not term:
                continue
            pattern = re.escape(term)
            text = re.sub(rf"\[\s*{pattern}\s*\]\s*", " ", text)
            text = re.sub(pattern, " ", text)
        text = re.sub(r"\[\s*\]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip(" -_/|·")

    def _filter_external_brand_items(self, values: list[str], product: MarketProduct, brand: str) -> list[str]:
        external_terms = [
            re.sub(r"[^가-힣A-Za-z0-9]", "", term)
            for term in self._external_brand_terms(product, brand)
        ]
        cleaned: list[str] = []
        for value in values:
            normalized = re.sub(r"[^가-힣A-Za-z0-9]", "", str(value or ""))
            if normalized and any(term and term in normalized for term in external_terms):
                continue
            cleaned.append(value)
        return self._dedupe_text_items(cleaned)

    def _coupang_search_tags(self, copy: dict[str, object], product: MarketProduct, brand: str) -> list[str]:
        platform_tags = copy.get("coupang_search_tags")
        if isinstance(platform_tags, list):
            cleaned_platform_tags = [
                re.sub(r"[^가-힣A-Za-z0-9]", "", str(tag or ""))
                for tag in platform_tags
            ]
            cleaned_platform_tags = [tag for tag in cleaned_platform_tags if 2 <= len(tag) <= 20]
            if cleaned_platform_tags:
                return self._dedupe_text_items(cleaned_platform_tags)[:20]
        clean_tags = self._market_search_tag_candidates(copy, product, brand, include_brand=True, limit=20)
        if clean_tags:
            return clean_tags[:20]
        seeds = [brand, product.product_name, str(copy.get("seo_title") or ""), str(copy.get("category_text") or "")]
        external_terms = self._external_brand_terms(product, brand)
        if self._is_baby_chair_product(product):
            seeds.extend(["유아식탁의자", "아기식탁의자", "하이체어", "아기의자", "유아의자", "원목식탁의자", "접이식식탁의자", "이유식의자"])
        elif self._is_storage_shelf_product(product):
            seeds.extend(["수납선반", "이동식선반", "다용도선반", "바퀴선반", "틈새수납", "공간활용"])
        for key in ("search_tags", "related_keywords", "keywords"):
            value = copy.get(key, [])
            if isinstance(value, list):
                seeds.extend(str(item or "") for item in value)
        seeds.extend(re.findall(r"[가-힣A-Za-z0-9]{2,20}", product.product_name or ""))
        cleaned: list[str] = []
        for seed in seeds:
            tag = re.sub(r"[^가-힣A-Za-z0-9]", "", str(seed or ""))
            if not tag or len(tag) > 20:
                continue
            if any(re.sub(r"[^가-힣A-Za-z0-9]", "", term) in tag for term in external_terms):
                continue
            if any(noise in tag for noise in ("랭킹", "점수", "추천", "상품번호", "도매꾹", "돈버는", "최저가", "무료배송")):
                continue
            cleaned.append(tag)
        return self._dedupe_text_items(cleaned)[:20]

    def _coupang_option_item_name(self, option: dict[str, object], index: int) -> str:
        values = option.get("option_values", {}) if isinstance(option, dict) else {}
        parts: list[str] = []
        if isinstance(values, dict):
            for name, value in values.items():
                cleaned = self._clean_coupang_option_text(name, value)
                if cleaned:
                    parts.append(cleaned)
        label = " ".join(self._dedupe_text_items(parts)).strip()
        return label or f"옵션 {index}"

    def _build_coupang_payload(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        settings: dict[str, str],
        image_refs: dict[str, object],
    ) -> dict[str, object]:
        pricing = self._market_pricing_plan(product, settings, "coupang")
        sale_price = int(pricing.get("sale_price") or 0)
        stock_quantity = self._positive_int(settings.get("stock_quantity", "")) or 100
        representative = image_refs.get("representative", {}) if isinstance(image_refs.get("representative"), dict) else {}
        optional_refs = image_refs.get("optional", []) if isinstance(image_refs.get("optional"), list) else []
        detail_ref = image_refs.get("detail_page", {}) if isinstance(image_refs.get("detail_page"), dict) else {}
        animated_webp_ref = image_refs.get("coupang_animated_webp", {}) if isinstance(image_refs.get("coupang_animated_webp"), dict) else {}
        animated_webp_url = str(animated_webp_ref.get("public_url") or "") if self._is_https_webp_url(animated_webp_ref.get("public_url")) else ""
        category_code = self._effective_category_code(product, "coupang", settings)
        outbound_code = self._effective_location_code(settings, "coupang", "outbound")
        return_code = self._effective_location_code(settings, "coupang", "return")
        manufacturer = self._market_effective_value(product, settings, "manufacturer", DEFAULT_MARKET_MANUFACTURER)
        brand = self._market_effective_value(product, settings, "brand", DEFAULT_MARKET_BRAND)
        origin = self._market_source_origin(product) or self._market_effective_value(product, settings, "origin", "중국")
        delivery_fee = self._platform_delivery_fee(settings, "coupang")
        return_fee = self._positive_int(settings.get("return_delivery_fee", "")) or 3000
        delivery_company_code = self._market_setting_or_auto(settings, "coupang_delivery_company_code", "coupang_delivery_company_code")
        vendor_user_id = str(settings.get("coupang_vendor_user_id") or "").strip()
        vendor_id = self._market_setting_or_auto(settings, "coupang_vendor_id", "coupang_vendor_id")
        images = [
            {
                "imageOrder": 0,
                "imageType": "REPRESENTATION",
                "vendorPath": str(representative.get("url") or self._local_file_url(product.thumbnail_paths[0])),
                "_localPath": str(representative.get("local_path") or product.thumbnail_paths[0]),
            }
        ]
        images.extend(
            {
                "imageOrder": index,
                "imageType": "DETAIL",
                "vendorPath": str(item.get("url") or self._local_file_url(Path(str(item.get("local_path") or "")))),
                "_localPath": str(item.get("local_path") or ""),
            }
            for index, item in enumerate(optional_refs[:4], start=1)
        )
        product_title = self._coupang_product_title(product, copy, brand)
        option_items = self._coupang_items(
            product=product,
            copy=copy,
            settings=settings,
            images=images,
            detail_ref=detail_ref,
            product_title=product_title,
            sale_price=sale_price,
            stock_quantity=stock_quantity,
            manufacturer=manufacturer,
            brand=brand,
            origin=origin,
            animated_webp_url=animated_webp_url,
        )
        payload = {
            "_draft": {
                "draft_only": True,
                "draft_version": MARKET_DRAFT_VERSION,
                "keywords": copy.get("coupang_keywords", copy["keywords"]),
                "related_keywords": copy.get("coupang_keywords", copy.get("related_keywords", [])),
                "search_tags": copy.get("coupang_search_tags", []),
                "coupang_product_title": product_title,
                "category_candidates": copy.get("category_candidates", []),
                "image_refs": image_refs,
                "pricing": pricing,
                "category_auto_text": copy.get("category_text", ""),
                "validation_required": [
                    "AUTO_LOOKUP 값은 live 업로드 전 API 조회 결과 또는 저장 설정으로 교체",
                    "local-file 이미지는 live 등록 전 네이버 이미지 업로드 HTTPS URL 또는 공개 CDN URL로 교체",
                ],
            },
            "_kcCertificationText": self._market_kc_certification_text(product),
            "displayCategoryCode": category_code if self._is_auto_lookup_value(category_code) else (self._positive_int(category_code) or category_code),
            "sellerProductName": product_title,
            "vendorId": vendor_id,
            "saleStartedAt": datetime.now().strftime("%Y-%m-%dT00:00:00"),
            "saleEndedAt": "2099-12-31T23:59:59",
            "displayProductName": product_title,
            "brand": brand,
            "manufacture": manufacturer,
            "manufacturer": manufacturer,
            "generalProductName": product_title,
            "productGroup": copy.get("category_text", ""),
            "deliveryMethod": "SEQUENCIAL",
            "deliveryCompanyCode": delivery_company_code,
            "deliveryChargeType": "FREE" if delivery_fee == 0 else "NOT_FREE",
            "deliveryCharge": delivery_fee,
            "freeShipOverAmount": 0,
            "deliveryChargeOnReturn": return_fee,
            "returnCharge": return_fee,
            "remoteAreaDeliverable": "Y",
            "unionDeliveryType": "UNION_DELIVERY",
            "returnCenterCode": return_code,
            "returnChargeName": self._market_setting_or_auto(settings, "return_charge_name", "return_charge_name"),
            "companyContactNumber": self._market_setting_or_auto(settings, "company_contact_number", "company_contact_number"),
            "returnZipCode": self._market_setting_or_auto(settings, "return_zip_code", "return_zip_code"),
            "returnAddress": self._market_setting_or_auto(settings, "return_address", "return_address"),
            "returnAddressDetail": self._market_setting_or_auto(settings, "return_address_detail", "return_address_detail"),
            "outboundShippingPlaceCode": outbound_code,
            "requested": True,
            "items": option_items,
        }
        if vendor_user_id and not self._is_auto_lookup_value(vendor_user_id):
            payload["vendorUserId"] = vendor_user_id
        return payload

    def _market_setting_or_auto(self, settings: dict[str, str], key: str, auto_key: str) -> str:
        value = str(settings.get(key) or "").strip()
        return value if value else AUTO_LOOKUP_PREFIX + auto_key

    def _platform_delivery_fee(self, settings: dict[str, str], platform: str) -> int:
        platform_fee = self._positive_int(settings.get(f"{platform}_delivery_fee", ""))
        if platform_fee > 0:
            return platform_fee
        return self._positive_int(settings.get("delivery_fee", "")) or 0

    def _naver_option_info(
        self,
        copy: dict[str, object],
        product: MarketProduct | None = None,
        settings: dict[str, str] | None = None,
        base_sale_price: int = 0,
    ) -> dict[str, object]:
        groups = copy.get("option_groups", [])
        options = copy.get("options", [])
        if not isinstance(groups, list) or not groups:
            groups = [{"name": "옵션", "values": ["기본"]}]
        if not isinstance(options, list) or not options:
            options = [
                {
                    "label": "옵션:기본",
                    "option_values": {"옵션": "기본"},
                    "stock_quantity": 100,
                    "price_delta": 0,
                    "seller_sku": "DEFAULT-001",
                }
            ]
        group_names = {
            f"optionGroupName{index}": str(group.get("name") or f"옵션{index}")[:25]
            for index, group in enumerate(groups[:3], start=1)
            if isinstance(group, dict)
        }
        option_combinations: list[dict[str, object]] = []
        for index, option in enumerate(options[:300], start=1):
            if not isinstance(option, dict):
                continue
            values = option.get("option_values", {})
            if not isinstance(values, dict):
                values = {}
            option_price_delta = self._positive_int(option.get("price_delta", ""))
            if product is not None and settings is not None and base_sale_price > 0:
                source_price = self._positive_int(option.get("source_price", ""))
                if source_price:
                    option_price = int(
                        self._market_pricing_plan(
                            product,
                            settings,
                            "naver",
                            source_cost_override=source_price,
                        ).get("sale_price")
                        or base_sale_price
                    )
                    option_price_delta = max(0, option_price - base_sale_price) + option_price_delta
            manager_prefix = "OPT"
            if product is not None:
                manager_prefix = re.sub(r"[^A-Za-z0-9_-]+", "", str(product.code or "").upper())[:16] or "OPT"
            seller_manager_code = f"{manager_prefix}{index:04d}"[:20]
            row: dict[str, object] = {
                "stockQuantity": self._positive_int(option.get("stock_quantity", "")) or 100,
                "price": option_price_delta,
                "usable": True,
                "sellerManagerCode": seller_manager_code,
                "skuYn": False,
            }
            for group_index, group in enumerate(groups[:3], start=1):
                name = str(group.get("name") or f"옵션{group_index}") if isinstance(group, dict) else f"옵션{group_index}"
                row[f"optionName{group_index}"] = str(values.get(name) or "기본")[:100]
            option_combinations.append(row)
        return {
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": group_names or {"optionGroupName1": "옵션"},
            "optionCombinations": option_combinations,
            "useStockManagement": True,
        }

    def _coupang_items(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        settings: dict[str, str],
        images: list[dict[str, object]],
        detail_ref: dict[str, object],
        product_title: str,
        sale_price: int,
        stock_quantity: int,
        manufacturer: str,
        brand: str,
        origin: str,
        animated_webp_url: str = "",
    ) -> list[dict[str, object]]:
        options = copy.get("options", [])
        if not isinstance(options, list) or not options:
            options = [{"label": "기본", "option_values": {"옵션": "기본"}, "stock_quantity": stock_quantity, "price_delta": 0, "seller_sku": product.code}]
        else:
            raw_options = [option for option in options if isinstance(option, dict)]
            available_options = [option for option in raw_options if not self._coupang_option_is_unavailable(option)]
            if available_options:
                options = available_options
            elif raw_options:
                raise RuntimeError("쿠팡 등록 가능한 옵션이 없습니다. 판매종료/품절 옵션만 감지되었습니다.")
        items: list[dict[str, object]] = []
        for index, option in enumerate(options[:200], start=1):
            if not isinstance(option, dict):
                continue
            label = str(option.get("label") or f"옵션 {index}")
            option_price_delta = int(option.get("price_delta") or 0)
            option_price = sale_price + option_price_delta
            source_price = self._positive_int(option.get("source_price", ""))
            if source_price:
                option_price = int(
                    self._market_pricing_plan(
                        product,
                        settings,
                        "coupang",
                        source_cost_override=source_price,
                    ).get("sale_price")
                    or option_price
                ) + option_price_delta
            option_stock = self._positive_int(option.get("stock_quantity", "")) or stock_quantity or 100
            item_name = self._clip_text(self._coupang_option_item_name(option, index), 150)
            seller_sku = self._clip_text(str(option.get("seller_sku") or f"{product.code}-{index:03d}"), 100)
            notice_copy = {
                **copy,
                "coupang_product_title": product_title,
                "_kcCertificationText": self._market_kc_certification_text(product),
            }
            items.append(
                {
                    "itemName": item_name,
                    "originalPrice": option_price,
                    "salePrice": option_price,
                    "maximumBuyCount": min(option_stock, 99999),
                    "maximumBuyForPerson": 0,
                    "maximumBuyForPersonPeriod": 1,
                    "outboundShippingTimeDay": 2,
                    "unitCount": 1,
                    "adultOnly": "EVERYONE",
                    "taxType": settings.get("tax_type", "TAX"),
                    "parallelImported": "NOT_PARALLEL_IMPORTED",
                    "overseasPurchased": "NOT_OVERSEAS_PURCHASED",
                    "pccNeeded": False,
                    "externalVendorSku": seller_sku,
                    "emptyBarcode": True,
                    "emptyBarcodeReason": "상품에 바코드가 없음",
                    "modelNo": product.code,
                    "extraProperties": {"optionLabel": item_name, "sourceCode": product.code},
                    "images": images,
                    "notices": self._coupang_notices(product, notice_copy, manufacturer, origin),
                    "attributes": self._coupang_attributes(product, copy, manufacturer, brand, origin, option),
                    "contents": [
                        {
                            "contentsType": "HTML",
                            "contentDetails": [
                                {
                                    "content": self._market_detail_html(product, str(detail_ref.get("url") or ""), animated_webp_url),
                                    "detailType": "TEXT",
                                }
                            ],
                        }
                    ],
                    "certifications": [
                        {
                            "certificationType": "NOT_REQUIRED",
                            "certificationCode": "인증대상 아님",
                        }
                    ],
                    "searchTags": self._coupang_search_tags(copy, product, brand),
                }
            )
        return items or self._coupang_items(
            product,
            {**copy, "options": [{"label": "기본", "option_values": {"옵션": "기본"}, "stock_quantity": stock_quantity, "price_delta": 0}]},
            settings,
            images,
            detail_ref,
            product_title,
            sale_price,
            stock_quantity,
            manufacturer,
            brand,
            origin,
            animated_webp_url,
        )

    def _clip_text(self, value: str | object, limit: int) -> str:
        text = self._clean_detail_copy_text(str(value or ""))
        return text[:limit] if text else "기본"

    def _clip_utf8_bytes(self, value: str | object, limit: int) -> str:
        text = self._clean_detail_copy_text(str(value or ""))
        if len(text.encode("utf-8")) <= limit:
            return text
        clipped = ""
        for char in text:
            candidate = clipped + char
            if len(candidate.encode("utf-8")) > limit:
                break
            clipped = candidate
        return clipped.strip()

    def _market_search_tag_candidates(
        self,
        copy: dict[str, object],
        product: MarketProduct | None = None,
        brand: str = "",
        include_brand: bool = False,
        limit: int = 20,
    ) -> list[str]:
        seeds: list[str] = []
        for key in ("seo_title", "category_text"):
            seeds.append(str(copy.get(key) or ""))
        for key in ("keywords", "related_keywords", "search_tags"):
            value = copy.get(key, [])
            if isinstance(value, list):
                seeds.extend(str(item or "") for item in value)
        if product is not None:
            source_facts = product.source.get("facts", []) if isinstance(product.source, dict) else []
            metadata_facts = product.metadata.get("facts", []) if isinstance(product.metadata, dict) else []
            seeds.extend(
                [
                    product.product_name,
                    str(product.source.get("title") or "") if isinstance(product.source, dict) else "",
                    str(product.source.get("product_name") or "") if isinstance(product.source, dict) else "",
                    str(product.source.get("category") or "") if isinstance(product.source, dict) else "",
                    str(product.source.get("options_text") or "") if isinstance(product.source, dict) else "",
                ]
            )
            if isinstance(source_facts, list):
                seeds.extend(str(item or "") for item in source_facts[:20])
            if isinstance(metadata_facts, list):
                seeds.extend(str(item or "") for item in metadata_facts[:20])
        options = copy.get("options", [])
        if isinstance(options, list):
            for option in options[:50]:
                if not isinstance(option, dict):
                    continue
                values = option.get("option_values", {})
                if isinstance(values, dict):
                    seeds.extend(str(item or "") for item in values.keys())
                    seeds.extend(str(item or "") for item in values.values())
        if include_brand and brand:
            seeds.insert(0, brand)

        brand_text = re.sub(r"[^0-9A-Za-z가-힣]", "", str(brand or "")).lower()
        blocked = {
            "상품", "상품명", "핵심", "문제", "상세", "상세페이지", "페이지", "이미지", "옵션", "확인", "구매", "판매", "추천",
            "도매꾹", "네이버", "카테고리", "브랜드", "선택", "기본", "사용", "정리", "쉽게",
            "바로", "순간", "더하는", "더한", "하세요", "합니다", "됩니다", "입니다", "두세요",
            "씻은", "돌려", "더해", "보관할", "매번", "불편했던", "상황", "고민했다면", "이제", "으로", "확인된", "기능", "장면", "맞춘",
            "착용하세요", "정리하세요", "라인을정리하세요", "존재감을정리하세요",
            "쇼핑", "옵션선택", "색상", "원산지", "수입산", "아시아", "중국", "모델명",
            "해당없음", "품명", "제조국", "또는", "오너클랜", "상품정보", "상세정보",
            "관련", "연락처", "참고", "제조사", "수입사", "상품코드", "해외", "협력업체",
            "상품군", "기타",
        }
        blocked_suffixes = ("하세요", "합니다", "됩니다", "입니다", "두세요", "납니다", "보세요", "주세요", "다면", "했던")
        blocked_particles = ("로", "과", "와", "에", "를", "을", "은", "는")
        noisy_substrings = (
            "최저가",
            "생활",
            "주방",
            "디지털",
            "가전",
            "별도표기",
            "상세정보",
            "이거찜",
            "협력사",
            "사입",
            "삼미호협력사",
            "위셀사입",
            "꽃님이사입",
            "스크래치커머스",
            "모두톡톡",
        )
        tags: list[str] = []
        for seed in seeds:
            text = re.sub(r"https?://\S+", " ", str(seed or ""))
            text = re.sub(r"[\[\]{}()<>\"'`~!@#$%^&*=+\\|;:,.?/·•]+", " ", text)
            for part in re.split(r"\s+|/|>|_|-", text):
                tag = re.sub(r"[^0-9A-Za-z가-힣]", "", part)
                if not 2 <= len(tag) <= 20:
                    continue
                if re.fullmatch(r"\d+", tag):
                    continue
                lowered = tag.lower()
                if brand_text and brand_text in lowered and not include_brand:
                    continue
                if re.fullmatch(r"[A-Z]+\d[A-Z0-9_-]*", tag, flags=re.IGNORECASE):
                    continue
                if lowered in blocked or any(noise in lowered for noise in blocked if len(noise) >= 4):
                    continue
                if any(noise in lowered for noise in noisy_substrings):
                    continue
                if lowered.endswith(blocked_suffixes):
                    continue
                if len(tag) >= 3 and tag.endswith(blocked_particles):
                    continue
                tags.append(tag)
        return self._dedupe_text_items(tags)[:limit]

    def _naver_seller_tags(
        self,
        copy: dict[str, object],
        product: MarketProduct | None = None,
        brand: str = "",
    ) -> list[dict[str, str]]:
        platform_tags = copy.get("naver_search_tags")
        if isinstance(platform_tags, list):
            cleaned_platform_tags = [
                re.sub(r"[^가-힣A-Za-z0-9]", "", str(tag or ""))
                for tag in platform_tags
            ]
            cleaned_platform_tags = [tag for tag in cleaned_platform_tags if 2 <= len(tag) <= 20]
            if cleaned_platform_tags:
                return [{"text": tag} for tag in self._dedupe_text_items(cleaned_platform_tags)[:10]]
        if product is not None and self._is_baby_chair_product(product):
            return [
                {"text": tag}
                for tag in self._dedupe_text_items(
                    [
                        "접이식",
                        "식판형",
                        "발받침",
                        "안전벨트",
                        "내추럴",
                        "간편접이",
                        "트레이형",
                    ]
                )[:10]
            ]
        clean_tags = self._market_search_tag_candidates(copy, product, brand, include_brand=False, limit=10)
        if clean_tags:
            return [{"text": tag} for tag in clean_tags[:10]]
        seeds = [
            str(copy.get("seo_title") or ""),
            str(copy.get("category_text") or ""),
        ]
        if product is not None:
            seeds.append(product.product_name)
            if self._is_baby_chair_product(product):
                seeds.extend(["유아식탁의자", "아기식탁의자", "하이체어", "아기의자", "유아의자", "원목식탁의자", "접이식식탁의자", "이유식의자"])
            elif self._is_storage_shelf_product(product):
                seeds.extend(["수납선반", "이동식선반", "다용도선반", "바퀴선반", "틈새수납", "공간활용"])
        for key in ("related_keywords", "keywords", "search_tags"):
            value = copy.get(key, [])
            if isinstance(value, list):
                seeds.extend(str(item or "") for item in value)
        brand_text = re.sub(r"[^가-힣A-Za-z0-9]", "", str(brand or ""))
        blocked = {
            "랭킹",
            "점수",
            "추천",
            "상품번호",
            "도매꾹",
            "돈버는",
            "카테고리",
            "사이드테이블",
            "카트",
            "트롤리",
            "소파",
            "가죽소파",
            "브랜드",
        }
        cleaned: list[str] = []
        for seed in seeds:
            tag = re.sub(r"[^가-힣A-Za-z0-9]", "", str(seed or ""))
            if not tag:
                continue
            if len(tag.encode("utf-8")) > 30:
                continue
            if brand_text and brand_text in tag:
                continue
            if any(noise in tag for noise in blocked):
                continue
            cleaned.append(tag)
        return [{"text": tag} for tag in self._dedupe_text_items(cleaned)[:10]]

    def _naver_product_notice(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        manufacturer: str,
        origin: str,
    ) -> dict[str, object]:
        source_title = self._market_source_field(product, ("품명 및 모델명",)) or copy.get("naver_product_title") or product.product_name
        source_manufacturer = self._market_source_field(product, ("제조자", "제조사", "수입자")) or manufacturer
        source_origin = self._market_source_origin(product) or origin
        source_kc = self._market_kc_certification_text(product)
        quality = self._market_source_field(product, ("품질보증기준",)) or str(copy.get("as_message") or "상품 수령 후 판매자 문의")
        phone = (
            self._market_field_text("naver_as_phone")
            or str(getattr(self, "market_resolved_settings", {}).get("naver_as_phone") or "").strip()
            or AUTO_LOOKUP_PREFIX + "seller_as_phone"
        )
        return {
            "productInfoProvidedNoticeType": "ETC",
            "etc": {
                "itemName": self._clip_text(source_title, 49),
                "modelName": product.code,
                "manufacturer": source_manufacturer,
                "origin": source_origin,
                "certificationDetails": source_kc or "관련 법령에 따름",
                "customerServicePhoneNumber": phone,
                "qualityAssuranceStandard": quality,
                "returnCostReason": "상품 불량 및 오배송은 판매자 확인 후 처리",
                "noRefundReason": "사용 흔적 또는 구성품 훼손 시 제한 가능",
                "compensationProcedure": "판매자 고객센터 접수 후 마켓 정책에 따라 처리",
            },
        }

    def _coupang_notices(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        manufacturer: str,
        origin: str,
    ) -> list[dict[str, str]]:
        title = self._clip_text(self._market_source_field(product, ("품명 및 모델명",)) or copy.get("coupang_product_title") or product.product_name, 100)
        source_manufacturer = self._market_source_field(product, ("제조자", "제조사", "수입자")) or manufacturer
        source_origin = self._market_source_origin(product) or origin
        source_kc = self._market_kc_certification_text(product) or "관련 법령에 따름"
        return [
            {"noticeCategoryName": "기타 재화", "noticeCategoryDetailName": "품명 및 모델명", "content": title},
            {"noticeCategoryName": "기타 재화", "noticeCategoryDetailName": "인증/허가 사항", "content": source_kc},
            {"noticeCategoryName": "기타 재화", "noticeCategoryDetailName": "제조국(원산지)", "content": source_origin},
            {"noticeCategoryName": "기타 재화", "noticeCategoryDetailName": "제조자(수입자)", "content": source_manufacturer},
            {"noticeCategoryName": "기타 재화", "noticeCategoryDetailName": "A/S 책임자와 전화번호", "content": str(copy.get("as_message") or "판매자 문의")},
        ]

    def _coupang_attributes(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        manufacturer: str,
        brand: str,
        origin: str,
        option: dict[str, object] | None = None,
    ) -> list[dict[str, str]]:
        category = str(copy.get("category_text") or "생활용품")
        attributes: list[dict[str, str]] = []
        seen: set[str] = set()

        def append_attr(name: str, value: str | object, exposed: str = "NONE") -> None:
            clean_name = self._clean_detail_copy_text(name)
            clean_value = self._clean_detail_copy_text(str(value or ""))
            if not clean_name or not clean_value:
                return
            if any(noise in clean_value for noise in ("랭킹", "점수", "추천", "도매꾹", "돈버는", "상품번호")):
                return
            if clean_name in seen:
                return
            seen.add(clean_name)
            attributes.append(
                {
                    "attributeTypeName": clean_name[:30],
                    "attributeValueName": clean_value[:100],
                    "exposed": exposed,
                }
            )

        option_values = option.get("option_values", {}) if isinstance(option, dict) else {}
        if isinstance(option_values, dict):
            for name, value in option_values.items():
                clean_name = self._clean_option_text(name) or "옵션"
                clean_value = self._clean_coupang_option_text(clean_name, value) or "기본"
                exposed = "EXPOSED" if clean_name in self._coupang_variant_attribute_names() else "NONE"
                append_attr(clean_name, clean_value, exposed)
        option_text = " ".join(
            str(value or "")
            for value in option_values.values()
        ) if isinstance(option_values, dict) else ""
        shelf_count = "3단" if "3단" in option_text else ("2단" if "2단" in option_text else "")
        width = "50cm" if "50" in option_text else ("35cm" if "35" in option_text else "")
        height = "82cm" if shelf_count == "3단" else ("50cm" if shelf_count == "2단" else "")
        form = "서랍형" if "서랍" in option_text else ("오픈형" if "오픈" in option_text else "선반형")
        size = " x ".join([item for item in (width, "30cm", height) if item])

        if self._is_baby_chair_product(product):
            source_title = self._market_source_field(product, ("품명 및 모델명",)) or self._market_seo_title(product.product_name, "")
            source_manufacturer = self._market_source_field(product, ("제조자", "제조사", "수입자")) or manufacturer
            source_origin = self._market_source_origin(product) or origin
            source_color = self._market_source_field(product, ("색상", "컬러")) or "원목색"
            source_material = self._market_source_field(product, ("재질", "주요 소재", "소재")) or "원목"
            source_size = self._market_source_field(product, ("크기, 중량", "크기", "규격", "사이즈")) or "상세페이지 참조"
            source_age = self._market_source_field(product, ("사용연령 또는 권장사용연령", "사용연령", "권장사용연령")) or "상세페이지 참조"
            source_kc = self._market_kc_certification_text(product) or "관련 법령에 따름"
            care = self._market_source_field(product, ("취급방법 및 취급시 주의사항, 안전표시", "취급방법", "주의사항"))
            append_attr("브랜드", brand)
            append_attr("제조사", source_manufacturer)
            append_attr("원산지", source_origin)
            append_attr("상품유형", "유아식탁의자")
            append_attr("상품형태", "유아용 식탁의자")
            append_attr("품명 및 모델명", source_title)
            append_attr("색상", source_color, "EXPOSED")
            append_attr("색상계열", source_color)
            append_attr("사이즈", source_size, "EXPOSED")
            append_attr("크기", source_size)
            append_attr("재질", source_material)
            append_attr("프레임재질", source_material)
            append_attr("사용연령", source_age)
            append_attr("KC 인증정보", source_kc)
            append_attr("어린이제품 인증", source_kc)
            append_attr("조립 필요여부", "조립 필요")
            append_attr("본품/리필", "본품")
            append_attr("수량", "1개")
            append_attr("안전벨트 포함 여부", "포함")
            append_attr("접이 가능 여부", "접이식")
            if care:
                append_attr("취급시 주의사항", care)
            append_attr("GTIN", "없음")
            if isinstance(option, dict):
                append_attr("Variation MPN", option.get("seller_sku", ""))
            append_attr("Parent MPN", product.code)
            return [
                {key: value for key, value in attribute.items() if str(value or "").strip()}
                for attribute in attributes
            ]

        if not self._is_storage_shelf_product(product):
            append_attr("브랜드", brand)
            append_attr("제조사", manufacturer)
            append_attr("원산지", origin)
            append_attr("상품유형", category[-30:])
            append_attr("모델명", product.code)
            append_attr("수량", "1개")
            append_attr("GTIN", "없음")
            if isinstance(option, dict):
                append_attr("Variation MPN", option.get("seller_sku", ""))
            append_attr("Parent MPN", product.code)
            return [
                {key: value for key, value in attribute.items() if str(value or "").strip()}
                for attribute in attributes
            ]

        append_attr("브랜드", brand)
        append_attr("제조사", manufacturer)
        append_attr("원산지", origin)
        append_attr("상품유형", category[-30:])
        append_attr("상품형태", "이동식 수납선반")
        append_attr("상품 구성", "동일한 상품으로 구성됨")
        append_attr("모델명", product.code)
        append_attr("색상", "브라운", "EXPOSED")
        append_attr("색상계열", "브라운계열")
        append_attr("가구/홈 계절", "사계절")
        append_attr("인테리어 컨셉", "내추럴")
        append_attr("가구 수납 형태", form)
        append_attr("선반 유형", "이동식 선반")
        append_attr("프레임 재질", "우드톤")
        append_attr("조립식 여부", "조립식")
        append_attr("조립 여부", "조립 필요")
        append_attr("조립 필요여부", "조립 필요")
        append_attr("설치지원방식", "자가설치")
        append_attr("품목 모양", "직사각형")
        append_attr("필수 구성 요소", "본품")
        append_attr("포함 구성 요소", "본품")
        append_attr("수량", "1개")
        append_attr("손잡이 유무", "있음")
        append_attr("바퀴 고정 가능 여부", "확인 필요")
        append_attr("슬라이딩 여부", "해당없음")
        append_attr("물조절 가능 여부", "해당없음")
        append_attr("물마개 조절 여부", "해당없음")
        append_attr("GTIN", "없음")
        if shelf_count:
            append_attr("단수", shelf_count)
            append_attr("가구 단수", shelf_count)
        if width:
            append_attr("가로길이", width)
        if height:
            append_attr("높이", height)
            append_attr("아이템 높이", height)
        if size:
            append_attr("사이즈", size, "EXPOSED")
        if isinstance(option, dict):
            append_attr("Variation MPN", option.get("seller_sku", ""))
        append_attr("Parent MPN", product.code)
        return [
            {key: value for key, value in attribute.items() if str(value or "").strip()}
            for attribute in attributes
        ]

    def _market_detail_html(self, product: MarketProduct, detail_url: str, animated_webp_url: str = "") -> str:
        alt_name = self._strip_external_brand_terms(product.product_name, product, DEFAULT_MARKET_BRAND)
        for noise in ("최저가", "무료배송"):
            alt_name = alt_name.replace(noise, " ")
        escaped_name = html.escape(re.sub(r"\s+", " ", alt_name).strip())
        image_url = detail_url.strip() or self._local_file_url(product.detail_page_path)
        escaped_url = html.escape(image_url)
        motion_url = animated_webp_url.strip()
        motion_html = ""
        if self._is_https_webp_url(motion_url):
            escaped_motion_url = html.escape(motion_url)
            motion_html = (
                f"<img src=\"{escaped_motion_url}\" alt=\"{escaped_name}\" "
                f"style=\"display:block;width:100%;max-width:{COUPANG_ANIMATED_WEBP_WIDTH}px;height:auto;margin:0 auto 24px auto;border:0;\" />"
            )
        return (
            f"<div style=\"text-align:center;margin:0 auto;padding:0;\">"
            f"{motion_html}"
            f"<img src=\"{escaped_url}\" alt=\"{escaped_name}\" "
            f"style=\"display:block;width:100%;max-width:860px;height:auto;margin:0 auto;border:0;\" />"
            f"</div>"
        )

    def _build_market_chatgpt_prompt(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        naver_prompt: str = "",
        coupang_prompt: str = "",
    ) -> str:
        return f"""이 파일은 호환용 통합 검수 프롬프트입니다.
실제 마켓별 검수는 같은 폴더의 naver_market_prompt.txt와 coupang_market_prompt.txt를 각각 사용하세요.

--- 네이버 전용 검수 ---
{naver_prompt}

--- 쿠팡 전용 검수 ---
{coupang_prompt}
"""

    def _build_naver_market_chatgpt_prompt(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        payload: dict[str, object],
    ) -> str:
        origin = payload.get("originProduct", {}) if isinstance(payload, dict) else {}
        detail = origin.get("detailAttribute", {}) if isinstance(origin, dict) else {}
        seo = detail.get("seoInfo", {}) if isinstance(detail, dict) else {}
        tags = seo.get("sellerTags", []) if isinstance(seo, dict) else []
        attributes = detail.get("productAttributes", []) if isinstance(detail, dict) else []
        option_info = detail.get("optionInfo", {}) if isinstance(detail, dict) else {}
        return f"""아래 상품의 네이버 스마트스토어 등록 초안만 검수해줘.

상품명: {product.product_name}
상품코드: {product.code}
완료폴더: {product.folder}
네이버 상품명: {origin.get("name", "") if isinstance(origin, dict) else ""}
네이버 카테고리ID: {origin.get("leafCategoryId", "") if isinstance(origin, dict) else ""}
네이버 SEO 제목: {seo.get("pageTitle", "") if isinstance(seo, dict) else ""}
네이버 metaDescription: {seo.get("metaDescription", "") if isinstance(seo, dict) else ""}
네이버 판매자 태그: {json.dumps(tags, ensure_ascii=False)}
네이버 상품속성: {json.dumps(attributes, ensure_ascii=False)}
네이버 옵션정보: {json.dumps(option_info, ensure_ascii=False)[:2500]}
네이버 키워드 초안: {", ".join([str(item) for item in copy.get("naver_keywords", copy.get("keywords", []))])}
네이버 카테고리 후보: {json.dumps(copy.get("category_candidates", []), ensure_ascii=False)}
네이버 전용 SEO 생성 기준:
{copy.get("naver_chatgpt_seo_prompt", "")}
수집 기반 요약: {copy.get("summary", "")}

확인할 것:
1. 네이버 상품명/페이지타이틀/메타설명 SEO
2. 네이버 카테고리ID와 상품속성(productAttributes) 적합성
3. 네이버 판매자 태그에서 금지/무관 단어
4. 네이버 옵션 조합, 판매가, 재고, 고시정보 누락
5. 네이버 정책상 과장/금지 표현 위험

쿠팡 기준으로 판단하지 말고 네이버 등록 기준만 확인해줘.
확인 안 되는 정보는 단정하지 말고 '확인 필요'로 표시해줘.
"""

    def _build_coupang_market_chatgpt_prompt(
        self,
        product: MarketProduct,
        copy: dict[str, object],
        payload: dict[str, object],
    ) -> str:
        items = payload.get("items", []) if isinstance(payload, dict) else []
        first_item = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
        return f"""아래 상품의 쿠팡 등록 초안만 검수해줘.

상품명: {product.product_name}
상품코드: {product.code}
완료폴더: {product.folder}
쿠팡 sellerProductName: {payload.get("sellerProductName", "") if isinstance(payload, dict) else ""}
쿠팡 displayCategoryCode: {payload.get("displayCategoryCode", "") if isinstance(payload, dict) else ""}
쿠팡 검색태그: {json.dumps(first_item.get("searchTags", []), ensure_ascii=False)}
쿠팡 첫 옵션명: {first_item.get("itemName", "")}
쿠팡 첫 옵션 attributes: {json.dumps(first_item.get("attributes", []), ensure_ascii=False)}
쿠팡 옵션 개수: {len(items) if isinstance(items, list) else 0}
쿠팡 키워드 초안: {", ".join([str(item) for item in copy.get("coupang_keywords", copy.get("keywords", []))])}
쿠팡 전용 SEO/옵션 생성 기준:
{copy.get("coupang_chatgpt_seo_prompt", "")}
수집 기반 요약: {copy.get("summary", "")}

확인할 것:
1. 쿠팡 상품명/검색태그 SEO
2. 쿠팡 displayCategoryCode 적합성
3. 쿠팡 필수 구매옵션/메타값: 색상, 사이즈, 수량, 개당 수량/용량/중량
4. 쿠팡에서 허용하지 않는 자유 옵션명 '옵션' 사용 여부
5. 쿠팡 판매가, 이미지, 고시정보, 상세 HTML 누락
6. 쿠팡 정책상 과장/금지 표현 위험

네이버 기준으로 판단하지 말고 쿠팡 등록 기준만 확인해줘.
확인 안 되는 정보는 단정하지 말고 '확인 필요'로 표시해줘.
"""

    def _price_from_metadata(self, metadata: dict[str, object]) -> int:
        price_text = " ".join(
            str(metadata.get(key) or "")
            for key in ("price_text", "sale_price", "price")
        )
        numbers = re.findall(r"\d[\d,]*", price_text)
        values = [int(value.replace(",", "")) for value in numbers if value.replace(",", "").isdigit()]
        return values[0] if values else 0

    def _market_unit_price_from_total_quantity(self, text: str | object) -> int:
        cleaned = str(text or "")
        match = re.search(r"총\s*상품금액\s*\(\s*수량\s*\)\s*\(\s*(\d[\d,]*)\s*개\s*\)\s*(\d[\d,]*)\s*원", cleaned)
        if not match:
            return 0
        quantity = int(match.group(1).replace(",", ""))
        total = int(match.group(2).replace(",", ""))
        if quantity <= 0 or total <= 0:
            return 0
        return max(1, round(total / quantity))

    def _market_unit_price_near_title(self, product: MarketProduct, text: str | object) -> int:
        cleaned = str(text or "")
        title = re.sub(r"\|.*$", "", str(product.product_name or "")).strip()
        if not cleaned or not title:
            return 0
        start = cleaned.find(title)
        if start < 0:
            return 0
        window = cleaned[start : start + 400]
        match = re.search(r"(\d[\d,]*)\s*원\s*가격\s*기록", window)
        if not match:
            match = re.search(r"판매가\s*(\d[\d,]*)\s*원", window)
        return int(match.group(1).replace(",", "")) if match else 0

    def _market_source_cost(self, product: MarketProduct) -> int:
        option_prices = [
            self._positive_int(row.get("source_price", ""))
            for row in self._market_source_option_rows(product)
            if isinstance(row, dict)
        ]
        option_prices = [price for price in option_prices if price > 0]
        if option_prices:
            return min(option_prices)
        text = self._market_clean_product_source_text(product.source.get("text")) if isinstance(product.source, dict) else ""
        unit_match = re.search(r"단가\s*\(원\)\s*([\d,\s\t]+)", text)
        if unit_match:
            values = [
                int(value.replace(",", ""))
                for value in re.findall(r"\d[\d,]*", unit_match.group(1))
                if value.replace(",", "").isdigit()
            ]
            values = [value for value in values if value > 0]
            if values:
                return values[0]
        title_price = self._market_unit_price_near_title(product, text)
        if title_price:
            return title_price
        unit_price = self._market_unit_price_from_total_quantity(text)
        if unit_price:
            return unit_price
        return self._price_from_metadata(product.metadata)

    def _effective_sale_price(self, product: MarketProduct, platform: str = "naver") -> int:
        settings = self._market_settings_data(include_secrets=False)
        return int(self._market_pricing_plan(product, settings, platform).get("sale_price") or 0)

    def _market_pricing_plan(
        self,
        product: MarketProduct,
        settings: dict[str, str],
        platform: str,
        source_cost_override: int | None = None,
    ) -> dict[str, object]:
        manual_price = (
            self._positive_int(settings.get(f"{platform}_sale_price", ""))
            or self._positive_int(settings.get("sale_price", ""))
        )
        source_cost = (
            self._positive_int(source_cost_override)
            if source_cost_override is not None
            else self._positive_int(settings.get("source_cost", "")) or self._market_source_cost(product)
        )
        extra_cost = self._positive_int(settings.get("base_cost_extra", ""))
        low_cost_delivery_fee = (
            LOW_COST_DELIVERY_FEE
            if 0 < source_cost < LOW_COST_DELIVERY_THRESHOLD
            else 0
        )
        total_cost = source_cost + extra_cost + low_cost_delivery_fee
        legacy_default_pricing = self._market_uses_legacy_default_pricing(settings)
        target_margin_rate = (
            float(DEFAULT_TARGET_NET_MARGIN_RATE)
            if legacy_default_pricing
            else self._percent_number(settings.get("margin_rate"), float(DEFAULT_TARGET_NET_MARGIN_RATE))
        )
        fee_default = float(DEFAULT_COUPANG_FEE_RATE if platform == "coupang" else DEFAULT_NAVER_FEE_RATE)
        fee_rate = fee_default if legacy_default_pricing else self._percent_number(settings.get(f"{platform}_fee_rate"), fee_default)
        tax_rate = self._percent_number(settings.get("tax_rate"), float(DEFAULT_MARKET_TAX_RATE))
        other_fee_rate = self._percent_number(settings.get("other_fee_rate"), float(DEFAULT_MARKET_OTHER_FEE_RATE))
        round_unit = self._positive_int(settings.get("price_round_unit", "")) or int(DEFAULT_PRICE_ROUND_UNIT)
        round_unit = max(1, round_unit)
        if manual_price > 0:
            sale_price = manual_price
            source = "manual_sale_price"
        else:
            denominator = 1 - (fee_rate / 100.0) - (tax_rate / 100.0) - (other_fee_rate / 100.0)
            if denominator <= 0:
                denominator = (
                    1
                    - (fee_default / 100.0)
                    - (float(DEFAULT_MARKET_TAX_RATE) / 100.0)
                    - (float(DEFAULT_MARKET_OTHER_FEE_RATE) / 100.0)
                )
            target_net_profit = total_cost * (target_margin_rate / 100.0)
            raw_price = (total_cost + target_net_profit) / denominator if total_cost > 0 and denominator > 0 else total_cost
            sale_price = self._ceil_to_unit(int(raw_price) + (1 if raw_price % 1 else 0), round_unit)
            source = "auto_cost_margin_plus_platform_costs"
        estimated_fee = int(round(sale_price * fee_rate / 100.0))
        estimated_tax = int(round(sale_price * tax_rate / 100.0))
        estimated_other_fee = int(round(sale_price * other_fee_rate / 100.0))
        estimated_net_profit = max(0, sale_price - estimated_fee - estimated_tax - estimated_other_fee - total_cost)
        estimated_net_margin_rate = round((estimated_net_profit / sale_price) * 100, 2) if sale_price else 0
        estimated_net_profit_on_cost_rate = round((estimated_net_profit / total_cost) * 100, 2) if total_cost else 0
        return {
            "platform": platform,
            "sale_price": sale_price,
            "source": source,
            "pricing_basis": "cost_net_profit",
            "pricing_policy": "margin20_fee10_tax10" if legacy_default_pricing else "custom_or_default",
            "legacy_default_pricing_upgraded": legacy_default_pricing,
            "source_cost": source_cost,
            "extra_cost": extra_cost,
            "low_cost_delivery_fee": low_cost_delivery_fee,
            "low_cost_delivery_threshold": LOW_COST_DELIVERY_THRESHOLD,
            "total_cost": total_cost,
            "target_net_margin_rate": target_margin_rate,
            "target_net_profit_on_cost_rate": target_margin_rate,
            "fee_rate": fee_rate,
            "tax_rate": tax_rate,
            "other_fee_rate": other_fee_rate,
            "price_round_unit": round_unit,
            "estimated_fee": estimated_fee,
            "estimated_tax": estimated_tax,
            "estimated_other_fee": estimated_other_fee,
            "estimated_net_profit": estimated_net_profit,
            "estimated_net_margin_rate": estimated_net_margin_rate,
            "estimated_net_profit_on_cost_rate": estimated_net_profit_on_cost_rate,
        }

    def _market_uses_legacy_default_pricing(self, settings: dict[str, str]) -> bool:
        def same_rate(key: str, expected: str) -> bool:
            raw = str(settings.get(key) or "").strip()
            if not raw:
                return False
            return abs(self._percent_number(raw, -999.0) - float(expected)) < 0.0001

        return (
            same_rate("margin_rate", LEGACY_TARGET_NET_MARGIN_RATE)
            and same_rate("naver_fee_rate", LEGACY_NAVER_FEE_RATE)
            and same_rate("coupang_fee_rate", LEGACY_COUPANG_FEE_RATE)
        )

    def _percent_number(self, value: str | object, default: float) -> float:
        text = str(value or "").strip().replace("%", "")
        match = re.search(r"\d+(?:\.\d+)?", text)
        if not match:
            return default
        try:
            return max(0.0, float(match.group(0)))
        except ValueError:
            return default

    def _ceil_to_unit(self, value: int, unit: int) -> int:
        if unit <= 1:
            return max(0, value)
        return ((max(0, value) + unit - 1) // unit) * unit

    def _positive_int(self, value: str | object) -> int:
        text = re.sub(r"[^\d]", "", str(value or ""))
        if not text:
            return 0
        try:
            return int(text)
        except ValueError:
            return 0

    def _market_price_expression_int(self, value: str | object) -> int:
        text = str(value or "")
        numbers = [
            int(match.group(0).replace(",", ""))
            for match in re.finditer(r"\d[\d,]*", text)
            if match.group(0).replace(",", "").isdigit()
        ]
        if not numbers:
            return 0
        if "+" in text:
            return sum(numbers)
        return numbers[0]

    def _market_forbidden_copy_issues(self, text: str) -> list[str]:
        forbidden = [
            "완치",
            "치료",
            "의학적 효능",
            "100%",
            "무조건",
            "최저가",
            "1위",
            "공식 인증",
            "평생 보장",
        ]
        return [f"금지/과장 표현 확인 필요: {word}" for word in forbidden if word in text]

    def _save_login_credentials(self, show_message: bool = True) -> bool:
        email = self.login_email_field.text().strip()
        password = self.login_password_field.text()
        if not email:
            QMessageBox.information(self, "아이디 필요", "ChatGPT 로그인 아이디를 입력하세요.")
            return False
        if not password:
            QMessageBox.information(self, "비밀번호 필요", "ChatGPT 비밀번호를 입력하세요.")
            return False
        if keyring is None:
            QMessageBox.warning(
                self,
                "저장 불가",
                "Windows 자격 증명 저장소를 사용할 수 없습니다. 비밀번호를 평문 파일로 저장하지 않습니다.",
            )
            return False
        try:
            keyring.set_password(KEYRING_SERVICE, email, password)
        except Exception as exc:
            QMessageBox.warning(self, "저장 실패", f"로그인 정보를 저장하지 못했습니다.\n{exc}")
            return False
        self._save_config()
        self._set_login_panel_status(f"로그인 정보 저장됨: {email}")
        if show_message:
            QMessageBox.information(
                self,
                "저장 완료",
                "아이디는 GUI 설정에 저장했고, 비밀번호는 Windows 자격 증명 저장소에 저장했습니다.",
            )
        return True

    def _load_saved_password_for_current_email(self) -> bool:
        email = self.login_email_field.text().strip()
        if not email or keyring is None:
            return False
        try:
            password = keyring.get_password(KEYRING_SERVICE, email)
        except Exception as exc:
            self._set_login_panel_status(f"저장된 비밀번호를 불러오지 못했습니다: {exc}")
            return False
        if password:
            self.login_password_field.setText(password)
            self._set_login_panel_status(f"저장된 로그인 정보 불러옴: {email}")
            return True
        self._set_login_panel_status(f"저장된 비밀번호 없음: {email}")
        return False

    def _start_chatgpt_login(self) -> None:
        if self.login_running:
            QMessageBox.information(self, "로그인 중", "이미 자동화 브라우저 로그인을 진행 중입니다.")
            return
        if not self._save_login_credentials(show_message=False):
            return
        email = self.login_email_field.text().strip()
        password = self.login_password_field.text()
        self.login_running = True
        self._set_login_panel_status("자동화 브라우저 로그인 중...")
        thread = threading.Thread(
            target=self._run_chatgpt_login_worker,
            args=(email, password),
            daemon=True,
        )
        thread.start()

    def _open_manual_login(self) -> None:
        self._set_login_panel_status("자동화 Chrome의 기존 ChatGPT 탭을 그대로 엽니다. 직접 로그인하세요.")
        self._open_url_in_automation_browser(
            GPT_URL,
            "기존 ChatGPT 탭을 그대로 사용합니다. 직접 로그인/모델 선택 후 2. 로그인 완료를 누르세요.",
        )

    def _open_1688_login(self) -> None:
        self._set_login_panel_status("자동화 Chrome에서 1688 로그인 페이지를 엽니다. 직접 로그인해두세요.")
        self._open_url_in_automation_browser(
            ALI_1688_LOGIN_URL,
            "1688 로그인 탭을 열었습니다. 로그인 후 다시 이 GUI로 돌아와 작업을 실행하세요.",
        )

    def _open_selected_product_login(self) -> None:
        index = self._selected_link_index()
        if index < 0:
            index = self.current_link_index if 0 <= self.current_link_index < len(self.link_tasks) else -1
        if index < 0 or index >= len(self.link_tasks):
            QMessageBox.information(self, "선택 필요", "먼저 로그인할 상품 URL 행을 선택하세요.")
            return
        task = self.link_tasks[index]
        if not task.url.strip():
            QMessageBox.information(self, "URL 없음", "선택한 행에 상품 URL이 없습니다.")
            return
        self._set_login_panel_status("자동화 Chrome에서 상품 URL을 엽니다. 필요한 사이트에 직접 로그인해두세요.")
        self._open_url_in_automation_browser(
            task.url.strip(),
            f"{index + 1}번 상품 URL 로그인 탭을 열었습니다. 로그인 후 작업을 실행하세요.",
        )

    def _start_login_check(self) -> None:
        if self.login_running:
            QMessageBox.information(self, "확인 중", "이미 로그인 상태 확인을 진행 중입니다.")
            return
        self.login_running = True
        self._set_login_panel_status("자동화 브라우저 로그인 상태 확인 중...")
        thread = threading.Thread(target=self._run_login_check_worker, daemon=True)
        thread.start()

    def _start_gpt_analysis(self, checked: bool = False, *, use_manual_resume: bool = False) -> None:
        if self.automation_running:
            QMessageBox.information(self, "실행 중", "이미 GPT 자동 분석이 실행 중입니다.")
            return
        jobs: list[tuple[int, str]] = []
        if use_manual_resume:
            self.active_manual_resume_request = self.manual_resume_request
            self.manual_resume_request = None
        else:
            self.manual_resume_request = None
            self.active_manual_resume_request = None
        if self.active_manual_resume_request:
            index = int(self.active_manual_resume_request.get("task_index", -1))
            if 0 <= index < len(self.link_tasks):
                jobs.append((index, self.link_tasks[index].url))
            else:
                self.active_manual_resume_request = None
        else:
            for index, task in enumerate(self.link_tasks):
                if self._task_output_complete(index, task.url, task.secondary_url):
                    if task.status != "완료":
                        task.status = "완료"
                    continue
                jobs.append((index, task.url))
        if not jobs:
            QMessageBox.information(
                self,
                "작업 없음",
                "분석할 URL이 없습니다. 완료 표시된 URL은 결과 PNG까지 있는지 확인했습니다.",
            )
            return

        self.automation_running = True
        self.automation_stop_requested = False
        self.automation_skip_requested = False
        self.result_box.clear()
        self.statusBar().showMessage("GPT 자동 분석 준비 중입니다.")
        thread = threading.Thread(target=self._run_gpt_analysis_worker, args=(jobs,), daemon=True)
        thread.start()

    def _request_current_task_stop(self) -> None:
        if not self.automation_running:
            self.statusBar().showMessage("현재 실행 중인 자동화가 없습니다.")
            return
        self.automation_stop_requested = True
        self.statusBar().showMessage("현재 자동화 중지를 요청했습니다. 진행 중인 대기 루프가 끝나면 멈춥니다.")

    def _raise_if_user_requested_stop_or_skip(self) -> None:
        if self.automation_stop_requested:
            raise AutomationStopRequested("사용자가 현재 작업 중지를 요청했습니다.")
        if self.automation_skip_requested:
            raise AutomationSkipRequested("사용자가 현재 항목 건너뛰기를 요청했습니다.")

    def _manual_resume_for_index(self, index: int) -> tuple[str | None, int]:
        request = self.active_manual_resume_request
        if not isinstance(request, dict):
            return None, 1
        try:
            request_index = int(request.get("task_index", -1))
        except Exception:
            return None, 1
        if request_index != index:
            return None, 1
        stage = str(request.get("stage") or "").strip()
        if stage not in {"section", "merge", "thumbnail"}:
            return None, 1
        try:
            number = max(1, int(request.get("number", 1) or 1))
        except Exception:
            number = 1
        if stage == "section" and number > MANUAL_SECTION_BUTTON_COUNT:
            return "merge", 1
        return stage, number

    def _run_gpt_analysis_worker(self, jobs: list[tuple[int, str]]) -> None:
        try:
            self.automation_signals.status.emit("자동화 브라우저 연결 중...")
            self._ensure_cdp_browser()
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                try:
                    page = self._ensure_chatgpt_section_planner_page_alive(context)
                    image_page = None
                except RuntimeError:
                    self.automation_signals.status.emit(
                        "ChatGPT 로그인이 필요합니다. 1. 로그인을 누르고 직접 로그인한 뒤 2. 로그인 완료를 누르세요."
                    )
                    return

                for index, url in jobs:
                    try:
                        self.automation_skip_requested = False
                        task = self.link_tasks[index]
                        secondary_url = task.secondary_url.strip()
                        resume_stage, resume_number = self._manual_resume_for_index(index)
                        if resume_stage:
                            page = self._ensure_chatgpt_section_planner_page_alive(context, page)
                        else:
                            page = self._ensure_chatgpt_section_planner_page_alive(context, page)
                            page = self._reset_gpt_page_for_url_job(context, page)
                        self.automation_signals.task_status.emit(index, "진행중")
                        if resume_stage:
                            resume_label = {
                                "section": f"섹션 {resume_number}",
                                "merge": "합치기",
                                "thumbnail": f"썸네일 {resume_number}",
                            }.get(resume_stage, "선택 지점")
                            self.automation_signals.status.emit(
                                f"{index + 1}번 URL {resume_label}부터 내부 이어가기 시작..."
                            )
                        if secondary_url:
                            self.automation_signals.status.emit(f"{index + 1}번 URL + 1688 보조 링크 상품 정보 추출 중...")
                        else:
                            self.automation_signals.status.emit(f"{index + 1}번 URL 상품 정보 추출 중...")
                        run_stamp = now_stamp()
                        existing_refresh = (
                            self._load_existing_detail_for_thumbnail_refresh(index, url, secondary_url)
                            if ENABLE_THUMBNAIL_ONLY_REFRESH
                            else None
                        )
                        if existing_refresh and not resume_stage and not self._task_output_complete(index, url, secondary_url):
                            saved_path = None
                            thumbnail_result = ThumbnailResult(paths=[], prompt_paths=[], image_model=CHATGPT_WEB_IMAGE_MODEL)
                            job_attempt = 0
                            thumbnail_job_limit = 1
                            while (
                                not self._thumbnail_result_complete(thumbnail_result)
                                and job_attempt < thumbnail_job_limit
                            ):
                                self._raise_if_user_requested_stop_or_skip()
                                job_attempt += 1
                                self.automation_signals.task_status.emit(index, f"썸네일 재시도중 {job_attempt}회")
                                self.automation_signals.status.emit(
                                    f"{index + 1}번 URL 기존 상세페이지 유지, 썸네일 5장 재생성 중... "
                                    f"{job_attempt}회차"
                                )
                                try:
                                    image_page = self._ensure_chatgpt_image_generation_page(context, image_page or page)
                                    saved_path, thumbnail_result = self._regenerate_existing_thumbnails_only(
                                        index,
                                        url,
                                        secondary_url,
                                        run_stamp,
                                        image_page,
                                        progress_callback=lambda done, total, job_index=index: (
                                            self.automation_signals.task_status.emit(job_index, f"썸네일 생성중 {done}/{total}"),
                                            self.automation_signals.status.emit(f"{job_index + 1}번 URL 썸네일 재생성 중... {done}/{total}"),
                                        ),
                                    )
                                except (AutomationStopRequested, AutomationSkipRequested):
                                    raise
                                except Exception as exc:
                                    if self._is_browser_disconnected_error(exc):
                                        raise AutomationBrowserDisconnected(str(exc)) from exc
                                    self.automation_signals.result.emit(
                                        f"## {index + 1}번 URL 썸네일 재시도 {job_attempt}회\n"
                                        f"URL: {url}\n"
                                        f"오류: {exc}\n\n"
                                    )
                                    try:
                                        if image_page is not None:
                                            self._click_chatgpt_retry_button(image_page, timeout_ms=12000)
                                    except Exception:
                                        pass
                                    if image_page is not None:
                                        image_page.wait_for_timeout(5000)
                                    continue
                            if not self._thumbnail_result_complete(thumbnail_result):
                                self.automation_signals.result.emit(
                                    f"## {index + 1}번 URL 썸네일 재생성 실패\n"
                                    f"URL: {url}\n"
                                    f"생성 썸네일: {len(thumbnail_result.paths)}/{REQUIRED_THUMBNAIL_IMAGE_COUNT}장\n"
                                    f"시도: {job_attempt}/{thumbnail_job_limit}회\n"
                                    "조치: 현재 상품은 확인 필요로 남기고 다음 상품으로 이동합니다.\n\n"
                                )
                                self.automation_signals.task_status.emit(index, "썸네일 실패 - 확인 필요")
                                continue
                            self.automation_signals.result.emit(
                                f"## {index + 1}번 URL 썸네일 재생성 완료\n"
                                f"URL: {url}\n"
                                f"저장: {saved_path or '-'}\n"
                                f"생성 썸네일: {len(thumbnail_result.paths)}/{REQUIRED_THUMBNAIL_IMAGE_COUNT}장\n\n"
                            )
                            self.automation_signals.task_status.emit(index, "완료")
                            continue
                        product = self._scrape_product_page(
                            p,
                            index,
                            url,
                            run_stamp,
                            browser_context=context,
                            secondary_url=secondary_url,
                        )
                        attachment_paths = self._prepare_gpt_attachment_images(product, run_stamp)
                        if attachment_paths:
                            logo_check_status = self._run_brand_logo_reference_check(page, product, attachment_paths)
                            self.automation_signals.status.emit(
                                f"{index + 1}번 URL 상품 이미지 {len(attachment_paths)}장 첨부, 로고 검수 {logo_check_status or 'SKIP'} 후 GPT 섹션 기획 생성 중..."
                            )
                        else:
                            self.automation_signals.status.emit(
                                f"{index + 1}번 URL 첨부할 상품 이미지가 없어 URL만 GPT에 전송 중..."
                            )
                        prompt = self._build_gpt_section_plan_request(product)
                        result_text = ""
                        sections: list[SectionPlan] = []
                        gpt_plan_errors: list[str] = []
                        latest_failed_gpt_text = ""
                        existing_result_text = self._load_existing_section_plan_text(product, prompt)
                        if existing_result_text:
                            try:
                                existing_sections = self._section_plans_from_gpt(existing_result_text, product)
                                if self._section_plan_set_is_clean(existing_sections):
                                    result_text = existing_result_text.strip()
                                    sections = existing_sections
                                    self.automation_signals.task_status.emit(index, "기존 GPT 기획 재사용")
                                    self.automation_signals.result.emit(
                                        f"## {index + 1}번 URL 기존 GPT 기획 재사용\n"
                                        f"URL: {url}\n"
                                        "result.md/metadata.json에서 깨끗한 섹션 기획을 확인해 재기획 없이 진행합니다.\n\n"
                                    )
                            except Exception as exc:
                                gpt_plan_errors.append(f"기존 GPT 기획 재사용 실패: {self._compact_error_text(str(exc), 220)}")
                                try:
                                    partial_sections = self._section_plans_from_saved_raw_gpt_text(existing_result_text, product)
                                except Exception:
                                    partial_sections = []
                                if partial_sections:
                                    result_text = existing_result_text.strip()
                                    latest_failed_gpt_text = result_text
                                    self.automation_signals.task_status.emit(index, "기존 GPT 기획 일부 확인")
                                    self.automation_signals.result.emit(
                                        f"## {index + 1}번 URL 기존 GPT 기획 일부 확인\n"
                                        f"URL: {url}\n"
                                        f"확인 섹션: {len(partial_sections)}/{REQUIRED_SECTION_IMAGE_COUNT}개\n"
                                        "부족한 섹션은 같은 ChatGPT 대화에서 이어받은 뒤 이미지 생성 단계로 진행합니다.\n\n"
                                    )
                        if len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
                            self._raise_if_user_requested_stop_or_skip()
                            try:
                                self.automation_signals.task_status.emit(index, "GPT 기획 요청")
                                page = self._ensure_chatgpt_section_planner_page_alive(context, page)
                                if len(sections) < REQUIRED_SECTION_IMAGE_COUNT and latest_failed_gpt_text:
                                    try:
                                        partial_sections = self._section_plans_from_saved_raw_gpt_text(latest_failed_gpt_text, product)
                                    except Exception:
                                        partial_sections = []
                                    if partial_sections:
                                        recovered_text, recovered_sections, completed_from_gpt = self._recover_partial_gpt_section_plan(
                                            page,
                                            product,
                                            latest_failed_gpt_text,
                                            partial_sections,
                                        )
                                        if recovered_sections:
                                            result_text = recovered_text
                                            sections = recovered_sections
                                            status_label = "GPT 기획 이어받기 완료" if completed_from_gpt else "GPT 기획 이어받기 보강"
                                            self.automation_signals.task_status.emit(index, status_label)
                                            self.automation_signals.result.emit(
                                                f"## {index + 1}번 URL {status_label}\n"
                                                f"URL: {url}\n"
                                                f"확인 섹션: {min(len(sections), REQUIRED_SECTION_IMAGE_COUNT)}/{REQUIRED_SECTION_IMAGE_COUNT}개\n"
                                                "부족했던 섹션을 같은 ChatGPT 대화에서 이어받아 섹션 1 이미지 생성 단계로 진행합니다.\n\n"
                                            )
                                reusable_before_submit = self._find_reusable_gpt_plan_on_page(page, prompt, product)
                                if reusable_before_submit:
                                    reusable_sections = self._section_plans_from_gpt(reusable_before_submit, product)
                                    if self._section_plan_set_is_clean(reusable_sections):
                                        result_text = reusable_before_submit.strip()
                                        sections = reusable_sections
                                        self.automation_signals.task_status.emit(index, "GPT 기획 재사용")
                                        self.automation_signals.result.emit(
                                            f"## {index + 1}번 URL GPT 기획 화면 재사용\n"
                                            f"URL: {url}\n"
                                            "이미 화면에 완성된 섹션 기획이 있어 재전송 없이 그대로 이미지 생성 단계로 진행합니다.\n\n"
                                        )
                                if len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
                                    attempt_text = self._submit_section_plan_request(
                                        page,
                                        prompt,
                                        attachment_paths=attachment_paths,
                                        product=product,
                                    )
                                    latest_failed_gpt_text = attempt_text.strip()
                                    try:
                                        attempt_sections = self._section_plans_from_gpt(attempt_text, product)
                                    except Exception as parse_exc:
                                        partial_sections = self._section_plans_from_saved_raw_gpt_text(attempt_text, product)
                                        if not partial_sections:
                                            raise parse_exc
                                        result_text, sections, completed_from_gpt = self._recover_partial_gpt_section_plan(
                                            page,
                                            product,
                                            attempt_text,
                                            partial_sections,
                                        )
                                        status_label = "GPT 기획 이어받기 완료" if completed_from_gpt else "GPT 기획 이어받기 보강"
                                        self.automation_signals.task_status.emit(index, status_label)
                                        self.automation_signals.result.emit(
                                            f"## {index + 1}번 URL {status_label}\n"
                                            f"URL: {url}\n"
                                            f"확인 섹션: {min(len(sections), REQUIRED_SECTION_IMAGE_COUNT)}/{REQUIRED_SECTION_IMAGE_COUNT}개\n"
                                            "부족했던 섹션을 같은 ChatGPT 대화에서 이어받아 섹션 1 이미지 생성 단계로 진행합니다.\n\n"
                                        )
                                    else:
                                        if self._section_plan_set_is_clean(attempt_sections):
                                            result_text = attempt_text.strip()
                                            sections = attempt_sections
                                        else:
                                            partial_sections = self._section_plans_from_saved_raw_gpt_text(attempt_text, product)
                                            if partial_sections:
                                                result_text, sections, completed_from_gpt = self._recover_partial_gpt_section_plan(
                                                    page,
                                                    product,
                                                    attempt_text,
                                                    partial_sections,
                                                )
                                                status_label = "GPT 기획 이어받기 완료" if completed_from_gpt else "GPT 기획 이어받기 보강"
                                                self.automation_signals.task_status.emit(index, status_label)
                                                self.automation_signals.result.emit(
                                                    f"## {index + 1}번 URL {status_label}\n"
                                                    f"URL: {url}\n"
                                                    f"확인 섹션: {min(len(sections), REQUIRED_SECTION_IMAGE_COUNT)}/{REQUIRED_SECTION_IMAGE_COUNT}개\n"
                                                    "부족했던 섹션을 같은 ChatGPT 대화에서 이어받아 섹션 1 이미지 생성 단계로 진행합니다.\n\n"
                                                )
                                            else:
                                                gpt_plan_errors.append("GPT 섹션 기획은 받았지만 필수 10개 섹션 또는 정리된 문구 조건을 통과하지 못했습니다.")
                            except (AutomationStopRequested, AutomationSkipRequested):
                                raise
                            except Exception as exc:
                                gpt_plan_errors.append(self._compact_error_text(str(exc), 360))
                                try:
                                    latest_text, _ = self._latest_gpt_text(page)
                                    if latest_text:
                                        latest_failed_gpt_text = latest_text.strip()
                                        if self._can_reuse_existing_gpt_plan(latest_failed_gpt_text, prompt):
                                            try:
                                                latest_sections = self._section_plans_from_gpt(latest_failed_gpt_text, product)
                                                if self._section_plan_set_is_clean(latest_sections):
                                                    result_text = latest_failed_gpt_text
                                                    sections = latest_sections
                                                    self.automation_signals.task_status.emit(index, "GPT 기획 재사용")
                                                    self.automation_signals.result.emit(
                                                        f"## {index + 1}번 URL GPT 기획 화면 재사용\n"
                                                        f"URL: {url}\n"
                                                        "최근 응답이 늦게 완성되어 새로 묻지 않고 화면의 섹션 기획을 그대로 사용합니다.\n\n"
                                                    )
                                            except Exception:
                                                pass
                                except Exception:
                                    pass
                            if len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
                                try:
                                    reusable_text = self._find_reusable_gpt_plan_on_page(page, prompt, product)
                                    if reusable_text:
                                        reusable_sections = self._section_plans_from_gpt(reusable_text, product)
                                        if self._section_plan_set_is_clean(reusable_sections):
                                            result_text = reusable_text.strip()
                                            sections = reusable_sections
                                            self.automation_signals.task_status.emit(index, "GPT 기획 재사용")
                                            self.automation_signals.result.emit(
                                                f"## {index + 1}번 URL GPT 기획 화면 재사용\n"
                                                f"URL: {url}\n"
                                                "이전 정상 기획을 찾아 재기획 없이 이어서 진행합니다.\n\n"
                                            )
                                except Exception:
                                    pass

                        saved_raw_section_text = ""
                        if len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
                            recovery_candidates = [
                                latest_failed_gpt_text,
                                self._load_existing_section_plan_text(product, prompt),
                            ]
                            try:
                                latest_text, _ = self._latest_gpt_text(page)
                                if latest_text:
                                    recovery_candidates.insert(0, latest_text.strip())
                            except Exception:
                                pass
                            for recovery_text in recovery_candidates:
                                recovery_text = (recovery_text or "").strip()
                                if not recovery_text:
                                    continue
                                if not self._can_reuse_existing_gpt_plan(recovery_text, prompt):
                                    continue
                                if not saved_raw_section_text and self._gpt_text_has_any_section_heading(recovery_text):
                                    saved_raw_section_text = recovery_text
                                try:
                                    recovery_sections = self._section_plans_from_gpt(recovery_text, product)
                                except Exception:
                                    continue
                                if self._section_plan_set_is_clean(recovery_sections, recovery_text):
                                    result_text = recovery_text
                                    sections = recovery_sections
                                    self.automation_signals.task_status.emit(index, "GPT 기획 재사용")
                                    self.automation_signals.result.emit(
                                        f"## {index + 1}번 URL GPT 기획 복구 재사용\n"
                                        f"URL: {url}\n"
                                        "실패로 저장되기 전 정상 섹션 기획을 다시 확인해 이미지 생성 단계로 진행합니다.\n\n"
                                    )
                                    break

                        if len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
                            if saved_raw_section_text:
                                fallback_sections: list[SectionPlan] = []
                                try:
                                    fallback_sections = self._section_plans_from_structured_gpt_text(saved_raw_section_text, product)
                                except Exception:
                                    fallback_sections = []
                                if len(fallback_sections) < REQUIRED_SECTION_IMAGE_COUNT:
                                    fallback_sections = self._section_plans_from_saved_raw_gpt_text(saved_raw_section_text, product)
                                if fallback_sections:
                                    result_text, sections, completed_from_gpt = self._recover_partial_gpt_section_plan(
                                        page,
                                        product,
                                        saved_raw_section_text,
                                        fallback_sections,
                                    )
                                    status_label = "GPT 기획 원문 이어받기 완료" if completed_from_gpt else "GPT 기획 원문 보강"
                                    self.automation_signals.task_status.emit(index, status_label)
                                    self.automation_signals.result.emit(
                                        f"## {index + 1}번 URL {status_label}\n"
                                        f"URL: {url}\n"
                                        "저장된 섹션 원문을 같은 ChatGPT 대화에서 이어받아 섹션 1 이미지 생성 단계로 자동 진행합니다.\n\n"
                                    )
                                else:
                                    self.automation_signals.result.emit(
                                        f"## {index + 1}번 URL GPT 기획 원문 파싱 실패\n"
                                        f"URL: {url}\n"
                                        "저장 원문은 보존하고, 상품 정보 기준 보강 섹션 10개로 완료 흐름을 계속합니다.\n\n"
                                    )
                        if len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
                            sections = self._build_product_fallback_sections(product)
                            result_text = self._section_plans_to_result_text(sections)
                            self.automation_signals.result.emit(
                                f"## {index + 1}번 URL 상품 정보 기준 섹션 보강\n"
                                f"URL: {url}\n"
                                "GPT 기획 응답이 없거나 파싱되지 않아도 실패로 넘기지 않고, 상품 원본 정보 기준 섹션 10개로 상세페이지 생성을 계속합니다.\n"
                                f"오류 이력: {' / '.join(gpt_plan_errors[-3:]) or '-'}\n\n"
                            )
                            self.automation_signals.task_status.emit(index, "기획 보강 후 진행")

                        sections = self._prepare_detail_sections_for_generation(product, sections)
                        result_text = self._remove_review_points_from_result_text(result_text)
                        if not resume_stage:
                            image_page = self._open_fresh_chatgpt_image_generation_page(context, image_page)
                        self.automation_signals.task_status.emit(index, "상품이미지 렌더중")
                        self.automation_signals.status.emit(f"{index + 1}번 URL GPT 섹션 기획 기반 상세페이지 렌더 준비 중...")
                        visual_paths: list[Path] = []
                        image_generation_errors: list[str] = []
                        visual_dir = product.output_dir / "generated_visuals"
                        image_attempt = 0
                        section_attempt_counts: dict[int, int] = {}
                        skipped_section_indexes: set[int] = set()
                        target_section_count = len(sections)
                        # If ChatGPT exits without producing a usable image, resume from the
                        # same missing section and retry up to the configured F5 limit.
                        section_retry_limit = CHATGPT_SECTION_IMAGE_RELOAD_RETRY_LIMIT
                        resume_from_section = resume_number if resume_stage == "section" else None
                        if resume_stage in {"merge", "thumbnail"}:
                            existing_visual_paths = self._collect_section_visual_paths(product, sections, visual_dir)
                            if len(existing_visual_paths) >= target_section_count:
                                visual_paths = existing_visual_paths
                            else:
                                resume_from_section = self._first_missing_section_visual_index(sections, visual_dir, skipped_section_indexes)
                        while len(visual_paths) < target_section_count:
                            self._raise_if_user_requested_stop_or_skip()
                            next_missing_section = self._first_missing_section_visual_index(sections, visual_dir, skipped_section_indexes)
                            if next_missing_section is None:
                                visual_paths = self._collect_section_visual_paths(product, sections, visual_dir)
                                break
                            if resume_from_section is None or resume_from_section < next_missing_section:
                                resume_from_section = next_missing_section
                            attempt_section = int(resume_from_section or next_missing_section or 0)
                            active_attempt_section = attempt_section
                            image_attempt = section_attempt_counts.get(attempt_section, 0) + 1
                            section_attempt_counts[attempt_section] = image_attempt
                            try:
                                image_page = self._ensure_chatgpt_image_generation_page(context, image_page or page)
                                self.automation_signals.task_status.emit(index, f"섹션 {resume_from_section}부터 생성중")
                                visual_paths = self._generate_section_visuals(
                                    product,
                                    sections,
                                    run_stamp,
                                    page=image_page,
                                    resume_from_section=resume_from_section,
                                    progress_callback=lambda done, total, job_index=index: (
                                        self.automation_signals.task_status.emit(job_index, f"ChatGPT 이미지 생성중 {done}/{total}"),
                                        self.automation_signals.status.emit(f"{job_index + 1}번 URL 섹션 이미지 생성 중... {done}/{total}"),
                                    ),
                                )
                            except (AutomationStopRequested, AutomationSkipRequested):
                                raise
                            except Exception as exc:
                                if self._is_browser_disconnected_error(exc):
                                    raise AutomationBrowserDisconnected(str(exc)) from exc
                                visual_paths = self._collect_section_visual_paths(product, sections, visual_dir)
                                resume_from_section = self._first_missing_section_visual_index(sections, visual_dir, skipped_section_indexes)
                                if resume_from_section is None:
                                    break
                                attempt_section = int(resume_from_section)
                                if attempt_section == active_attempt_section:
                                    image_attempt = section_attempt_counts.get(attempt_section, image_attempt)
                                else:
                                    image_attempt = section_attempt_counts.get(attempt_section, 0) + 1
                                section_attempt_counts[attempt_section] = image_attempt
                                image_generation_errors.append(
                                    f"섹션 {attempt_section} {image_attempt}회: {self._compact_error_text(str(exc), 260)}"
                                )
                                self.automation_signals.result.emit(
                                    f"## {index + 1}번 URL 섹션 이미지 실패 기록 {image_attempt}회\n"
                                    f"URL: {url}\n"
                                    f"현재 생성: {len(visual_paths)}/{target_section_count}장\n"
                                    f"다음 시작: 섹션 {resume_from_section}\n"
                                    f"오류: {self._compact_error_text(str(exc), 260)}\n\n"
                                )
                                if image_attempt >= section_retry_limit:
                                    self.automation_signals.result.emit(
                                        f"## {index + 1}번 URL 섹션 {attempt_section} 3회 실패 후 현재 상품 중지\n"
                                        f"URL: {url}\n"
                                        f"완료 섹션: {len(visual_paths)}/{target_section_count}장\n\n"
                                    )
                                    break
                                self.automation_signals.status.emit(
                                    f"{index + 1}번 URL 섹션 {resume_from_section} 이미지 실패, "
                                    f"새로고침 후 재시도 {image_attempt}/{section_retry_limit}"
                                )
                                try:
                                    image_page = self._ensure_chatgpt_image_generation_page(context, image_page or page)
                                    self._reload_chatgpt_for_section_image_retry(image_page, resume_from_section, image_attempt)
                                except Exception as reload_exc:
                                    if self._is_browser_disconnected_error(reload_exc):
                                        raise AutomationBrowserDisconnected(str(reload_exc)) from reload_exc
                                    image_generation_errors.append(
                                        f"{image_attempt}회 새로고침 실패: {self._compact_error_text(str(reload_exc), 260)}"
                                    )
                                    break
                                continue
                            visual_paths = self._collect_section_visual_paths(product, sections, visual_dir)
                            if len(visual_paths) >= target_section_count:
                                break
                            resume_from_section = self._first_missing_section_visual_index(sections, visual_dir, skipped_section_indexes)
                            if resume_from_section is None:
                                break
                            attempt_section = int(resume_from_section)
                            image_attempt = section_attempt_counts.get(attempt_section, 0) + 1
                            section_attempt_counts[attempt_section] = image_attempt
                            image_generation_errors.append(
                                f"섹션 {attempt_section} {image_attempt}회: 생성 이미지 {len(visual_paths)}/{target_section_count}장"
                            )
                            self.automation_signals.result.emit(
                                f"## {index + 1}번 URL 섹션 이미지 수량 부족 기록 {image_attempt}회\n"
                                f"URL: {url}\n"
                                f"현재 생성: {len(visual_paths)}/{target_section_count}장\n\n"
                                f"다음 시작: 섹션 {resume_from_section}\n\n"
                            )
                            if image_attempt >= section_retry_limit:
                                self.automation_signals.result.emit(
                                    f"## {index + 1}번 URL 섹션 {attempt_section} 3회 수량 부족 후 현재 상품 중지\n"
                                    f"URL: {url}\n"
                                    f"완료 섹션: {len(visual_paths)}/{target_section_count}장\n\n"
                                )
                                break
                            self.automation_signals.status.emit(
                                f"{index + 1}번 URL 섹션 {resume_from_section} 이미지 수량 부족, "
                                f"새로고침 후 재시도 {image_attempt}/{section_retry_limit}"
                            )
                            try:
                                image_page = self._ensure_chatgpt_image_generation_page(context, image_page or page)
                                self._reload_chatgpt_for_section_image_retry(image_page, resume_from_section, image_attempt)
                            except Exception as reload_exc:
                                if self._is_browser_disconnected_error(reload_exc):
                                    raise AutomationBrowserDisconnected(str(reload_exc)) from reload_exc
                                image_generation_errors.append(
                                    f"{image_attempt}회 새로고침 실패: {self._compact_error_text(str(reload_exc), 260)}"
                                )
                                break
                            continue

                        if len(visual_paths) < target_section_count:
                            saved_path = self._save_failed_result(
                                product,
                                prompt,
                                "ChatGPT 실제 섹션 이미지 생성 미완료: 섹션 이미지 "
                                f"{len(visual_paths)}/{target_section_count}장\n"
                                + "\n".join(image_generation_errors),
                                run_stamp,
                                result_text,
                            )
                            self.automation_signals.result.emit(
                                f"## {index + 1}번 URL ChatGPT 섹션 이미지 생성 미완료\n"
                                f"URL: {url}\n"
                                f"저장: {saved_path}\n"
                                f"생성 이미지: {len(visual_paths)}/{target_section_count}장\n"
                                f"오류 이력: {' / '.join(image_generation_errors[-3:]) or '-'}\n"
                                "완료 폴더에는 저장하지 않습니다. 완료는 ChatGPT 실제 생성 섹션 이미지가 모두 있을 때만 처리하고, 다음 상품으로 이동합니다.\n\n"
                            )
                            self.automation_signals.task_status.emit(index, "이미지 실패 - 실제 생성 미완료")
                            continue

                        self.automation_signals.status.emit(f"{index + 1}번 URL 섹션 PNG 합본 중...")
                        try:
                            visual_model = (
                                CHATGPT_WEB_IMAGE_MODEL
                                if visual_paths and page is not None and ENABLE_CHATGPT_WEB_IMAGE_GENERATION
                                else LATEST_CODEX_IMAGE_MODEL
                            )
                            render_result = self._render_detail_page(
                                product,
                                sections,
                                visual_paths,
                                generated_image_model=visual_model,
                            )
                        except Exception as exc:
                            saved_path = self._save_failed_result(
                                product,
                                prompt,
                                f"렌더 실패: {exc}",
                                run_stamp,
                                result_text,
                            )
                            self.automation_signals.result.emit(
                                f"## {index + 1}번 URL 렌더 실패\nURL: {url}\n저장: {saved_path}\n오류: {exc}\n\n"
                            )
                            self.automation_signals.task_status.emit(index, "렌더 실패")
                            continue

                        self.automation_signals.task_status.emit(index, "썸네일 생성중 0/5")
                        self.automation_signals.status.emit(f"{index + 1}번 URL 썸네일 5장 생성 준비 중...")
                        thumbnail_result = ThumbnailResult(paths=[], prompt_paths=[], image_model=CHATGPT_WEB_IMAGE_MODEL)
                        saved_path = None
                        thumbnail_error = ""
                        thumbnail_stopped = False
                        job_attempt = 0
                        thumbnail_job_limit = 1
                        resume_from_thumbnail = resume_number if resume_stage == "thumbnail" else None
                        while (
                            not self._thumbnail_result_complete(thumbnail_result)
                            and job_attempt < thumbnail_job_limit
                        ):
                            self._raise_if_user_requested_stop_or_skip()
                            job_attempt += 1
                            try:
                                image_page = self._ensure_chatgpt_image_generation_page(context, image_page or page)
                                self.automation_signals.task_status.emit(index, "썸네일 생성중")
                                thumbnail_result = self._generate_thumbnail_images(
                                    product,
                                    sections,
                                    run_stamp,
                                    page=image_page,
                                    resume_from_thumbnail=resume_from_thumbnail,
                                    progress_callback=lambda done, total, job_index=index: (
                                        self.automation_signals.task_status.emit(job_index, f"썸네일 생성중 {done}/{total}"),
                                        self.automation_signals.status.emit(f"{job_index + 1}번 URL 썸네일 생성 중... {done}/{total}"),
                                    ),
                                )
                                resume_from_thumbnail = None
                            except (AutomationStopRequested, AutomationSkipRequested):
                                raise
                            except Exception as exc:
                                if self._is_browser_disconnected_error(exc):
                                    raise AutomationBrowserDisconnected(str(exc)) from exc
                                thumbnail_error = str(exc)
                                thumbnail_stopped = isinstance(exc, ThumbnailGenerationFailed)
                                thumbnail_result = self._current_thumbnail_result(product)
                                saved_path = self._save_detail_page_result(
                                    product,
                                    prompt,
                                    result_text,
                                    sections,
                                    render_result,
                                    run_stamp,
                                    thumbnail_result,
                                )
                                self.automation_signals.result.emit(
                                    f"## {index + 1}번 URL "
                                    f"{'썸네일 생성 중단' if thumbnail_stopped else f'썸네일 재시도 {job_attempt}회'}\n"
                                    f"URL: {url}\n"
                                    f"저장: {saved_path}\n"
                                    f"오류: {exc}\n"
                                    f"현재 썸네일: {len(thumbnail_result.paths)}/{REQUIRED_THUMBNAIL_IMAGE_COUNT}장\n\n"
                                )
                                if thumbnail_stopped:
                                    self.automation_signals.task_status.emit(index, "썸네일 실패")
                                    break
                                try:
                                    if image_page is not None:
                                        self._click_chatgpt_retry_button(image_page, timeout_ms=12000)
                                except Exception:
                                    pass
                                if image_page is not None:
                                    image_page.wait_for_timeout(5000)
                                continue
                            if self._thumbnail_result_complete(thumbnail_result):
                                break
                            saved_path = self._save_detail_page_result(
                                product,
                                prompt,
                                result_text,
                                sections,
                                render_result,
                                run_stamp,
                                thumbnail_result,
                            )
                            self.automation_signals.result.emit(
                                f"## {index + 1}번 URL 썸네일 수량 부족\n"
                                f"URL: {url}\n"
                                f"저장: {saved_path}\n"
                                f"생성 썸네일: {len(thumbnail_result.paths)}/{REQUIRED_THUMBNAIL_IMAGE_COUNT}장\n\n"
                            )
                            if image_page is not None:
                                image_page.wait_for_timeout(5000)
                        if not self._thumbnail_result_complete(thumbnail_result):
                            saved_path = self._save_detail_page_result(
                                product,
                                prompt,
                                result_text,
                                sections,
                                render_result,
                                run_stamp,
                                thumbnail_result,
                            )
                            self.automation_signals.result.emit(
                                f"## {index + 1}번 URL 썸네일 생성 미완료\n"
                                f"URL: {url}\n"
                                f"저장: {saved_path}\n"
                                f"생성 썸네일: {len(thumbnail_result.paths)}/{REQUIRED_THUMBNAIL_IMAGE_COUNT}장\n"
                                f"마지막 오류: {thumbnail_error or '-'}\n"
                                f"시도: {job_attempt}/{thumbnail_job_limit}회\n"
                                "조치: 현재 상품은 확인 필요로 남기고 다음 상품으로 이동합니다.\n\n"
                            )
                            self.automation_signals.task_status.emit(
                                index,
                                "썸네일 실패 - 확인 필요" if thumbnail_stopped else "썸네일 미완료 - 확인 필요",
                            )
                            continue

                        saved_path = self._save_detail_page_result(
                            product,
                            prompt,
                            result_text,
                            sections,
                            render_result,
                            run_stamp,
                            thumbnail_result,
                        )
                        image_note = "\n".join(f"- 섹션: {path}" for path in render_result.section_paths)
                        image_note += f"\n- 전체: {render_result.detail_page_path}"
                        image_note += "\n" + "\n".join(f"- 썸네일 {thumb_index}: {path}" for thumb_index, path in enumerate(thumbnail_result.paths, start=1))
                        output_complete = self._task_output_complete(index, url, secondary_url)
                        task_status = "완료" if output_complete else "완료 검증 실패"
                        summary = (
                            f"## {index + 1}번 URL 상세페이지 렌더 완료\n"
                            f"URL: {url}\n"
                            f"1688 URL: {secondary_url or '-'}\n"
                            f"저장: {saved_path}\n"
                            f"저장된 섹션 이미지: {len(render_result.section_paths)}장\n"
                            f"저장된 썸네일 이미지: {len(thumbnail_result.paths)}장\n"
                            f"{image_note}\n\n"
                            f"{result_text}\n\n"
                        )
                        self.automation_signals.result.emit(summary)
                        self.automation_signals.task_status.emit(index, task_status)
                        if not output_complete:
                            continue
                    except AutomationSkipRequested as exc:
                        self.automation_skip_requested = False
                        saved_path = self._save_url_failure_result(index, url, f"사용자 스킵: {exc}")
                        self.automation_signals.result.emit(
                            f"## {index + 1}번 URL 사용자 스킵\nURL: {url}\n저장: {saved_path}\n\n"
                        )
                        self.automation_signals.task_status.emit(index, "스킵")
                        continue
                    except AutomationStopRequested as exc:
                        self.automation_signals.result.emit(
                            f"## {index + 1}번 URL 작업 중지\nURL: {url}\n사유: {exc}\n\n"
                        )
                        self.automation_signals.task_status.emit(index, "대기")
                        break
                    except AutomationBrowserDisconnected as exc:
                        self.automation_stop_requested = True
                        message = self._compact_error_text(str(exc), 260)
                        self.automation_signals.result.emit(
                            f"## {index + 1}번 URL 자동화 브라우저 연결 끊김\n"
                            f"URL: {url}\n"
                            f"사유: {message}\n\n"
                            "현재 상품은 대기 상태로 되돌리고, 남은 상품은 실패 처리하지 않고 중지합니다.\n\n"
                        )
                        self.automation_signals.task_status.emit(index, "대기")
                        break
                    except Exception as exc:
                        if self._is_browser_disconnected_error(exc):
                            self.automation_stop_requested = True
                            message = self._compact_error_text(str(exc), 260)
                            self.automation_signals.result.emit(
                                f"## {index + 1}번 URL 자동화 브라우저 연결 끊김\n"
                                f"URL: {url}\n"
                                f"사유: {message}\n\n"
                                "현재 상품은 대기 상태로 되돌리고, 남은 상품은 실패 처리하지 않고 중지합니다.\n\n"
                            )
                            self.automation_signals.task_status.emit(index, "대기")
                            break
                        saved_path = self._save_url_failure_result(index, url, f"상품 추출/작업 실패: {exc}")
                        self.automation_signals.result.emit(
                            f"## {index + 1}번 URL 작업 실패\nURL: {url}\n저장: {saved_path}\n오류: {exc}\n\n"
                        )
                        self.automation_signals.task_status.emit(index, "렌더 실패")
                if self.automation_stop_requested:
                    self.automation_signals.status.emit("사용자 요청으로 자동화를 중지했습니다.")
                else:
                    self.automation_signals.status.emit("URL 분석, ChatGPT 이미지 생성, PNG 합본 처리가 끝났습니다.")
        except Exception as exc:
            self.automation_signals.status.emit(f"GPT 자동 분석 실패: {exc}")
        finally:
            self.automation_signals.finished.emit()

    def _run_chatgpt_login_worker(self, email: str, password: str) -> None:
        page = None
        try:
            self.automation_signals.login_status.emit("자동화 브라우저 연결 중...")
            self._ensure_cdp_browser()
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = self._existing_chatgpt_page(context)
                if page is None:
                    raise RuntimeError("열려 있는 ChatGPT 탭을 찾지 못했습니다. 1. 로그인을 먼저 눌러 Chrome을 여세요.")
                self._accept_chatgpt_cookies(page)
                if not self._page_needs_login(page):
                    page.bring_to_front()
                    self.automation_signals.login_status.emit("기존 ChatGPT 탭 로그인 확인 완료. 현재 탭/모델을 그대로 사용합니다.")
                    return

                page.bring_to_front()
                self.automation_signals.login_status.emit(
                    "기존 ChatGPT 탭에서 직접 로그인하세요. 자동으로 새 탭/로그인 페이지를 열지 않습니다."
                )
        except Exception as exc:
            self.automation_signals.login_status.emit(
                f"ChatGPT 로그인 확인 실패: {exc}"
            )
        finally:
            self.automation_signals.login_finished.emit()

    def _run_login_check_worker(self) -> None:
        try:
            self._ensure_cdp_browser()
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = self._existing_chatgpt_page(context)
                if page is None:
                    raise RuntimeError("열려 있는 ChatGPT 탭을 찾지 못했습니다. 1. 로그인을 눌러 Chrome을 여세요.")
                self._accept_chatgpt_cookies(page)
                if self._page_needs_login(page):
                    page.bring_to_front()
                    self.automation_signals.login_status.emit(
                        "아직 로그인 전입니다. 열린 ChatGPT 탭에서 직접 로그인하세요."
                    )
                else:
                    page.bring_to_front()
                    self.automation_signals.login_status.emit("로그인 확인 완료. 현재 ChatGPT 탭/모델을 그대로 사용합니다.")
        except Exception as exc:
            self.automation_signals.login_status.emit(f"로그인 상태 확인 실패: {exc}")
        finally:
            self.automation_signals.login_finished.emit()

    def _open_url_in_automation_browser(self, url: str, status_message: str = "") -> None:
        self.statusBar().showMessage("자동화 브라우저로 URL을 여는 중...")
        thread = threading.Thread(
            target=self._open_url_in_automation_browser_worker,
            args=(url, status_message),
            daemon=True,
        )
        thread.start()

    def _open_url_in_automation_browser_worker(self, url: str, status_message: str = "") -> None:
        try:
            self._ensure_cdp_browser()
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                if self._is_chatgpt_url(url):
                    page = self._existing_chatgpt_page(context)
                    if page is None:
                        page = context.new_page()
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                else:
                    page = self._existing_page_for_url(context, url)
                    if page is None:
                        page = context.new_page()
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    except Exception:
                        page.goto(url, wait_until="load", timeout=60000)
                page.bring_to_front()
                self.automation_signals.status.emit(status_message or f"자동화 브라우저에서 URL을 열었습니다: {url}")
        except Exception as exc:
            self.automation_signals.status.emit(f"자동화 브라우저 URL 열기 실패: {exc}")

    def _is_chatgpt_url(self, url: str) -> bool:
        host = urllib.parse.urlparse(url or "").netloc.lower()
        return host.endswith("chatgpt.com")

    def _existing_page_for_url(self, context, url: str):
        expected_host = urllib.parse.urlparse(url or "").netloc.lower()
        if not expected_host:
            return None
        expected_root = ".".join(expected_host.split(".")[-2:])
        for page in context.pages:
            try:
                host = urllib.parse.urlparse(page.url or "").netloc.lower()
            except Exception:
                continue
            if not host:
                continue
            root = ".".join(host.split(".")[-2:])
            if root == expected_root:
                return page
        return None

    def _ensure_cdp_browser(self) -> None:
        if self._is_cdp_alive():
            return
        browser_path = self._system_browser_executable_path()
        if not browser_path:
            raise RuntimeError("Chrome 또는 Edge 실행 파일을 찾지 못했습니다.")
        profile_dir = ROOT_DIR.parent / "debug" / "chrome_cdp_profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(
            [
                str(browser_path),
                "--remote-debugging-port=9222",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                GPT_URL,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(20):
            if self._is_cdp_alive():
                return
            time.sleep(0.5)
        raise RuntimeError("자동화 브라우저 CDP 연결을 열지 못했습니다.")

    def _system_browser_executable_path(self) -> Path | None:
        candidates = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ]
        return next((path for path in candidates if path.exists()), None)

    def _is_cdp_alive(self) -> bool:
        try:
            with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def _is_browser_disconnected_error(self, exc: BaseException) -> bool:
        text = str(exc).lower()
        markers = (
            "target page, context or browser has been closed",
            "browsercontext.new_page",
            "connect econnrefused 127.0.0.1:9222",
            "connection refused",
            "browser has been closed",
            "context has been closed",
            "target page has been closed",
        )
        return any(marker in text for marker in markers)

    def _existing_chatgpt_page(self, context, page=None):
        if page is not None:
            try:
                if not page.is_closed() and "chatgpt.com" in (page.url or "").lower():
                    return page
            except Exception:
                pass
        for candidate in reversed(context.pages):
            try:
                if not candidate.is_closed() and "chatgpt.com" in (candidate.url or "").lower():
                    return candidate
            except Exception:
                continue
        return None

    def _ensure_gpt_page_alive(self, context, page=None):
        page = self._existing_chatgpt_page(context, page)
        if page is None:
            raise RuntimeError("열려 있는 ChatGPT 탭을 찾지 못했습니다. 기존 탭을 열고 모델을 맞춘 뒤 다시 실행하세요.")
        self._accept_chatgpt_cookies(page)
        if self._page_needs_login(page):
            page.bring_to_front()
            raise RuntimeError("ChatGPT 로그인이 필요합니다.")
        page.bring_to_front()
        return page

    def _is_chatgpt_encoding_error_page(self, page) -> bool:
        try:
            title = page.title()
            if "메시지 인코딩 오류" in title:
                return True
        except Exception:
            pass
        try:
            body_text = page.locator("body").inner_text(timeout=800)
        except Exception:
            return False
        body_head = body_text[:2500]
        return "메시지가 문자 인코딩이 깨져서" in body_head or "????" in body_head

    def _ensure_chatgpt_section_planner_page_alive(self, context, page=None):
        candidates = []
        if page is not None:
            candidates.append(page)
        candidates.extend(reversed(context.pages))
        for candidate in candidates:
            try:
                if (
                    candidate is not None
                    and not candidate.is_closed()
                    and self._is_chatgpt_section_planner_url(candidate.url)
                    and not self._is_chatgpt_encoding_error_page(candidate)
                ):
                    self._accept_chatgpt_cookies(candidate)
                    if not self._page_needs_login(candidate):
                        candidate.bring_to_front()
                        return candidate
            except Exception:
                continue

        target_page = page
        try:
            if target_page is None or target_page.is_closed():
                target_page = context.new_page()
        except Exception:
            target_page = context.new_page()
        target_page.goto(GPT_URL, wait_until="domcontentloaded", timeout=60000)
        target_page.wait_for_timeout(5000)
        self._accept_chatgpt_cookies(target_page)
        self._dismiss_chatgpt_blocking_modal(target_page)
        self._force_hide_chatgpt_open_sheets(target_page)
        if self._page_needs_login(target_page):
            target_page.bring_to_front()
            raise RuntimeError("ChatGPT 기획용 커스텀 GPT 로그인이 필요합니다.")
        target_page.bring_to_front()
        return target_page

    def _ensure_chatgpt_image_generation_page(self, context, page=None):
        stored_page = getattr(self, "_chatgpt_image_generation_page", None)
        for candidate in (stored_page, page):
            try:
                if (
                    candidate is not None
                    and not candidate.is_closed()
                    and "chatgpt.com" in (candidate.url or "").lower()
                    and not self._is_chatgpt_section_planner_url(candidate.url)
                    and not self._is_chatgpt_encoding_error_page(candidate)
                ):
                    self._accept_chatgpt_cookies(candidate)
                    _, busy = self._latest_gpt_text(candidate)
                    if not busy and not self._page_needs_login(candidate):
                        candidate.bring_to_front()
                        self._chatgpt_image_generation_page = candidate
                        return candidate
            except Exception:
                continue

        for candidate in reversed(context.pages):
            try:
                if (
                    not candidate.is_closed()
                    and "chatgpt.com" in (candidate.url or "").lower()
                    and not self._is_chatgpt_section_planner_url(candidate.url)
                    and not self._is_chatgpt_encoding_error_page(candidate)
                ):
                    self._accept_chatgpt_cookies(candidate)
                    _, busy = self._latest_gpt_text(candidate)
                    if not busy and not self._page_needs_login(candidate):
                        candidate.bring_to_front()
                        self._chatgpt_image_generation_page = candidate
                        return candidate
            except Exception:
                continue

        image_page = context.new_page()
        image_page.goto(CHATGPT_HOME_URL, wait_until="domcontentloaded", timeout=60000)
        image_page.wait_for_timeout(8000)
        self._accept_chatgpt_cookies(image_page)
        self._dismiss_chatgpt_blocking_modal(image_page)
        self._force_hide_chatgpt_open_sheets(image_page)
        if self._page_needs_login(image_page):
            image_page.bring_to_front()
            raise RuntimeError("ChatGPT 기본 이미지 생성 탭 로그인이 필요합니다.")
        image_page.bring_to_front()
        self._chatgpt_image_generation_page = image_page
        return image_page

    def _open_fresh_chatgpt_image_generation_page(self, context, old_page=None):
        for candidate in (getattr(self, "_chatgpt_image_generation_page", None), old_page):
            try:
                if (
                    candidate is not None
                    and not candidate.is_closed()
                    and "chatgpt.com" in (candidate.url or "").lower()
                    and not self._is_chatgpt_section_planner_url(candidate.url)
                ):
                    candidate.close()
            except Exception:
                pass
        image_page = context.new_page()
        image_page.goto(CHATGPT_HOME_URL, wait_until="domcontentloaded", timeout=60000)
        image_page.wait_for_timeout(8000)
        self._accept_chatgpt_cookies(image_page)
        self._dismiss_chatgpt_blocking_modal(image_page)
        self._force_hide_chatgpt_open_sheets(image_page)
        if self._page_needs_login(image_page):
            image_page.bring_to_front()
            raise RuntimeError("ChatGPT 기본 이미지 생성 탭 로그인이 필요합니다.")
        image_page.bring_to_front()
        self._chatgpt_image_generation_page = image_page
        return image_page

    def _reset_gpt_page_for_url_job(self, context, page=None):
        page = self._ensure_gpt_page_alive(context, page)
        force_new_chat = False
        try:
            self._wait_for_gpt_idle(page, timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS)
        except RuntimeError as exc:
            if not self._is_retryable_section_plan_wait_error(str(exc)):
                raise
            self.automation_signals.status.emit("이전 GPT 응답이 끝나지 않아 새 기획 화면으로 전환합니다.")
            force_new_chat = True
        if force_new_chat:
            page.goto(GPT_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
        self._accept_chatgpt_cookies(page)
        if self._page_needs_login(page):
            page.bring_to_front()
            raise RuntimeError("ChatGPT 로그인이 필요합니다.")
        page.bring_to_front()
        return page

    def _accept_chatgpt_cookies(self, page) -> None:
        for label in ("모두 허용", "Accept all", "Accept All"):
            button = page.get_by_text(label, exact=True)
            try:
                if button.count() > 0:
                    button.first.click(timeout=1500)
                    page.wait_for_timeout(500)
                    return
            except Exception:
                continue

    def _page_needs_login(self, page) -> bool:
        try:
            current_url = (page.url or "").lower()
        except Exception:
            current_url = ""
        if "/auth/login" in current_url or "/login" in current_url:
            return True
        try:
            body = page.locator("body").inner_text(timeout=10000)
        except Exception:
            body = ""
        if self._chatgpt_login_or_upload_blocked_text(body):
            return True
        composer_count = self._composer_count(page)
        login_markers = ["로그인", "Log in", "무료로 회원 가입", "Sign up", "Welcome back"]
        return composer_count == 0 and any(marker in body for marker in login_markers)

    def _chatgpt_login_or_upload_blocked_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", text or "").strip().lower()
        if not normalized:
            return False
        return (
            "로그인하거나 가입" in normalized
            or "무료로 회원 가입" in normalized
            or "chatgpt를 사용해 주셔서 감사합니다" in normalized
            or "파일 및 이미지 업로드" in normalized and "로그인" in normalized
            or "한 번에 최대 0개" in normalized
            or "업로드할 수 없습니다" in normalized and "최대 0개" in normalized
            or "log in or sign up" in normalized
            or "log in to use" in normalized
            or "sign up to use" in normalized
            or "thanks for using chatgpt" in normalized
            or "maximum of 0" in normalized
            or "up to 0" in normalized and "upload" in normalized
        )

    def _fill_chatgpt_login_form(self, page, email: str, password: str) -> None:
        self._click_first_enabled_button(page, ["로그인", "Log in"])
        email_input = self._wait_for_visible_locator(
            page,
            [
                "input[type='email']",
                "input[name='email']",
                "input[name='username']",
                "#email-input",
                "input[autocomplete='username']",
                "input[inputmode='email']",
                "input[placeholder*='Email']",
                "input[placeholder*='이메일']",
                "input:not([type='hidden'])",
            ],
            timeout_seconds=25,
            error_message="ChatGPT 이메일 입력창을 찾지 못했습니다.",
        )
        email_input.click(timeout=5000)
        email_input.fill(email, timeout=10000)
        if not self._click_first_enabled_button(page, ["계속", "Continue", "다음", "Next"]):
            page.keyboard.press("Enter")

        password_input = self._wait_for_visible_locator(
            page,
            [
                "input[type='password']",
                "input[name='password']",
                "#password",
                "#password-input",
                "input[autocomplete='current-password']",
                "input[placeholder*='Password']",
                "input[placeholder*='비밀번호']",
            ],
            timeout_seconds=35,
            error_message="ChatGPT 비밀번호 입력창을 찾지 못했습니다. 소셜 로그인 또는 보안 확인이 필요할 수 있습니다.",
        )
        password_input.click(timeout=5000)
        password_input.fill(password, timeout=10000)
        if not self._click_first_enabled_button(page, ["로그인", "Log in", "계속", "Continue"]):
            page.keyboard.press("Enter")

    def _wait_for_visible_locator(
        self,
        page,
        selectors: list[str],
        timeout_seconds: int,
        error_message: str,
    ):
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            for selector in selectors:
                locator = page.locator(selector)
                try:
                    count = min(locator.count(), 5)
                except Exception:
                    continue
                for index in range(count):
                    candidate = locator.nth(index)
                    try:
                        if candidate.is_visible(timeout=500):
                            return candidate
                    except Exception:
                        continue
            page.wait_for_timeout(500)
        raise RuntimeError(error_message)

    def _click_first_enabled_button(self, page, labels: list[str]) -> bool:
        for label in labels:
            for selector in (f"button:has-text('{label}')", f"[role='button']:has-text('{label}')"):
                locator = page.locator(selector)
                try:
                    count = min(locator.count(), 5)
                except Exception:
                    continue
                for index in range(count):
                    button = locator.nth(index)
                    try:
                        if button.is_visible(timeout=500) and button.is_enabled(timeout=500):
                            button.click(timeout=5000)
                            page.wait_for_timeout(1200)
                            return True
                    except Exception:
                        continue
        for selector in ("button[type='submit']", "button"):
            locator = page.locator(selector)
            try:
                count = min(locator.count(), 5)
            except Exception:
                continue
            for index in range(count):
                button = locator.nth(index)
                try:
                    if button.is_visible(timeout=500) and button.is_enabled(timeout=500):
                        button.click(timeout=5000)
                        page.wait_for_timeout(1200)
                        return True
                except Exception:
                    continue
        return False

    def _composer_count(self, page) -> int:
        selectors = [
            "form [contenteditable='true']",
            "div.ProseMirror",
            "#prompt-textarea",
            "[contenteditable='true']",
            "[role='textbox']",
            "textarea",
        ]
        return sum(page.locator(selector).count() for selector in selectors)

    def _composer_locator(self, page):
        selectors = [
            "form [contenteditable='true']",
            "div.ProseMirror",
            "#prompt-textarea",
            "[contenteditable='true']",
            "[role='textbox']",
            "textarea",
        ]
        for selector in selectors:
            locator = page.locator(selector)
            try:
                count = locator.count()
                if count > 0 and locator.last.is_visible(timeout=2000):
                    return locator.last
            except Exception:
                continue
        raise RuntimeError("ChatGPT 입력창을 찾지 못했습니다.")

    def _build_gpt_section_plan_request(self, product: ProductRecord) -> str:
        detail_facts = [
            fact
            for fact in product.facts[:12]
            if not any(skip in fact for skip in ("원산지", "제조국", "제조사", "수입사"))
        ]
        product_info = "\n".join(
            item
            for item in [
                f"상품명: {product.product_name or product.title or product.code}",
                f"상품 URL: {product.url.strip()}",
                f"카테고리: {product.category}" if product.category else "",
                f"가격/옵션: {product.price_text} / {product.options_text}".strip(" /") if (product.price_text or product.options_text) else "",
                "상품 확인 정보:\n" + "\n".join(f"- {fact}" for fact in detail_facts) if detail_facts else "",
            ]
            if item.strip()
        )
        source_excerpt = re.sub(r"\s+", " ", product.source_text or "").strip()[:700]
        secondary_block = ""
        if product.secondary_url.strip():
            secondary_block = (
                f"\n1688 참고 링크(이미지/상품 외형 참고 전용): {product.secondary_url.strip()}\n"
                "중요: 1688은 첨부 이미지와 상품 외형, 옵션 사진 참고에만 사용하세요. "
                "1688의 배송, 통관, 반품, A/S, 정책, 중국어 상세 문구는 상세페이지 카피와 사실 정보에 반영하지 마세요.\n"
            )
        return (
            "첨부한 실제 상품 이미지와 아래 상품 정보를 기준으로 한국 쇼핑몰 상세페이지 섹션 1~10을 설계해줘.\n"
            "불필요한 설명 없이 섹션 기획만 작성해.\n"
            "섹션 11은 만들지 말고, 반드시 섹션 10까지만 작성해.\n"
            "상품과 맞지 않는 내용, 없는 기능, 원산지/제조국 강조, 허구 후기, 허위 인증, 배송/반품/A/S 정책 문구는 넣지 마.\n"
            "오너클랜/도매꾹/1688 원문에 있는 중국어 문구나 워터마크 문구는 카피에 쓰지 마.\n\n"
            f"{product_info}\n"
            f"{secondary_block}\n"
            f"상품 원문 핵심 참고:\n{source_excerpt}\n\n"
            "출력 형식은 아래 형식을 섹션 1부터 섹션 10까지 반복해서 지켜줘.\n"
            "각 섹션은 상품별로 다르게 기획하고, 이미지 프롬프트에는 첨부 이미지의 실제 상품 외형/색상/소재/옵션/비율을 유지한다는 조건을 넣어줘.\n\n"
            f"{self._detail_section_common_design_rules()}\n\n"
            "섹션 1. 히어로\n"
            "제목\n"
            "메인 헤드라인\n"
            "서브 카피\n"
            "본문/불릿\n"
            "이미지 프롬프트\n\n"
            "섹션 2. 공감\n"
            "제목\n"
            "메인 헤드라인\n"
            "서브 카피\n"
            "본문/불릿\n"
            "이미지 프롬프트\n\n"
            "이 형식 그대로 섹션 10까지 완성해줘."
        )

    def _submit_section_plan_request(
        self,
        page,
        prompt: str,
        attachment_paths: list[Path] | None = None,
        allow_retry: bool = True,
        product: ProductRecord | None = None,
    ) -> str:
        self._ensure_chatgpt_section_planner_page(page)
        self._accept_chatgpt_cookies(page)
        if self._page_needs_login(page):
            raise RuntimeError("ChatGPT 로그인이 필요합니다.")
        previous_text, busy = self._latest_gpt_text(page)
        reusable_text = self._find_reusable_gpt_plan_on_page(page, prompt, product)
        if reusable_text:
            return reusable_text
        if self._can_reuse_existing_gpt_plan(previous_text, prompt):
            return previous_text

        if busy:
            return self._wait_for_gpt_section_plan_detection(
                page,
                previous_text=previous_text,
                timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS,
            )

        self._wait_for_gpt_idle(page, timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS)
        previous_text, _ = self._latest_gpt_text(page)
        reusable_text = self._find_reusable_gpt_plan_on_page(page, prompt, product)
        if reusable_text:
            return reusable_text
        if self._can_reuse_existing_gpt_plan(previous_text, prompt):
            return previous_text

        pre_submit_text = previous_text
        self._send_prompt_to_gpt_page(page, prompt.strip(), attachment_paths=attachment_paths or [])
        return self._wait_for_gpt_section_plan_detection(
            page,
            previous_text=pre_submit_text,
            timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS,
        )

    def _complete_gpt_section_plan_by_continuation(
        self,
        page,
        product: ProductRecord,
        initial_text: str,
        max_attempts: int = 3,
    ) -> tuple[str, list[SectionPlan]]:
        texts = [(initial_text or "").strip()]
        combined_text = self._merge_gpt_section_texts(texts)
        best_sections = self._section_plans_from_saved_raw_gpt_text(combined_text, product)
        for _attempt in range(max(1, max_attempts)):
            try:
                full_sections = self._section_plans_from_gpt(combined_text, product)
                if self._section_plan_set_is_clean(full_sections, combined_text):
                    return combined_text, full_sections[:REQUIRED_SECTION_IMAGE_COUNT]
            except Exception:
                pass
            numbers = self._gpt_section_numbers_from_text(combined_text)
            if len(numbers) >= REQUIRED_SECTION_IMAGE_COUNT:
                break
            next_number = self._first_missing_gpt_section_number(numbers)
            continue_prompt = self._build_section_plan_continue_prompt(product, next_number)
            try:
                previous_text, _ = self._latest_gpt_text(page)
            except Exception:
                previous_text = ""
            self._send_prompt_to_gpt_page(page, continue_prompt, attachment_paths=[])
            continuation_text = self._wait_for_gpt_section_plan_detection(
                page,
                previous_text=previous_text,
                timeout_seconds=CHATGPT_SECTION_PLAN_RETRY_WAIT_TIMEOUT_SECONDS,
            )
            if continuation_text.strip():
                texts.append(continuation_text.strip())
                combined_text = self._merge_gpt_section_texts(texts)
                parsed = self._section_plans_from_saved_raw_gpt_text(combined_text, product)
                if len(parsed) > len(best_sections):
                    best_sections = parsed
        try:
            full_sections = self._section_plans_from_gpt(combined_text, product)
            if self._section_plan_set_is_clean(full_sections, combined_text):
                return combined_text, full_sections[:REQUIRED_SECTION_IMAGE_COUNT]
        except Exception:
            pass
        return combined_text, best_sections

    def _recover_partial_gpt_section_plan(
        self,
        page,
        product: ProductRecord,
        partial_text: str,
        partial_sections: list[SectionPlan],
    ) -> tuple[str, list[SectionPlan], bool]:
        source_text = (partial_text or "").strip()
        continued_text, continued_sections = self._complete_gpt_section_plan_by_continuation(
            page,
            product,
            source_text,
        )
        if len(continued_sections) >= REQUIRED_SECTION_IMAGE_COUNT and self._section_plan_set_is_clean(
            continued_sections,
            continued_text,
        ):
            return continued_text, continued_sections[:REQUIRED_SECTION_IMAGE_COUNT], True

        fallback_sections = continued_sections or partial_sections
        if fallback_sections:
            return (
                continued_text or source_text,
                self._extend_section_plans_to_required_count(product, fallback_sections),
                False,
            )
        return continued_text or source_text, [], False

    def _build_section_plan_continue_prompt(self, product: ProductRecord, next_number: int) -> str:
        next_number = max(1, min(REQUIRED_SECTION_IMAGE_COUNT, int(next_number or 1)))
        product_label = self._short_detail_text(product.product_name or product.title or product.code or "상품", "상품", 80)
        return (
            f"방금 작성한 '{product_label}' 상세페이지 기획을 이어서 작성해줘.\n"
            f"섹션 {next_number}부터 섹션 {REQUIRED_SECTION_IMAGE_COUNT}까지만 출력.\n"
            f"섹션 1~{next_number - 1}은 반복하지 마.\n"
            "각 섹션은 아래 형식을 그대로 지켜줘.\n\n"
            "섹션 N. 섹션명\n\n"
            "제목\n"
            "섹션명\n\n"
            "메인 헤드라인\n"
            "한글 메인 카피\n\n"
            "서브 카피\n"
            "한글 서브 카피\n\n"
            "본문/불릿\n"
            "상품 이미지와 옵션에서 확인되는 실제 구매 포인트만 정리\n\n"
            "이미지 프롬프트\n"
            "세로 9:16 한국 쇼핑몰 상세페이지 이미지 프롬프트\n\n"
            "설명, 사과, 요약, 코드블록 없이 섹션만 출력.\n"
            "원산지, 제조국, 배송, 반품, A/S 정책 문구는 상세페이지 섹션에 넣지 마."
        )

    def _merge_gpt_section_texts(self, texts: list[str]) -> str:
        blocks_by_number: dict[int, dict[str, str]] = {}
        fallback_texts: list[str] = []
        for text in texts:
            cleaned = (text or "").strip()
            if not cleaned:
                continue
            blocks = self._extract_structured_gpt_section_blocks(cleaned)
            if not blocks:
                fallback_texts.append(cleaned)
                continue
            for block in blocks:
                try:
                    number = int(str(block.get("number") or "").strip())
                except ValueError:
                    continue
                if 1 <= number <= REQUIRED_SECTION_IMAGE_COUNT:
                    blocks_by_number[number] = block
        if blocks_by_number:
            return "\n\n".join(
                str(blocks_by_number[number].get("source_section_text") or "").strip()
                for number in range(1, REQUIRED_SECTION_IMAGE_COUNT + 1)
                if number in blocks_by_number
            ).strip()
        return "\n\n".join(fallback_texts).strip()

    def _gpt_section_numbers_from_text(self, text: str) -> set[int]:
        numbers: set[int] = set()
        for block in self._extract_structured_gpt_section_blocks(text):
            try:
                number = int(str(block.get("number") or "").strip())
            except ValueError:
                continue
            if 1 <= number <= REQUIRED_SECTION_IMAGE_COUNT:
                numbers.add(number)
        return numbers

    def _first_missing_gpt_section_number(self, numbers: set[int]) -> int:
        for number in range(1, REQUIRED_SECTION_IMAGE_COUNT + 1):
            if number not in numbers:
                return number
        return REQUIRED_SECTION_IMAGE_COUNT

    def _wait_for_gpt_section_plan_detection(
        self,
        page,
        previous_text: str = "",
        timeout_seconds: int = CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS,
    ) -> str:
        wait_seconds = max(1, int(timeout_seconds))
        deadline = time.monotonic() + wait_seconds
        previous_text = (previous_text or "").strip()
        previous_key = self._normalize_text_key(previous_text[:2000])
        last_text = ""
        retry_clicked = False
        wait_label = f"{wait_seconds // 60}분 {wait_seconds % 60}초"
        self.automation_signals.status.emit(
            f"GPT 기획중... {wait_label} 뒤 최신 원문을 저장합니다."
        )
        status_update_interval = max(1, CHATGPT_SECTION_PLAN_STATUS_UPDATE_SECONDS)
        next_status_at = time.monotonic() + status_update_interval
        hard_deadline = time.monotonic() + max(wait_seconds, CHATGPT_SECTION_PLAN_BUSY_MAX_WAIT_SECONDS)
        while time.monotonic() < hard_deadline:
            self._raise_if_user_requested_stop_or_skip()
            page.wait_for_timeout(1000)
            latest_text, busy = self._latest_gpt_text(page)
            latest_text = (latest_text or "").strip()
            if not latest_text:
                if time.monotonic() >= deadline and not busy:
                    break
                if time.monotonic() >= next_status_at:
                    if time.monotonic() >= deadline:
                        remaining = max(0, int(hard_deadline - time.monotonic()))
                        self.automation_signals.status.emit(
                            f"GPT 기획 답변 마무리 대기... 남은 최대 {remaining // 60}분 {remaining % 60}초"
                        )
                    else:
                        remaining = max(0, int(deadline - time.monotonic()))
                        self.automation_signals.status.emit(
                            f"GPT 기획중... 남은 대기 {remaining // 60}분 {remaining % 60}초"
                        )
                    next_status_at = time.monotonic() + status_update_interval
                continue
            latest_key = self._normalize_text_key(latest_text[:2000])
            if previous_key and latest_key == previous_key:
                if time.monotonic() >= deadline and not busy:
                    break
                if time.monotonic() >= next_status_at:
                    if time.monotonic() >= deadline:
                        remaining = max(0, int(hard_deadline - time.monotonic()))
                        self.automation_signals.status.emit(
                            f"GPT 기획 답변 마무리 대기... 남은 최대 {remaining // 60}분 {remaining % 60}초"
                        )
                    else:
                        remaining = max(0, int(deadline - time.monotonic()))
                        self.automation_signals.status.emit(
                            f"GPT 기획중... 남은 대기 {remaining // 60}분 {remaining % 60}초"
                        )
                    next_status_at = time.monotonic() + status_update_interval
                continue
            last_text = latest_text
            if self._is_chatgpt_transient_send_error_text(latest_text):
                if not retry_clicked and self._click_chatgpt_retry_button(page, timeout_ms=12000):
                    retry_clicked = True
                    deadline = time.monotonic() + wait_seconds
                    next_status_at = time.monotonic() + status_update_interval
                    self.automation_signals.status.emit(
                        f"GPT 전송 시간초과 감지. 다시 시도 버튼만 누르고 {wait_label} 대기합니다."
                    )
                    page.wait_for_timeout(3000)
                    last_text = ""
                    continue
                raise RuntimeError(f"GPT 전송 시간초과: {self._compact_error_text(latest_text, 240)}")
            if (
                not busy
                and (
                    self._gpt_text_has_any_section_heading(latest_text)
                    or self._gpt_text_has_structured_section_headings(latest_text)
                    or self._gpt_text_has_section_plan_signal(latest_text)
                )
            ):
                return latest_text
            if time.monotonic() >= next_status_at:
                if time.monotonic() >= deadline and busy:
                    remaining = max(0, int(hard_deadline - time.monotonic()))
                    self.automation_signals.status.emit(
                        f"GPT 기획 답변 마무리 대기... 남은 최대 {remaining // 60}분 {remaining % 60}초"
                    )
                else:
                    remaining = max(0, int(deadline - time.monotonic()))
                    self.automation_signals.status.emit(
                        f"GPT 기획중... 남은 대기 {remaining // 60}분 {remaining % 60}초"
                    )
                next_status_at = time.monotonic() + status_update_interval

        try:
            latest_text, _ = self._latest_gpt_text(page)
            latest_text = (latest_text or "").strip()
            latest_key = self._normalize_text_key(latest_text[:2000])
            if latest_text and (not previous_key or latest_key != previous_key):
                last_text = latest_text
        except Exception:
            pass
        if last_text and (
            self._gpt_text_has_any_section_heading(last_text)
            or self._gpt_text_has_structured_section_headings(last_text)
            or self._gpt_text_has_section_plan_signal(last_text)
        ):
            return last_text
        if last_text:
            return last_text
        raise RuntimeError(f"기획 응답 없음: {wait_label} 대기 후 GPT 답변을 찾지 못했습니다.")

    def _find_reusable_gpt_plan_on_page(
        self,
        page,
        prompt: str,
        product: ProductRecord | None = None,
    ) -> str:
        if not prompt:
            return ""
        candidates: list[str] = []
        selectors = (
            "[data-message-author-role='assistant']",
            "article:has([data-message-author-role='assistant'])",
            "article",
        )
        for selector in selectors:
            try:
                locator = page.locator(selector)
                count = min(locator.count(), 24)
            except Exception:
                continue
            for index in range(count - 1, -1, -1):
                try:
                    text = locator.nth(index).inner_text(timeout=1000).strip()
                except Exception:
                    continue
                if text:
                    candidates.append(text)
        try:
            latest_text, _ = self._latest_gpt_text(page)
            if latest_text:
                candidates.insert(0, latest_text)
        except Exception:
            pass

        seen: set[str] = set()
        for text in candidates:
            key = self._normalize_text_key(text[:1000])
            if not key or key in seen:
                continue
            seen.add(key)
            can_reuse = self._can_reuse_existing_gpt_plan(text, prompt)
            if not can_reuse:
                continue
            if product is None:
                return text.strip()
            try:
                sections = self._section_plans_from_gpt(text, product)
            except Exception:
                continue
            if self._section_plan_set_is_clean(sections):
                return text.strip()
        return ""

    def _ensure_chatgpt_section_planner_page(self, page) -> None:
        if self._is_chatgpt_section_planner_url(page.url):
            return
        try:
            self._wait_for_gpt_idle(page, timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS)
        except RuntimeError as exc:
            if not self._is_retryable_section_plan_wait_error(str(exc)):
                raise
            raise RuntimeError("ChatGPT가 아직 답변 또는 이미지를 생성 중입니다. 완료된 뒤 이어서 실행하세요.") from exc
        page.goto(GPT_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        self._accept_chatgpt_cookies(page)
        if self._page_needs_login(page):
            raise RuntimeError("ChatGPT 로그인이 필요합니다.")

    def _is_chatgpt_section_planner_url(self, url: str) -> bool:
        normalized = (url or "").lower()
        return "chatgpt.com/g/g-69ca98c6b4308191abf5d1b33aac6c5e" in normalized

    def _can_reuse_existing_gpt_plan(self, text: str, prompt: str) -> bool:
        if not text or not prompt:
            return False
        has_structured_headings = self._gpt_text_has_structured_section_headings(text)
        if (self._gpt_text_is_incomplete_state(text) and not has_structured_headings) or not self._gpt_text_has_section_plan_signal(text):
            return False
        tokens: list[str] = []
        for pattern in (
            r"selfcode=([A-Za-z0-9_-]+)",
            r"domeggook\.com/([0-9]+)",
            r"offer/([0-9]+)",
        ):
            tokens.extend(match.group(1) for match in re.finditer(pattern, prompt, flags=re.IGNORECASE))
        tokens.extend(
            token
            for token in re.findall(r"\b[A-Z0-9]{5,}\b", prompt)
            if not token.startswith(("HTTP", "HTTPS"))
        )
        unique_tokens = [token for token in dict.fromkeys(tokens) if len(token) >= 5]
        return bool(unique_tokens and any(token in text for token in unique_tokens))

    def _gpt_plan_matches_product_terms(self, text: str, product: ProductRecord) -> bool:
        if not text or product is None or not self._gpt_text_has_section_plan_signal(text):
            return False
        text_key = self._normalize_text_key(text)
        if product.code and product.code in text:
            return True
        token_sources = " ".join(
            item
            for item in (
                product.product_name,
                product.title,
                product.category,
                product.options_text,
            )
            if item
        )
        skip_tokens = {
            "도매",
            "도매꾹",
            "돈버는",
            "쇼핑",
            "상품",
            "상세정보",
            "옵션",
            "옵션선택",
            "인쇄가능",
        }
        tokens = []
        for token in re.findall(r"[0-9A-Za-z가-힣]{2,}", token_sources):
            if token in skip_tokens:
                continue
            if len(token) < 3 and not re.search(r"[A-Za-z0-9]", token):
                continue
            tokens.append(token)
        unique_tokens = list(dict.fromkeys(tokens))
        matched = sum(1 for token in unique_tokens[:24] if self._normalize_text_key(token) in text_key)
        return matched >= 2

    def _load_existing_section_plan_text(self, product: ProductRecord, prompt: str) -> str:
        candidate_texts: list[str] = []
        result_paths = [
            product.output_dir / "result.md",
            self._completed_product_dir(product) / "result.md",
        ]
        for result_path in result_paths:
            if not result_path.exists():
                continue
            metadata = self._read_output_metadata(result_path.parent, prefer_completed=False)
            if not metadata or not self._metadata_matches_task_url(metadata, product.url, product.secondary_url):
                continue
            try:
                content = result_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            matches = re.findall(r"## GPT 원문 결과\s*```(?:text)?\s*(.*?)\s*```", content, flags=re.DOTALL)
            candidate_texts.extend(text.strip() for text in reversed(matches) if text.strip())
            if not matches and self._gpt_text_has_section_plan_signal(content):
                candidate_texts.append(content.strip())
        for metadata_path in (product.output_dir / "metadata.json", self._completed_product_dir(product) / "metadata.json"):
            if not metadata_path.exists():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            if not self._metadata_matches_task_url(metadata, product.url, product.secondary_url):
                continue
            raw_response = str(metadata.get("gpt_response") or "").strip()
            if raw_response:
                candidate_texts.append(raw_response)
        for cleaned in candidate_texts:
            if self._can_reuse_existing_gpt_plan(cleaned, prompt):
                return cleaned
            if self._gpt_text_has_any_section_heading(cleaned) and self._gpt_plan_matches_product_terms(cleaned, product):
                return cleaned
            try:
                sections = self._section_plans_from_gpt(cleaned, product)
                if self._section_plan_set_is_clean(sections, cleaned):
                    return cleaned
            except Exception:
                continue
        return ""

    def _build_section_plan_retry_prompt(self, original_prompt: str, result_text: str) -> str:
        return original_prompt.strip()

    def _build_section_plan_wait_retry_prompt(self, original_prompt: str) -> str:
        return original_prompt.strip()

    def _is_retryable_section_plan_wait_error(self, message: str) -> bool:
        return (
            "GPT 응답 대기 제한" in message
            or "응답이 오래 멈춰" in message
            or "이전 답변 생성" in message
            or "답변 생성이 중지" in message
            or "스트리밍이 중지" in message
            or "메시지 완료를 기다리는 중" in message
            or "전송 시간초과" in message
            or "전송 시간이 초과" in message
            or "최종 답변을 확인하지 못했습니다" in message
        )

    def _section_plans_from_gpt(self, result_text: str, product: ProductRecord) -> list[SectionPlan]:
        payload = self._extract_json_payload(result_text)
        raw_sections = payload.get("sections") if isinstance(payload, dict) else None
        if not isinstance(raw_sections, list):
            structured_plans = self._section_plans_from_structured_gpt_text(result_text, product)
            if len(structured_plans) >= REQUIRED_SECTION_IMAGE_COUNT:
                return structured_plans
            raise RuntimeError(f"GPT 답변이 {REQUIRED_SECTION_IMAGE_COUNT}개 섹션 JSON 또는 섹션 실행본 형식이 아닙니다.")

        plans: list[SectionPlan] = []
        missing: list[str] = []
        for section_index, section in enumerate(raw_sections, start=1):
            if not isinstance(section, dict):
                missing.append(f"section_{section_index:02d}")
                continue
            bullets = section.get("bullets") or []
            if not isinstance(bullets, list):
                bullets = [str(bullets)]
            headline = str(section.get("headline") or "").strip()
            body = str(section.get("body") or "").strip()
            image_prompt = str(
                section.get("image_prompt_ko")
                or section.get("image_prompt")
                or section.get("prompt")
                or ""
            ).strip()
            if not headline or not body or not image_prompt:
                missing.append(f"section_{section_index:02d}")
                continue
            key = str(section.get("section_key") or f"section_{section_index:02d}").strip()
            name = str(section.get("section_name") or section.get("name") or f"섹션 {section_index}").strip()
            plans.append(
                SectionPlan(
                    section_key=key,
                    section_name=self._display_section_name(key, name or f"섹션 {section_index}"),
                    headline=headline,
                    subheadline=str(section.get("subheadline") or "").strip(),
                    body=body,
                    bullets=[str(item).strip() for item in bullets if str(item).strip()][:4],
                    image_prompt=image_prompt,
                    overlay_text=str(section.get("overlay_text") or section.get("copy_overlay") or "").strip(),
                    source_section_text=str(section.get("source_section_text") or "").strip(),
                )
            )
        if missing:
            raise RuntimeError(f"GPT 답변에 필요한 섹션 JSON 항목이 부족합니다: {', '.join(missing)}")
        if len(plans) < REQUIRED_SECTION_IMAGE_COUNT:
            raise RuntimeError(f"GPT 답변에 필요한 {REQUIRED_SECTION_IMAGE_COUNT}개 섹션 JSON 항목이 부족합니다: {len(plans)}개")
        if not self._section_plan_set_is_clean(plans, result_text):
            raise RuntimeError("GPT 섹션 JSON에 오염 문구가 포함되어 있습니다.")
        return plans

    def _section_plans_from_structured_gpt_text(self, result_text: str, product: ProductRecord) -> list[SectionPlan]:
        blocks = self._extract_structured_gpt_section_blocks(result_text)
        if len(blocks) < REQUIRED_SECTION_IMAGE_COUNT:
            return []
        plans: list[SectionPlan] = []
        for section_index, block in enumerate(blocks, start=1):
            key = self._structured_section_key(block, section_index)
            name = self._structured_section_name(block, section_index)
            headline = self._clean_detail_copy_text(block.get("headline") or block.get("title_copy") or block.get("title") or "")
            subheadline = self._clean_detail_copy_text(block.get("subheadline") or "")
            body_source = str(block.get("body") or block.get("subheadline") or block.get("title_copy") or "")
            body = self._clean_structured_section_body(body_source)
            bullets = self._structured_body_bullets(body_source)
            image_prompt = str(block.get("image_prompt") or "").strip()
            overlay_text = self._extract_overlay_text_from_image_prompt(image_prompt)
            if not headline or not body or not image_prompt:
                return []
            plans.append(
                SectionPlan(
                    section_key=key,
                    section_name=name,
                    headline=headline,
                    subheadline=subheadline,
                    body=body,
                    bullets=bullets,
                    image_prompt=image_prompt,
                    overlay_text=overlay_text,
                    source_section_text=str(block.get("source_section_text") or "").strip(),
                )
            )
        if not self._section_plan_set_is_clean(plans):
            return []
        return plans

    def _section_plans_from_saved_raw_gpt_text(self, result_text: str, product: ProductRecord) -> list[SectionPlan]:
        blocks = self._extract_structured_gpt_section_blocks(result_text)
        if not blocks:
            return []
        plans: list[SectionPlan] = []
        for section_index, block in enumerate(blocks, start=1):
            key = self._structured_section_key(block, section_index)
            name = self._structured_section_name(block, section_index)
            headline = self._clean_detail_copy_text(block.get("headline") or block.get("title_copy") or block.get("title") or name)
            subheadline = self._clean_detail_copy_text(block.get("subheadline") or "")
            source_text = str(block.get("source_section_text") or "").strip()
            body_source = str(block.get("body") or block.get("subheadline") or block.get("title_copy") or source_text)
            body = self._clean_structured_section_body(body_source) or self._clean_structured_section_body(source_text)
            if not headline:
                headline = name
            if not body:
                body = headline
            bullets = self._structured_body_bullets(body_source or source_text)
            image_prompt = str(block.get("image_prompt") or "").strip()
            if not image_prompt:
                image_prompt = self._fallback_structured_section_image_prompt(product, key, headline, subheadline, body)
            section = SectionPlan(
                section_key=key,
                section_name=name,
                headline=headline,
                subheadline=subheadline,
                body=body,
                bullets=bullets,
                image_prompt=image_prompt,
                overlay_text=self._extract_overlay_text_from_image_prompt(image_prompt),
                source_section_text=source_text,
            )
            if self._section_text_is_contaminated(section):
                continue
            if self._contains_1688_policy_contamination(
                "\n".join(
                    [
                        section.section_name,
                        section.headline,
                        section.subheadline,
                        section.body,
                        section.image_prompt,
                        section.overlay_text,
                        section.source_section_text,
                        " ".join(section.bullets),
                    ]
                )
            ):
                continue
            plans.append(section)
        if not plans:
            return []
        combined = "\n".join(
            "\n".join(
                [
                    section.section_key,
                    section.section_name,
                    section.headline,
                    section.subheadline,
                    section.body,
                    section.image_prompt,
                    section.overlay_text,
                    section.source_section_text,
                    " ".join(section.bullets),
                ]
            )
            for section in plans
        )
        if self._contains_gpt_result_contamination(combined):
            return []
        return plans

    def _structured_section_name(self, block: dict[str, str], section_index: int) -> str:
        title_copy = self._clean_detail_copy_text(block.get("title_copy") or "")
        title = self._clean_detail_copy_text(block.get("title") or "")
        return title_copy or title or f"섹션 {section_index}"

    def _structured_section_key(self, block: dict[str, str], section_index: int) -> str:
        raw_number = str(block.get("number") or section_index).strip()
        try:
            number = int(raw_number)
        except ValueError:
            number = section_index
        name = self._structured_section_name(block, section_index)
        slug = slugify(name, "section")
        return f"section_{number:02d}_{slug}"

    def _fallback_structured_section_image_prompt(
        self,
        product: ProductRecord,
        section_key: str,
        headline: str,
        subheadline: str,
        body: str,
    ) -> str:
        section_name = SECTION_DISPLAY_NAMES.get(section_key, section_key)
        product_name = self._clean_detail_copy_text(product.product_name or product.code or "상품")
        copy = " / ".join(part.strip() for part in (headline, subheadline, body) if part and part.strip())
        return (
            f"세로 9:16 쇼핑몰 상세페이지용 상업 이미지. 상품은 {product_name}. "
            f"섹션은 {section_name}. GPT가 만든 카피 흐름은 다음과 같다: {copy}. "
            "원본 상품 이미지의 형태, 색상, 구조를 유지하고, 기존 상세페이지 캡처를 복사하지 않는다. "
            "한국 쇼핑몰/SNS 광고형 레이아웃, 고해상도, 한글 카피를 얹을 여백을 확보한다."
        )

    def _extract_structured_gpt_section_blocks(self, result_text: str) -> list[dict[str, str]]:
        text = (result_text or "").replace("\r\n", "\n").replace("\r", "\n")
        section_heading_pattern = re.compile(
            r"(?im)^\s*(?:섹션|section)\s*(\d+)\s*[.\-:]?\s*([^\n]+?)\s*$"
        )
        matches = list(section_heading_pattern.finditer(text))
        blocks: list[dict[str, str]] = []
        for idx, match in enumerate(matches):
            heading_text = match.group(0).strip()
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            raw_body = self._trim_structured_section_tail(text[start:end].strip())
            title = re.sub(r"\s+", " ", match.group(2).strip())
            if not raw_body:
                continue
            parsed = {
                "number": str(match.group(1)),
                "title": title,
                "source_section_text": f"{heading_text}\n{raw_body}".strip(),
                "title_copy": self._extract_structured_labeled_text(raw_body, ("제목",), single_line=True),
                "headline": self._extract_structured_labeled_text(raw_body, ("메인 헤드라인", "헤드라인"), single_line=False),
                "subheadline": self._extract_structured_labeled_text(raw_body, ("서브 카피", "서브카피"), single_line=False),
                "body": self._extract_structured_labeled_text(
                    raw_body,
                    (
                        "본문 / 불릿",
                        "본문/불릿",
                        "본문 / FAQ",
                        "본문 / 포인트",
                        "본문/포인트",
                        "본문 / 비교 카피",
                        "본문/비교 카피",
                        "본문 / 옵션 안내",
                        "본문/옵션 안내",
                        "본문 / 디테일 포인트",
                        "본문/디테일 포인트",
                        "본문 / 활용 예시",
                        "본문/활용 예시",
                        "본문 / 체크리스트",
                        "본문/체크리스트",
                        "본문 / 추천 체크리스트",
                        "본문/추천 체크리스트",
                        "본문 / 배송 체크",
                        "본문/배송 체크",
                        "본문 카피",
                        "본문카피",
                        "CTA 문구",
                        "CTA 카피",
                        "본문",
                        "FAQ",
                        "FAQ 카피",
                    ),
                    single_line=False,
                ),
                "image_prompt": self._extract_structured_image_prompt(raw_body),
            }
            if parsed["headline"] or parsed["title_copy"] or parsed["body"] or parsed["image_prompt"]:
                blocks.append(parsed)
        return blocks

    def _trim_structured_section_tail(self, block: str) -> str:
        text = (block or "").strip()
        if not text:
            return ""
        tail_patterns = (
            r"(?im)^\s*(?:\d+\.\s*)?(?:가정\s*/\s*추가|가정|추가\s*확인|실무\s*메모)\b",
            r"(?im)^\s*히어로\s*훅\b",
            r"(?im)^\s*https?://\S+",
            r"(?im)^\s*1688\s+참고\b",
            r"(?im)^\s*중요\s*:",
            r"(?im)^\s*(?:Pro\s*)?생각\s+중\b",
            r"(?im)^\s*문서\s*읽는\s*중\b",
            r"(?im)^\s*Thought\s+for\b",
            r"(?im)^\s*To meet the user's\b",
            r"(?im)^\s*첨부파일\b",
        )
        cut_at: int | None = None
        for pattern in tail_patterns:
            match = re.search(pattern, text)
            if match:
                cut_at = match.start() if cut_at is None else min(cut_at, match.start())
        if cut_at is not None:
            text = text[:cut_at]
        return text.strip()

    def _extract_structured_labeled_text(self, block: str, labels: tuple[str, ...], single_line: bool = False) -> str:
        lines = block.splitlines()
        stop_pattern = re.compile(
            r"^\s*(제목|메인\s*헤드라인|헤드라인|서브\s*카피|서브카피|본문\s*/\s*[^:：\n]+|본문\s*카피|본문카피|본문|FAQ\s*카피|FAQ|CTA\s*문구|CTA\s*카피|CTA|이미지\s*프롬프트|히어로\s*훅|(?:\d+\.\s*)?가정\s*/\s*추가|추가\s*확인)\s*(?:[:：].*)?$",
            re.IGNORECASE,
        )
        label_set = {self._normalize_text_key(label) for label in labels}
        start = None
        inline_value = ""
        for idx, line in enumerate(lines):
            label_part, sep, value_part = line.partition(":")
            if not sep:
                label_part, sep, value_part = line.partition("：")
            if self._normalize_text_key(label_part) in label_set:
                start = idx + 1
                inline_value = value_part.strip() if sep else ""
                break
        if start is None:
            return ""
        if single_line and inline_value:
            return inline_value
        collected: list[str] = [inline_value] if inline_value else []
        for line in lines[start:]:
            stripped = line.strip()
            if not stripped:
                if single_line and collected:
                    break
                continue
            if stop_pattern.match(stripped):
                break
            collected.append(stripped)
            if single_line:
                break
        return "\n".join(collected).strip()

    def _extract_structured_image_prompt(self, block: str) -> str:
        text = self._extract_structured_labeled_text(block, ("이미지 프롬프트",), single_line=False)
        if not text:
            return ""
        text = re.split(
            r"(?im)^\s*(히어로\s*훅|(?:\d+\.\s*)?가정\s*/\s*추가|추가\s*확인|\d+\.\s*(?:제품|상세페이지|섹션별|가정)\b|섹션\s*\d+|section\s*\d+|https?://|중요\s*:|Pro\s+생각\s+중|Thought\s+for|문서\s*읽는\s*중)\b",
            text,
            maxsplit=1,
        )[0]
        return text.strip()

    def _map_structured_blocks_to_default_sections(self, blocks: list[dict[str, str]]) -> dict[str, dict[str, str]]:
        preferences: dict[str, tuple[str, ...]] = {
            "hero": ("히어로", "hook", "첫 화면"),
            "empathy": ("문제 공감", "empathy", "공감", "왜"),
            "solution": ("해결 제안", "solution", "contrast", "솔루션", "해결"),
            "benefits": ("옵션", "사이즈", "비교", "오픈형", "서랍형", "구조 포인트", "proof", "디테일"),
            "how_to_use": ("활용 장면", "공간별 활용", "활용", "수납 루틴", "사용법", "detail"),
            "trust": ("배송", "반품", "통관", "구매 전 확인", "조립", "수령", "체크", "신뢰", "구매 결정", "추천 대상", "proof", "구조 포인트"),
            "cta": ("faq", "cta", "마지막", "구매 전 체크", "offer"),
        }
        selected: dict[str, dict[str, str]] = {}
        used: set[int] = set()
        cta_tokens = preferences["cta"]
        cta_index = None
        cta_score = 0
        for idx in range(len(blocks) - 1, -1, -1):
            block = blocks[idx]
            haystack = f"{block.get('title', '')} {block.get('title_copy', '')} {block.get('headline', '')}".lower()
            score = self._structured_block_match_score(haystack, cta_tokens)
            if score > cta_score:
                cta_index = idx
                cta_score = score
        if cta_index is not None and cta_score > 0:
            selected["cta"] = blocks[cta_index]
            used.add(cta_index)
        for key, _ in self._default_detail_sections():
            if key in selected:
                continue
            tokens = preferences.get(key, ())
            found_index = None
            found_score = 0
            for idx, block in enumerate(blocks):
                if idx in used:
                    continue
                haystack = f"{block.get('title', '')} {block.get('title_copy', '')} {block.get('headline', '')}".lower()
                score = self._structured_block_match_score(haystack, tokens)
                if score > found_score:
                    found_index = idx
                    found_score = score
            if found_index is None:
                for idx, _block in enumerate(blocks):
                    if idx not in used:
                        found_index = idx
                        break
            if found_index is None:
                break
            selected[key] = blocks[found_index]
            used.add(found_index)
        return selected

    def _structured_block_match_score(self, haystack: str, tokens: tuple[str, ...]) -> int:
        best = 0
        for priority, token in enumerate(tokens):
            needle = token.lower()
            if needle and needle in haystack:
                best = max(best, (len(tokens) - priority) * 10)
        return best

    def _clean_structured_section_body(self, body: str) -> str:
        lines = [
            self._clean_detail_copy_text(line)
            for line in str(body or "").splitlines()
            if self._clean_detail_copy_text(line)
        ]
        lines = [line for line in lines if not self._is_noisy_copy_label(line)]
        joined = " ".join(lines[:8]).strip()
        return joined[:520].rstrip()

    def _structured_body_bullets(self, body: str) -> list[str]:
        candidates: list[str] = []
        for raw_line in str(body or "").splitlines():
            line = self._clean_detail_copy_text(raw_line)
            if not line or self._is_noisy_copy_label(line):
                continue
            if len(line) <= 90:
                candidates.append(line)
        return self._dedupe_text_items(candidates)[:4]

    def _section_plan_set_is_clean(self, sections: list[SectionPlan], source_text: str = "") -> bool:
        if len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
            return False
        combined_parts: list[str] = []
        for section in sections:
            combined_parts.extend(
                [
                    section.section_key,
                    section.section_name,
                    section.headline,
                    section.subheadline,
                    section.body,
                    section.image_prompt,
                    section.overlay_text,
                    section.source_section_text,
                    " ".join(section.bullets),
                ]
            )
            if not section.section_key.strip() or not section.headline.strip() or not section.body.strip() or not section.image_prompt.strip():
                return False
            if self._section_text_is_contaminated(section):
                return False
            if self._contains_1688_policy_contamination(
                "\n".join(
                    [
                        section.section_name,
                        section.headline,
                        section.subheadline,
                        section.body,
                        section.image_prompt,
                        section.overlay_text,
                        section.source_section_text,
                        " ".join(section.bullets),
                    ]
                )
            ):
                return False
        return not self._contains_gpt_result_contamination("\n".join(combined_parts))

    def _metadata_sections_are_clean(self, raw_sections: object) -> bool:
        if not isinstance(raw_sections, list) or len(raw_sections) < REQUIRED_SECTION_IMAGE_COUNT:
            return False
        sections: list[SectionPlan] = []
        for raw in raw_sections:
            if not isinstance(raw, dict):
                return False
            bullets = raw.get("bullets") or []
            if not isinstance(bullets, list):
                bullets = [str(bullets)]
            sections.append(
                SectionPlan(
                    section_key=str(raw.get("section_key") or "").strip(),
                    section_name=str(raw.get("section_name") or "").strip(),
                    headline=str(raw.get("headline") or "").strip(),
                    subheadline=str(raw.get("subheadline") or "").strip(),
                    body=str(raw.get("body") or "").strip(),
                    bullets=[str(item).strip() for item in bullets if str(item).strip()],
                    image_prompt=str(raw.get("image_prompt") or "").strip(),
                    overlay_text=str(raw.get("overlay_text") or "").strip(),
                    source_section_text=str(raw.get("source_section_text") or "").strip(),
                )
            )
        return self._section_plan_set_is_clean(sections)

    def _sections_include_review_points(self, raw_sections: object) -> bool:
        if not isinstance(raw_sections, list):
            return False
        for section in raw_sections:
            if self._is_review_points_section(section):
                return True
        return False

    def _is_review_points_section(self, section: object) -> bool:
        if isinstance(section, SectionPlan):
            section_key = section.section_key
            section_name = section.section_name
        elif isinstance(section, dict):
            section_key = str(section.get("section_key") or "")
            section_name = str(section.get("section_name") or "")
        else:
            return False
        if section_key.strip() == DETAIL_REVIEW_SECTION_KEY:
            return True
        return "리뷰형 만족" in section_name

    def _prepare_detail_sections_for_generation(self, product: ProductRecord, sections: list[SectionPlan]) -> list[SectionPlan]:
        cleaned: list[SectionPlan] = []
        for section in sections:
            if self._is_review_points_section(section):
                continue
            cleaned.append(section)
            if len(cleaned) >= MANUAL_SECTION_BUTTON_COUNT:
                break
        cleaned = self._extend_section_plans_to_required_count(product, cleaned)
        return self._merge_satisfaction_points_into_final_section(product, cleaned)

    def _extend_section_plans_to_required_count(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
    ) -> list[SectionPlan]:
        if len(sections) >= REQUIRED_SECTION_IMAGE_COUNT:
            return sections[:REQUIRED_SECTION_IMAGE_COUNT]
        product_label = self._short_detail_text(product.product_name or product.title or product.code or "상품", "상품", 56)
        category = self._short_detail_text(product.category, "상품 정보", 44)
        options = self._short_detail_text(product.options_text, "옵션과 구성을 확인하세요.", 70)
        price = self._short_detail_text(product.price_text, "가격 정보는 상품 페이지 기준입니다.", 48)
        clean_facts = self._dedupe_text_items(
            [
                fact
                for fact in product.facts
                if fact and not any(marker in fact for marker in ("공급사", "리뷰", "평점", "배지", "원산지", "제조국"))
            ]
        )
        templates = [
            (
                "hero",
                "히어로",
                f"{product_label}",
                "첫눈에 상품을 확인하세요",
                f"{category} 정보를 참고해 확인한 상품입니다.",
            ),
            (
                "empathy",
                "공감",
                "필요한 순간 바로 쓰기 좋게",
                "복잡한 설명보다 실제 상품 형태를 먼저 보여줍니다.",
                options,
            ),
            (
                "solution",
                "솔루션",
                "상품 구조를 한눈에",
                "첨부된 사진을 보고 외형과 구성을 정리했습니다.",
                clean_facts[0] if clean_facts else options,
            ),
            (
                "benefits",
                "특징·혜택",
                "구매 전 보는 핵심 포인트",
                "색상, 구성, 사용 목적을 빠르게 확인하세요.",
                clean_facts[1] if len(clean_facts) > 1 else category,
            ),
            (
                "detail",
                "디테일",
                "눈으로 확인하는 디테일",
                "상품 외형과 구성 포인트를 크게 보여드립니다.",
                clean_facts[2] if len(clean_facts) > 2 else options,
            ),
            (
                "how_to_use",
                "사용법",
                "이럴 때 활용하세요",
                "상품 쓰임새가 드러나는 상황별 포인트를 보여드립니다.",
                category,
            ),
            (
                "trust",
                "신뢰요소",
                "구매 전 확인 정보",
                "상품명, 옵션, 구성 등 원본 정보를 참고해 확인했습니다.",
                price,
            ),
            (
                "options",
                "옵션 확인",
                "옵션 선택 전 체크",
                "색상, 사이즈, 구성 정보를 주문 전 확인하세요.",
                options,
            ),
            (
                "purchase_check",
                "구매 전 확인 포인트",
                "마지막으로 한 번 더",
                "실제 상품 이미지와 옵션 정보를 함께 확인하세요.",
                f"{category} / {price}",
            ),
            (
                "final_cta",
                "마지막 선택 안내",
                "필요한 옵션으로 준비하세요",
                "상품 목적과 사용 장면에 맞춰 선택하면 됩니다.",
                "상세정보와 옵션을 확인한 뒤 주문하세요.",
            ),
        ]
        extended = list(sections)
        while len(extended) < REQUIRED_SECTION_IMAGE_COUNT:
            section_number = len(extended) + 1
            template_index = min(len(templates) - 1, section_number - 1)
            key, name, headline, subheadline, body = templates[template_index]
            section_key = f"{key}_{section_number:02d}"
            image_prompt = (
                "세로 9:16, 고해상도 한국 쇼핑몰 상세페이지 이미지. "
                f"현재 섹션은 {section_number}번 '{name}'입니다. "
                "첨부 이미지의 실제 상품 형태, 색상, 소재, 옵션, 비율을 유지하고 다른 상품으로 바꾸지 않는다. "
                f"화면에는 '{headline}' 중심의 짧은 한글 카피와 보조 문구 1~2개만 배치한다. "
                f"본문 포인트는 '{body}' 내용을 바탕으로 자연스럽게 정리한다. "
                "같은 CTA 문구를 반복하지 말고 이 섹션 역할에 맞는 화면 구성을 만든다. "
                "별점, 후기 아이디, 허구 리뷰 수, 판매량 표현, 인증 과장, 배송/반품 정책 문구는 넣지 않는다. "
                "흰색 또는 밝은 그레이 배경, 충분한 여백, 굵은 한글 산세리프, 오타/깨짐 없이 구성한다."
            )
            source_section_text = (
                f"섹션 {section_number}. {name}\n\n"
                f"제목\n{name}\n\n"
                f"메인 헤드라인\n{headline}\n\n"
                f"서브 카피\n{subheadline}\n\n"
                f"본문 / 불릿\n{body}\n\n"
                f"이미지 프롬프트\n{image_prompt}"
            )
            extended.append(
                SectionPlan(
                    section_key=section_key,
                    section_name=name,
                    headline=headline,
                    subheadline=subheadline,
                    body=body,
                    bullets=[body],
                    image_prompt=image_prompt,
                    overlay_text=headline,
                    source_section_text=source_section_text,
                )
            )
        return extended

    def _build_product_fallback_sections(self, product: ProductRecord) -> list[SectionPlan]:
        product_label = self._short_detail_text(product.product_name or product.title or product.code or "상품", "상품", 56)
        category = self._short_detail_text(product.category, "상품 정보", 44)
        options = self._short_detail_text(product.options_text, "옵션과 구성을 확인하세요.", 70)
        price = self._short_detail_text(product.price_text, "가격 정보는 상품 페이지 기준입니다.", 48)
        clean_facts = self._dedupe_text_items(
            [
                fact
                for fact in product.facts
                if fact and not any(marker in fact for marker in ("공급사", "리뷰", "평점", "배지", "원산지", "제조국"))
            ]
        )
        templates = [
            ("hero", "히어로", f"{product_label}", "첫눈에 상품을 확인하세요", f"{category} 정보를 참고해 확인한 상품입니다."),
            ("empathy", "공감", "필요한 순간 바로 쓰기 좋게", "복잡한 설명보다 실제 상품 형태를 먼저 보여줍니다.", options),
            ("solution", "솔루션", "상품 구조를 한눈에", "첨부된 사진을 보고 외형과 구성을 정리했습니다.", clean_facts[0] if clean_facts else options),
            ("benefits", "특징·혜택", "구매 전 보는 핵심 포인트", "색상, 구성, 사용 목적을 빠르게 확인하세요.", clean_facts[1] if len(clean_facts) > 1 else category),
            ("detail", "디테일", "눈으로 확인하는 디테일", "상품 외형과 구성 포인트를 크게 보여드립니다.", clean_facts[2] if len(clean_facts) > 2 else options),
            ("how_to_use", "사용법", "이럴 때 활용하세요", "상품 쓰임새가 드러나는 상황별 포인트를 보여드립니다.", category),
            ("trust", "신뢰요소", "구매 전 확인 정보", "상품명, 옵션, 구성 등 원본 정보를 참고해 확인했습니다.", "옵션과 상품 구성 정보를 주문 전 확인하세요."),
            ("options", "옵션 확인", "옵션 선택 전 체크", "색상, 사이즈, 구성 정보를 주문 전 확인하세요.", options),
            ("purchase_check", "구매 전 확인 포인트", "마지막으로 한 번 더", "실제 상품 이미지와 옵션 정보를 함께 확인하세요.", f"{category} / {price}"),
            ("final_cta", "마지막 선택 안내", "필요한 옵션으로 준비하세요", "상품 목적과 사용 장면에 맞춰 선택하면 됩니다.", "상세정보와 옵션을 확인한 뒤 주문하세요."),
        ]
        sections: list[SectionPlan] = []
        for section_index, (key, name, headline, subheadline, body) in enumerate(templates, start=1):
            bullets = self._dedupe_text_items([body, options, price, *clean_facts[:2]])[:3]
            image_prompt = (
                "세로 9:16 한국 쇼핑몰 상세페이지 이미지. "
                f"상품은 {product_label}. 섹션은 {name}. "
                "첨부 이미지의 실제 상품 형태, 색상, 소재, 옵션, 비율을 유지한다. "
                "한글 카피는 짧고 크게, 오타 없이. 로고, 워터마크, 중국어, 허구 인증, 배송/반품 정책 문구 금지."
            )
            source_section_text = (
                f"섹션 {section_index}. {name}\n\n"
                f"제목\n{name}\n\n"
                f"메인 헤드라인\n{headline}\n\n"
                f"서브 카피\n{subheadline}\n\n"
                f"본문/불릿\n{body}\n\n"
                f"이미지 프롬프트\n{image_prompt}"
            )
            sections.append(
                SectionPlan(
                    section_key=key,
                    section_name=name,
                    headline=self._clean_detail_copy_text(headline) or name,
                    subheadline=self._clean_detail_copy_text(subheadline),
                    body=self._clean_detail_copy_text(body) or self._fallback_section_body(product, SectionPlan(key, name, headline, subheadline, body, [])),
                    bullets=bullets or [self._clean_detail_copy_text(body) or name],
                    image_prompt=image_prompt,
                    overlay_text=headline,
                    source_section_text=source_section_text,
                )
            )
        return self._merge_satisfaction_points_into_final_section(product, sections)

    def _section_plans_to_result_text(self, sections: list[SectionPlan]) -> str:
        blocks: list[str] = []
        for index, section in enumerate(sections, start=1):
            blocks.append(
                "\n".join(
                    [
                        f"섹션 {index}. {section.section_name or section.section_key}",
                        "제목",
                        section.section_name,
                        "",
                        "메인 헤드라인",
                        section.headline,
                        "",
                        "서브 카피",
                        section.subheadline,
                        "",
                        "본문/불릿",
                        section.body,
                        *[f"- {item}" for item in section.bullets],
                        "",
                        "이미지 프롬프트",
                        section.image_prompt,
                    ]
                ).strip()
            )
        return "\n\n".join(blocks)

    def _merge_satisfaction_points_into_final_section(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
    ) -> list[SectionPlan]:
        if not sections:
            return sections
        final_section = sections[-1]
        marker = "구매 전 만족 포인트"
        if marker in "\n".join(
            [
                final_section.body,
                final_section.image_prompt,
                final_section.source_section_text,
                " ".join(final_section.bullets),
            ]
        ):
            return sections
        product_label = product.product_name or product.title or "상품"
        point_lines = [
            "실제 상품 사진을 보고 외형과 구성을 확인하세요.",
            "옵션 선택 전 색상, 사이즈, 구성 정보를 확인하세요.",
            "일상 사용 목적에 맞는 실용 포인트를 보고 선택하세요.",
        ]
        body_addition = f"{marker}: " + " ".join(point_lines)
        prompt_addition = (
            "마지막 구매 결정을 돕는 깔끔한 CTA 섹션. "
            f"{product_label}을 중심에 두고 하단에는 짧은 만족 포인트 3개만 정리한다. "
            "별점, 후기 아이디, 허구 리뷰 수, 판매량 표현은 넣지 않는다. "
            "실제 구매후기라고 단정하지 않는다."
        )
        source_addition = (
            f"\n\n{marker}\n"
            + "\n".join(f"- {line}" for line in point_lines)
            + "\n\n이미지 프롬프트 추가 기준\n"
            + prompt_addition
        )
        updated = SectionPlan(
            section_key=final_section.section_key,
            section_name=final_section.section_name,
            headline=final_section.headline,
            subheadline=final_section.subheadline,
            body=f"{final_section.body.rstrip()}\n\n{body_addition}".strip(),
            bullets=[*final_section.bullets, *point_lines],
            image_prompt=f"{final_section.image_prompt.rstrip()} {prompt_addition}".strip(),
            overlay_text=final_section.overlay_text,
            source_section_text=f"{final_section.source_section_text.rstrip()}{source_addition}".strip()
            if final_section.source_section_text.strip()
            else "",
        )
        return [*sections[:-1], updated]

    def _ensure_review_points_section(self, product: ProductRecord, sections: list[SectionPlan]) -> list[SectionPlan]:
        cleaned = list(sections)
        if self._sections_include_review_points(cleaned):
            return cleaned
        cleaned.append(self._build_review_points_section(product, cleaned))
        return cleaned

    def _append_review_section_to_result_text(self, result_text: str, sections: list[SectionPlan]) -> str:
        text = (result_text or "").rstrip()
        if "리뷰형 만족 포인트" in text and any(mask in text for mask in ("su**room", "mi**pick", "li**35")):
            return text
        review_section = next((section for section in sections if section.section_key == DETAIL_REVIEW_SECTION_KEY), None)
        if not review_section or not review_section.source_section_text.strip():
            return text
        return f"{text}\n\n{review_section.source_section_text.strip()}\n".lstrip()

    def _remove_review_points_from_result_text(self, result_text: str) -> str:
        text = (result_text or "").rstrip()
        if not text or "리뷰형 만족 포인트" not in text:
            return text
        return re.sub(
            r"\n{0,3}(?:섹션|SECTION|section)\s*\d+\s*[.)/:：\-]?\s*리뷰형 만족 포인트.*\Z",
            "",
            text,
            flags=re.DOTALL,
        ).rstrip()

    def _build_review_points_section(self, product: ProductRecord, sections: list[SectionPlan]) -> SectionPlan:
        product_type = self._review_product_type(product, sections)
        cards = self._review_cards_for_product_type(product_type, product)
        product_name = product.product_name or product.title or "상품"
        option_hint = self._review_option_hint(product)
        headline = "구매 전 많이 보는 만족 포인트"
        subheadline = "상품 특징을 후기 카드처럼 정리해 마지막 구매 결정을 도와줍니다."
        body = (
            "실제 후기라고 단정하지 않고, 상품 이미지와 섹션 기획에서 확인한 사용 포인트를 "
            "마스킹 아이디 카드로 보여줍니다."
        )
        review_text = "\n\n".join(f"★★★★★  {card_id}\n{card_body}" for card_id, card_body in cards)
        image_prompt = (
            "세로 9:16, 고해상도 한국 쇼핑몰 상세페이지 마지막 섹션 이미지. "
            "첨부 이미지와 같은 상품의 형태, 색상, 단수, 구조, 비율을 유지하고 다른 상품으로 바꾸지 않는다. "
            "배경은 따뜻한 화이트/크림 톤, 은은한 종이 질감과 얕은 그림자를 사용해 세련된 SNS형 후기 카드 영역처럼 구성한다. "
            "제품은 오른쪽 하단 또는 배경 한쪽에 자연스럽게 배치하고, 왼쪽과 중앙에는 둥근 모서리의 흰색 후기 카드 5개를 겹치지 않게 배치한다. "
            "카드에는 별점 5개와 마스킹 아이디, 짧은 만족 포인트 문장을 넣는다. "
            "실제 구매후기라고 단정하는 문구, 플랫폼 로고, 워터마크, 외국어 텍스트, 허구 인증, 과장 수치, 배송/반품 정책 문구는 넣지 않는다. "
            "글꼴은 굵은 한글 산세리프, 높은 대비, 여백 넉넉하게, 오타/깨짐 없이 읽히게 한다. "
            f"상품명 참고: {product_name}. {option_hint}\n\n"
            "이미지 안에 아래 문구를 한국어로 정확히 인쇄해 넣어라:\n"
            f"“{headline}\n"
            f"{review_text}”"
        )
        source_section_text = self._format_review_source_section(
            section_number=len(sections) + 1,
            headline=headline,
            subheadline=subheadline,
            body=body,
            review_cards=cards,
            image_prompt=image_prompt,
        )
        return SectionPlan(
            section_key=DETAIL_REVIEW_SECTION_KEY,
            section_name=SECTION_DISPLAY_NAMES[DETAIL_REVIEW_SECTION_KEY],
            headline=headline,
            subheadline=subheadline,
            body=body,
            bullets=[f"★★★★★  {card_id}\n{card_body}" for card_id, card_body in cards],
            image_prompt=image_prompt,
            overlay_text=f"{headline}\n\n{review_text}",
            source_section_text=source_section_text,
        )

    def _review_product_type(self, product: ProductRecord, sections: list[SectionPlan]) -> str:
        text = " ".join(
            [
                product.product_name,
                product.title,
                product.category,
                product.options_text,
                " ".join(product.facts),
                " ".join(
                    " ".join(
                        [
                            section.section_name,
                            section.headline,
                            section.subheadline,
                            section.body,
                            " ".join(section.bullets),
                        ]
                    )
                    for section in sections
                ),
            ]
        ).lower()
        checks = (
            ("storage_furniture", ("선반", "수납", "트롤리", "카트", "협탁", "가구", "서랍", "책장", "rack", "shelf")),
            ("fashion", ("의류", "원피스", "티셔츠", "바지", "자켓", "코트", "셔츠", "스커트", "패션")),
            ("shoes", ("신발", "운동화", "슬리퍼", "샌들", "부츠", "로퍼", "슈즈")),
            ("bag", ("가방", "백팩", "토트", "숄더백", "크로스백", "파우치")),
            ("beauty", ("화장품", "스킨", "로션", "크림", "세럼", "쿠션", "미용")),
            ("kitchen", ("주방", "냄비", "프라이팬", "그릇", "컵", "조리", "식기")),
            ("electronics", ("가전", "충전", "무선", "led", "케이블", "스피커", "전기", "전자")),
        )
        for product_type, keywords in checks:
            if any(keyword in text for keyword in keywords):
                return product_type
        return "generic"

    def _review_cards_for_product_type(self, product_type: str, product: ProductRecord) -> list[tuple[str, str]]:
        option_hint = self._review_option_hint(product)
        by_type: dict[str, list[tuple[str, str]]] = {
            "storage_furniture": [
                (
                    "su**room",
                    "바퀴가 있어서 청소할 때 옆으로 옮기기 쉽고, 거실 옆이나 침대 옆처럼 필요한 자리로 바꿔 쓰기 좋습니다. 한곳에 고정되는 선반보다 활용도가 높게 느껴집니다.",
                ),
                (
                    "mi**pick",
                    "윗칸에는 자주 쓰는 컵과 조명, 가운데는 책이나 안경, 아래칸에는 바구니를 두면 층별로 정리감이 생깁니다.",
                ),
                (
                    "li**35",
                    "35cm와 50cm 폭을 보고 고를 수 있어서 둘 공간에 맞춰 선택하기 좋습니다. 좁은 옆자리는 35cm, 여유 있는 수납은 50cm처럼 기준이 선명합니다.",
                ),
                (
                    "no**table",
                    "우드톤이라 소파 옆에 두어도 튀지 않고, 컵·책·티슈처럼 자주 쓰는 물건을 한곳에 모으기 좋습니다.",
                ),
                (
                    "ha**move",
                    "가볍게 옮겨 쓰는 보조 선반 느낌이라 거실, 침실, 작업 공간을 오가며 쓰기 좋은 타입입니다.",
                ),
            ],
            "fashion": [
                ("jo**fit", "출근룩이나 데일리룩에 과하게 튀지 않고 자연스럽게 매치하기 좋은 타입입니다."),
                ("mu**wear", "단독으로 입어도 좋고 아우터나 기본 아이템과 같이 입었을 때 활용도가 높게 느껴집니다."),
                ("ye**line", "색감과 실루엣이 부담스럽지 않아 평소 입던 스타일에 쉽게 더하기 좋습니다."),
                ("co**daily", "사진보다 실제 코디를 상상하기 쉬운 편이라 계절 아이템으로 고르기 좋습니다."),
                ("ra**pick", "매일 손이 가는 기본 아이템을 찾는 분께 어울리는 실용적인 선택입니다."),
            ],
            "shoes": [
                ("so**walk", "외출할 때 부담 없이 신기 좋고, 데일리 코디에 자연스럽게 어울리는 타입입니다."),
                ("mi**step", "발끝 라인이 과하지 않아 바지나 스커트처럼 여러 스타일에 맞추기 좋습니다."),
                ("lo**day", "짧은 외출부터 일상 착용까지 무난하게 쓰기 좋은 실용적인 느낌입니다."),
                ("ha**fit", "디자인이 튀지 않아 계절이 바뀌어도 자주 신기 좋은 편입니다."),
                ("ne**road", "코디 폭을 넓히고 싶은 분께 기본으로 두기 좋은 신발입니다."),
            ],
            "bag": [
                ("ba**room", "자주 쓰는 소지품을 나눠 담기 좋고, 외출할 때 필요한 것만 챙기기 편합니다."),
                ("mi**carry", "데일리룩에 자연스럽게 어울려 출근이나 가벼운 외출에 쓰기 좋습니다."),
                ("su**pack", "부담스럽지 않은 크기감이라 손이 자주 가는 보조 가방으로 잘 맞습니다."),
                ("li**bag", "수납과 스타일을 같이 챙기고 싶은 분께 무난하게 어울리는 타입입니다."),
                ("do**pick", "계절이나 코디를 크게 타지 않는 디자인이라 활용도가 높습니다."),
            ],
            "beauty": [
                ("ye**skin", "데일리 루틴에 넣기 부담스럽지 않고 사용감 중심으로 고르기 좋은 타입입니다."),
                ("su**glow", "화장대에 두고 쓰기 좋고, 필요한 단계에 맞춰 꾸준히 사용하기 편합니다."),
                ("mi**care", "텍스처와 사용 목적이 명확해 처음 써보는 분도 루틴에 넣기 쉽습니다."),
                ("ha**tone", "과한 표현보다 매일 관리하는 느낌으로 접근하기 좋은 제품입니다."),
                ("no**kit", "휴대하거나 보관하기에도 부담이 적어 일상용으로 잘 맞습니다."),
            ],
            "kitchen": [
                ("ki**home", "주방 동선 안에서 자주 쓰는 물건을 꺼내기 쉽고 정리하기 좋은 타입입니다."),
                ("mi**cook", "세척과 보관을 생각했을 때 매일 쓰는 주방 아이템으로 부담이 적습니다."),
                ("su**dish", "조리나 식사 준비 과정에서 필요한 순간 바로 꺼내 쓰기 좋습니다."),
                ("li**meal", "공간을 크게 차지하지 않으면서도 쓰임새가 분명해 주방에 두기 좋습니다."),
                ("ha**prep", "반복해서 쓰는 용도에 맞춰 실용적으로 고르기 좋은 상품입니다."),
            ],
            "electronics": [
                ("te**room", "설치나 배치가 복잡하지 않아 일상 공간에 자연스럽게 더하기 좋습니다."),
                ("mi**plug", "필요한 기능이 한눈에 들어와 처음 쓰는 분도 부담이 적은 타입입니다."),
                ("li**desk", "책상이나 방 안에서 자주 쓰는 용도에 맞춰 두기 좋습니다."),
                ("ha**tech", "군더더기 없는 구성이라 데일리 기기로 쓰기 편합니다."),
                ("so**use", "공간을 많이 차지하지 않고 필요한 순간 바로 쓰기 좋은 느낌입니다."),
            ],
            "generic": [
                ("su**pick", "상품 이미지에서 보이는 핵심 기능이 분명해 처음 보는 사람도 쓰임새를 이해하기 쉽습니다."),
                ("mi**day", "일상에서 자주 쓰는 상황을 생각하면 부담 없이 선택하기 좋은 타입입니다."),
                ("li**use", "복잡한 설명보다 실제로 어디에 쓰면 좋은지 바로 떠오르는 점이 좋습니다."),
                ("no**fit", "옵션과 용도를 보고 내 생활에 맞춰 고르기 쉬운 구성입니다."),
                ("ha**best", "기본에 충실한 상품을 찾는 분께 어울리는 실용적인 선택입니다."),
            ],
        }
        cards = by_type.get(product_type, by_type["generic"])
        if product_type != "storage_furniture" and option_hint:
            card_id, card_text = cards[-1]
            cards = [*cards[:-1], (card_id, f"{card_text} {option_hint}")]
        return cards

    def _review_option_hint(self, product: ProductRecord) -> str:
        text = re.sub(r"\s+", " ", " ".join([product.options_text, " ".join(product.facts)])).strip()
        if not text:
            return ""
        parts = []
        if re.search(r"35\s*cm|50\s*cm|35폭|50폭", text, re.IGNORECASE):
            parts.append("폭이나 크기 옵션을 확인해 공간에 맞춰 선택할 수 있습니다.")
        if re.search(r"2\s*단|3\s*단|4\s*단|5\s*단", text):
            parts.append("단수 옵션을 보고 필요한 수납량에 맞춰 고르기 좋습니다.")
        if "서랍" in text:
            parts.append("오픈형과 서랍형처럼 보관 방식에 맞춰 고르는 흐름도 만들 수 있습니다.")
        return " ".join(parts)

    def _format_review_source_section(
        self,
        section_number: int,
        headline: str,
        subheadline: str,
        body: str,
        review_cards: list[tuple[str, str]],
        image_prompt: str,
    ) -> str:
        review_block = "\n\n".join(f"★★★★★  {card_id}\n{card_body}" for card_id, card_body in review_cards)
        return (
            f"섹션 {section_number}. 리뷰형 만족 포인트\n\n"
            "제목\n"
            f"{SECTION_DISPLAY_NAMES[DETAIL_REVIEW_SECTION_KEY]}\n\n"
            "메인 헤드라인\n"
            f"{headline}\n\n"
            "서브 카피\n"
            f"{subheadline}\n\n"
            "본문/불릿\n"
            f"{body}\n\n"
            f"{review_block}\n\n"
            "이미지 프롬프트\n"
            f"{image_prompt}"
        )

    def _section_text_is_contaminated(self, section: SectionPlan) -> bool:
        return self._contains_gpt_result_contamination(
            "\n".join(
                [
                    section.section_name,
                    section.headline,
                    section.subheadline,
                    section.body,
                    section.image_prompt,
                    section.overlay_text,
                    section.source_section_text,
                    " ".join(section.bullets),
                ]
            )
        )

    def _contains_gpt_result_contamination(self, text: str) -> bool:
        compact = re.sub(r"\s+", " ", (text or "")).strip()
        if not compact:
            return False
        markers = (
            "방금 부족했던 답변",
            "방금 답변",
            "원 요청",
            "원문 요청",
            "이미지 생성은 하지 말고",
            "GPT 기획 시도",
            "GPT 부분 응답",
            "자동 보정 결과",
            "문서 읽는 중",
            "생각 중",
            "스트리밍 중지",
            "Cropping and enlarging",
            "We can try inspecting",
            "Requesting image from URL",
        )
        return any(marker.lower() in compact.lower() for marker in markers)

    def _contains_1688_policy_contamination(self, text: str) -> bool:
        compact = re.sub(r"\s+", " ", (text or "")).strip()
        if not compact:
            return False
        lowered = compact.lower()
        if not any(anchor in lowered for anchor in ("1688", "alibaba", "알리바바", "중국어", "중국 판매", "중국 상세")):
            return False
        if any(negation in compact for negation in ("반영하지", "사용하지", "제외", "미반영", "참고 전용")):
            return False
        return any(marker.lower() in lowered for marker in DETAIL_COPY_POLICY_MARKERS)

    def _gpt_text_has_structured_section_headings(self, result_text: str) -> bool:
        text = (result_text or "").replace("\r\n", "\n").replace("\r", "\n")
        if len(text.strip()) < 250:
            return False
        heading_count = len(
            re.findall(r"(?im)^\s*(?:섹션|section)\s*\d+\s*[.\-:]?", text)
        )
        korean_count = len(re.findall(r"[가-힣]", text))
        return heading_count >= REQUIRED_SECTION_IMAGE_COUNT and korean_count >= 80

    def _gpt_text_has_any_section_heading(self, result_text: str) -> bool:
        text = (result_text or "").replace("\r\n", "\n").replace("\r", "\n")
        if len(text.strip()) < 80:
            return False
        heading_count = len(
            re.findall(r"(?im)^\s*(?:섹션|SECTION|section)\s*0?\d+\s*(?:[.)/:：\-]|\s)", text)
        )
        if heading_count < 1:
            return False
        korean_count = len(re.findall(r"[가-힣]", text))
        if korean_count < 30:
            return False
        content_markers = (
            "제목",
            "메인 헤드라인",
            "서브 카피",
            "본문",
            "이미지 프롬프트",
            "headline",
            "prompt",
        )
        return heading_count >= 2 or any(marker in text for marker in content_markers)

    def _gpt_text_has_completed_structured_plan(self, result_text: str) -> bool:
        text = (result_text or "").replace("\r\n", "\n").replace("\r", "\n")
        if not self._gpt_text_has_structured_section_headings(text):
            return False
        blocks = self._extract_structured_gpt_section_blocks(text)
        if len(blocks) >= REQUIRED_SECTION_IMAGE_COUNT:
            return True
        lowered = text.lower()
        completion_markers = (
            "섹션 10",
            "section 10",
            "section 010",
            "cta 클로징",
            "가정 / 추가",
            "추가 확인 필요",
            "다음 단계",
        )
        return len(blocks) >= REQUIRED_SECTION_IMAGE_COUNT and any(marker in lowered for marker in completion_markers)

    def _gpt_text_has_section_plan_signal(self, result_text: str) -> bool:
        if self._gpt_text_has_structured_section_headings(result_text):
            return True
        text = re.sub(r"\s+", " ", (result_text or "")).strip()
        if len(text) < 250:
            return False
        if self._gpt_text_is_incomplete_state(text):
            return False
        section_markers = (
            "히어로",
            "공감",
            "솔루션",
            "특징",
            "혜택",
            "사용법",
            "신뢰",
            "CTA",
            "구매",
            "section",
            "headline",
        )
        marker_count = sum(1 for marker in section_markers if marker.lower() in text.lower())
        korean_count = len(re.findall(r"[가-힣]", text))
        return marker_count >= 4 and korean_count >= 80

    def _gpt_text_is_incomplete_state(self, text: str) -> bool:
        compact = re.sub(r"\s+", " ", (text or "")).strip()
        if not compact:
            return True
        blocked = (
            "Requesting image from URL",
            "No response received",
            "No response provided",
            "문서 읽는 중",
            "생각 중",
            "분석 중",
            "이미지 분석 중",
            "개의 이미지 분석 중",
            "업로드 중",
            "파일 처리 중",
            "스트리밍 중지",
            "생각 중지됨",
            "Thinking stopped",
            "응답이 중지됨",
            "이미지 요청 중",
            "이미지 생성 중",
            "Generating",
            "Analyzing",
            "Reading",
            "Thinking",
        )
        return any(marker in compact for marker in blocked)

    def _font(self, size: int, bold: bool = False):
        from PIL import ImageFont

        if bold:
            candidates = [
                Path("C:/Windows/Fonts/malgunbd.ttf"),
                Path("C:/Windows/Fonts/NotoSansKR-VF.ttf"),
                Path("C:/Windows/Fonts/NanumGothicBold.ttf"),
            ]
        else:
            candidates = [
                Path("C:/Windows/Fonts/NotoSansKR-VF.ttf"),
                Path("C:/Windows/Fonts/malgun.ttf"),
                Path("C:/Windows/Fonts/NanumGothic.ttf"),
            ]
        for path in candidates:
            if path.exists():
                return ImageFont.truetype(str(path), size)
        return ImageFont.load_default()

    def _text_width(self, draw, text: str, font) -> int:
        box = draw.textbbox((0, 0), text, font=font)
        return max(0, box[2] - box[0])

    def _wrap_text(self, draw, text: str, font, max_width: int, max_lines: int | None = None) -> list[str]:
        normalized = re.sub(r"\s+", " ", (text or "").strip())
        if not normalized:
            return []

        lines: list[str] = []
        current = ""
        for token in re.findall(r"\S+\s*", normalized):
            trial = current + token
            if self._text_width(draw, trial.rstrip(), font) <= max_width:
                current = trial
                continue
            if current.strip():
                lines.append(current.rstrip())
            current = token
            while self._text_width(draw, current.rstrip(), font) > max_width and len(current.strip()) > 1:
                chunk = ""
                rest = current
                for char in rest:
                    trial_chunk = chunk + char
                    if chunk and self._text_width(draw, trial_chunk.rstrip(), font) > max_width:
                        break
                    chunk = trial_chunk
                if not chunk.strip():
                    break
                lines.append(chunk.rstrip())
                current = rest[len(chunk):].lstrip()
        if current.strip():
            lines.append(current.rstrip())

        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
        return lines

    def _draw_wrapped_text(
        self,
        draw,
        xy: tuple[int, int],
        text: str,
        font,
        fill: tuple[int, int, int] | str,
        max_width: int,
        line_spacing: int = 8,
        max_lines: int | None = None,
    ) -> int:
        x, y = xy
        for line in self._wrap_text(draw, text, font, max_width, max_lines=max_lines):
            draw.text((x, y), line, font=font, fill=fill)
            box = draw.textbbox((x, y), line, font=font)
            y += max(1, box[3] - box[1]) + line_spacing
        return y

    def _draw_chip(self, draw, xy: tuple[int, int], text: str, font, fill, text_fill, padding: tuple[int, int] = (18, 8)) -> tuple[int, int, int, int]:
        x, y = xy
        width = self._text_width(draw, text, font) + padding[0] * 2
        box = (x, y, x + width, y + font.size + padding[1] * 2)
        draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=fill)
        draw.text((x + padding[0], y + padding[1] - 1), text, font=font, fill=text_fill)
        return box

    def _draw_shadow(self, canvas, box: tuple[int, int, int, int], radius: int = 28, alpha: int = 42, blur: int = 18, offset: tuple[int, int] = (0, 10)) -> None:
        from PIL import Image, ImageDraw, ImageFilter

        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow = ImageDraw.Draw(layer)
        ox, oy = offset
        shadow.rounded_rectangle(
            (box[0] + ox, box[1] + oy, box[2] + ox, box[3] + oy),
            radius=radius,
            fill=(0, 0, 0, alpha),
        )
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
        canvas.paste(layer, (0, 0), layer)

    def _draw_card(self, canvas, box: tuple[int, int, int, int], fill=(255, 255, 255), outline=(226, 232, 240), radius: int = 28) -> None:
        from PIL import ImageDraw

        draw = ImageDraw.Draw(canvas)
        self._draw_shadow(canvas, box, radius=radius, alpha=28, blur=16, offset=(0, 8))
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)

    def _source_image_paths(self, product: ProductRecord) -> list[Path]:
        source_dir = product.output_dir / "source_images"
        paths = [path for path in product.source_image_paths if path.exists() and path.stat().st_size > 0]
        candidates: list[Path] = []
        for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            candidates.extend(source_dir.rglob(pattern))
        merged: list[Path] = []
        seen: set[str] = set()
        for path in [*paths, *sorted(candidates)]:
            if not path.exists() or path.stat().st_size <= 0:
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(path)
        return merged

    def _open_product_image(self, path: Path):
        from PIL import Image, ImageOps

        with Image.open(path) as image:
            return ImageOps.exif_transpose(image).convert("RGBA")

    def _gpt_attachment_source_paths(self, product: ProductRecord) -> list[Path]:
        from PIL import Image

        ranked: list[tuple[str, int, int, Path]] = []
        for path in self._source_image_paths(product):
            if not path.exists() or path.stat().st_size <= 0:
                continue
            try:
                with Image.open(path) as image:
                    width, height = image.size
            except Exception:
                continue
            if "page_capture" in path.name.lower() and height < 12000:
                continue
            if width < 240 or height < 240:
                continue
            name = path.name.lower()
            role_rank = self._gpt_attachment_role_rank(path)
            area_score = min(width * height, 4_000_000)
            origin = "1688" if "1688" in [part.lower() for part in path.parts] else "ownerclan"
            ranked.append((origin, role_rank, -area_score, path))

        by_origin: dict[str, list[tuple[int, int, Path]]] = {}
        for origin, role_rank, area_score, path in sorted(ranked, key=lambda item: (item[0] != "ownerclan", item[1], item[2])):
            by_origin.setdefault(origin, []).append((role_rank, area_score, path))

        domestic_items = by_origin.get("ownerclan", [])
        secondary_items = by_origin.get("1688", [])

        domestic_selected: list[Path] = []
        for role_rank, _, path in domestic_items:
            if role_rank != 0:
                continue
            if path not in domestic_selected:
                domestic_selected.append(path)
            if len(domestic_selected) >= GPT_ATTACHMENT_DOMESTIC_THUMBNAIL_LIMIT:
                break
        for role_rank, _, path in domestic_items:
            if len(domestic_selected) >= GPT_ATTACHMENT_DOMESTIC_IMAGE_LIMIT:
                break
            if role_rank == 0 or path in domestic_selected:
                continue
            domestic_selected.append(path)
        for _, _, path in domestic_items:
            if len(domestic_selected) >= GPT_ATTACHMENT_DOMESTIC_IMAGE_LIMIT:
                break
            if path not in domestic_selected:
                domestic_selected.append(path)

        if not secondary_items:
            return domestic_selected[:GPT_ATTACHMENT_DOMESTIC_IMAGE_LIMIT]

        secondary_selected: list[Path] = []
        for _, _, path in secondary_items:
            if path not in secondary_selected:
                secondary_selected.append(path)
            if len(secondary_selected) >= GPT_ATTACHMENT_1688_IMAGE_LIMIT:
                break
        return (domestic_selected[:GPT_ATTACHMENT_DOMESTIC_IMAGE_LIMIT] + secondary_selected[:GPT_ATTACHMENT_1688_IMAGE_LIMIT])[
            :GPT_ATTACHMENT_IMAGE_LIMIT
        ]

    def _gpt_attachment_role_rank(self, path: Path) -> int:
        name = path.name.lower()
        if "page_capture" in name:
            return 3
        if "primary" in name or "thumb" in name:
            return 0
        if "detail" in name or "capture_derived" in name:
            return 1
        return 2

    def _prepare_gpt_attachment_images(self, product: ProductRecord, run_stamp: str) -> list[Path]:
        from PIL import Image, ImageOps

        attachment_dir = product.output_dir / "gpt_attachments"
        attachment_dir.mkdir(parents=True, exist_ok=True)
        for old_file in attachment_dir.glob("*"):
            if old_file.is_file() and old_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                old_file.unlink(missing_ok=True)

        branded_dir = product.output_dir / BRAND_LOGO_REFERENCE_DIR_NAME
        branded_dir.mkdir(parents=True, exist_ok=True)
        for old_file in branded_dir.glob("*"):
            if old_file.is_file() and old_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".json"}:
                old_file.unlink(missing_ok=True)

        brand_logo_path = self._brand_logo_source_path()
        brand_logo_records: list[dict[str, object]] = []
        prepared: list[Path] = []
        for index, source_path in enumerate(self._gpt_attachment_source_paths(product), start=1):
            try:
                with Image.open(source_path) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.thumbnail((1400, 2400), Image.Resampling.LANCZOS)
                    original_image = image.copy()
                    preview_path = branded_dir / f"branded_reference_{run_stamp}_{index:02d}.jpg"
                    changed_pixels = 0
                    if brand_logo_path is not None:
                        image = self._apply_brand_logo_to_reference_image(image, brand_logo_path, branded_dir, run_stamp, index, product)
                        changed_pixels = self._brand_logo_changed_pixel_count(original_image, image)
                    target = attachment_dir / f"attachment_{run_stamp}_{index:02d}.jpg"
                    image.save(target, format="JPEG", quality=92, optimize=True)
                if self._is_valid_image_file(target):
                    prepared.append(target)
                    brand_logo_records.append(
                        {
                            "index": index,
                            "source_path": str(source_path),
                            "attachment_path": str(target),
                            "branded_preview_path": str(preview_path) if preview_path.exists() else "",
                            "logo_applied": bool(brand_logo_path is not None and changed_pixels > 0),
                            "changed_pixels": changed_pixels,
                        }
                    )
            except Exception:
                continue
        self._write_brand_logo_reference_manifest(product, branded_dir, brand_logo_path, brand_logo_records)
        return prepared

    def _brand_logo_source_path(self) -> Path | None:
        configured_path = Path(str(getattr(self, "brand_logo_path", "") or "").strip())
        candidate_paths = [configured_path] if str(configured_path) not in {"", "."} else []
        candidate_paths.extend(BRAND_LOGO_FILE_CANDIDATES)
        seen: set[str] = set()
        for logo_path in candidate_paths:
            try:
                key = str(logo_path.resolve()).lower()
            except Exception:
                key = str(logo_path).lower()
            if key in seen:
                continue
            seen.add(key)
            if not logo_path.exists() or logo_path.stat().st_size <= 0:
                continue
            if self._is_valid_image_file(logo_path):
                return logo_path
        return None

    def _apply_brand_logo_to_reference_image(
        self,
        image,
        logo_path: Path,
        branded_dir: Path,
        run_stamp: str,
        index: int,
        product: ProductRecord | None = None,
    ):
        try:
            branded = self._render_surface_brand_logo(image, logo_path, product)
        except Exception:
            return image
        try:
            preview_path = branded_dir / f"branded_reference_{run_stamp}_{index:02d}.jpg"
            branded.save(preview_path, format="JPEG", quality=92, optimize=True)
        except Exception:
            pass
        return branded

    def _brand_logo_changed_pixel_count(self, before, after) -> int:
        try:
            from PIL import ImageChops

            diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB")).convert("L")
            return sum(1 for value in diff.getdata() if value > 4)
        except Exception:
            return 0

    def _brand_logo_reference_check_prompt(self, product: ProductRecord, records: list[dict[str, object]]) -> str:
        applied_count = len([record for record in records if record.get("logo_applied")])
        return (
            "브랜드 로고 적용 검수 요청.\n"
            "첨부/저장된 로고 적용 상품 이미지를 보고 아래 기준만 판단해줘.\n"
            f"상품명: {product.product_name or product.title or product.code}\n"
            f"검수 대상 이미지: {len(records)}장 / 로고 변화 감지: {applied_count}장\n\n"
            "검수 기준:\n"
            "- KKEURONG MAJE 로고가 상품 표면 구석에 작고 자연스럽게 붙었는지 확인.\n"
            "- 로고가 배경, 사람 얼굴/피부, 상세 스펙 표, 카드, 패키지 문구 위에 떠 있으면 부적합.\n"
            "- 로고 때문에 상품 색상, 소재, 형태, 옵션, 비율이 바뀌면 부적합.\n"
            "- 상품 표면이 불명확한 이미지는 로고가 없거나 약하게 처리돼도 적합.\n"
            "- 공급사 로고, 중국어, 워터마크, 치수선은 여전히 금지.\n\n"
            "출력은 PASS/REVIEW 중 하나와 이미지 번호별 짧은 사유만 적어줘."
        )

    def _write_brand_logo_reference_manifest(
        self,
        product: ProductRecord,
        branded_dir: Path,
        brand_logo_path: Path | None,
        records: list[dict[str, object]],
    ) -> Path:
        branded_dir.mkdir(parents=True, exist_ok=True)
        prompt = self._brand_logo_reference_check_prompt(product, records)
        prompt_path = branded_dir / "brand_logo_check_prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        manifest_path = branded_dir / "brand_logo_manifest.json"
        payload = {
            "version": BRAND_LOGO_MANIFEST_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "product_code": product.code,
            "product_name": product.product_name,
            "logo_path": str(brand_logo_path or ""),
            "check_prompt_path": str(prompt_path),
            "records": records,
        }
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest_path

    def _brand_logo_check_status_from_result(self, result_text: str) -> str:
        normalized = (result_text or "").strip().upper()
        first_line = normalized.splitlines()[0].strip() if normalized else ""
        if first_line.startswith("ERROR"):
            return "ERROR"
        if first_line.startswith("PASS") or first_line.startswith("통과"):
            return "PASS"
        if first_line.startswith("REVIEW") or first_line.startswith("검토"):
            return "REVIEW"
        if re.search(r"\bPASS\b", normalized) and not re.search(r"\bREVIEW\b", normalized):
            return "PASS"
        if re.search(r"\bREVIEW\b", normalized) or "검토" in normalized or "수정" in normalized:
            return "REVIEW"
        return "UNKNOWN"

    def _write_brand_logo_reference_check_result(self, product: ProductRecord, result_text: str, status: str) -> None:
        branded_dir = product.output_dir / BRAND_LOGO_REFERENCE_DIR_NAME
        manifest_path = branded_dir / "brand_logo_manifest.json"
        result_path = branded_dir / "brand_logo_check_result.txt"
        result_path.write_text(result_text.strip(), encoding="utf-8")
        manifest = self._read_json_file(manifest_path)
        if not isinstance(manifest, dict):
            manifest = {}
        manifest["check_status"] = status
        manifest["check_result_path"] = str(result_path)
        manifest["check_result_excerpt"] = self._compact_error_text(result_text, 500)
        manifest["checked_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_json_file(manifest_path, manifest)

    def _wait_for_brand_logo_check_response(self, page, previous_text: str = "", timeout_seconds: int = 240) -> str:
        deadline = time.time() + timeout_seconds
        previous_text = (previous_text or "").strip()
        last_text = ""
        stable_count = 0
        while time.time() < deadline:
            self._raise_if_user_requested_stop_or_skip()
            page.wait_for_timeout(2500)
            text, busy = self._latest_gpt_text(page)
            text = (text or "").strip()
            if previous_text and text == previous_text:
                continue
            if not text or re.fullmatch(r"https?://\S+", text):
                continue
            if self._gpt_text_is_non_result_noise(text) or self._gpt_text_is_incomplete_state(text):
                continue
            if text == last_text:
                stable_count += 1
            else:
                last_text = text
                stable_count = 0
            if stable_count >= 2 and not busy and len(text) >= 4:
                return text
        raise RuntimeError("브랜드 로고 ChatGPT 검수 응답을 제한 시간 안에 받지 못했습니다.")

    def _run_brand_logo_reference_check(self, page, product: ProductRecord, attachment_paths: list[Path]) -> str:
        branded_dir = product.output_dir / BRAND_LOGO_REFERENCE_DIR_NAME
        manifest_path = branded_dir / "brand_logo_manifest.json"
        prompt_path = branded_dir / "brand_logo_check_prompt.txt"
        manifest = self._read_json_file(manifest_path)
        records = manifest.get("records") if isinstance(manifest, dict) else []
        if not prompt_path.exists() or not isinstance(records, list):
            return "SKIP"
        if not any(isinstance(record, dict) and record.get("logo_applied") for record in records):
            return "SKIP"
        try:
            previous_text, _ = self._latest_gpt_text(page)
            prompt = prompt_path.read_text(encoding="utf-8", errors="ignore").strip()
            self._send_prompt_to_gpt_page(page, prompt, attachment_paths=attachment_paths, image_mode=False)
            result_text = self._wait_for_brand_logo_check_response(page, previous_text=previous_text)
        except (AutomationStopRequested, AutomationSkipRequested):
            raise
        except Exception as exc:
            status = "ERROR"
            result_text = f"ERROR\n{self._compact_error_text(str(exc), 500)}"
            self._write_brand_logo_reference_check_result(product, result_text, status)
            return status
        status = self._brand_logo_check_status_from_result(result_text)
        self._write_brand_logo_reference_check_result(product, result_text, status)
        return status

    def _render_surface_brand_logo(self, image, logo_path: Path, product: ProductRecord | None = None):
        try:
            import cv2
            import numpy as np
            from PIL import Image
        except Exception:
            return image

        logo = self._load_brand_logo_rgba(logo_path)
        if logo is None:
            return image
        base = image.convert("RGBA")
        base_rgb = np.asarray(base.convert("RGB"))
        if self._brand_logo_reference_looks_informational(base_rgb, cv2, np):
            return image
        if self._brand_logo_product_needs_body_surface_guard(product) and self._brand_logo_reference_has_large_skin_surface(base_rgb, cv2, np):
            return image
        mask = self._foreground_mask_for_brand_logo(base_rgb, cv2, np)
        quad = self._brand_logo_quad_from_mask(mask, logo.size, base_rgb, cv2, np)
        if quad is None:
            return image
        logo = self._distort_logo_for_surface(logo, quad, np, cv2)
        warped = self._warp_logo_to_quad(logo, base.size, quad, cv2, np)
        if warped is None:
            return image
        result = self._blend_surface_logo(base, warped, mask, cv2, np)
        return Image.fromarray(result, mode="RGBA").convert("RGB")

    def _load_brand_logo_rgba(self, logo_path: Path):
        try:
            import numpy as np
            from PIL import Image

            with Image.open(logo_path) as logo_image:
                logo_image = logo_image.convert("RGBA")
            data = np.asarray(logo_image)
            rgb = data[:, :, :3].astype(np.int16)
            alpha = data[:, :, 3]
            non_white = (np.max(np.abs(rgb - 255), axis=2) > 18) & (alpha > 0)
            ys, xs = np.where(non_white)
            if len(xs) == 0:
                return None
            pad = 10
            left = max(0, int(xs.min()) - pad)
            top = max(0, int(ys.min()) - pad)
            right = min(logo_image.width, int(xs.max()) + pad + 1)
            bottom = min(logo_image.height, int(ys.max()) + pad + 1)
            cropped = logo_image.crop((left, top, right, bottom))
            data = np.asarray(cropped).copy()
            rgb = data[:, :, :3].astype(np.int16)
            alpha = data[:, :, 3]
            ink_alpha = np.clip((255 - np.min(rgb, axis=2)) * 2.3, 0, 255).astype(np.uint8)
            data[:, :, :3] = (14, 24, 38)
            data[:, :, 3] = np.minimum(ink_alpha, alpha)
            data[:, :, 3][data[:, :, 3] < 24] = 0
            return self._compact_brand_logo_rgba(Image.fromarray(data, mode="RGBA"), np)
        except Exception:
            return None

    def _compact_brand_logo_rgba(self, logo, np):
        from PIL import Image, ImageDraw

        data = np.asarray(logo)
        alpha = data[:, :, 3]
        row_strength = alpha.sum(axis=1)
        if row_strength.max() <= 0:
            return logo
        threshold = max(float(row_strength.max()) * 0.045, 64.0)
        active_rows = row_strength > threshold
        segments: list[tuple[int, int]] = []
        start = None
        for index, is_active in enumerate(active_rows):
            if is_active and start is None:
                start = index
            elif not is_active and start is not None:
                segments.append((start, index))
                start = None
        if start is not None:
            segments.append((start, len(active_rows)))
        merged: list[tuple[int, int]] = []
        for top, bottom in segments:
            if merged and top - merged[-1][1] <= 8:
                merged[-1] = (merged[-1][0], bottom)
            else:
                merged.append((top, bottom))
        segments = [(top, bottom) for top, bottom in merged if bottom - top >= max(8, logo.height * 0.045)]
        if len(segments) < 2:
            return logo

        def crop_band(top: int, bottom: int):
            band_alpha = alpha[top:bottom, :]
            column_strength = band_alpha.sum(axis=0)
            active_columns = np.where(column_strength > max(float(column_strength.max()) * 0.02, 16.0))[0]
            if len(active_columns) == 0:
                return None
            left = max(0, int(active_columns.min()) - 4)
            right = min(logo.width, int(active_columns.max()) + 5)
            return logo.crop((left, max(0, top - 3), right, min(logo.height, bottom + 3)))

        primary = crop_band(*segments[0])
        secondary = crop_band(*segments[1])
        if primary is None or secondary is None or primary.width <= 0 or secondary.width <= 0:
            return logo
        target_secondary_height = max(12, int(primary.height * 0.58))
        secondary = secondary.copy()
        secondary.thumbnail((int(secondary.width * target_secondary_height / max(1, secondary.height)), target_secondary_height), Image.Resampling.LANCZOS)
        gap = max(8, int(primary.height * 0.22))
        padding = max(14, int(primary.height * 0.18))
        canvas_width = primary.width + gap + secondary.width + padding * 2
        underline_width = max(16, int((primary.width + secondary.width) * 0.30))
        underline_height = max(2, int(primary.height * 0.035))
        underline_gap = max(3, int(primary.height * 0.08))
        canvas_height = max(primary.height, secondary.height) + padding * 2 + underline_gap + underline_height
        compact = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        plate = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(plate)
        radius = max(8, int(canvas_height * 0.26))
        border_width = max(2, int(canvas_height * 0.028))
        draw.rounded_rectangle(
            (1, 1, canvas_width - 2, canvas_height - 2),
            radius=radius,
            fill=(248, 248, 242, 104),
            outline=(14, 24, 38, 58),
            width=border_width,
        )
        compact.alpha_composite(plate)
        text_height = max(primary.height, secondary.height)
        text_top = padding
        compact.alpha_composite(primary, (padding, text_top + (text_height - primary.height) // 2))
        compact.alpha_composite(secondary, (padding + primary.width + gap, text_top + (text_height - secondary.height) // 2))
        underline = Image.new("RGBA", (underline_width, underline_height), (14, 24, 38, 210))
        compact.alpha_composite(underline, ((canvas_width - underline_width) // 2, text_top + text_height + underline_gap))
        return compact

    def _foreground_mask_for_brand_logo(self, rgb_array, cv2, np):
        height, width = rgb_array.shape[:2]
        patch = max(4, min(width, height) // 24)
        corners = np.concatenate(
            [
                rgb_array[:patch, :patch].reshape(-1, 3),
                rgb_array[:patch, -patch:].reshape(-1, 3),
                rgb_array[-patch:, :patch].reshape(-1, 3),
                rgb_array[-patch:, -patch:].reshape(-1, 3),
            ],
            axis=0,
        )
        background = np.median(corners, axis=0)
        distance = np.linalg.norm(rgb_array.astype(np.float32) - background.astype(np.float32), axis=2)
        mask = (distance > 28).astype(np.uint8) * 255
        kernel_size = max(3, min(width, height) // 90)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def _brand_logo_reference_looks_informational(self, rgb_array, cv2, np) -> bool:
        height, width = rgb_array.shape[:2]
        if width < 220 or height < 220:
            return False
        gray = (
            rgb_array[:, :, 0].astype(np.float32) * 0.299
            + rgb_array[:, :, 1].astype(np.float32) * 0.587
            + rgb_array[:, :, 2].astype(np.float32) * 0.114
        ).astype(np.uint8)
        blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
        edges = cv2.Canny(blurred, 45, 140)
        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180,
            threshold=max(42, min(width, height) // 9),
            minLineLength=max(120, int(min(width, height) * 0.34)),
            maxLineGap=10,
        )
        horizontal = 0
        vertical = 0
        if lines is not None:
            for x1, y1, x2, y2 in lines[:, 0, :]:
                dx = float(x2 - x1)
                dy = float(y2 - y1)
                length = float(np.hypot(dx, dy))
                if length < min(width, height) * 0.30:
                    continue
                angle = abs(float(np.degrees(np.arctan2(dy, dx))))
                angle = min(angle, abs(180.0 - angle))
                if angle <= 5.0:
                    horizontal += 1
                elif angle >= 85.0:
                    vertical += 1
        saturation = (rgb_array.max(axis=2).astype(np.float32) - rgb_array.min(axis=2).astype(np.float32)) / 255.0
        bottom_band = saturation[int(height * 0.78) :, :]
        bottom_saturated = bool(bottom_band.size and float(np.mean(bottom_band > 0.34)) > 0.34)
        footer_band = saturation[int(height * 0.82) :, :]
        wide_saturated_footer = False
        if footer_band.size:
            saturated_rows = np.mean(footer_band > 0.34, axis=1)
            wide_saturated_footer = int(np.count_nonzero(saturated_rows > 0.58)) >= max(8, int(len(saturated_rows) * 0.12))
        top_band = gray[: int(height * 0.24), :]
        top_text_like = bool(top_band.size and float(top_band.std()) / 255.0 > 0.20)
        edge_density = float(np.mean(edges > 0))
        white_background_ratio = float(np.mean(gray > 235))
        top_dark_band_ratio = float(np.mean(gray[: max(1, int(height * 0.12)), :] < 55))
        top_dark_rows = int(np.count_nonzero(np.mean(gray[: max(1, int(height * 0.22)), :] < 55, axis=1) > 0.45))
        sparse_document_page = (
            white_background_ratio > 0.72
            and top_dark_band_ratio > 0.55
            and top_dark_rows >= max(18, int(height * 0.035))
            and float(np.mean(saturation)) < 0.08
            and edge_density < 0.045
        )
        quick_mask = self._foreground_mask_for_brand_logo(rgb_array, cv2, np)
        mask_ratio = float(np.count_nonzero(quick_mask)) / float(max(1, quick_mask.size))
        dark_background_ratio = float(np.mean(gray < 72))
        bright_pixels = gray > 190
        dark_nearby = cv2.dilate((gray < 95).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
        bright_on_dark_ratio = float(np.mean(bright_pixels & dark_nearby))
        contours, _ = cv2.findContours(quick_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        display_contours = [contour for contour in contours if cv2.contourArea(contour) > 300]
        multi_object_display = mask_ratio > 0.42 and edge_density > 0.052 and len(display_contours) >= 7
        collage_or_guide = (
            (len(display_contours) >= 10 and edge_density > 0.050 and top_text_like)
            or (mask_ratio > 0.68 and len(display_contours) >= 5 and edge_density > 0.030 and top_text_like)
        )
        annotated_use_scene = mask_ratio > 0.50 and len(display_contours) >= 4 and edge_density > 0.028 and top_text_like
        dark_annotation_scene = dark_background_ratio > 0.82 and bright_on_dark_ratio > 0.010 and mask_ratio < 0.30
        hsv = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2HSV)
        hue = hsv[:, :, 0]
        warm_surface = (hue >= 8) & (hue <= 38) & (hsv[:, :, 1] > 65) & (hsv[:, :, 2] > 80)
        central_warm_ratio = float(np.mean(warm_surface[int(height * 0.28) : int(height * 0.88), int(width * 0.18) : int(width * 0.82)]))
        warm_contents_scene = dark_background_ratio > 0.35 and mask_ratio > 0.70 and central_warm_ratio > 0.50
        warm_bokeh = (hue >= 8) & (hue <= 38) & (hsv[:, :, 1] > 35) & (hsv[:, :, 2] > 160)
        warm_bokeh_scene = float(np.mean(warm_bokeh)) > 0.48 and edge_density < 0.030 and mask_ratio > 0.50
        top_mask_ratio = float(np.mean(quick_mask[: height // 2, :] > 0))
        bottom_mask_ratio = float(np.mean(quick_mask[height // 2 :, :] > 0))
        top_bright_ratio = float(np.mean(gray[: height // 2, :] > 170))
        bottom_bright_ratio = float(np.mean(gray[height // 2 :, :] > 170))
        dark_reflection_scene = (
            dark_background_ratio > 0.55
            and mask_ratio > 0.35
            and bottom_mask_ratio >= top_mask_ratio * 0.75
            and top_bright_ratio > 0.08
            and bottom_bright_ratio < 0.05
        )
        panel_like = horizontal + vertical >= 6 and horizontal >= 2
        return bool(sparse_document_page or panel_like or wide_saturated_footer or multi_object_display or collage_or_guide or annotated_use_scene or dark_annotation_scene or warm_contents_scene or warm_bokeh_scene or dark_reflection_scene or (bottom_saturated and horizontal + vertical >= 3))

    def _brand_logo_product_needs_body_surface_guard(self, product: ProductRecord | None) -> bool:
        if product is None:
            return False
        text = " ".join(
            [
                product.product_name or "",
                product.title or "",
                product.category or "",
                product.options_text or "",
                product.source_text or "",
            ]
        ).lower()
        body_surface_keywords = (
            "\uc8fc\uc5bc\ub9ac",
            "\uc96c\uc5bc\ub9ac",
            "\uc545\uc138",
            "\uc561\uc138",
            "\ubc1c\ucc0c",
            "\ud314\ucc0c",
            "\ubaa9\uac78\uc774",
            "\ubc18\uc9c0",
            "\uadc0\uac78\uc774",
            "\ud53c\uc5b4\uc2f1",
            "anklet",
            "bracelet",
            "necklace",
            "ring",
            "earring",
        )
        return any(keyword in text for keyword in body_surface_keywords)

    def _brand_logo_reference_has_large_skin_surface(self, rgb_array, cv2, np) -> bool:
        if rgb_array.size == 0:
            return False
        ycrcb = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2YCrCb)
        hsv = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2HSV)
        y_channel = ycrcb[:, :, 0]
        cr_channel = ycrcb[:, :, 1]
        cb_channel = ycrcb[:, :, 2]
        hue = hsv[:, :, 0]
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        skin_like = (
            (cr_channel > 133)
            & (cr_channel < 173)
            & (cb_channel > 77)
            & (cb_channel < 127)
            & (y_channel > 45)
            & (y_channel < 235)
            & (hue < 25)
            & (saturation > 35)
            & (saturation < 190)
            & (value > 50)
            & (value < 245)
        )
        skin_ratio = float(np.mean(skin_like))
        if skin_ratio < 0.42:
            return False
        gray = (
            rgb_array[:, :, 0].astype(np.float32) * 0.299
            + rgb_array[:, :, 1].astype(np.float32) * 0.587
            + rgb_array[:, :, 2].astype(np.float32) * 0.114
        ).astype(np.uint8)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (0, 0), 1.0), 45, 140)
        edge_density = float(np.mean(edges > 0))
        return edge_density < 0.045

    def _brand_logo_quad_from_mask(self, mask, logo_size: tuple[int, int], rgb_array, cv2, np):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = [contour for contour in contours if cv2.contourArea(contour) > 1800]
        if not contours:
            return None
        contour = max(contours, key=cv2.contourArea)
        x, y, width, height = cv2.boundingRect(contour)
        mask_height, mask_width = mask.shape[:2]
        mask_ratio = float(np.count_nonzero(mask)) / float(max(1, mask_width * mask_height))
        if width > mask_width * 0.92 and height > mask_height * 0.92 and mask_ratio > 0.55:
            return self._brand_logo_quad_from_image_regions(rgb_array, logo_size, cv2, np)
        if width < 120 or height < 120:
            return None
        logo_width, logo_height = logo_size
        logo_ratio = logo_height / max(1, logo_width)
        target_width = int(max(56, min(width * 0.115, 98)))
        target_height = int(max(20, min(target_width * logo_ratio, height * 0.09)))
        rect = cv2.minAreaRect(contour)
        angle = float(rect[-1])
        if angle < -45:
            angle += 90
        if abs(angle) > 28:
            angle = 0
        radians = np.deg2rad(angle)
        cos_value = float(np.cos(radians))
        sin_value = float(np.sin(radians))
        half_width = target_width / 2
        half_height = target_height / 2

        def make_points(center_x: float, center_y: float) -> list[tuple[float, float]]:
            points = []
            for px, py in [(-half_width, -half_height), (half_width, -half_height), (half_width, half_height), (-half_width, half_height)]:
                points.append((center_x + px * cos_value - py * sin_value, center_y + px * sin_value + py * cos_value))
            return points

        luma = (
            rgb_array[:, :, 0].astype(np.float32) * 0.299
            + rgb_array[:, :, 1].astype(np.float32) * 0.587
            + rgb_array[:, :, 2].astype(np.float32) * 0.114
        )
        gray = luma.astype(np.uint8)
        edge_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        edge_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge = np.sqrt(edge_x * edge_x + edge_y * edge_y)
        saturation = (rgb_array.max(axis=2).astype(np.float32) - rgb_array.min(axis=2).astype(np.float32)) / 255.0
        hsv = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2HSV)
        hue = hsv[:, :, 0]
        warm_surface = (hue >= 8) & (hue <= 38) & (hsv[:, :, 1] > 65) & (hsv[:, :, 2] > 80)
        dark_background_ratio = float(np.mean(luma < 72))
        candidate_fractions = [
            (0.64, 0.46),
            (0.52, 0.78),
            (0.52, 0.88),
            (0.46, 0.62),
            (0.58, 0.68),
            (0.38, 0.50),
            (0.68, 0.32),
            (0.70, 0.56),
        ]
        corner_candidates = [(x + width * fx, y + height * fy) for fx, fy in candidate_fractions]
        best_points = None
        best_center = None
        best_score = -1.0
        for center_x, center_y in corner_candidates:
            candidate_points = make_points(center_x, center_y)
            point_array = np.asarray(candidate_points, dtype=np.float32)
            left = max(0, int(np.floor(point_array[:, 0].min())))
            right = min(mask_width, int(np.ceil(point_array[:, 0].max())) + 1)
            top = max(0, int(np.floor(point_array[:, 1].min())))
            bottom = min(mask_height, int(np.ceil(point_array[:, 1].max())) + 1)
            if right <= left or bottom <= top:
                continue
            region = mask[top:bottom, left:right]
            mask_score = float(np.count_nonzero(region)) / float(max(1, region.size))
            local_edge = float(edge[top:bottom, left:right].mean()) / 255.0
            local_luma_std = float(luma[top:bottom, left:right].std()) / 255.0
            local_saturation = float(saturation[top:bottom, left:right].mean())
            local_warm_surface = float(np.mean(warm_surface[top:bottom, left:right]))
            smoothness = 1.0 / (1.0 + local_edge * 3.4)
            flatness = 1.0 / (1.0 + local_luma_std * 5.8)
            x_norm = (center_x - x) / max(1, width)
            y_norm = (center_y - y) / max(1, height)
            global_x_norm = center_x / max(1, mask_width)
            upper_panel_bias = 1.0 - min(
                1.0,
                abs(x_norm - 0.64) * 1.45
                + abs(y_norm - 0.46) * 1.30,
            )
            lower_lip_bias = 1.0 - min(
                1.0,
                abs(x_norm - 0.52) * 1.30
                + abs(y_norm - 0.84) * 1.22,
            )
            product_surface_bias = max(upper_panel_bias, lower_lip_bias * 0.96)
            clean_surface = (
                smoothness * 0.46
                + flatness * 0.44
                + (1.0 - min(1.0, local_saturation * 4.2)) * 0.22
            )
            object_signal = min(1.0, local_edge * 3.8 + local_luma_std * 2.4 + local_saturation * 0.65)
            score = (
                mask_score * 0.46
                + product_surface_bias * 0.66
                + clean_surface * 0.40
            )
            if y_norm > 0.72 and local_saturation < 0.10 and dark_background_ratio <= 0.45:
                score += 0.34
            if y_norm > 0.70 and local_saturation < 0.18 and dark_background_ratio > 0.45:
                score *= 0.035
            if y_norm > 0.72 and local_luma_std > 0.14 and local_saturation > 0.11:
                score *= 0.86
            if y_norm < 0.60 and (local_edge > 0.24 or local_luma_std > 0.18):
                score *= 0.70
            if 0.54 <= y_norm <= 0.76 and local_saturation > 0.24 and object_signal > 0.55:
                score += 0.28
            if local_saturation > 0.52 and y_norm > 0.66 and object_signal > 0.80:
                score += 0.22
            elif local_saturation > 0.45:
                score *= 0.78
            elif local_saturation > 0.30 and y_norm > 0.70:
                score *= 0.82
            if y_norm > 0.84 and local_saturation < 0.06 and local_luma_std < 0.16 and local_edge < 0.32:
                score *= 0.55
            if local_edge < 0.055 and local_luma_std < 0.055 and y_norm < 0.68:
                score *= 0.22
            if object_signal < 0.28:
                score *= 0.42
            if dark_background_ratio > 0.35 and y_norm > 0.50 and local_warm_surface > 0.32 and local_saturation > 0.22:
                score *= 0.10
            if y_norm < 0.64 and local_saturation < 0.16 and local_edge < 0.15 and local_luma_std < 0.10 and global_x_norm > 0.68:
                score *= 0.30
            edge_clearance = min(
                point_array[:, 0].min() / max(1, mask_width),
                (mask_width - point_array[:, 0].max()) / max(1, mask_width),
                point_array[:, 1].min() / max(1, mask_height),
                (mask_height - point_array[:, 1].max()) / max(1, mask_height),
            )
            if edge_clearance < 0.035:
                score *= 0.55
            if x_norm > 0.70 and y_norm < 0.70 and clean_surface > 0.74 and local_saturation < 0.08:
                score *= 0.24
            if x_norm > 0.74 and local_edge < 0.035 and local_luma_std < 0.045:
                score *= 0.18
            if (center_y / max(1, mask_height)) > 0.66 and (center_x / max(1, mask_width)) < 0.42:
                score *= 0.48
            if score > best_score:
                best_score = score
                best_points = candidate_points
                best_center = (center_x, center_y)
        if best_points is None or best_score < 0.28:
            return None

        if best_center is not None:
            center_x, center_y = best_center
            local_angle = self._brand_logo_local_surface_angle(gray, center_x, center_y, target_width, target_height, cv2, np)
            global_angle = self._brand_logo_local_surface_angle(gray, mask_width / 2, mask_height / 2, int(mask_width * 0.62), int(mask_height * 0.62), cv2, np)
            surface_angle = local_angle if abs(local_angle) >= 2.5 else (global_angle if abs(global_angle) >= 2.5 else angle)
            radians = np.deg2rad(surface_angle)
            cos_value = float(np.cos(radians))
            sin_value = float(np.sin(radians))
            points = make_points(center_x, center_y)
        else:
            points = best_points
        center_y = sum(point[1] for point in points) / 4
        skew = min(18, max(-18, (center_y - (y + height / 2)) / max(1, height) * 28))
        points[0] = (points[0][0] + skew, points[0][1])
        points[1] = (points[1][0] - skew, points[1][1])
        return points

    def _brand_logo_quad_from_image_regions(self, rgb_array, logo_size: tuple[int, int], cv2, np):
        height, width = rgb_array.shape[:2]
        if width < 160 or height < 160:
            return None
        logo_width, logo_height = logo_size
        logo_ratio = logo_height / max(1, logo_width)
        target_width = int(max(56, min(width * 0.115, 98)))
        target_height = int(max(20, min(target_width * logo_ratio, height * 0.09)))
        half_width = target_width / 2
        half_height = target_height / 2
        luma = (
            rgb_array[:, :, 0].astype(np.float32) * 0.299
            + rgb_array[:, :, 1].astype(np.float32) * 0.587
            + rgb_array[:, :, 2].astype(np.float32) * 0.114
        )
        gray = luma.astype(np.uint8)
        edge_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        edge_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge = np.sqrt(edge_x * edge_x + edge_y * edge_y)
        saturation = (rgb_array.max(axis=2).astype(np.float32) - rgb_array.min(axis=2).astype(np.float32)) / 255.0
        hsv = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2HSV)
        hue = hsv[:, :, 0]
        warm_surface = (hue >= 8) & (hue <= 38) & (hsv[:, :, 1] > 65) & (hsv[:, :, 2] > 80)
        dark_background_ratio = float(np.mean(luma < 72))
        centers = [
            (width * 0.64, height * 0.46),
            (width * 0.52, height * 0.78),
            (width * 0.52, height * 0.88),
            (width * 0.46, height * 0.62),
            (width * 0.58, height * 0.68),
            (width * 0.38, height * 0.50),
            (width * 0.68, height * 0.32),
            (width * 0.70, height * 0.56),
        ]
        global_angle = self._brand_logo_local_surface_angle(gray, width / 2, height / 2, int(width * 0.62), int(height * 0.62), cv2, np)
        best_center = None
        best_score = -1.0
        best_angle = 0.0
        for center_x, center_y in centers:
            left = max(0, int(center_x - half_width))
            right = min(width, int(center_x + half_width))
            top = max(0, int(center_y - half_height))
            bottom = min(height, int(center_y + half_height))
            if right <= left or bottom <= top:
                continue
            local_edge = float(edge[top:bottom, left:right].mean()) / 255.0
            local_saturation = float(saturation[top:bottom, left:right].mean())
            local_luma_std = float(luma[top:bottom, left:right].std()) / 255.0
            local_warm_surface = float(np.mean(warm_surface[top:bottom, left:right]))
            x_norm = center_x / width
            y_norm = center_y / height
            upper_panel_bias = 1.0 - min(1.0, abs(x_norm - 0.64) * 1.45 + abs(y_norm - 0.46) * 1.30)
            lower_lip_bias = 1.0 - min(1.0, abs(x_norm - 0.52) * 1.30 + abs(y_norm - 0.84) * 1.22)
            product_surface_bias = max(upper_panel_bias, lower_lip_bias * 0.96)
            central_surface_bonus = 0.16 if 0.44 <= x_norm <= 0.66 and 0.56 <= y_norm <= 0.92 else 0.0
            edge_clearance = min(
                (center_x - half_width) / max(1, width),
                (width - center_x - half_width) / max(1, width),
                (center_y - half_height) / max(1, height),
                (height - center_y - half_height) / max(1, height),
            )
            smoothness = 1.0 / (1.0 + local_edge * 3.2)
            flatness = 1.0 / (1.0 + local_luma_std * 5.5)
            clean_surface = (
                smoothness * 0.46
                + flatness * 0.44
                + (1.0 - min(1.0, local_saturation * 4.2)) * 0.22
            )
            object_signal = min(1.0, local_edge * 3.8 + local_luma_std * 2.4 + local_saturation * 0.65)
            score = (
                product_surface_bias * 0.70
                + clean_surface * 0.44
                + central_surface_bonus
            )
            if y_norm > 0.72 and local_saturation < 0.10 and dark_background_ratio <= 0.45:
                score += 0.34
            if y_norm > 0.70 and local_saturation < 0.18 and dark_background_ratio > 0.45:
                score *= 0.035
            if y_norm > 0.72 and local_luma_std > 0.14 and local_saturation > 0.11:
                score *= 0.86
            if y_norm < 0.60 and (local_edge > 0.24 or local_luma_std > 0.18):
                score *= 0.70
            if 0.54 <= y_norm <= 0.76 and local_saturation > 0.24 and object_signal > 0.55:
                score += 0.28
            if local_saturation > 0.52 and y_norm > 0.66 and object_signal > 0.80:
                score += 0.22
            elif local_saturation > 0.45:
                score *= 0.78
            elif local_saturation > 0.30 and y_norm > 0.70:
                score *= 0.82
            if y_norm > 0.84 and local_saturation < 0.06 and local_luma_std < 0.16 and local_edge < 0.32:
                score *= 0.55
            if local_edge < 0.055 and local_luma_std < 0.055 and y_norm < 0.68:
                score *= 0.22
            if object_signal < 0.28:
                score *= 0.42
            if dark_background_ratio > 0.35 and y_norm > 0.50 and local_warm_surface > 0.32 and local_saturation > 0.22:
                score *= 0.10
            if y_norm < 0.64 and local_saturation < 0.16 and local_edge < 0.15 and local_luma_std < 0.10 and x_norm > 0.68:
                score *= 0.30
            if edge_clearance < 0.04:
                score *= 0.48
            if x_norm > 0.70 and y_norm < 0.70 and clean_surface > 0.74 and local_saturation < 0.08:
                score *= 0.24
            if x_norm > 0.74 and local_edge < 0.035 and local_luma_std < 0.045:
                score *= 0.18
            if center_y / height > 0.64 and center_x / width < 0.43:
                score *= 0.42
            if score > best_score:
                best_score = score
                best_center = (center_x, center_y)
                local_angle = self._brand_logo_local_surface_angle(gray, center_x, center_y, target_width, target_height, cv2, np)
                best_angle = local_angle if abs(local_angle) >= 2.5 else global_angle
        if best_center is None or best_score < 0.16:
            return None
        center_x, center_y = best_center
        radians = np.deg2rad(best_angle)
        cos_value = float(np.cos(radians))
        sin_value = float(np.sin(radians))
        perspective = min(8.0, max(-8.0, (center_x / width - 0.5) * 11.0))

        def rotate_point(offset_x: float, offset_y: float) -> tuple[float, float]:
            return (
                center_x + offset_x * cos_value - offset_y * sin_value,
                center_y + offset_x * sin_value + offset_y * cos_value,
            )

        return [
            rotate_point(-half_width + perspective, -half_height),
            rotate_point(half_width - perspective, -half_height),
            rotate_point(half_width * 0.96 + perspective, half_height),
            rotate_point(-half_width * 0.96 - perspective, half_height),
        ]

    def _brand_logo_local_surface_angle(self, gray, center_x: float, center_y: float, logo_width: int, logo_height: int, cv2, np) -> float:
        height, width = gray.shape[:2]
        sample_width = int(max(logo_width * 1.8, 96))
        sample_height = int(max(logo_height * 5.0, 90))
        left = max(0, int(center_x - sample_width / 2))
        right = min(width, int(center_x + sample_width / 2))
        top = max(0, int(center_y - sample_height / 2))
        bottom = min(height, int(center_y + sample_height / 2))
        if right - left < 24 or bottom - top < 24:
            return 0.0
        region = gray[top:bottom, left:right]
        blurred = cv2.GaussianBlur(region, (0, 0), 1.2)
        edges = cv2.Canny(blurred, 45, 135)
        min_length = max(18, min(region.shape[:2]) // 4)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=18, minLineLength=min_length, maxLineGap=8)
        if lines is None:
            return 0.0
        weighted_angles: list[tuple[float, float]] = []
        for line in lines[:, 0, :]:
            x1, y1, x2, y2 = [float(value) for value in line]
            dx = x2 - x1
            dy = y2 - y1
            length = float(np.hypot(dx, dy))
            if length < min_length:
                continue
            raw_angle = float(np.degrees(np.arctan2(dy, dx)))
            while raw_angle > 90:
                raw_angle -= 180
            while raw_angle < -90:
                raw_angle += 180
            if abs(raw_angle) > 56:
                angle = raw_angle - 90 if raw_angle > 0 else raw_angle + 90
            else:
                angle = raw_angle
            if abs(angle) > 34:
                continue
            if abs(angle) < 2.5:
                continue
            weighted_angles.append((angle, length))
        if not weighted_angles:
            return 0.0
        total_weight = sum(weight for _, weight in weighted_angles)
        if total_weight <= 0:
            return 0.0
        angle = sum(angle * weight for angle, weight in weighted_angles) / total_weight
        return float(max(-14.0, min(14.0, angle * 0.68)))

    def _distort_logo_for_surface(self, logo, quad, np, cv2):
        data = np.asarray(logo).copy()
        height, width = data.shape[:2]
        if width < 4 or height < 4:
            return logo
        ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
        period = max(10.0, width / 9.0)
        strength = max(1.0, min(5.0, width / 90.0))
        map_x = np.clip(xs + np.sin(xs / period * 2 * np.pi) * strength, 0, width - 1).astype(np.float32)
        map_y = ys.astype(np.float32)
        distorted = cv2.remap(data, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        groove = (0.82 + 0.18 * np.cos(xs / period * 2 * np.pi)).astype(np.float32)
        distorted[:, :, 3] = np.clip(distorted[:, :, 3].astype(np.float32) * groove, 0, 255).astype(np.uint8)
        from PIL import Image

        return Image.fromarray(distorted, mode="RGBA")

    def _warp_logo_to_quad(self, logo, canvas_size: tuple[int, int], quad, cv2, np):
        from PIL import Image

        canvas_width, canvas_height = canvas_size
        quad_array = np.asarray(quad, dtype=np.float32)
        top_width = np.linalg.norm(quad_array[1] - quad_array[0])
        bottom_width = np.linalg.norm(quad_array[2] - quad_array[3])
        left_height = np.linalg.norm(quad_array[3] - quad_array[0])
        right_height = np.linalg.norm(quad_array[2] - quad_array[1])
        target_width = max(20, int((top_width + bottom_width) / 2))
        target_height = max(12, int((left_height + right_height) / 2))
        logo_copy = logo.copy()
        logo_copy.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        logo_canvas = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
        logo_canvas.alpha_composite(logo_copy, ((target_width - logo_copy.width) // 2, (target_height - logo_copy.height) // 2))
        source_points = np.asarray(
            [[0, 0], [target_width - 1, 0], [target_width - 1, target_height - 1], [0, target_height - 1]],
            dtype=np.float32,
        )
        matrix = cv2.getPerspectiveTransform(source_points, quad_array)
        return cv2.warpPerspective(
            np.asarray(logo_canvas),
            matrix,
            (canvas_width, canvas_height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )

    def _brand_logo_ink_color(self, base_rgb, logo_alpha, cv2, np):
        logo_mask = logo_alpha > 0
        if not np.any(logo_mask):
            return np.asarray([12.0, 22.0, 36.0], dtype=np.float32)
        surface = base_rgb[logo_mask].astype(np.float32)
        surface_rgb = np.median(surface, axis=0)
        surface_luma = float(surface_rgb[0] * 0.299 + surface_rgb[1] * 0.587 + surface_rgb[2] * 0.114)
        surface_chroma = float(surface_rgb.max() - surface_rgb.min())
        candidate_colors = np.asarray(
            [
                [9.0, 22.0, 38.0],
                [244.0, 239.0, 221.0],
                [42.0, 180.0, 170.0],
                [226.0, 176.0, 48.0],
                [184.0, 44.0, 72.0],
            ],
            dtype=np.float32,
        )
        best_color = candidate_colors[0]
        best_score = -1.0
        for color in candidate_colors:
            color_luma = float(color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114)
            luma_distance = abs(color_luma - surface_luma) / 255.0
            chroma_distance = float(np.linalg.norm(color - surface_rgb)) / 441.7
            brand_bias = 0.05 if color_luma < 80 or color_luma > 210 else 0.0
            score = luma_distance * 1.55 + chroma_distance * (0.65 if surface_chroma < 38 else 0.95) + brand_bias
            if score > best_score:
                best_score = score
                best_color = color
        return best_color

    def _blend_surface_logo(self, base, warped_logo, mask, cv2, np):
        base_array = np.asarray(base).astype(np.float32)
        alpha_source = warped_logo[:, :, 3]
        if alpha_source.max() <= 0:
            return np.asarray(base)
        logo_area = alpha_source > 0
        mask_coverage = float(np.mean(mask[logo_area].astype(np.float32) / 255.0)) if np.any(logo_area) else 1.0
        luma = (base_array[:, :, 0] * 0.299 + base_array[:, :, 1] * 0.587 + base_array[:, :, 2] * 0.114) / 255.0
        ink_color = self._brand_logo_ink_color(base_array[:, :, :3], alpha_source, cv2, np)
        warped_rgb = warped_logo[:, :, :3].astype(np.float32)
        warped_luma = (warped_rgb[:, :, 0] * 0.299 + warped_rgb[:, :, 1] * 0.587 + warped_rgb[:, :, 2] * 0.114)
        text_source = (alpha_source > 82) & (warped_luma < 172)
        plate_source = logo_area & ~text_source
        mask_softener = np.ones_like(luma, dtype=np.float32)
        if mask_coverage >= 0.72:
            mask_softener = 0.72 + (mask.astype(np.float32) / 255.0) * 0.28
        gray = (luma * 255).astype(np.uint8)
        edge_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        edge_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge = np.sqrt(edge_x * edge_x + edge_y * edge_y)
        texture_base = cv2.GaussianBlur(luma.astype(np.float32), (0, 0), 0.9)
        texture_smooth = cv2.GaussianBlur(texture_base, (0, 0), 4.0)
        surface_texture = np.clip(1.0 + (texture_base - texture_smooth) * 0.22, 0.90, 1.08)
        plate_alpha = (alpha_source.astype(np.float32) / 255.0) * plate_source.astype(np.float32) * 0.44
        plate_alpha *= mask_softener
        plate_alpha *= np.clip(0.98 + (surface_texture - 1.0) * 0.45, 0.92, 1.04)
        text_alpha = (alpha_source.astype(np.float32) / 255.0) * text_source.astype(np.float32) * 0.94
        text_alpha *= mask_softener
        text_alpha *= surface_texture
        text_alpha *= np.clip(1.0 - edge / 420.0, 0.80, 1.0)
        text_alpha *= np.clip(1.06 - luma * 0.16, 0.84, 1.0)
        logo_binary = text_source.astype(np.uint8)
        border = cv2.dilate(logo_binary, np.ones((3, 3), np.uint8), iterations=1).astype(np.float32) - logo_binary.astype(np.float32)
        border_alpha = np.clip(border, 0, 1) * np.clip(text_alpha.max() * 0.18, 0.03, 0.12)
        border_color = np.asarray([255.0, 255.0, 255.0], dtype=np.float32) if np.mean(ink_color) < 120 else np.asarray([8.0, 14.0, 24.0], dtype=np.float32)
        surface_shade = cv2.GaussianBlur(luma.astype(np.float32), (0, 0), 2.2)
        ink = ink_color[None, None, :] * (0.92 + 0.12 * surface_shade[:, :, None])
        surface_rgb = cv2.GaussianBlur(base_array[:, :, :3], (0, 0), 3.0)
        light_plate = surface_rgb * 0.78 + 255.0 * 0.22
        dark_plate = surface_rgb * 0.88
        plate_color = np.where(luma[:, :, None] < 0.48, light_plate, dark_plate)
        plate_binary = plate_source.astype(np.uint8)
        plate_shadow = cv2.GaussianBlur(plate_binary.astype(np.float32), (0, 0), 1.6)
        plate_shadow = np.roll(np.roll(plate_shadow, 1, axis=0), 1, axis=1)
        plate_shadow_alpha = plate_shadow * 0.035 * mask_softener
        plate_shadow_alpha_3 = plate_shadow_alpha[:, :, None]
        plate_alpha_3 = plate_alpha[:, :, None]
        alpha_3 = text_alpha[:, :, None]
        border_alpha_3 = border_alpha[:, :, None]
        base_array[:, :, :3] = base_array[:, :, :3] * (1 - plate_shadow_alpha_3)
        base_array[:, :, :3] = base_array[:, :, :3] * (1 - plate_alpha_3) + plate_color * plate_alpha_3
        base_array[:, :, :3] = base_array[:, :, :3] * (1 - border_alpha_3) + border_color[None, None, :] * border_alpha_3
        base_array[:, :, :3] = base_array[:, :, :3] * (1 - alpha_3) + ink * alpha_3
        return np.clip(base_array, 0, 255).astype(np.uint8)

    def _brand_logo_prompt_instruction(self) -> str:
        if self._brand_logo_source_path() is None:
            return ""
        return (
            "Brand mark rule: attached product references may already include a KKEURONG MAJE mark on the product surface. "
            "Before generating, treat only a small mark placed naturally on a real product-surface corner as valid branding; "
            "ignore any mark that appears on the background, skin, face, spec table, text card, packaging copy, or as a floating badge. "
            "Treat that mark as intentional product branding for both detail-page section images and thumbnails. Keep it "
            "small, subtle, and physically attached to a natural product-surface corner; do not erase it, move it off the "
            "product, or treat it as an external watermark. This is the only logo exception. When the generated image "
            "redraws the product, reproduce the KKEURONG MAJE mark only as a printed/engraved mark aligned to the product "
            "perspective, lighting, and material. Never place the mark on the background, a person's skin, a text/spec "
            "panel, packaging text, or a floating badge. If there is no clear product surface, do not invent a separate "
            "logo placement. Other supplier logos, platform marks, Chinese text, badges, and watermarks are still forbidden."
        )

    def _best_reference_image_path(self, product: ProductRecord) -> Path | None:
        from PIL import Image

        best: tuple[int, Path] | None = None
        for path in self._source_image_paths(product):
            try:
                with Image.open(path) as image:
                    width, height = image.size
            except Exception:
                continue
            if width < 300 or height < 300:
                continue
            ratio = height / max(1, width)
            if ratio > 1.8:
                continue
            score = min(width, height) + (200 if 0.7 <= ratio <= 1.35 else 0)
            if best is None or score > best[0]:
                best = (score, path)
        return best[1] if best else None

    def _long_detail_image_path(self, product: ProductRecord) -> Path | None:
        from PIL import Image

        best: tuple[int, Path] | None = None
        for path in self._source_image_paths(product):
            try:
                with Image.open(path) as image:
                    width, height = image.size
            except Exception:
                continue
            ratio = height / max(1, width)
            if width < 600 or height < 1800 or ratio < 2.2:
                continue
            score = height * width
            if best is None or score > best[0]:
                best = (score, path)
        return best[1] if best else None

    def _generate_section_visuals(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        run_stamp: str,
        page=None,
        resume_from_section: int | None = None,
        progress_callback=None,
    ) -> list[Path]:
        resume_start = max(1, min(len(sections), int(resume_from_section or 1))) if sections else 1
        prompt_dir = product.output_dir / "codex_image_prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        if resume_from_section is None:
            for old_file in prompt_dir.glob("section_*"):
                if old_file.is_file():
                    old_file.unlink(missing_ok=True)

        visual_dir = product.output_dir / "generated_visuals"
        visual_dir.mkdir(parents=True, exist_ok=True)
        existing_pipeline_version = ""
        metadata_path = product.output_dir / "metadata.json"
        if metadata_path.exists():
            try:
                existing_pipeline_version = str(json.loads(metadata_path.read_text(encoding="utf-8")).get("pipeline_version", ""))
            except Exception:
                existing_pipeline_version = ""
        force_regenerate = existing_pipeline_version != DETAIL_PIPELINE_VERSION
        for old_file in visual_dir.glob("section_*.png"):
            if old_file.is_file() and (
                (force_regenerate and resume_from_section is None)
                or not self._is_valid_generated_visual_file(old_file)
            ):
                old_file.unlink(missing_ok=True)

        source_path = self._best_reference_image_path(product)
        if source_path is None:
            source_paths = self._source_image_paths(product)
            source_path = source_paths[0] if source_paths else None
        if source_path is None:
            raise RuntimeError("섹션 이미지를 만들 상품 원본 이미지가 없습니다.")
        self._write_latest_imagegen_batch_files(product, sections, prompt_dir, visual_dir, source_path)
        if page is not None:
            if not ENABLE_CHATGPT_WEB_IMAGE_GENERATION:
                return []
            return self._run_chatgpt_web_section_image_generation(
                product,
                sections,
                prompt_dir,
                visual_dir,
                page,
                resume_from_section=resume_from_section,
                progress_callback=progress_callback,
            )
        return self._run_gpt_image2_section_generation(
            product,
            sections,
            prompt_dir,
            visual_dir,
            resume_from_section=resume_from_section,
            progress_callback=progress_callback,
        )

    def _product_visual_descriptor(self, product: ProductRecord) -> str:
        parts = [
            product.product_name,
            product.category,
            product.options_text,
            " / ".join(product.facts[:3]),
        ]
        return " | ".join(self._dedupe_text_items([part for part in parts if part]))[:700]

    def _detail_section_common_design_rules(self) -> str:
        return (
            "공통 디자인 기준:\n"
            "- 폰트는 최대 2종류만 사용.\n"
            "- 제목은 64px 이상처럼 크게, 서브 카피는 36~40px 기준으로 제목보다 작게 구성.\n"
            "- 메인 컬러는 2개 중심, 많아도 3개 이하.\n"
            "- 좌우 여백은 최소 40px 이상 확보.\n"
            "- 섹션 위아래 여백은 80~100px 기준으로 넉넉하게 확보.\n"
            "- 한 문단은 2줄 이내로 짧게 구성.\n"
            "- 한 섹션에는 핵심 메시지 1개만 배치.\n"
            "- 텍스트, 카드, 상품 이미지의 기준선을 정렬 오차 없이 맞춤.\n"
            "- 위 기준은 디자인 지시이며, 이미지 안에 px 숫자나 이 규칙 문장을 직접 쓰지 말 것."
        )

    def _latest_image_prompt_for_section(
        self,
        product: ProductRecord,
        section: SectionPlan,
        section_index: int,
        source_path: Path,
    ) -> str:
        section_prompt = self._section_image_prompt_context(section, section_index)
        if not section_prompt:
            raise RuntimeError(f"{section_index:02d}번 섹션의 GPT 섹션 실행본이 없습니다.")
        return (
            "상세페이지 섹션 이미지 1장 생성.\n"
            "설명 없이 이미지 결과만 출력.\n"
            "첨부 이미지들의 실제 상품 외형, 색상, 단수, 구조, 비율을 유지.\n\n"
            "사람이 포함된 참고 이미지가 있을 경우, 상품의 착용 핏/자세/사용 장면은 유지하되\n"
            "사람 얼굴과 개인 식별 특징은 원본과 다르게 변경해,\n"
            "원본 인물로 식별되지 않게 처리.\n"
            "원본 모델의 얼굴, 눈/코/입, 헤어라인, 점, 문신 등 신원 식별 요소를 그대로 복제하지 말고, 필요하면 얼굴이 보이지 않는 각도나 익명 모델 느낌으로 처리.\n"
            "단, 상품 자체의 색상, 소재, 핏, 길이, 구조는 절대 바꾸지 않음.\n\n"
            f"{self._detail_section_common_design_rules()}\n\n"
            f"{section_prompt}"
        )

    def _section_image_prompt_context(self, section: SectionPlan, section_index: int) -> str:
        image_prompt = self._sanitize_chatgpt_image_prompt(section.image_prompt)
        if not image_prompt:
            return ""
        blocked_markers = (
            "가격",
            "판매가",
            "리뷰",
            "후기",
            "평점",
            "별점",
            "오너클랜",
            "Ownerclan",
            "도매꾹",
            "원산지",
            "제조국",
            "배송",
            "반품",
            "A/S",
            "AS",
        )
        price_pattern = re.compile(r"\d{1,3}(?:,\d{3})+\s*원|\d+\s*원")

        def clean_copy_line(value: str) -> str:
            line = self._clean_detail_copy_text(value)
            if not line or price_pattern.search(line):
                return ""
            if any(marker in line for marker in blocked_markers):
                return ""
            return line

        def clean_prompt_text(value: str) -> str:
            pieces = re.split(r"\n+|[,，]\s*", value)
            cleaned: list[str] = []
            for piece in pieces:
                item = re.sub(r"\s+", " ", str(piece or "").strip(" -•\t\r\n"))
                if not item or price_pattern.search(item):
                    continue
                if any(marker in item for marker in blocked_markers):
                    continue
                cleaned.append(item)
            return " ".join(self._dedupe_text_items(cleaned)).strip()

        headline = clean_copy_line(section.headline)
        subheadline = clean_copy_line(section.subheadline)
        body = clean_copy_line(section.body)
        bullets = [line for line in (clean_copy_line(item) for item in section.bullets) if line][:3]
        image_prompt = clean_prompt_text(image_prompt)
        if not image_prompt:
            return ""
        lines = [
            f"섹션 {section_index}. {section.section_name or section.section_key}",
            "제목",
            section.section_name,
            "",
            "메인 헤드라인",
            headline,
            "",
            "서브 카피",
            subheadline,
            "",
            "본문/불릿",
            body,
        ]
        lines.extend(f"- {item}" for item in bullets)
        lines.extend(["", "이미지 프롬프트", image_prompt])
        return "\n".join(line for line in lines if line).strip()[:12000].rstrip()

    def _write_latest_imagegen_batch_files(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        prompt_dir: Path,
        visual_dir: Path,
        source_path: Path,
    ) -> None:
        jobs_path = prompt_dir / f"imagegen_{LATEST_CODEX_IMAGE_MODEL}_jobs.jsonl"
        run_script_path = prompt_dir / "run_latest_imagegen.ps1"
        jobs: list[dict[str, str]] = []
        for section_index, section in enumerate(sections, start=1):
            key = slugify(section.section_key, f"section_{section_index:02d}")
            prompt = self._latest_image_prompt_for_section(product, section, section_index, source_path)
            prompt_path = prompt_dir / f"section_{section_index:02d}_{key}_prompt.txt"
            prompt_path.write_text(prompt, encoding="utf-8")
            jobs.append(
                {
                    "prompt": prompt,
                    "use_case": "product-mockup",
                    "size": LATEST_CODEX_IMAGE_SIZE,
                    "quality": "high",
                    "output_format": "png",
                    "out": f"section_{section_index:02d}_{key}.png",
                    "negative": "text, logo, watermark, copied screenshot, childish template, clutter",
                }
            )
        jobs_path.write_text(
            "\n".join(json.dumps(job, ensure_ascii=False) for job in jobs) + "\n",
            encoding="utf-8",
        )
        run_script = (
            "$ErrorActionPreference = 'Stop'\n"
            "Write-Host '이 파일은 섹션 프롬프트 기록용입니다.'\n"
            "Write-Host '앱 실행 경로는 열린 ChatGPT 같은 탭에서 이미지를 생성하고 generated_visuals에 저장합니다.'\n"
            f"Write-Host '프롬프트 JSONL: {jobs_path}'\n"
            f"Write-Host '생성 이미지 폴더: {visual_dir}'\n"
        )
        run_script_path.write_text(run_script, encoding="utf-8")

    def _chatgpt_section_image_request(
        self,
        product: ProductRecord,
        section: SectionPlan,
        section_index: int,
        retry_variant: int = 0,
    ) -> str:
        section_prompt = self._section_image_prompt_context(section, section_index)
        if not section_prompt or len(section_prompt) < 30:
            raise RuntimeError(f"{section_index:02d}번 섹션의 GPT 섹션 실행본이 없습니다.")
        face_rule = (
            "사람이 포함된 참고 이미지가 있을 경우, 상품의 착용 핏/자세/사용 장면은 유지하되\n"
            "사람 얼굴과 개인 식별 특징은 원본과 다르게 변경해,\n"
            "원본 인물로 식별되지 않게 처리.\n"
            "원본 모델의 얼굴, 눈/코/입, 헤어라인, 점, 문신 등 신원 식별 요소를 그대로 복제하지 말고, 필요하면 얼굴이 보이지 않는 각도나 익명 모델 느낌으로 처리.\n"
            "단, 상품 자체의 색상, 소재, 핏, 길이, 구조는 절대 바꾸지 않음.\n"
        )
        brand_logo_rule = self._brand_logo_prompt_instruction()
        if retry_variant <= 0:
            return (
                "상세페이지 섹션 이미지 1장 생성.\n"
                "설명 없이 이미지 결과만 출력.\n"
                "첨부 이미지들의 실제 상품 외형, 색상, 단수, 구조, 비율을 유지.\n\n"
                f"{face_rule}\n"
                f"{brand_logo_rule}\n"
                f"{self._detail_section_common_design_rules()}\n\n"
                f"{section_prompt}"
            )
        product_label = product.product_name or product.title or product.code or "상품"
        if retry_variant == 1:
            return (
                "이미지 생성만 해줘. 설명 문장 금지.\n"
                f"상품명: {product_label}\n"
                f"섹션 {section_index}: {section.headline}\n"
                f"보조 문구: {section.subheadline or section.body}\n"
                "첨부 이미지의 실제 상품 형태, 색상, 소재, 옵션, 비율을 그대로 유지.\n"
                "세로 9:16 한국 쇼핑몰 상세페이지 이미지 1장.\n"
                "한글 문구는 짧고 크게, 오타 없이.\n"
                "중국어, 영어, 로고, 워터마크, 허구 인증, 배송/반품 정책 문구 금지.\n"
                f"{brand_logo_rule}\n"
                f"{self._detail_section_common_design_rules()}\n"
                f"{face_rule}"
            )
        return (
            "상세페이지 섹션 이미지 1장 생성.\n"
            "이미지 결과만 출력.\n"
            f"첨부 상품을 기준으로 {product_label}의 쇼핑몰 상세페이지 컷을 만든다.\n"
            f"핵심 문구: {section.headline}\n"
            "상품 외형과 색상은 첨부 이미지 그대로. 배경은 단순하고 깨끗하게.\n"
            "세로형 9:16, 상품이 잘 보이게, 텍스트는 최소화.\n"
            f"{brand_logo_rule}\n"
            f"{self._detail_section_common_design_rules()}\n"
            f"{face_rule}"
        )

    def _default_chatgpt_visual_concept(self, product: ProductRecord, section: SectionPlan, section_index: int) -> str:
        product_label = product.product_name or product.title or "상품"
        concepts = {
            "hero": f"{product_label}를 현관 또는 수납 공간 오른쪽에 세워 둔 프리미엄 라이프스타일 장면, 좌측 상단은 넓은 여백, 자연광과 정돈된 배경",
            "empathy": f"좁은 현관 바닥에 신발이 흩어져 있다가 {product_label}로 정리되는 문제 공감형 장면, 답답함과 정돈감을 대비",
            "solution": f"{product_label}의 세로 수납 구조가 잘 보이는 before-after 느낌의 장면, 제품은 3/4 각도, 배경은 밝은 현관",
            "benefits": f"{product_label} 여러 칸에 운동화, 슬리퍼, 플랫슈즈, 작은 소품이 정돈된 활용 장면, 제품 디테일과 수납량 강조",
            "how_to_use": f"{product_label}를 사람이 현관 옆에서 신발을 꺼내거나 넣는 실제 사용 장면, 손동작 중심, 생활감은 깔끔하게",
            "trust": f"{product_label}의 소재, 모서리, 칸 구조, 조립부가 보이는 깨끗한 제품 디테일 클로즈업 장면, 배경은 화이트 스튜디오",
            "cta": f"{product_label}가 정돈된 현관 코너에 놓인 완성형 라이프스타일 장면, 하단은 버튼형 카피를 얹기 좋은 여백",
            "review_points": f"{product_label}를 배경 오른쪽에 자연스럽게 두고, 왼쪽에는 마스킹 아이디와 별점이 있는 후기형 만족 포인트 카드 5개를 세련되게 배치한 상세페이지 마무리 장면",
        }
        return concepts.get(section.section_key, f"{product_label}를 중심으로 한 한국 쇼핑몰 상세페이지용 제품 장면, 섹션 {section_index}에 맞는 다른 배경과 각도")

    def _sanitize_chatgpt_image_prompt(self, prompt: str) -> str:
        raw = (prompt or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not raw:
            return ""
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw[:6000].rstrip()

    def _assistant_image_candidates(
        self,
        page,
        latest_only: bool = True,
        strict_latest_turn: bool = False,
    ) -> list[dict]:
        try:
            candidates = page.evaluate(
                """({latestOnly, strictLatestTurn}) => {
                    const assistantScopes = Array.from(document.querySelectorAll("[data-message-author-role='assistant']"));
                    const scopes = [];
                    if (latestOnly && assistantScopes.length) scopes.push(assistantScopes[assistantScopes.length - 1]);
                    if (!latestOnly) scopes.push(...assistantScopes);
                    const allImages = Array.from(document.querySelectorAll("img"));
                    const seen = new Set();
                    const images = [];
                    for (const scope of scopes) {
                        for (const img of Array.from(scope.querySelectorAll("img"))) {
                            const globalIndex = allImages.indexOf(img);
                            if (globalIndex < 0 || seen.has(globalIndex)) continue;
                            seen.add(globalIndex);
                            images.push(img);
                        }
                    }
                    if (!strictLatestTurn) {
                        for (const img of allImages) {
                            const globalIndex = allImages.indexOf(img);
                            if (globalIndex < 0 || seen.has(globalIndex)) continue;
                            const roleNode = img.closest("[data-message-author-role]");
                            const role = roleNode ? (roleNode.getAttribute("data-message-author-role") || "") : "";
                            if (role === "user") continue;
                            seen.add(globalIndex);
                            images.push(img);
                        }
                    }
                    return images.map((img) => {
                        const rect = img.getBoundingClientRect();
                        const style = window.getComputedStyle(img);
                        const src = img.currentSrc || img.src || "";
                        const alt = img.alt || "";
                        const roleNode = img.closest("[data-message-author-role]");
                        const role = roleNode ? (roleNode.getAttribute("data-message-author-role") || "") : "";
                        const width = img.naturalWidth || 0;
                        const height = img.naturalHeight || 0;
                        const clientWidth = Math.round(rect.width || 0);
                        const clientHeight = Math.round(rect.height || 0);
                        const globalIndex = allImages.indexOf(img);
                        return {
                            global_index: globalIndex,
                            src,
                            alt,
                            width,
                            height,
                            client_width: clientWidth,
                            client_height: clientHeight,
                            area: clientWidth * clientHeight,
                            role,
                            signature: `${src}|${width}x${height}|${alt}|${globalIndex}`,
                            content_signature: `${src}|${width}x${height}|${alt}`,
                            visible: clientWidth >= 160 && clientHeight >= 160 && style.display !== "none" && style.visibility !== "hidden"
                        };
                    }).filter((item) => {
                        const src = (item.src || "").toLowerCase();
                        const alt = (item.alt || "").toLowerCase();
                        if ((item.role || "").toLowerCase() === "user") return false;
                        if (!item.visible) return false;
                        if (item.width && item.width < 700) return false;
                        if (item.height && item.height < 700) return false;
                        if (src.includes("avatar") || alt.includes("avatar") || alt.includes("user")) return false;
                        if (alt.includes("업로드") || alt.includes("uploaded") || alt.includes("attachment_")) return false;
                        return true;
                    }).sort((a, b) => (b.area - a.area) || (b.width * b.height - a.width * a.height));
                }""",
                {"latestOnly": latest_only, "strictLatestTurn": strict_latest_turn},
            )
            return candidates if isinstance(candidates, list) else []
        except Exception:
            return []

    def _assistant_image_signatures(self, page) -> set[str]:
        return {
            str(candidate.get("content_signature") or candidate.get("signature") or "")
            for candidate in self._assistant_image_candidates(page, latest_only=False)
            if candidate.get("content_signature") or candidate.get("signature")
        }

    def _latest_new_assistant_image_candidate(self, page, previous_signatures: set[str]) -> dict | None:
        candidates = [
            candidate
            for candidate in self._assistant_image_candidates(page, latest_only=False)
            if str(candidate.get("content_signature") or candidate.get("signature") or "") not in previous_signatures
        ]
        return candidates[0] if candidates else None

    def _wait_fixed_section_image_save_delay(self, page, section_index: int) -> None:
        deadline = time.time() + CHATGPT_SECTION_IMAGE_SAVE_DELAY_SECONDS
        while time.time() < deadline:
            self._raise_if_user_requested_stop_or_skip()
            remaining = max(0, int(deadline - time.time()))
            self.automation_signals.status.emit(
                f"섹션 {section_index} 이미지 저장 대기 {remaining // 60}:{remaining % 60:02d}"
            )
            page.wait_for_timeout(min(1000, max(500, remaining * 1000)))

    def _reload_chatgpt_for_section_image_retry(self, page, section_index: int, attempt: int) -> None:
        self.automation_signals.status.emit(
            f"섹션 {section_index} 이미지 오류 감지, F5 새로고침 후 같은 섹션 재시도 {attempt}/{CHATGPT_SECTION_IMAGE_RELOAD_RETRY_LIMIT}"
        )
        page.bring_to_front()
        page.keyboard.press("F5")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=60000)
        except Exception:
            pass
        page.wait_for_timeout(8000)
        self._accept_chatgpt_cookies(page)
        self._dismiss_chatgpt_blocking_modal(page)
        if self._page_needs_login(page):
            raise RuntimeError("ChatGPT 새로고침 후 로그인이 필요합니다.")

    def _reload_chatgpt_for_thumbnail_image_retry(self, page, thumbnail_index: int, attempt: int) -> None:
        self.automation_signals.status.emit(
            f"썸네일 {thumbnail_index} 이미지 시간초과/오류 감지, F5 새로고침 후 같은 썸네일 재시도 {attempt}/{CHATGPT_THUMBNAIL_IMAGE_RETRY_LIMIT}"
        )
        page.bring_to_front()
        page.keyboard.press("F5")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=60000)
        except Exception:
            pass
        page.wait_for_timeout(8000)
        self._accept_chatgpt_cookies(page)
        self._dismiss_chatgpt_blocking_modal(page)
        self._force_hide_chatgpt_open_sheets(page)
        if self._page_needs_login(page):
            raise RuntimeError("ChatGPT 새로고침 후 로그인이 필요합니다.")

    def _wait_for_chatgpt_generated_image(
        self,
        page,
        previous_signatures: set[str],
        previous_stop_count: int = 0,
        timeout_seconds: int = 2400,
        previous_text: str = "",
        wait_status: str = "",
        prefer_candidate_on_error: bool = False,
    ) -> dict:
        deadline = time.time() + timeout_seconds
        extension_deadline = deadline + CHATGPT_THUMBNAIL_ACTIVE_WAIT_EXTENSION_SECONDS
        thumbnail_active_extension_used = False
        started_at = time.time()
        previous_text = previous_text.strip()
        last_signature = ""
        stable_count = 0
        last_candidate: dict | None = None
        candidate_seen_at = 0.0
        transient_send_retries = 0
        while time.time() < deadline:
            self._raise_if_user_requested_stop_or_skip()
            if wait_status:
                remaining = max(0, int(deadline - time.time()))
                self.automation_signals.status.emit(
                    f"{wait_status} {remaining // 60}:{remaining % 60:02d}"
                )
            stop_marker_increased = False
            try:
                stop_marker_increased = self._chatgpt_stop_marker_count(page) > previous_stop_count
            except Exception:
                pass
            candidates = [
                candidate
                for candidate in self._assistant_image_candidates(page, latest_only=True, strict_latest_turn=True)
                if str(candidate.get("content_signature") or candidate.get("signature") or "") not in previous_signatures
            ]
            if not candidates:
                candidates = [
                    candidate
                    for candidate in self._assistant_image_candidates(page, latest_only=False)
                    if str(candidate.get("content_signature") or candidate.get("signature") or "") not in previous_signatures
                ]
            if stop_marker_increased and not candidates:
                raise RuntimeError("ChatGPT 이미지 생성이 중지됐습니다.")
            latest_text, busy = self._latest_gpt_text(page)
            image_wait_active = self._is_chatgpt_image_wait_text(latest_text)
            if (
                wait_status.startswith("썸네일")
                and (busy or image_wait_active)
                and not thumbnail_active_extension_used
                and time.time() >= deadline - 5
            ):
                deadline = extension_deadline
                thumbnail_active_extension_used = True
                continue
            if self._is_chatgpt_transient_send_error_text(latest_text):
                if time.time() - started_at < CHATGPT_RETRY_GRACE_SECONDS:
                    page.wait_for_timeout(5000)
                    continue
                if transient_send_retries < 3 and self._click_chatgpt_retry_button(page, timeout_ms=8000):
                    transient_send_retries += 1
                    page.wait_for_timeout(5000)
                    continue
                raise RuntimeError(f"ChatGPT 메시지 전송 오류: {self._compact_error_text(latest_text)}")
            if self._is_chatgpt_image_generation_error_text(latest_text) and latest_text.strip() != previous_text:
                raise RuntimeError(f"ChatGPT 이미지 생성 오류 응답: {self._compact_error_text(latest_text)}")
            if candidates:
                candidate = candidates[0]
                signature = str(candidate.get("signature") or "")
                if signature == last_signature:
                    stable_count += 1
                else:
                    stable_count = 0
                    last_signature = signature
                    last_candidate = candidate
                    candidate_seen_at = time.time()
                # ChatGPT sometimes leaves a "generating a more detailed image"
                # status in the latest turn even after the generated image is
                # already attached to the DOM. Treat a stable, full-size image
                # candidate as ready instead of waiting forever on that stale
                # busy text.
                candidate_stable_seconds = time.time() - candidate_seen_at
                if stable_count >= 2 and (not busy or candidate_stable_seconds >= 10):
                    return candidate
            if time.time() - started_at >= CHATGPT_RETRY_GRACE_SECONDS and self._is_chatgpt_stream_stalled_text(latest_text):
                page.wait_for_timeout(5000)
                continue
            elif (
                time.time() - started_at >= CHATGPT_RETRY_GRACE_SECONDS
                and not busy
                and self._latest_message_role(page).startswith("assistant")
                and latest_text
                and latest_text.strip() != previous_text
                and not self._gpt_text_is_non_result_noise(latest_text)
            ):
                raise RuntimeError(f"ChatGPT가 이미지 대신 텍스트로 응답했습니다: {self._compact_error_text(latest_text, 220)}")
            if time.time() - started_at >= CHATGPT_RETRY_GRACE_SECONDS and not busy and self._latest_message_role(page) == "user":
                raise RuntimeError("ChatGPT가 이미지 요청을 받았지만 20분 안에 이미지 응답을 시작하지 않았습니다.")
            page.wait_for_timeout(5000)
        if last_candidate:
            return last_candidate
        raise RuntimeError("ChatGPT 이미지 생성 결과를 제한 시간 안에 찾지 못했습니다.")

    def _is_chatgpt_stream_stalled_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", (text or "")).strip().lower()
        if not normalized:
            return False
        return (
            "스트리밍이 중지" in normalized
            or "메시지 완료를 기다리는 중" in normalized
            or "streaming stopped" in normalized
            or "waiting for message completion" in normalized
        )

    def _is_chatgpt_image_generation_error_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", (text or "")).strip().lower()
        if not normalized:
            return False
        error_markers = (
            "이미지 생성 중 오류",
            "이미지를 만들지 못했습니다",
            "이미지를 만들지 못했어요",
            "이미지를 만들지 못했",
            "이미지를 생성하지 못했어요",
            "이미지를 생성하지 못했",
            "이미지를 만들 수 없어요",
            "이미지를 만들 수 없",
            "이미지 생성에 실패",
            "content policies",
            "content policy",
            "violate our content",
            "policy violation",
            "couldn't generate",
            "could not generate",
            "failed to generate",
            "experienced an error when generating images",
            "error when generating images",
            "error generating",
            "unable to generate",
        )
        image_markers = ("이미지", "image")
        return any(marker in normalized for marker in error_markers) and any(marker in normalized for marker in image_markers)

    def _compact_error_text(self, text: str, limit: int = 180) -> str:
        compact = re.sub(r"\s+", " ", (text or "")).strip()
        return compact[:limit] + ("..." if len(compact) > limit else "")

    def _should_retry_chatgpt_image_request(self, exc: Exception) -> bool:
        message = str(exc)
        normalized = re.sub(r"\s+", " ", message).strip().lower()
        if "chatgpt" in normalized and ("이미지" in normalized or "image" in normalized) and (
            "오류" in normalized
            or "실패" in normalized
            or "못했습니다" in normalized
            or "error" in normalized
            or "failed" in normalized
            or "couldn't" in normalized
            or "could not" in normalized
        ):
            return True
        return (
            "ChatGPT 이미지 생성 오류 응답" in message
            or "이미지를 만들지 못했습니다" in message
            or "이미지 생성 중 오류" in message
            or "이미지 생성 도중 오류" in message
            or "이미지 생성이 중지" in message
            or "이번 요청에서는 이미지를 만들지 못했습니다" in message
            or "ChatGPT 전송 버튼을 누르지 못했습니다" in message
            or "ChatGPT 전송 후에도 프롬프트가 입력창에 남아 있습니다" in message
            or "전송 버튼을 누르지 못했습니다" in message
            or "프롬프트가 입력창에 남아 있습니다" in message
            or "메시지 전송 시간이 초과" in message
            or "메시지를 전송하지 못했습니다" in message
            or "스트리밍 정지" in message
            or "스트리밍이 중지" in message
            or "메시지 완료를 기다리는 중" in message
            or "생성 이미지 해상도 검증 실패" in message
            or "이미지 대신 텍스트" in message
            or "send button" in normalized
            or "send timed out" in normalized
            or "message send" in normalized
            or "failed to send" in normalized
            or "could not send" in normalized
            or "content polic" in normalized
            or "violate our content" in normalized
            or "couldn't generate" in normalized
            or "could not generate" in normalized
            or "failed to generate" in normalized
            or "error generating" in normalized
        )

    def _is_chatgpt_transient_send_error_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", (text or "")).strip().lower()
        if not normalized:
            return False
        return (
            "메시지 전송 시간이 초과" in normalized
            or "다시 시도해 주세요" in normalized
            or "메시지를 전송하지 못했습니다" in normalized
            or "message send timed out" in normalized
            or "please try again" in normalized
            or "failed to send message" in normalized
            or "could not send message" in normalized
        )

    def _latest_message_role(self, page) -> str:
        try:
            role = page.evaluate(
                """() => {
                    const turns = Array.from(document.querySelectorAll("[data-testid^='conversation-turn-']"));
                    const latestTurn = turns[turns.length - 1];
                    if (latestTurn) {
                        const roleNode = latestTurn.querySelector("[data-message-author-role]");
                        if (roleNode) return roleNode.getAttribute("data-message-author-role") || "";
                        const images = Array.from(latestTurn.querySelectorAll("img"));
                        const hasGeneratedImage = images.some((img) => {
                            const alt = (img.alt || "").toLowerCase();
                            const src = (img.currentSrc || img.src || "").toLowerCase();
                            return !alt.includes("업로드") && !alt.includes("uploaded") && !src.includes("avatar");
                        });
                        if (hasGeneratedImage) return "assistant";
                        if ((latestTurn.innerText || "").trim()) return "assistant_pending";
                    }
                    const messages = Array.from(document.querySelectorAll("[data-message-author-role]"));
                    const latest = messages[messages.length - 1];
                    return latest ? (latest.getAttribute("data-message-author-role") || "") : "";
                }"""
            )
            return str(role or "")
        except Exception:
            return ""

    def _chatgpt_stop_marker_count(self, page) -> int:
        try:
            body_text = page.locator("body").inner_text(timeout=5000)
        except Exception:
            return 0
        return sum(body_text.count(marker) for marker in ("생각 중지됨", "Thinking stopped", "응답이 중지됨"))

    def _save_chatgpt_generated_image(self, page, candidate: dict, target: Path) -> None:
        from PIL import Image, ImageOps

        target.parent.mkdir(parents=True, exist_ok=True)
        global_index = int(candidate.get("global_index") or -1)
        payload = None
        if global_index >= 0:
            try:
                payload = page.evaluate(
                    """async ({globalIndex}) => {
                        const img = Array.from(document.querySelectorAll("img"))[globalIndex];
                        if (!img) return { ok: false, error: "image element missing" };
                        const src = img.currentSrc || img.src || "";
                        if (!src) return { ok: false, error: "image src missing" };
                        try {
                            const response = await fetch(src);
                            const blob = await response.blob();
                            const buffer = await blob.arrayBuffer();
                            const bytes = new Uint8Array(buffer);
                            let binary = "";
                            const chunkSize = 32768;
                            for (let i = 0; i < bytes.length; i += chunkSize) {
                                binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
                            }
                            return {
                                ok: true,
                                data: btoa(binary),
                                content_type: blob.type || response.headers.get("content-type") || "image/png",
                                width: img.naturalWidth || 0,
                                height: img.naturalHeight || 0
                            };
                        } catch (error) {
                            return { ok: false, error: String(error) };
                        }
                    }""",
                    {"globalIndex": global_index},
                )
            except Exception:
                payload = None
        if isinstance(payload, dict) and payload.get("ok") and payload.get("data"):
            raw = base64.b64decode(str(payload["data"]))
            with Image.open(BytesIO(raw)) as image:
                image = ImageOps.exif_transpose(image)
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGB")
                image.save(target, "PNG")
        elif global_index >= 0:
            page.locator("img").nth(global_index).screenshot(path=str(target), timeout=60000)
        else:
            raise RuntimeError("저장할 ChatGPT 이미지 요소를 찾지 못했습니다.")

        if not self._is_valid_image_file(target):
            raise RuntimeError(f"ChatGPT 생성 이미지 저장에 실패했습니다: {target}")

    def _run_chatgpt_web_section_image_generation(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        prompt_dir: Path,
        visual_dir: Path,
        page,
        resume_from_section: int | None = None,
        progress_callback=None,
    ) -> list[Path]:
        resume_start = max(1, min(len(sections), int(resume_from_section or 1))) if sections else 1
        self._accept_chatgpt_cookies(page)
        if self._page_needs_login(page):
            raise RuntimeError("ChatGPT 로그인이 필요합니다.")
        if resume_from_section is None:
            try:
                self._wait_for_gpt_idle(page, timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS)
            except RuntimeError as exc:
                if not self._is_retryable_section_plan_wait_error(str(exc)):
                    raise
                raise RuntimeError("ChatGPT가 아직 답변 또는 이미지를 생성 중입니다. 완료된 뒤 이어서 실행하세요.") from exc
        else:
            # A user-triggered section resume should use the stored plan immediately.
            page.wait_for_timeout(1000)
        prompt_dir.mkdir(parents=True, exist_ok=True)
        visual_dir.mkdir(parents=True, exist_ok=True)

        attachment_paths = [
            path
            for path in sorted((product.output_dir / "gpt_attachments").glob("*.jpg"))
            if path.exists() and path.stat().st_size > 0
        ][:GPT_ATTACHMENT_IMAGE_LIMIT]
        visual_paths: list[Path] = []
        for section_index, section in enumerate(sections, start=1):
            key = slugify(section.section_key, f"section_{section_index:02d}")
            request = self._chatgpt_section_image_request(product, section, section_index)
            (prompt_dir / f"section_{section_index:02d}_{key}_chatgpt_image_request.txt").write_text(
                request,
                encoding="utf-8",
            )
            out_path = visual_dir / f"section_{section_index:02d}_{key}.png"
            existing_path = self._existing_section_visual_path(visual_dir, section, section_index)
            if existing_path is not None:
                if self._image_matches_reference_sources(existing_path, product.output_dir):
                    existing_path.unlink(missing_ok=True)
                else:
                    visual_paths.append(existing_path)
                    if progress_callback:
                        progress_callback(section_index, len(sections))
                    continue
            if section_index < resume_start:
                continue
            reload_retry_count = 0
            while True:
                if out_path.exists():
                    out_path.unlink(missing_ok=True)
                request_to_send = self._chatgpt_section_image_request(
                    product,
                    section,
                    section_index,
                    retry_variant=min(reload_retry_count, 2),
                )
                if reload_retry_count:
                    (prompt_dir / f"section_{section_index:02d}_{key}_retry_{reload_retry_count + 1:02d}_request.txt").write_text(
                        request_to_send,
                        encoding="utf-8",
                    )
                reference_paths = self._reference_attachment_paths(product, section_index)
                self._raise_if_user_requested_stop_or_skip()
                previous_signatures = self._assistant_image_signatures(page)
                send_error: Exception | None = None
                try:
                    self._send_prompt_to_gpt_page(page, request_to_send, attachment_paths=reference_paths, image_mode=False)
                except Exception as exc:
                    # ChatGPT can accept the prompt while UI confirmation times out.
                    # Wait once, then decide from the actual page result.
                    send_error = exc
                try:
                    self._wait_fixed_section_image_save_delay(page, section_index)
                except RuntimeError as exc:
                    if (
                        self._is_chatgpt_image_generation_error_text(str(exc))
                        and reload_retry_count < CHATGPT_SECTION_IMAGE_RELOAD_RETRY_LIMIT
                    ):
                        reload_retry_count += 1
                        self.automation_signals.result.emit(
                            f"## {product.index + 1}번 URL 섹션 {section_index} 이미지 오류 자동 재시도 {reload_retry_count}회\n"
                            f"오류: {self._compact_error_text(str(exc), 260)}\n\n"
                        )
                        self._reload_chatgpt_for_section_image_retry(page, section_index, reload_retry_count)
                        continue
                    raise
                candidate = self._latest_new_assistant_image_candidate(page, previous_signatures)
                if candidate is None:
                    latest_text, _ = self._latest_gpt_text(page)
                    if (
                        self._is_chatgpt_image_generation_error_text(latest_text)
                        and reload_retry_count < CHATGPT_SECTION_IMAGE_RELOAD_RETRY_LIMIT
                    ):
                        reload_retry_count += 1
                        self.automation_signals.result.emit(
                            f"## {product.index + 1}번 URL 섹션 {section_index} 이미지 오류 자동 재시도 {reload_retry_count}회\n"
                            f"오류: {self._compact_error_text(latest_text, 260)}\n\n"
                        )
                        self._reload_chatgpt_for_section_image_retry(page, section_index, reload_retry_count)
                        continue
                    if send_error is not None:
                        raise RuntimeError(
                            f"섹션 {section_index} 이미지 저장 실패: 전송 확인 실패 후 {CHATGPT_SECTION_IMAGE_SAVE_DELAY_SECONDS}초 동안 새 이미지를 찾지 못했습니다. "
                            f"{self._compact_error_text(str(send_error), 180)}"
                        )
                    raise RuntimeError(f"섹션 {section_index} 이미지 저장 실패: {CHATGPT_SECTION_IMAGE_SAVE_DELAY_SECONDS}초 대기 후 새 이미지를 찾지 못했습니다.")
                self._save_chatgpt_generated_image(page, candidate, out_path)
                if not self._is_valid_generated_visual_file(out_path):
                    out_path.unlink(missing_ok=True)
                    raise RuntimeError(f"생성 이미지 해상도 검증 실패: {out_path}")
                if self._image_matches_reference_sources(out_path, product.output_dir):
                    out_path.unlink(missing_ok=True)
                    raise RuntimeError(f"섹션 {section_index} 이미지가 첨부/원본 이미지와 같아 재시도가 필요합니다.")
                visual_paths.append(out_path)
                if progress_callback:
                    progress_callback(section_index, len(sections))
                break
        return self._collect_section_visual_paths(product, sections, visual_dir)

    def _section_visual_output_path(
        self,
        visual_dir: Path,
        section: SectionPlan,
        section_index: int,
    ) -> Path:
        key = slugify(section.section_key, f"section_{section_index:02d}")
        return visual_dir / f"section_{section_index:02d}_{key}.png"

    def _existing_section_visual_path(
        self,
        visual_dir: Path,
        section: SectionPlan,
        section_index: int,
    ) -> Path | None:
        exact_path = self._section_visual_output_path(visual_dir, section, section_index)
        if self._is_valid_generated_visual_file(exact_path):
            return exact_path
        prefix = f"section_{section_index:02d}_"
        candidates = [
            path
            for path in visual_dir.glob(f"{prefix}*.png")
            if path.name.startswith(prefix)
        ]
        candidates.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
        for candidate in candidates:
            if self._is_valid_generated_visual_file(candidate):
                return candidate
        return None

    def _collect_section_visual_paths(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        visual_dir: Path | None = None,
    ) -> list[Path]:
        visual_dir = visual_dir or (product.output_dir / "generated_visuals")
        paths: list[Path] = []
        for section_index, section in enumerate(sections, start=1):
            existing_path = self._existing_section_visual_path(visual_dir, section, section_index)
            if existing_path is not None and not self._image_matches_reference_sources(existing_path, product.output_dir):
                paths.append(existing_path)
        return paths

    def _first_missing_section_visual_index(
        self,
        sections: list[SectionPlan],
        visual_dir: Path,
        skip_sections: set[int] | None = None,
    ) -> int | None:
        for section_index, section in enumerate(sections, start=1):
            if skip_sections and section_index in skip_sections:
                continue
            existing_path = self._existing_section_visual_path(visual_dir, section, section_index)
            if existing_path is None or self._image_matches_reference_sources(existing_path, visual_dir.parent):
                return section_index
        return None

    def _chatgpt_short_image_retry_request(self, product: ProductRecord, section: SectionPlan, section_index: int) -> str:
        product_label = product.product_name or product.title or "제품"
        display_name = self._display_section_name(section.section_key, section.section_name)
        concept = self._default_chatgpt_visual_concept(product, section, section_index)
        return (
            "이미지 생성. 설명 없이 이미지 1장.\n"
            f"{product_label}와 같은 형태의 제품을 참고한 한국 쇼핑몰 상세페이지용 세로 비주얼.\n"
            f"섹션 {section_index:02d} {display_name}: {concept}\n"
            "밝은 상업 사진, 실제 제품 형태 유지, 깨끗한 배경, 좌측 또는 상단 여백."
        )

    def _generate_thumbnail_images(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        run_stamp: str,
        page=None,
        resume_from_thumbnail: int | None = None,
        progress_callback=None,
    ) -> ThumbnailResult:
        resume_start = max(
            1,
            min(REQUIRED_THUMBNAIL_IMAGE_COUNT, int(resume_from_thumbnail or 1)),
        )
        if page is None:
            raise RuntimeError("썸네일 생성은 현재 열린 ChatGPT 탭이 필요합니다.")
        self._accept_chatgpt_cookies(page)
        if self._page_needs_login(page):
            raise RuntimeError("ChatGPT 로그인이 필요합니다.")
        self._wait_for_gpt_idle(page, timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS)

        thumbnail_dir = product.output_dir / "thumbnails"
        prompt_dir = product.output_dir / "thumbnail_prompts"
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        prompt_dir.mkdir(parents=True, exist_ok=True)
        for old_file in thumbnail_dir.glob("*.png"):
            try:
                file_index = int(old_file.stem)
            except ValueError:
                file_index = 0
            should_regenerate_from_resume = resume_from_thumbnail is not None and file_index >= resume_start
            if old_file.is_file() and (
                should_regenerate_from_resume
                or not self._is_valid_thumbnail_file(old_file)
            ):
                old_file.unlink(missing_ok=True)
        for old_file in prompt_dir.glob("thumbnail_*"):
            if old_file.is_file():
                match = re.search(r"thumbnail_(\d+)", old_file.name)
                file_index = int(match.group(1)) if match else 0
                if resume_from_thumbnail is None or file_index >= resume_start:
                    old_file.unlink(missing_ok=True)

        generated_paths: list[Path] = []
        prompt_paths: list[Path] = []
        for thumbnail_index in range(1, REQUIRED_THUMBNAIL_IMAGE_COUNT + 1):
            request = self._chatgpt_thumbnail_image_request(product, sections, thumbnail_index)
            prompt_path = prompt_dir / f"thumbnail_{thumbnail_index:02d}_request.txt"
            prompt_path.write_text(request, encoding="utf-8")
            prompt_paths.append(prompt_path)

            out_path = thumbnail_dir / f"{thumbnail_index}.png"
            existing_thumbnail_ok = False
            if self._is_valid_thumbnail_file(out_path):
                existing_thumbnail_ok = (
                    not self._image_matches_reference_sources(out_path, product.output_dir)
                    and not self._image_duplicates_existing_paths(out_path, generated_paths)
                    and not self._image_duplicates_other_product_thumbnail(out_path, product.output_dir)
                )
            if existing_thumbnail_ok:
                generated_paths.append(out_path)
                if progress_callback:
                    progress_callback(thumbnail_index, REQUIRED_THUMBNAIL_IMAGE_COUNT)
                continue
            if out_path.exists():
                out_path.unlink(missing_ok=True)
            if self._is_valid_thumbnail_file(out_path):
                generated_paths.append(out_path)
                if progress_callback:
                    progress_callback(thumbnail_index, REQUIRED_THUMBNAIL_IMAGE_COUNT)
                continue

            last_error: Exception | None = None
            generated_current_thumbnail = False
            thumbnail_attempt_limit = CHATGPT_THUMBNAIL_IMAGE_RETRY_LIMIT
            for attempt in range(1, thumbnail_attempt_limit + 1):
                request_to_send = self._chatgpt_thumbnail_image_request(
                    product,
                    sections,
                    thumbnail_index,
                    retry_variant=min(attempt - 1, 4),
                )
                if attempt > 1:
                    retry_prompt_path = prompt_dir / f"thumbnail_{thumbnail_index:02d}_retry_{attempt:02d}_request.txt"
                    retry_prompt_path.write_text(request_to_send, encoding="utf-8")
                self._raise_if_user_requested_stop_or_skip()
                self.automation_signals.task_status.emit(
                    product.index,
                    f"썸네일 생성중 {thumbnail_index - 1}/{REQUIRED_THUMBNAIL_IMAGE_COUNT}",
                )
                self.automation_signals.status.emit(
                    f"썸네일 {thumbnail_index}/{REQUIRED_THUMBNAIL_IMAGE_COUNT} 요청 준비 중..."
                    f" ({attempt}/{thumbnail_attempt_limit})"
                )
                previous_signatures = self._assistant_image_signatures(page)
                previous_stop_count = self._chatgpt_stop_marker_count(page)
                previous_text, _ = self._latest_gpt_text(page)
                attachment_paths = self._thumbnail_reference_attachment_paths(product, thumbnail_index)
                candidate: dict | None = None
                try:
                    self._send_prompt_to_gpt_page(page, request_to_send, attachment_paths=attachment_paths, image_mode=False)
                    self.automation_signals.status.emit(
                        f"썸네일 {thumbnail_index}/{REQUIRED_THUMBNAIL_IMAGE_COUNT} 이미지 생성 대기 중..."
                    )
                except Exception as send_exc:
                    last_error = send_exc
                    self.automation_signals.status.emit(
                        f"썸네일 {thumbnail_index}/{REQUIRED_THUMBNAIL_IMAGE_COUNT} 전송 확인 중..."
                    )
                    try:
                        candidate = self._wait_for_chatgpt_generated_image(
                            page,
                            previous_signatures,
                            previous_stop_count=previous_stop_count,
                            timeout_seconds=CHATGPT_IMAGE_WAIT_TIMEOUT_SECONDS,
                            previous_text=previous_text,
                            wait_status=f"썸네일 {thumbnail_index}/{REQUIRED_THUMBNAIL_IMAGE_COUNT} 이미지 생성 대기 중",
                        )
                    except Exception:
                        pass
                    if candidate is None:
                        if not self._should_retry_chatgpt_image_request(send_exc):
                            raise
                        retry_log_path = prompt_dir / f"thumbnail_{thumbnail_index:02d}_retry.log"
                        with retry_log_path.open("a", encoding="utf-8") as retry_log:
                            retry_log.write(
                                f"[{now_stamp()}] send retry after attempt {attempt}: "
                                f"{self._compact_error_text(str(send_exc), 260)}\n"
                            )
                        if attempt >= thumbnail_attempt_limit:
                            break
                        self.automation_signals.status.emit(
                            f"썸네일 {thumbnail_index}/{REQUIRED_THUMBNAIL_IMAGE_COUNT} 재시도 준비 중..."
                        )
                        self._reload_chatgpt_for_thumbnail_image_retry(page, thumbnail_index, attempt)
                        continue
                if candidate is None:
                    try:
                        candidate = self._wait_for_chatgpt_generated_image(
                            page,
                            previous_signatures,
                            previous_stop_count=previous_stop_count,
                            timeout_seconds=CHATGPT_IMAGE_WAIT_TIMEOUT_SECONDS,
                            previous_text=previous_text,
                            wait_status=f"썸네일 {thumbnail_index}/{REQUIRED_THUMBNAIL_IMAGE_COUNT} 이미지 생성 대기 중",
                        )
                    except Exception as exc:
                        last_error = exc
                        if not self._should_retry_chatgpt_image_request(exc):
                            raise
                        retry_log_path = prompt_dir / f"thumbnail_{thumbnail_index:02d}_retry.log"
                        with retry_log_path.open("a", encoding="utf-8") as retry_log:
                            retry_log.write(
                                f"[{now_stamp()}] retry after attempt {attempt}: "
                                f"{self._compact_error_text(str(exc), 260)}\n"
                            )
                        if attempt >= thumbnail_attempt_limit:
                            break
                        self.automation_signals.status.emit(
                            f"썸네일 {thumbnail_index}/{REQUIRED_THUMBNAIL_IMAGE_COUNT} 이미지 생성 재시도 중..."
                        )
                        self._reload_chatgpt_for_thumbnail_image_retry(page, thumbnail_index, attempt)
                        continue
                if candidate is None:
                    last_error = RuntimeError("ChatGPT 썸네일 생성 결과가 비어 있습니다.")
                    continue
                try:
                    self.automation_signals.status.emit(
                        f"썸네일 {thumbnail_index}/{REQUIRED_THUMBNAIL_IMAGE_COUNT} 이미지 저장 중..."
                    )
                    if out_path.exists():
                        out_path.unlink(missing_ok=True)
                    self._save_chatgpt_generated_image(page, candidate, out_path)
                    self._normalize_thumbnail_image(out_path, out_path)
                    if not self._is_valid_thumbnail_file(out_path):
                        raise RuntimeError(f"썸네일 이미지 해상도 검증 실패: {out_path}")
                    if self._image_duplicates_existing_paths(out_path, generated_paths):
                        raise RuntimeError(f"썸네일 {thumbnail_index} 이미지가 이전 썸네일과 같아 재시도가 필요합니다.")
                    if self._image_duplicates_other_product_thumbnail(out_path, product.output_dir):
                        raise RuntimeError(f"썸네일 {thumbnail_index} 이미지가 다른 상품 썸네일과 같아 재시도가 필요합니다.")
                    generated_paths.append(out_path)
                    if progress_callback:
                        progress_callback(thumbnail_index, REQUIRED_THUMBNAIL_IMAGE_COUNT)
                    generated_current_thumbnail = True
                    break
                except Exception as exc:
                    last_error = exc
                    if out_path.exists():
                        out_path.unlink(missing_ok=True)
                    retry_log_path = prompt_dir / f"thumbnail_{thumbnail_index:02d}_retry.log"
                    with retry_log_path.open("a", encoding="utf-8") as retry_log:
                        retry_log.write(
                            f"[{now_stamp()}] validation retry after attempt {attempt}: "
                            f"{self._compact_error_text(str(exc), 260)}\n"
                        )
                    if attempt >= thumbnail_attempt_limit:
                        break
                    self.automation_signals.status.emit(
                        f"썸네일 {thumbnail_index}/{REQUIRED_THUMBNAIL_IMAGE_COUNT} 검증 실패 후 재시도 중..."
                    )
                    self._reload_chatgpt_for_thumbnail_image_retry(page, thumbnail_index, attempt)
            if not generated_current_thumbnail:
                failure_text = self._compact_error_text(str(last_error), 260) if last_error else "-"
                self.automation_signals.result.emit(
                    f"## {product.index + 1}번 URL 썸네일 {thumbnail_index} 생성 실패\n"
                    f"{CHATGPT_THUMBNAIL_IMAGE_RETRY_LIMIT}회 실패 후 현재 상품 썸네일 생성을 중단합니다.\n"
                    f"오류: {failure_text}\n\n"
                )
                self.automation_signals.task_status.emit(
                    product.index,
                    f"썸네일 {thumbnail_index} 실패",
                )
                raise ThumbnailGenerationFailed(f"썸네일 {thumbnail_index} 생성 실패: {failure_text}")

        return ThumbnailResult(paths=generated_paths, prompt_paths=prompt_paths, image_model=CHATGPT_WEB_IMAGE_MODEL)

    def _current_thumbnail_result(self, product: ProductRecord) -> ThumbnailResult:
        thumbnail_dir = product.output_dir / "thumbnails"
        prompt_dir = product.output_dir / "thumbnail_prompts"
        thumbnail_paths: list[Path] = []
        for index in range(1, REQUIRED_THUMBNAIL_IMAGE_COUNT + 1):
            path = thumbnail_dir / f"{index}.png"
            if not self._is_valid_thumbnail_file(path):
                continue
            if self._image_matches_reference_sources(path, product.output_dir):
                continue
            if self._image_duplicates_existing_paths(path, thumbnail_paths):
                continue
            if self._image_duplicates_other_product_thumbnail(path, product.output_dir):
                continue
            thumbnail_paths.append(path)
        prompt_paths = sorted(prompt_dir.glob("thumbnail_*_request.txt")) if prompt_dir.exists() else []
        return ThumbnailResult(
            paths=thumbnail_paths,
            prompt_paths=prompt_paths,
            image_model=CHATGPT_WEB_IMAGE_MODEL,
        )

    def _thumbnail_result_complete(self, thumbnail_result: ThumbnailResult) -> bool:
        if thumbnail_result.image_model != CHATGPT_WEB_IMAGE_MODEL:
            return False
        if len(thumbnail_result.paths) != REQUIRED_THUMBNAIL_IMAGE_COUNT:
            return False
        if not all(self._is_valid_thumbnail_file(path) for path in thumbnail_result.paths):
            return False
        return self._thumbnail_files_are_visually_distinct(thumbnail_result.paths)

    def _thumbnail_plan_context(self, sections: list[SectionPlan]) -> str:
        lines = []
        for section in sections:
            if section.section_key == DETAIL_REVIEW_SECTION_KEY:
                continue
            if len(lines) >= 10:
                break
            index = len(lines) + 1
            display_name = self._display_section_name(section.section_key, section.section_name)
            pieces = self._dedupe_text_items(
                [
                    section.headline,
                    section.subheadline,
                    " / ".join(section.bullets[:2]),
                ]
            )
            lines.append(f"{index}. {display_name}: {' '.join(pieces)[:90]}")
        return "\n".join(lines)

    def _thumbnail_source_context(self, product: ProductRecord) -> str:
        counts = self._source_image_counts_by_origin(product)
        source_lines = [
            f"- ownerclan/도매꾹 이미지: {counts.get('ownerclan', 0)}장",
            f"- 1688 이미지: {counts.get('1688', 0)}장",
            f"- GPT 첨부 이미지: {len(list((product.output_dir / 'gpt_attachments').glob('*.jpg')))}장",
        ]
        facts = self._dedupe_text_items([product.category, product.options_text, product.price_text, *product.facts[:5]])
        if facts:
            source_lines.append(f"- 확인 정보: {' / '.join(facts)[:300]}")
        return "\n".join(source_lines)

    def _thumbnail_product_fact_summary(self, product: ProductRecord) -> str:
        def compact(value: str, limit: int) -> str:
            normalized = re.sub(r"\s+", " ", str(value or "")).strip()
            if len(normalized) <= limit:
                return normalized
            return normalized[:limit].rstrip() + "..."

        display_code = str(product.code or "").strip()
        if display_code.lower().startswith("url_"):
            for candidate in (product.output_dir.name, product.url):
                match = re.search(r"\d{5,}", str(candidate or ""))
                if match:
                    display_code = match.group(0)
                    break
        lines = self._dedupe_text_items(
            [
                f"상품코드 {compact(display_code, 80)}" if display_code else "",
                f"카테고리 {compact(product.category, 160)}" if product.category else "",
                f"옵션 {compact(product.options_text, 450)}" if product.options_text else "",
                f"가격 {compact(product.price_text, 180)}" if product.price_text else "",
            ]
        )
        fact_text = compact(" / ".join(self._dedupe_text_items(product.facts[:12])), 650)
        if fact_text:
            lines.append(f"기타스펙 {fact_text}")
        return " / ".join(lines) or "첨부 상품 이미지 기준"

    def _reference_attachment_paths(self, product: ProductRecord, variant_index: int = 1) -> list[Path]:
        attachment_dir = product.output_dir / "gpt_attachments"
        attachments = [
            path
            for path in sorted(attachment_dir.glob("*.jpg"))
            if path.exists() and path.stat().st_size > 0
        ]
        if not attachments:
            attachments = [
                path
                for path in self._gpt_attachment_source_paths(product)
                if path.exists() and path.stat().st_size > 0
            ]
        if not attachments:
            return []
        attachments = self._dedupe_paths(attachments)
        offset = max(0, (variant_index - 1) % len(attachments))
        rotated = attachments[offset:] + attachments[:offset]
        return rotated[:GPT_ATTACHMENT_IMAGE_LIMIT]

    def _thumbnail_reference_attachment_paths(self, product: ProductRecord, thumbnail_index: int) -> list[Path]:
        from PIL import Image, ImageOps

        source_paths = self._reference_attachment_paths(product, thumbnail_index)
        if not source_paths:
            return []
        reference_dir = product.output_dir / "thumbnail_references"
        reference_dir.mkdir(parents=True, exist_ok=True)
        clean_paths: list[Path] = []
        for index, source_path in enumerate(source_paths, start=1):
            if self._is_clean_thumbnail_reference(source_path):
                clean_paths.append(source_path)
                continue
            try:
                with Image.open(source_path) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    width, height = image.size
                    if width < 320 or height < 320:
                        continue
                    crop_size = min(width, height)
                    left = max(0, (width - crop_size) // 2)
                    top = max(0, min(height - crop_size, int(height * 0.18)))
                    cropped = image.crop((left, top, left + crop_size, top + crop_size))
                    cropped = ImageOps.contain(cropped, (1000, 1000), method=Image.Resampling.LANCZOS)
                    target = reference_dir / f"thumbnail_ref_{thumbnail_index:02d}_{index:02d}.jpg"
                    cropped.save(target, "JPEG", quality=92, optimize=True)
                if self._is_clean_thumbnail_reference(target):
                    clean_paths.append(target)
            except Exception:
                continue
        if not clean_paths:
            return source_paths[: min(2, GPT_ATTACHMENT_IMAGE_LIMIT)]
        return self._dedupe_paths(clean_paths)[: min(2, GPT_ATTACHMENT_IMAGE_LIMIT)]

    def _dedupe_paths(self, paths: list[Path]) -> list[Path]:
        deduped: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            try:
                key = str(path.resolve()).lower()
            except Exception:
                key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(path)
        return deduped

    def _is_clean_thumbnail_reference(self, path: Path) -> bool:
        if not path.exists() or path.stat().st_size <= 0:
            return False
        try:
            from PIL import Image

            with Image.open(path) as image:
                width, height = image.size
        except Exception:
            return False
        if width < 420 or height < 420:
            return False
        ratio = width / max(1, height)
        # Long detail-page strips, logos, and infographic captures confuse image generation.
        return 0.65 <= ratio <= 1.55

    def _chatgpt_thumbnail_image_request(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        thumbnail_index: int,
        retry_variant: int = 0,
    ) -> str:
        plan_context = self._thumbnail_plan_context(sections)
        shot_plan = self._thumbnail_shot_plan(product, thumbnail_index, plan_context)
        fact_summary = self._thumbnail_product_fact_summary(product)
        brand_logo_rule = self._brand_logo_prompt_instruction()
        plan_block = f"기획 요약:\n{plan_context}\n\n" if plan_context.strip() else ""
        if retry_variant == 1:
            return (
                "정사각형 상품 썸네일 1장만 이미지로 생성. 설명 문장 금지.\n"
                f"상품명: {product.product_name or product.title or product.code}\n"
                f"상품 정보: {fact_summary}\n"
                f"이번 컷 번호: {thumbnail_index}\n"
                f"{shot_plan['prompt'].strip()}\n"
                f"{brand_logo_rule}\n"
                "첨부 이미지의 실제 상품 형태, 색상, 소재, 옵션, 비율 유지.\n"
                "이미지 안 글자, 로고, 워터마크, 치수선 금지.\n"
                "사람은 필요하지 않으면 넣지 말고, 꼭 보이면 얼굴과 개인 식별 특징은 원본과 다르게 변경해 원본 인물로 식별되지 않게 처리.\n"
            )
        if retry_variant >= 4:
            return (
                f"{brand_logo_rule}\n"
                "첨부한 실제 제품만 참고해서 정사각형 제품사진 1장을 생성.\n"
                "설명 문장 없이 이미지 결과만 출력.\n"
                "사람, 얼굴, 손, 신체, 착용 장면, 로고, 글자, 숫자, 배지, 워터마크는 모두 제외.\n"
                "제품만 흰색 또는 아주 밝은 회색 배경 중앙에 배치.\n"
                "첨부 제품의 실제 색상, 소재, 형태, 비율은 유지하고 다른 물건으로 바꾸지 않음.\n"
                "1000x1000 정사각형, 제품 전체가 잘리지 않게 포함.\n"
            )
        if retry_variant >= 3:
            return (
                f"{brand_logo_rule}\n"
                "정사각형 상품 대표 썸네일 이미지 1장만 생성. 설명 문장 금지.\n"
                f"상품명: {product.product_name or product.title or product.code}\n"
                f"컷 번호: {thumbnail_index}\n"
                "첨부 이미지 속 실제 상품만 기준으로 한다.\n"
                "사람, 얼굴, 모델, 착용 장면, 손, 신체 일부는 넣지 않는다.\n"
                "상품 단독 또는 상품 묶음만 흰색/밝은 그레이 배경 위에 배치한다.\n"
                "상품의 색상, 소재, 옵션, 형태, 비율은 첨부 이미지와 다르게 바꾸지 않는다.\n"
                "1000x1000 정사각형, 상품 전체가 잘리지 않게 중앙 배치한다.\n"
                "이미지 안 글자, 숫자, 로고, 워터마크, 치수선, 배지, 허구 인증, 과장 효능 표현은 넣지 않는다.\n"
            )
        if retry_variant >= 2:
            return (
                f"{brand_logo_rule}\n"
                "상품 대표 썸네일 이미지 1장 생성. 텍스트 답변 금지.\n"
                f"상품명: {product.product_name or product.title or product.code}\n"
                f"컷 {thumbnail_index}: 첨부 상품을 기준으로 다른 배경/거리/각도로 구성.\n"
                "1000x1000 정사각형, 상품 전체가 잘리지 않게, 깨끗한 쇼핑몰 대표컷.\n"
                "첨부 이미지와 다른 상품으로 바꾸지 말 것. 글자/로고/워터마크 금지.\n"
                "사람, 얼굴, 신체는 넣지 말고 상품 중심으로 구성.\n"
            )
        common_header = (
            "현재 단계: 상세페이지 섹션 1~10 이후 이어지는 썸네일 생성. 섹션 11이나 세로 상세페이지를 만들지 마.\n"
            "정사각형 상품 썸네일 이미지 1장만 출력하고 설명 문장은 쓰지 마.\n"
            "첨부한 실제 상품 이미지 여러 장과 아래 짧은 기획 요약만 기준으로 작업해.\n"
            "상품 형태, 색상, 소재, 옵션, 비율은 그대로 유지하고 없는 상품을 상상하지 마.\n"
            "사람이 보이면 얼굴과 개인 식별 특징은 원본과 다르게 변경해 원본 인물로 식별되지 않게 처리하되, 상품 자체는 바꾸지 마.\n"
            "중국어, 치수선, 워터마크, 배경만 제거하거나 정돈해.\n\n"
            f"상품명: {product.product_name or product.title or product.code}\n"
            f"상품 확인 정보: {fact_summary}\n\n"
            f"{plan_block}"
            "공통 금지:\n"
            "- 이미지 안에 글자, 숫자, 중국어, 영어, 로고, 워터마크, 배지, 치수선 금지\n"
            "- 다른 상품으로 바꾸기 금지\n"
            "- 상품 구조 왜곡 금지\n"
            "- 첨부 이미지와 상세페이지 기획에 없는 색상, 소재, 옵션, 부품, 장식 추가 금지\n"
            "- 카드 템플릿, 상세페이지 세로 섹션, 설명 패널 금지\n"
            "- 빈 배경, 더미 이미지 금지\n"
        )
        return (
            common_header
            + "\n"
            + brand_logo_rule
            + "\n"
            + shot_plan["prompt"].strip()
            + "\n\n검수 기준:\n"
            f"- {THUMBNAIL_IMAGE_SIZE} 정사각 PNG에 맞는 대표 썸네일 구도\n"
            "- 1~5번은 같은 상품이어도 배경, 거리, 각도, 소품, 사람 포함 여부가 눈에 띄게 달라야 함\n"
            "- 상품 모양, 색상, 소재, 옵션, 비율을 첨부 이미지와 기획에서 벗어나게 바꾸지 말 것\n"
            "- 상품과 무관한 다른 제품, 추천상품, 허위 인증, 과장 효능 표현 금지\n"
        )

    def _thumbnail_shot_plan(self, product: ProductRecord, thumbnail_index: int, plan_context: str = "") -> dict[str, str]:
        product_text = " ".join(
            [
                product.product_name,
                product.category,
                product.options_text,
                " ".join(product.facts[:12]),
            ]
        ).lower()
        is_shoe_storage = any(token in product_text for token in ["신발장", "슈즈랙", "신발 선반", "신발 정리", "현관"])
        is_shelf = any(token in product_text for token in ["선반", "랙", "수납", "책장", "shelf", "rack"])

        detail_target = "상세페이지 기획과 첨부 이미지에서 반복 확인되는 실제 상품 핵심 디테일"
        use_scene = "상품 용도에 맞게 실제 사용 공간에 놓인 자연스러운 장면"
        lifestyle_space = "상세페이지 기획에 맞는 실제 착용/사용/배치 공간"
        sns_space = "상세페이지 기획과 상품 분위기에 맞는 자연광 공간"
        if is_shoe_storage:
            detail_target = "선반 칸 높이, 둥근 모서리, 신발이 들어가는 깊이, 하단 받침"
            use_scene = "현관에서 신발 한 켤레가 선반에 정리된 장면"
            lifestyle_space = "현관문 옆, 신발을 정리한 실제 입구 공간"
            sns_space = "밝은 현관 인테리어, 신발 2~3켤레와 작은 식물만 둔 공간"
        elif is_shelf:
            use_scene = "컵, 책, 소품이 선반에 자연스럽게 놓인 장면"

        plans = {
            1: {
                "prompt": (
                    "이번 컷: 1번 실제 상품 기준 대표컷\n"
                    "목적: 검색 결과에서 첨부 이미지의 실제 상품 형태를 바로 알아보게 하는 대표 이미지\n"
                    "구도: 정면보다 살짝 높은 3/4 각도, 상품 전체 중앙 배치\n"
                    "배경: 흰색 또는 아주 밝은 그레이 스튜디오 배경\n"
                    "소품: 없음 또는 상품 용도에 필요한 최소 소품만\n"
                    "상품 비중: 화면의 72~84%\n"
                    "크롭: 상품 상하좌우 절대 잘리지 않게 전체 포함\n"
                    "제품 기준: 상세페이지 기획과 첨부 이미지 속 실제 상품의 형태, 색상, 소재, 옵션, 비율을 그대로 유지"
                ),
            },
            2: {
                "prompt": (
                    "이번 컷: 2번 배경 있는 라이프스타일컷\n"
                    "목적: 첨부 상품을 실제 착용/사용/배치했을 때 분위기와 크기감 표현\n"
                    "구도: 1번과 다른 거리/각도, 35mm 넓은 시점, 상품을 좌측 또는 우측 1/3 지점에 배치\n"
                    f"배경: 상세페이지 기획에 맞는 실제 착용/사용/배치 공간. 현재 상품 추천 공간: {lifestyle_space}\n"
                    "소품: 상품 용도와 맞는 물건 2~4개\n"
                    "반복 금지: 1번처럼 흰 배경, 정중앙 단독컷 금지\n"
                    "상품 비중: 화면의 58~72%\n"
                    "제품 기준: 첨부 이미지 속 실제 상품 외형을 유지하고 배경과 각도만 바꿈"
                ),
            },
            3: {
                "prompt": (
                    "이번 컷: 3번 실제 사용 분위기컷\n"
                    "목적: 상품을 어디에 쓰는지 직관적으로 보여주기\n"
                    "구도: 상품이 실제 사용 공간 위에 놓인 45도 중근거리 컷\n"
                    f"상황: 상품 용도에 맞는 자연스러운 사용 환경. 현재 상품 추천 장면: {use_scene}\n"
                    "배경: 2번과 다른 위치 또는 다른 벽면의 실제 생활공간\n"
                    "반복 금지: 2번과 같은 배경/각도 금지, 인물/손/얼굴/신체 없이 상품 중심\n"
                    "상품 비중: 화면의 62~78%\n"
                    "제품 기준: 첨부 상품의 실제 형태와 비율이 우선"
                ),
            },
            4: {
                "prompt": (
                    "이번 컷: 4번 기능/구조 디테일컷\n"
                    "목적: 구매 결정에 필요한 상품 장점 보여주기\n"
                    "구도: 상품 핵심 부위 근접컷. 전체컷 반복 금지\n"
                    "상품별 자동 선택: 상세페이지 기획과 첨부 이미지에서 구매 판단에 중요한 실제 디테일 1~2개만 선택\n"
                    "- 예: 소재감, 마감, 크기감, 색상/옵션 차이, 착용 또는 사용 구조\n"
                    f"현재 상품에서 우선 볼 디테일: {detail_target}\n"
                    "배경: 단순한 실내 배경을 흐리게 처리\n"
                    "반복 금지: 2~3번과 같은 거리의 전체 상품컷 금지\n"
                    "제품 기준: 첨부 이미지에 실제로 보이는 디테일만 확대, 없는 부품/잠금/장식 생성 금지"
                ),
            },
            5: {
                "prompt": (
                    "이번 컷: 5번 상품 맞춤 랜덤 콘셉트컷\n"
                    "목적: 1~4번과 다른 분위기로 클릭 유도\n"
                    "콘셉트는 상세페이지 기획에 맞게 하나 선택:\n"
                    "- 대표 색상/옵션 분위기 컷\n"
                    "- 상품 사용 분위기가 보이는 SNS형 정물컷\n"
                    "- 상세페이지 기획의 핵심 장점을 보여주는 컷\n"
                    "- 계절/공간/용도 분위기가 살아나는 컷\n"
                    "구도: 하이앵글 또는 로우앵글 중 이전 컷과 다른 원근감\n"
                    f"배경: 이전 컷과 다른 공간/조명/소품. 현재 상품 추천 분위기: {sns_space}\n"
                    "반복 금지: 2번 같은 방 모서리, 3번 같은 생활공간, 4번 같은 클로즈업 금지\n"
                    "상품 비중: 화면의 60~76%\n"
                    "제품 기준: 콘셉트만 바꾸고 상품은 첨부 이미지의 실제 상품 그대로 유지"
                ),
            },
        }
        return plans.get(thumbnail_index, plans[5])

    def _normalize_thumbnail_image(self, source_path: Path, target_path: Path, size: int = 1000) -> None:
        from PIL import Image, ImageOps

        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image = ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            image.save(target_path, "PNG")

    def _imagegen_cli_python(self) -> str:
        if getattr(sys, "frozen", False):
            return "python"
        return sys.executable or "python"

    def _run_gpt_image2_section_generation(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        prompt_dir: Path,
        visual_dir: Path,
        resume_from_section: int | None = None,
        progress_callback=None,
    ) -> list[Path]:
        resume_start = max(1, min(len(sections), int(resume_from_section or 1))) if sections else 1
        imagegen_script = Path.home() / ".codex" / "skills" / "imagegen" / "scripts" / "image_gen.py"
        if not imagegen_script.exists():
            raise RuntimeError(f"imagegen 스크립트를 찾지 못했습니다: {imagegen_script}")

        attachment_paths = [
            path
            for path in sorted((product.output_dir / "gpt_attachments").glob("*.jpg"))
            if path.exists() and path.stat().st_size > 0
        ][:GPT_ATTACHMENT_IMAGE_LIMIT]
        if not attachment_paths:
            attachment_paths = self._gpt_attachment_source_paths(product)[:GPT_ATTACHMENT_IMAGE_LIMIT]
        if not attachment_paths:
            raise RuntimeError(f"{LATEST_CODEX_IMAGE_MODEL}에 넣을 상품/상세 이미지가 없습니다.")

        if not os.environ.get("OPENAI_API_KEY"):
            self._write_manual_imagegen_runner(product, sections, prompt_dir, visual_dir, attachment_paths, imagegen_script)
            return []

        visual_paths: list[Path] = []
        log_dir = product.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        for section_index, section in enumerate(sections, start=1):
            key = slugify(section.section_key, f"section_{section_index:02d}")
            prompt_path = prompt_dir / f"section_{section_index:02d}_{key}_prompt.txt"
            if not prompt_path.exists():
                prompt_path.write_text(
                    self._latest_image_prompt_for_section(product, section, section_index, attachment_paths[0]),
                    encoding="utf-8",
                )
            out_path = visual_dir / f"section_{section_index:02d}_{key}.png"
            existing_path = self._existing_section_visual_path(visual_dir, section, section_index)
            if existing_path is not None:
                visual_paths.append(existing_path)
                if progress_callback:
                    progress_callback(section_index, len(sections))
                continue
            if section_index < resume_start:
                continue
            command = [
                self._imagegen_cli_python(),
                str(imagegen_script),
                "edit",
                "--model",
                LATEST_CODEX_IMAGE_MODEL,
                "--prompt-file",
                str(prompt_path),
                "--out",
                str(out_path),
                "--size",
                LATEST_CODEX_IMAGE_SIZE,
                "--quality",
                "high",
                "--input-fidelity",
                "high",
                "--no-augment",
                "--force",
            ]
            for image_path in attachment_paths:
                command.extend(["--image", str(image_path)])
            completed = subprocess.run(
                command,
                cwd=str(product.output_dir),
                text=True,
                capture_output=True,
                timeout=900,
            )
            (log_dir / f"section_{section_index:02d}_{key}.stdout.log").write_text(completed.stdout or "", encoding="utf-8")
            (log_dir / f"section_{section_index:02d}_{key}.stderr.log").write_text(completed.stderr or "", encoding="utf-8")
            if completed.returncode != 0:
                raise RuntimeError(
                    f"{LATEST_CODEX_IMAGE_MODEL} 섹션 {section_index} 생성 실패: {(completed.stderr or completed.stdout or '').strip()[:700]}"
                )
            if not self._is_valid_image_file(out_path):
                raise RuntimeError(f"{LATEST_CODEX_IMAGE_MODEL} 섹션 {section_index} 결과 PNG가 없습니다: {out_path}")
            visual_paths.append(out_path)
            if progress_callback:
                progress_callback(section_index, len(sections))
        return self._collect_section_visual_paths(product, sections, visual_dir)

    def _write_manual_imagegen_runner(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        prompt_dir: Path,
        visual_dir: Path,
        attachment_paths: list[Path],
        imagegen_script: Path,
    ) -> Path:
        script_path = prompt_dir / "run_gpt_image2_real_sections.ps1"
        lines = [
            "$ErrorActionPreference = 'Stop'",
            "if (-not $env:OPENAI_API_KEY) { throw 'OPENAI_API_KEY 환경변수가 필요합니다.' }",
            f"$imagegen = '{imagegen_script}'",
            f"$outDir = '{visual_dir}'",
            "New-Item -ItemType Directory -Force -Path $outDir | Out-Null",
        ]
        attachment_args = " ".join(f"--image '{path}'" for path in attachment_paths)
        for section_index, section in enumerate(sections, start=1):
            key = slugify(section.section_key, f"section_{section_index:02d}")
            prompt_path = prompt_dir / f"section_{section_index:02d}_{key}_prompt.txt"
            out_path = visual_dir / f"section_{section_index:02d}_{key}.png"
            lines.append(
                f"python $imagegen edit --model {LATEST_CODEX_IMAGE_MODEL} --prompt-file '{prompt_path}' "
                f"--out '{out_path}' --size {LATEST_CODEX_IMAGE_SIZE} --quality high --input-fidelity high "
                f"--no-augment --force {attachment_args}"
            )
        script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return script_path

    def _render_detail_source_visuals(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        detail_source_path: Path,
        visual_dir: Path,
        progress_callback=None,
    ) -> list[Path]:
        from PIL import Image, ImageDraw, ImageFilter, ImageOps

        width = 960
        height = 860
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        starts = [0.00, 0.11, 0.24, 0.38, 0.52, 0.67, 0.82]
        visual_paths: list[Path] = []
        with Image.open(detail_source_path) as source:
            source = ImageOps.exif_transpose(source).convert("RGB")
            source_width, source_height = source.size
            crop_width = source_width
            crop_height = max(1200, min(2300, source_height // 5))
            if source_height <= crop_height:
                crop_height = source_height
            for section_index, section in enumerate(sections, start=1):
                key = slugify(section.section_key, f"section_{section_index:02d}")
                visual_path = visual_dir / f"section_{section_index:02d}_{key}.png"
                start_ratio = starts[min(section_index - 1, len(starts) - 1)]
                top = int(max(0, min(source_height - crop_height, source_height * start_ratio)))
                crop = source.crop((0, top, crop_width, min(source_height, top + crop_height)))
                fitted = ImageOps.fit(crop, (width, height), method=resample, centering=(0.5, 0.35))
                canvas = Image.new("RGB", (width, height), (250, 250, 248))
                canvas.paste(fitted, (0, 0))
                overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                overlay_draw.rectangle((0, 0, width, 96), fill=(255, 255, 255, 72))
                overlay_draw.rectangle((0, height - 92, width, height), fill=(255, 255, 255, 68))
                overlay = overlay.filter(ImageFilter.GaussianBlur(0))
                canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
                canvas.save(visual_path, "PNG")
                visual_paths.append(visual_path)
                if progress_callback:
                    progress_callback(section_index, len(sections))
        return visual_paths

    def _render_generated_visual(self, product: ProductRecord, section: SectionPlan, section_index: int, product_image):
        from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

        width = 960
        height = 860
        palettes = [
            {"bg": (246, 241, 233), "accent": (176, 92, 47), "deep": (31, 29, 26), "soft": (255, 250, 242)},
            {"bg": (242, 247, 244), "accent": (50, 128, 92), "deep": (23, 59, 44), "soft": (231, 242, 235)},
            {"bg": (236, 244, 251), "accent": (39, 91, 144), "deep": (17, 43, 74), "soft": (222, 235, 246)},
            {"bg": (249, 246, 239), "accent": (111, 83, 60), "deep": (42, 35, 30), "soft": (238, 228, 213)},
            {"bg": (245, 246, 248), "accent": (73, 84, 104), "deep": (25, 32, 43), "soft": (229, 233, 239)},
            {"bg": (247, 242, 247), "accent": (135, 84, 118), "deep": (48, 35, 50), "soft": (240, 229, 238)},
            {"bg": (237, 242, 241), "accent": (37, 112, 121), "deep": (20, 59, 66), "soft": (224, 238, 238)},
        ]
        palette = palettes[(section_index - 1) % len(palettes)]
        source = product_image.convert("RGB")
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

        background = ImageOps.fit(source, (width, height), method=resample, centering=(0.5, 0.45))
        background = background.filter(ImageFilter.GaussianBlur(18))
        background = ImageEnhance.Color(background).enhance(0.52)
        canvas = Image.blend(background, Image.new("RGB", (width, height), palette["bg"]), 0.66)

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle((0, 0, width, height), fill=palette["bg"] + (72,))
        if section_index in (1, 7):
            overlay_draw.rectangle((0, 0, width, 270), fill=palette["deep"] + (214,))
            overlay_draw.rectangle((0, height - 210, width, height), fill=palette["soft"] + (226,))
        elif section_index in (3, 5):
            overlay_draw.rectangle((0, 0, width, 180), fill=palette["deep"] + (190,))
            overlay_draw.rectangle((0, height - 190, width, height), fill=(255, 255, 255, 178))
        else:
            overlay_draw.rectangle((0, height - 220, width, height), fill=(255, 255, 255, 190))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

        product_area = {
            1: (115, 210, 845, 790),
            2: (420, 185, 900, 700),
            3: (80, 230, 700, 760),
            4: (170, 170, 830, 690),
            5: (310, 260, 815, 740),
            6: (545, 110, 875, 430),
            7: (110, 180, 690, 710),
        }.get(section_index, (140, 160, 820, 720))
        max_size = (product_area[2] - product_area[0], product_area[3] - product_area[1])
        product = ImageOps.contain(source, max_size, method=resample)
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        x = product_area[0] + (product_area[2] - product_area[0] - product.width) // 2
        y = product_area[1] + (product_area[3] - product_area[1] - product.height) // 2
        shadow_draw.ellipse((x + 12, y + product.height - 18, x + product.width - 12, y + product.height + 42), fill=(15, 23, 42, 58))
        shadow = shadow.filter(ImageFilter.GaussianBlur(22))
        canvas.paste(shadow, (0, 0), shadow)
        if section_index in (2, 4, 6):
            panel = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            panel_draw = ImageDraw.Draw(panel)
            panel_draw.rounded_rectangle((x - 28, y - 28, x + product.width + 28, y + product.height + 28), radius=10, fill=(255, 255, 255, 218))
            canvas.paste(panel, (0, 0), panel)
        canvas.paste(product, (x, y))
        return canvas

    def _paste_product_mockup(self, canvas, product_image, box: tuple[int, int, int, int], section_index: int, palette: dict) -> None:
        from PIL import Image, ImageDraw, ImageFilter, ImageOps

        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        product = ImageOps.contain(product_image.convert("RGB"), (box[2] - box[0], box[3] - box[1]), method=resample)
        card_pad = 42 if section_index % 2 else 28
        card_box = (
            box[0] - card_pad,
            box[1] - card_pad,
            box[0] + product.width + card_pad,
            box[1] + product.height + card_pad,
        )
        card_box = (
            max(30, card_box[0]),
            max(30, card_box[1]),
            min(canvas.width - 30, card_box[2]),
            min(canvas.height - 80, card_box[3]),
        )
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            (card_box[0] + 18, card_box[1] + 28, card_box[2] + 18, card_box[3] + 28),
            radius=42,
            fill=(15, 23, 42, 42),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        canvas.paste(shadow, (0, 0), shadow)

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(card_box, radius=42, fill=(255, 255, 255, 245))
        overlay_draw.rounded_rectangle(card_box, radius=42, outline=self._mix_color(palette["accent"], (255, 255, 255), 0.72), width=3)
        canvas.paste(overlay, (0, 0), overlay)

        x = card_box[0] + (card_box[2] - card_box[0] - product.width) // 2
        y = card_box[1] + (card_box[3] - card_box[1] - product.height) // 2
        canvas.paste(product, (x, y))

    def _add_photo_depth(self, canvas, palette: dict, section_index: int) -> None:
        from PIL import ImageDraw

        draw = ImageDraw.Draw(canvas)
        accent = palette["accent"]
        if section_index in (1, 4, 7):
            for offset in range(0, 120, 24):
                draw.arc((80 + offset, 790 - offset // 3, 310 + offset, 1020 - offset // 3), 190, 270, fill=self._mix_color(accent, (255, 255, 255), 0.45), width=4)
        elif section_index in (2, 5):
            for x in (100, 180, 760, 840):
                draw.rounded_rectangle((x, 112, x + 16, 232), radius=8, fill=self._mix_color(accent, (255, 255, 255), 0.55))
        else:
            for y in (100, 165, 230):
                draw.line((680, y, 900, y), fill=self._mix_color(accent, (255, 255, 255), 0.62), width=6)

    def _mix_color(self, a: tuple[int, int, int], b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        amount = max(0.0, min(1.0, amount))
        return tuple(int(a[i] * (1 - amount) + b[i] * amount) for i in range(3))

    def _paste_product_card(
        self,
        canvas,
        product_image,
        box: tuple[int, int, int, int],
        padding: int = 24,
        radius: int = 30,
        fill=(255, 255, 255),
    ) -> None:
        from PIL import Image, ImageDraw, ImageOps

        self._draw_card(canvas, box, fill=fill, radius=radius)
        card_w = max(1, box[2] - box[0] - padding * 2)
        card_h = max(1, box[3] - box[1] - padding * 2)
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        fitted = ImageOps.contain(product_image, (card_w, card_h), method=resample).convert("RGBA")
        x = box[0] + padding + (card_w - fitted.width) // 2
        y = box[1] + padding + (card_h - fitted.height) // 2
        canvas.paste(fitted, (x, y), fitted)

    def _paste_detail_image(
        self,
        canvas,
        product_image,
        box: tuple[int, int, int, int],
        mode: str = "cover",
        radius: int = 0,
        bg=(255, 255, 255),
        padding: int = 0,
    ) -> None:
        from PIL import Image, ImageDraw, ImageOps

        x1, y1, x2, y2 = box
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        inner_w = max(1, width - padding * 2)
        inner_h = max(1, height - padding * 2)
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        base = Image.new("RGBA", (width, height), bg + ((255,) if len(bg) == 3 else ()))
        source = product_image.convert("RGB")
        if mode == "cover":
            fitted = ImageOps.fit(source, (inner_w, inner_h), method=resample, centering=(0.5, 0.5)).convert("RGBA")
        else:
            fitted = ImageOps.contain(source, (inner_w, inner_h), method=resample).convert("RGBA")
        base.alpha_composite(fitted, (padding + (inner_w - fitted.width) // 2, padding + (inner_h - fitted.height) // 2))
        if radius > 0:
            mask = Image.new("L", (width, height), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, width, height), radius=radius, fill=255)
            canvas.paste(base.convert("RGB"), (x1, y1), mask)
        else:
            canvas.paste(base.convert("RGB"), (x1, y1))

    def _draw_centered_detail_text(self, draw, y: int, text: str, font, fill, max_width: int, max_lines: int | None = None) -> int:
        for line in self._wrap_text(draw, text, font, max_width, max_lines=max_lines):
            x = (860 - self._text_width(draw, line, font)) // 2
            draw.text((x, y), line, font=font, fill=fill)
            box = draw.textbbox((x, y), line, font=font)
            y += max(1, box[3] - box[1]) + 10
        return y

    def _draw_detail_rule(self, draw, y: int, color=(218, 221, 225), margin: int = 64, width: int = 2) -> None:
        draw.line((margin, y, 860 - margin, y), fill=color, width=width)

    def _short_detail_text(self, text: str, fallback: str, limit: int = 90) -> str:
        cleaned = self._clean_detail_copy_text(text)
        if not cleaned or len(re.findall(r"[가-힣]", cleaned)) < 2:
            cleaned = fallback
        cleaned = self._clean_detail_copy_text(cleaned)
        if len(cleaned) <= limit:
            return cleaned
        snippet = cleaned[:limit].rstrip(" ,/·")
        sentence_end = max(snippet.rfind("다."), snippet.rfind("요."), snippet.rfind("."))
        if sentence_end >= max(18, limit // 2):
            return snippet[: sentence_end + 2].rstrip()
        comma = max(snippet.rfind(","), snippet.rfind("·"), snippet.rfind("/"))
        if comma >= max(18, limit // 2):
            return snippet[:comma].rstrip(" ,/·")
        space = snippet.rfind(" ")
        if space >= max(18, limit // 2):
            return snippet[:space].rstrip(" ,/·")
        return snippet.rstrip(" ,/·")

    def _trim_source_detail_copy(self, text: str, limit: int = 120) -> str:
        cleaned = self._clean_detail_copy_text(text)
        if not cleaned:
            return ""
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) <= limit:
            return cleaned
        snippet = cleaned[:limit].rstrip(" ,/·")
        sentence_end = max(snippet.rfind("다."), snippet.rfind("요."), snippet.rfind("."), snippet.rfind("!"), snippet.rfind("?"))
        if sentence_end >= max(18, limit // 2):
            end_offset = 2 if snippet[sentence_end : sentence_end + 2] in {"다.", "요."} else 1
            return snippet[: sentence_end + end_offset].rstrip()
        space = snippet.rfind(" ")
        if space >= max(18, limit // 2):
            return snippet[:space].rstrip(" ,/·")
        return snippet.rstrip(" ,/·")

    def _extract_overlay_text_from_image_prompt(self, prompt: str) -> str:
        text = (prompt or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return ""
        marker = re.search(
            r"이미지\s*안에\s*아래\s*문구.*?(?:넣어라|넣으세요|표기|인쇄|출력)?\s*[:：]\s*(.+)",
            text,
            flags=re.DOTALL,
        )
        if not marker:
            return ""
        tail = marker.group(1).strip()
        quoted = re.search(r"[\"“'](?P<copy>.*?)[\"”']", tail, flags=re.DOTALL)
        if quoted:
            tail = quoted.group("copy").strip()
        else:
            tail = re.split(
                r"(?m)^\s*(글꼴|굵은\s*한글|오타|깨짐|외국어|제품은|고해상도|무작위|중앙정렬|빈\s*체크|허구|중국어)\b",
                tail,
                maxsplit=1,
            )[0].strip()
        lines: list[str] = []
        for raw_line in tail.splitlines():
            line = self._clean_detail_copy_text(raw_line.strip(" \t-•*\"'“”"))
            if not line:
                continue
            if any(marker in line for marker in ("이미지 안에", "글꼴", "오타", "깨짐", "금지", "고해상도")):
                continue
            lines.append(line)
            if len(lines) >= 5:
                break
        return "\n".join(self._dedupe_text_items(lines)).strip()

    def _section_overlay_text(self, section: SectionPlan) -> str:
        overlay_text = section.overlay_text.strip() or self._extract_overlay_text_from_image_prompt(section.image_prompt)
        if overlay_text:
            return overlay_text
        parts = [
            self._clean_detail_copy_text(section.headline),
            self._clean_detail_copy_text(section.subheadline),
            self._trim_source_detail_copy(section.body, 120),
        ]
        for bullet in section.bullets[:2]:
            if len([part for part in parts if part]) >= 4:
                break
            parts.append(self._trim_source_detail_copy(bullet, 80))
        return "\n".join(self._dedupe_text_items([part for part in parts if part])).strip()

    def _section_overlay_lines(self, section: SectionPlan, max_lines: int = 5) -> list[str]:
        lines: list[str] = []
        for raw_line in self._section_overlay_text(section).splitlines():
            line = self._clean_detail_copy_text(raw_line)
            if not line or self._is_noisy_copy_label(line):
                continue
            lines.append(self._trim_source_detail_copy(line, 118))
        if not lines:
            fallback_parts = [
                self._clean_detail_copy_text(section.headline),
                self._clean_detail_copy_text(section.subheadline),
                self._trim_source_detail_copy(section.body, 118),
            ]
            lines.extend(part for part in fallback_parts if part)
        return self._dedupe_text_items([line for line in lines if line])[:max_lines]

    def _section_copy_source_blob(self, section: SectionPlan) -> str:
        return "\n".join(
            [
                section.headline,
                section.subheadline,
                section.body,
                "\n".join(section.bullets),
                section.image_prompt,
                section.overlay_text,
                section.source_section_text,
                self._extract_overlay_text_from_image_prompt(section.image_prompt),
            ]
        )

    def _copy_line_from_gpt_source(self, section: SectionPlan, line: str) -> bool:
        normalized_line = self._normalize_text_key(line)
        if not normalized_line:
            return True
        source_blob = self._section_copy_source_blob(section)
        normalized_source_blob = self._normalize_text_key(source_blob)
        cleaned_source_blob = self._normalize_text_key(self._clean_detail_copy_text(source_blob))
        if normalized_line in normalized_source_blob or normalized_line in cleaned_source_blob:
            return True
        for prefix_length in (90, 80, 70, 60, 50, 40):
            if len(normalized_line) < prefix_length:
                continue
            prefix = normalized_line[:prefix_length]
            if prefix in normalized_source_blob or prefix in cleaned_source_blob:
                return True
        return False

    def _copy_panel_box(self, section_index: int, height: int, width: int = 860) -> tuple[int, int, int, int, bool]:
        panel_h = 282 if section_index not in {4, 6} else 316
        layouts = {
            1: (44, 58, 688, 58 + panel_h, True),
            2: (44, max(54, height - panel_h - 58), 816, max(54, height - 58), False),
            3: (54, 64, 816, 64 + panel_h, True),
            4: (44, max(54, height - panel_h - 64), 816, max(54, height - 64), False),
            5: (44, 64, 760, 64 + panel_h, False),
            6: (56, max(54, height - panel_h - 72), 804, max(54, height - 72), False),
            7: (44, max(54, height - panel_h - 58), 816, max(54, height - 58), True),
        }
        return layouts.get(section_index, (44, 64, width - 44, 64 + panel_h, False))

    def _draw_strict_copy_panel(self, canvas, section: SectionPlan, section_index: int) -> list[str]:
        from PIL import Image, ImageDraw, ImageFilter

        lines = self._section_overlay_lines(section, max_lines=5)
        if not lines:
            return []
        width, height = canvas.size
        panel = self._copy_panel_box(section_index, height, width)
        x1, y1, x2, y2, dark_panel = panel
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle((x1 + 8, y1 + 16, x2 + 8, y2 + 16), radius=22, fill=(0, 0, 0, 64))
        shadow = shadow.filter(ImageFilter.GaussianBlur(16))
        overlay.alpha_composite(shadow)
        draw_overlay = ImageDraw.Draw(overlay)
        if dark_panel:
            fill = (12, 18, 32, 222)
            outline = (255, 255, 255, 72)
            ink = (255, 255, 255)
            sub_ink = (218, 228, 240)
        else:
            fill = (255, 255, 255, 236)
            outline = (222, 230, 238, 170)
            ink = (22, 28, 38)
            sub_ink = (62, 72, 88)
        draw_overlay.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=fill, outline=outline, width=1)
        canvas.alpha_composite(overlay)

        draw = ImageDraw.Draw(canvas)
        title_font = self._font(43 if section_index != 7 else 40, True)
        sub_font = self._font(25, True)
        body_font = self._font(21)
        text_x = x1 + 34
        text_y = y1 + 30
        max_width = x2 - text_x - 34
        text_y = self._draw_wrapped_text(draw, (text_x, text_y), lines[0], title_font, ink, max_width, line_spacing=9, max_lines=2)
        if len(lines) >= 2:
            text_y = self._draw_wrapped_text(draw, (text_x, text_y + 12), lines[1], sub_font, sub_ink, max_width, line_spacing=7, max_lines=2)
        if len(lines) >= 3 and text_y < y2 - 66:
            self._draw_wrapped_text(
                draw,
                (text_x, text_y + 12),
                "\n".join(lines[2:]),
                body_font,
                sub_ink,
                max_width,
                line_spacing=6,
                max_lines=3,
            )
        return lines

    def _section_bullets(self, product: ProductRecord, section: SectionPlan, desired: int = 3) -> list[str]:
        blocked = {
            self._normalize_text_key(section.headline),
            self._normalize_text_key(section.subheadline),
            self._normalize_text_key(section.body),
        }
        items = [
            item
            for item in self._dedupe_text_items(section.bullets)
            if self._normalize_text_key(item) not in blocked
        ][:desired]
        fallback = [
            product.category or "상품 페이지에서 확인한 카테고리 기준으로 구성",
            product.price_text or "가격과 옵션은 구매 전 최종 확인 필요",
            product.options_text or "옵션 정보는 상품 페이지 기준으로 확인",
        ]
        fallback.extend(product.facts)
        for item in self._dedupe_text_items(fallback):
            if self._normalize_text_key(item) not in blocked and item not in items:
                items.append(item)
            if len(items) >= desired:
                break
        return items[:desired]

    def _draw_bullet_list(
        self,
        draw,
        bullets: list[str],
        x: int,
        y: int,
        max_width: int,
        font,
        fill=(31, 41, 55),
        accent=(37, 99, 235),
        gap: int = 18,
    ) -> int:
        for item in bullets:
            draw.ellipse((x, y + 8, x + 10, y + 18), fill=accent)
            y = self._draw_wrapped_text(draw, (x + 24, y), item, font, fill, max_width - 24, line_spacing=6, max_lines=2)
            y += gap
        return y

    def _render_detail_page(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        section_visual_paths: list[Path] | None = None,
        generated_image_model: str = LATEST_CODEX_IMAGE_MODEL,
    ) -> RenderResult:
        if len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
            raise RuntimeError(f"섹션 수가 {REQUIRED_SECTION_IMAGE_COUNT}개보다 적습니다.")
        source_paths = self._source_image_paths(product)
        visual_paths = [path for path in (section_visual_paths or []) if path.exists() and path.stat().st_size > 0]
        if visual_paths and len(visual_paths) < len(sections):
            raise RuntimeError(f"생성 이미지 수가 섹션 수보다 적습니다: {len(visual_paths)}/{len(sections)}")
        if not source_paths and not visual_paths:
            raise RuntimeError("섹션에 넣을 이미지가 없습니다.")

        sections_dir = product.output_dir / "sections"
        sections_dir.mkdir(parents=True, exist_ok=True)
        for old_section in sections_dir.glob("section_*.png"):
            old_section.unlink(missing_ok=True)

        section_paths: list[Path] = []
        if visual_paths:
            for section_index, (section, image_path) in enumerate(zip(sections, visual_paths), start=1):
                key = slugify(section.section_key, f"section_{section_index:02d}")
                path = sections_dir / f"section_{section_index:02d}_{key}.png"
                self._compose_generated_visual_section(product, section, section_index, image_path, path, width=860)
                section_paths.append(path)
            detail_path = product.output_dir / "detail_page.png"
            self._merge_section_images(section_paths, detail_path, width=860)
            return RenderResult(
                section_paths=section_paths,
                detail_page_path=detail_path,
                visual_paths=visual_paths,
                render_mode=CODEX_IMAGE_RENDER_MODE,
                image_model=generated_image_model,
            )

        return self._render_product_source_detail_page(product, sections, sections_dir)

    def _render_product_source_detail_page(
        self,
        product: ProductRecord,
        sections: list[SectionPlan],
        sections_dir: Path,
    ) -> RenderResult:
        source_assets = self._load_production_source_assets(product)
        if not source_assets:
            raise RuntimeError("상세페이지 렌더에 사용할 상품 이미지가 없습니다.")

        section_paths: list[Path] = []
        for section_index, section in enumerate(sections, start=1):
            key = slugify(section.section_key, f"section_{section_index:02d}")
            section_path = sections_dir / f"section_{section_index:02d}_{key}.png"
            canvas = self._render_production_detail_section(product, section, section_index, source_assets)
            canvas.save(section_path, "PNG")
            if not self._is_valid_image_file(section_path):
                raise RuntimeError(f"섹션 렌더 파일 검증 실패: {section_path}")
            section_paths.append(section_path)

        detail_path = product.output_dir / "detail_page.png"
        self._merge_section_images(section_paths, detail_path, width=860)
        return RenderResult(
            section_paths=section_paths,
            detail_page_path=detail_path,
            visual_paths=[],
            render_mode=PRODUCTION_RENDER_MODE,
            image_model=PRODUCTION_RENDERER_MODEL,
        )

    def _load_production_source_assets(self, product: ProductRecord) -> dict[str, list]:
        from PIL import Image, ImageOps

        assets: dict[str, list] = {"primary": [], "detail": [], "capture": [], "all": []}
        for path in self._source_image_paths(product):
            try:
                with Image.open(path) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    width, height = image.size
                    if width < 240 or height < 240:
                        continue
                    copied = image.copy()
            except Exception:
                continue
            name = path.name.lower()
            assets["all"].append(copied)
            if "capture" in name:
                assets["capture"].append(copied)
                if height >= 12000:
                    assets["detail"].append(copied)
            elif "detail" in name or height / max(1, width) >= 1.9:
                assets["detail"].append(copied)
            else:
                assets["primary"].append(copied)
        if not assets["primary"] and assets["all"]:
            assets["primary"].append(assets["all"][0].copy())
        return assets

    def _production_source_image(self, assets: dict[str, list], section_index: int):
        primary = assets.get("primary") or assets.get("all") or []
        detail = assets.get("detail") or []
        if detail and section_index in {3, 4, 5, 6}:
            return detail[(section_index - 1) % len(detail)]
        if primary:
            return primary[(section_index - 1) % len(primary)]
        if detail:
            return detail[(section_index - 1) % len(detail)]
        return (assets.get("all") or [])[0]

    def _production_image_at(self, assets: dict[str, list], index: int, prefer_detail: bool = False):
        detail = assets.get("detail") or []
        primary = assets.get("primary") or []
        all_images = assets.get("all") or []
        pool = detail if prefer_detail and detail else primary or detail or all_images
        if not pool:
            return None
        return pool[index % len(pool)]

    def _fit_production_image(self, image, size: tuple[int, int], section_index: int, mode: str = "cover"):
        from PIL import Image, ImageOps

        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        source = image.convert("RGB")
        width, height = source.size
        if height / max(1, width) > 1.9:
            crop_h = max(width, min(height, int(height * 0.24)))
            starts = [0.02, 0.13, 0.28, 0.43, 0.58, 0.73, 0.84]
            top = int(max(0, min(height - crop_h, (height - crop_h) * starts[min(section_index - 1, 6)])))
            source = source.crop((0, top, width, top + crop_h))
        if mode == "contain":
            fitted = ImageOps.contain(source, size, method=resample)
            canvas = Image.new("RGB", size, (255, 255, 255))
            canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
            return canvas
        return ImageOps.fit(source, size, method=resample, centering=(0.5, 0.42))

    def _paste_production_photo(
        self,
        canvas,
        image,
        box: tuple[int, int, int, int],
        section_index: int,
        mode: str = "cover",
        radius: int = 26,
        padding: int = 0,
        shadow: bool = True,
        outline=(226, 232, 240),
    ) -> None:
        from PIL import Image, ImageDraw

        x1, y1, x2, y2 = box
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        if shadow:
            self._draw_shadow(canvas, box, radius=radius, alpha=38, blur=20, offset=(0, 14))
        panel = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        inner_w = max(1, width - padding * 2)
        inner_h = max(1, height - padding * 2)
        fitted = self._fit_production_image(image, (inner_w, inner_h), section_index, mode=mode).convert("RGBA")
        panel.alpha_composite(fitted, (padding, padding))
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, width, height), radius=radius, fill=255)
        canvas.paste(panel.convert("RGB"), (x1, y1), mask)
        if outline:
            draw = ImageDraw.Draw(canvas)
            draw.rounded_rectangle(box, radius=radius, outline=outline, width=1)

    def _draw_production_kicker(self, draw, section_index: int, section_name: str, x: int, y: int, accent, light: bool = False) -> None:
        font = self._font(17, True)
        fill = (255, 255, 255) if light else accent
        draw.rounded_rectangle((x, y, x + 118, y + 34), radius=17, fill=accent if light else self._mix_color(accent, (255, 255, 255), 0.78))
        draw.text((x + 16, y + 7), f"{section_index:02d}. {section_name}", font=font, fill=fill)

    def _render_production_detail_section(
        self,
        product: ProductRecord,
        section: SectionPlan,
        section_index: int,
        assets: dict[str, list],
    ):
        from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

        width = 860
        strict_heights = {
            "hero": 1240,
            "empathy": 1160,
            "solution": 1160,
            "benefits": 1220,
            "how_to_use": 1120,
            "trust": 1120,
            "cta": 1040,
        }
        strict_height = strict_heights.get(section.section_key, 1140)
        strict_source = self._production_source_image(assets, section_index)
        if strict_source is None:
            raise RuntimeError("상세페이지 렌더에 사용할 상품 이미지가 없습니다.")
        strict_canvas = self._fit_production_image(strict_source, (width, strict_height), section_index, "cover").convert("RGBA")
        self._draw_strict_copy_panel(strict_canvas, section, section_index)
        return strict_canvas.convert("RGB")

    def _normalize_generated_section_image(self, source_path: Path, target_path: Path, width: int = 860) -> None:
        from PIL import Image, ImageOps

        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            if image.width != width:
                height = max(1, int(image.height * (width / image.width)))
                image = image.resize((width, height), Image.Resampling.LANCZOS)
            image.save(target_path, "PNG")

    def _compose_generated_visual_section(
        self,
        product: ProductRecord,
        section: SectionPlan,
        section_index: int,
        source_path: Path,
        target_path: Path,
        width: int = 860,
    ) -> None:
        from PIL import Image, ImageOps

        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            if image.width != width:
                height = max(1, int(image.height * (width / image.width)))
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                image = image.resize((width, height), resample)
            if image.height < 1100:
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                image = ImageOps.fit(image, (width, 1240), method=resample, centering=(0.5, 0.48))
            elif image.height > 1660:
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                image = ImageOps.fit(image, (width, 1560), method=resample, centering=(0.5, 0.48))

        target_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(target_path, "PNG")

    def _merge_section_images(self, section_paths: list[Path], output_path: Path, width: int = 860) -> None:
        from PIL import Image

        opened = []
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        try:
            total_height = 0
            for path in section_paths:
                image = Image.open(path).convert("RGB")
                if image.width != width:
                    height = int(image.height * (width / image.width))
                    image = image.resize((width, height), resample)
                opened.append(image)
                total_height += image.height
            if len(opened) < REQUIRED_SECTION_IMAGE_COUNT:
                raise RuntimeError("합본에 필요한 섹션 이미지 수가 부족합니다.")
            merged = Image.new("RGB", (width, total_height), (255, 255, 255))
            y = 0
            for image in opened:
                merged.paste(image, (0, y))
                y += image.height
            merged.save(output_path, "PNG")
        finally:
            for image in opened:
                try:
                    image.close()
                except Exception:
                    pass

    def _render_result_complete(self, render_result: RenderResult) -> bool:
        if render_result.render_mode not in {CODEX_IMAGE_RENDER_MODE, PRODUCTION_RENDER_MODE}:
            return False
        if REQUIRE_GENERATED_SECTION_IMAGES and render_result.render_mode != CODEX_IMAGE_RENDER_MODE:
            return False
        if render_result.render_mode == CODEX_IMAGE_RENDER_MODE and render_result.image_model not in {LATEST_CODEX_IMAGE_MODEL, CHATGPT_WEB_IMAGE_MODEL}:
            return False
        if render_result.render_mode == PRODUCTION_RENDER_MODE and render_result.image_model != PRODUCTION_RENDERER_MODEL:
            return False
        if render_result.render_mode == CODEX_IMAGE_RENDER_MODE and len(render_result.visual_paths) < REQUIRED_SECTION_IMAGE_COUNT:
            return False
        if render_result.render_mode == CODEX_IMAGE_RENDER_MODE and render_result.visual_paths and len(render_result.visual_paths) != len(render_result.section_paths):
            return False
        if render_result.visual_paths and not all(self._is_valid_generated_visual_file(path) for path in render_result.visual_paths):
            return False
        if len(render_result.section_paths) < REQUIRED_SECTION_IMAGE_COUNT:
            return False
        if not self._is_valid_image_file(render_result.detail_page_path):
            return False
        return all(self._is_valid_image_file(path) for path in render_result.section_paths)

    def _write_copy_manifest(self, product: ProductRecord, sections: list[SectionPlan], render_result: RenderResult) -> tuple[Path, bool]:
        manifest_path = product.output_dir / "copy_manifest.json"
        section_entries: list[dict[str, object]] = []
        forbidden: list[dict[str, str]] = []
        for section_index, section in enumerate(sections, start=1):
            rendered_lines = self._section_overlay_lines(section, max_lines=5)
            source_checks = [
                {
                    "line": line,
                    "from_gpt_source": self._copy_line_from_gpt_source(section, line),
                }
                for line in rendered_lines
            ]
            for check in source_checks:
                if not check["from_gpt_source"]:
                    forbidden.append({"section_key": section.section_key, "line": str(check["line"])})
            section_path = render_result.section_paths[section_index - 1] if section_index <= len(render_result.section_paths) else Path()
            section_entries.append(
                {
                    "section_index": section_index,
                    "section_key": section.section_key,
                    "section_name": section.section_name,
                    "section_path": str(section_path) if section_path else "",
                    "overlay_text": self._section_overlay_text(section),
                    "rendered_lines": rendered_lines,
                    "source_checks": source_checks,
                    "source_fields": ["headline", "subheadline", "body", "bullets", "image_prompt", "overlay_text", "source_section_text"],
                }
            )
        valid = (
            len(section_entries) >= REQUIRED_SECTION_IMAGE_COUNT
            and not forbidden
            and self._render_result_complete(render_result)
            and all(entry.get("rendered_lines") for entry in section_entries)
        )
        payload = {
            "version": DETAIL_PIPELINE_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "valid": valid,
            "product_code": product.code,
            "product_name": product.product_name,
            "detail_page_path": str(render_result.detail_page_path),
            "render_mode": render_result.render_mode,
            "image_model": render_result.image_model,
            "forbidden_local_copy_detected": forbidden,
            "sections": section_entries,
        }
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest_path, valid

    def _copy_manifest_is_valid(self, manifest_path: Path) -> bool:
        if not manifest_path.exists() or manifest_path.stat().st_size <= 0:
            return False
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        if payload.get("version") != DETAIL_PIPELINE_VERSION:
            return False
        if payload.get("valid") is not True:
            return False
        sections = payload.get("sections")
        if not isinstance(sections, list) or len(sections) < REQUIRED_SECTION_IMAGE_COUNT:
            return False
        for section in sections:
            if not isinstance(section, dict):
                return False
            rendered_lines = section.get("rendered_lines")
            if not isinstance(rendered_lines, list) or not rendered_lines:
                return False
            checks = section.get("source_checks")
            if not isinstance(checks, list) or not all(isinstance(check, dict) and check.get("from_gpt_source") is True for check in checks):
                return False
        return True

    def _source_image_counts_by_origin(self, product: ProductRecord) -> dict[str, int]:
        counts: dict[str, int] = {}
        for path in self._source_image_paths(product):
            origin = "1688" if "1688" in [part.lower() for part in path.parts] else "ownerclan"
            counts[origin] = counts.get(origin, 0) + 1
        return counts

    def _save_failed_result(
        self,
        product: ProductRecord,
        prompt: str,
        message: str,
        run_stamp: str,
        result_text: str = "",
    ) -> Path:
        product.output_dir.mkdir(parents=True, exist_ok=True)
        path = product.output_dir / "result.md"
        content = (
            f"# 상세페이지 자동화 실패\n\n"
            f"- 상태: {message}\n"
            f"- 상품명: {product.product_name}\n"
            f"- URL: {product.url}\n"
            f"- 1688 URL: {product.secondary_url or '-'}\n"
            f"- 저장 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "## 입력 프롬프트\n\n"
            "```text\n"
            f"{prompt.strip()}\n"
            "```\n"
        )
        if result_text.strip():
            content += (
                "\n## GPT 원문 결과\n\n"
                "```text\n"
                f"{result_text.strip()}\n"
                "```\n"
            )
        path.write_text(content, encoding="utf-8")
        metadata = {
            "status": message,
            "url": product.url,
            "secondary_url": product.secondary_url,
            "product_name": product.product_name,
            "code": product.code,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "run_stamp": run_stamp,
            "pipeline_version": DETAIL_PIPELINE_VERSION,
            "latest_image_model_target": LATEST_CODEX_IMAGE_MODEL,
            "require_generated_section_images": REQUIRE_GENERATED_SECTION_IMAGES,
            "source_image_count": len(product.source_image_paths),
            "source_image_counts_by_origin": self._source_image_counts_by_origin(product),
            "source_payloads": self._image_only_source_payloads(product.source_payloads),
            "gpt_response": result_text,
            "generated_visual_paths": [str(path) for path in sorted((product.output_dir / "generated_visuals").glob("section_*.png"))],
            "section_paths": [],
            "detail_page_path": "",
            "thumbnail_paths": [str(path) for path in sorted((product.output_dir / "thumbnails").glob("*.png"))],
            "thumbnail_model": "",
            "thumbnail_prompt_paths": [str(path) for path in sorted((product.output_dir / "thumbnail_prompts").glob("thumbnail_*_request.txt"))],
            "thumbnail_count": len([path for path in (product.output_dir / "thumbnails").glob("*.png") if self._is_valid_image_file(path)]),
            "source_image_paths": [str(path) for path in product.source_image_paths],
            "gpt_attachment_paths": [str(path) for path in sorted((product.output_dir / "gpt_attachments").glob("*.jpg"))],
        }
        (product.output_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _save_url_failure_result(self, index: int, url: str, message: str) -> Path:
        product_dir = self._url_output_folder(index, url)
        product_dir.mkdir(parents=True, exist_ok=True)
        path = product_dir / "result.md"
        content = (
            "# 상세페이지 자동화 실패\n\n"
            f"- 상태: {message}\n"
            f"- URL: {url}\n"
            f"- 저장 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        path.write_text(content, encoding="utf-8")
        metadata = {
            "status": message,
            "url": url,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "section_paths": [],
            "detail_page_path": "",
            "thumbnail_paths": [],
            "thumbnail_count": 0,
        }
        (product_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _completed_product_dir(self, product: ProductRecord) -> Path:
        return COMPLETED_DIR / product.output_dir.name

    def _completed_detail_page_path(self, product: ProductRecord) -> Path:
        return self._completed_product_dir(product) / "detail_page.png"

    def _copy_completed_section_images(self, product: ProductRecord, render_result: RenderResult, completed_product_dir: Path) -> list[Path]:
        source_sections_dir = product.output_dir / "sections"
        target_sections_dir = completed_product_dir / "sections"
        target_sections_dir.mkdir(parents=True, exist_ok=True)
        for old_section in target_sections_dir.glob("section_*.png"):
            old_section.unlink(missing_ok=True)
        copied_paths: list[Path] = []
        for section_path in render_result.section_paths:
            source_path = section_path if section_path.exists() else source_sections_dir / section_path.name
            if not self._is_valid_image_file(source_path):
                continue
            target_path = target_sections_dir / source_path.name
            shutil.copy2(source_path, target_path)
            copied_paths.append(target_path)
        if len(copied_paths) < REQUIRED_SECTION_IMAGE_COUNT:
            raise RuntimeError("완료된폴더 섹션 PNG 복사 검증에 실패했습니다.")
        return copied_paths

    def _publish_completed_detail_page(self, product: ProductRecord, render_result: RenderResult, result_path: Path) -> Path:
        if not self._render_result_complete(render_result):
            raise RuntimeError("완료된폴더에 저장할 수 있는 완성 결과가 아닙니다.")
        if len(self._valid_section_files(product.output_dir / "sections")) < len(render_result.section_paths):
            raise RuntimeError("완료된폴더 저장 전 섹션 PNG 검증에 실패했습니다.")
        thumbnail_paths = self._valid_thumbnail_files(product.output_dir / "thumbnails")
        if len(thumbnail_paths) != REQUIRED_THUMBNAIL_IMAGE_COUNT:
            raise RuntimeError("완료된폴더 저장 전 썸네일 PNG 5장 검증에 실패했습니다.")
        if not self._is_valid_image_file(render_result.detail_page_path):
            raise RuntimeError("완료된폴더 저장 전 detail_page.png 검증에 실패했습니다.")
        copy_manifest_path = product.output_dir / "copy_manifest.json"
        if not self._copy_manifest_is_valid(copy_manifest_path):
            raise RuntimeError("완료된폴더 저장 전 copy_manifest.json 검증에 실패했습니다.")

        completed_product_dir = self._completed_product_dir(product)
        completed_product_dir.mkdir(parents=True, exist_ok=True)
        target_detail = completed_product_dir / "detail_page.png"
        shutil.copy2(render_result.detail_page_path, target_detail)
        completed_section_paths = self._copy_completed_section_images(product, render_result, completed_product_dir)
        for index, thumbnail_path in enumerate(thumbnail_paths, start=1):
            shutil.copy2(thumbnail_path, completed_product_dir / f"{index}.png")
        for sidecar_name in ("metadata.json", "result.md", "source.json", "copy_manifest.json"):
            source_path = product.output_dir / sidecar_name
            if source_path.exists() and source_path.is_file():
                shutil.copy2(source_path, completed_product_dir / sidecar_name)
        if result_path.exists() and result_path.is_file():
            shutil.copy2(result_path, completed_product_dir / "result.md")
        completed_metadata = completed_product_dir / "metadata.json"
        if not self._is_valid_image_file(target_detail):
            raise RuntimeError("완료된폴더 detail_page.png 복사 검증에 실패했습니다.")
        for index in range(1, REQUIRED_THUMBNAIL_IMAGE_COUNT + 1):
            if not self._is_valid_image_file(completed_product_dir / f"{index}.png"):
                raise RuntimeError(f"완료된폴더 썸네일 {index}.png 복사 검증에 실패했습니다.")
        if not completed_metadata.exists() or completed_metadata.stat().st_size <= 0:
            raise RuntimeError("완료된폴더 metadata.json 복사 검증에 실패했습니다.")
        metadata = self._read_json_file(completed_metadata)
        metadata["section_paths"] = [str(path) for path in completed_section_paths]
        metadata["completed_sections_dir"] = str(completed_product_dir / "sections")
        metadata["completed_detail_page_path"] = str(target_detail)
        self._write_json_file(completed_metadata, metadata)
        if not self._copy_manifest_is_valid(completed_product_dir / "copy_manifest.json"):
            raise RuntimeError("완료된폴더 copy_manifest.json 복사 검증에 실패했습니다.")
        return target_detail

    def _save_detail_page_result(
        self,
        product: ProductRecord,
        prompt: str,
        result_text: str,
        sections: list[SectionPlan],
        render_result: RenderResult,
        run_stamp: str,
        thumbnail_result: ThumbnailResult,
    ) -> Path:
        render_complete = self._render_result_complete(render_result)
        thumbnail_complete = self._thumbnail_result_complete(thumbnail_result)
        section_plan_clean = self._section_plan_set_is_clean(sections, result_text)
        copy_manifest_path, copy_manifest_valid = self._write_copy_manifest(product, sections, render_result)
        review_section_present = self._sections_include_review_points(sections)
        complete = (
            render_complete
            and thumbnail_complete
            and section_plan_clean
            and copy_manifest_valid
        )
        if not section_plan_clean:
            incomplete_status = "GPT 기획 오염"
        elif not copy_manifest_valid:
            incomplete_status = "카피 검증 실패"
        elif render_complete and not thumbnail_complete:
            incomplete_status = "썸네일 대기"
        else:
            incomplete_status = "렌더 실패"
        section_lines = []
        for section, image_path in zip(sections, render_result.section_paths):
            display_name = self._display_section_name(section.section_key, section.section_name)
            section_lines.append(
                f"## {display_name} ({section.section_key})\n\n"
                f"- 헤드라인: {section.headline}\n"
                f"- 서브카피: {section.subheadline}\n"
                f"- 렌더 오버레이 원문: {section.overlay_text or self._extract_overlay_text_from_image_prompt(section.image_prompt)}\n"
                f"- 이미지 생성 프롬프트: {section.image_prompt}\n"
                f"- 이미지: {image_path}\n\n"
                f"{section.body}\n\n"
                + "\n".join(f"- {item}" for item in section.bullets)
            )
        sections_markdown = "\n\n".join(section_lines)
        path = product.output_dir / "result.md"
        content = (
            f"# {product.product_name} 상세페이지 자동화 결과\n\n"
            f"- 상태: {'완료' if complete else incomplete_status}\n"
            f"- URL: {product.url}\n"
            f"- 1688 URL: {product.secondary_url or '-'}\n"
            f"- 상품코드: {product.code}\n"
            f"- URL별 폴더: {product.output_dir}\n"
            f"- 전체 상세페이지: {render_result.detail_page_path}\n"
            f"- 파이프라인 버전: {DETAIL_PIPELINE_VERSION}\n"
            f"- 리뷰 섹션 버전: {DETAIL_REVIEW_SECTION_STYLE_VERSION}\n"
            f"- 리뷰 섹션 포함: {'예' if review_section_present else '아니오'}\n"
            f"- 저장 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "## 저장된 파일\n\n"
            f"- 원본 이미지 폴더: {product.output_dir / 'source_images'}\n"
            f"- 오너클랜 이미지 폴더: {product.output_dir / 'source_images' / 'ownerclan'}\n"
            f"- 1688 이미지 폴더: {product.output_dir / 'source_images' / '1688'}\n"
            f"- ChatGPT 첨부 이미지 폴더: {product.output_dir / 'gpt_attachments'}\n"
                f"- 최신 이미지 생성 프롬프트 폴더: {product.output_dir / 'codex_image_prompts'}\n"
                f"- 카피 검증 파일: {copy_manifest_path}\n"
                f"- 이미지 생성 대상 모델: {LATEST_CODEX_IMAGE_MODEL}\n"
                f"- 실제 섹션 이미지 모델/경로: {render_result.image_model}\n"
            f"- 섹션 이미지 폴더: {product.output_dir / 'sections'}\n"
            f"- 썸네일 이미지 폴더: {product.output_dir / 'thumbnails'}\n"
            f"- 전체 합본: {render_result.detail_page_path}\n\n"
            "## 섹션 기획\n\n"
            f"{sections_markdown}\n\n"
            "## 썸네일\n\n"
            + "\n".join(f"- {path.name}: {path}" for path in thumbnail_result.paths)
            + "\n\n"
            "## GPT 요청 프롬프트\n\n"
            "```text\n"
            f"{prompt.strip()}\n"
            "```\n\n"
            "## GPT 원문 결과\n\n"
            "```text\n"
            f"{result_text.strip()}\n"
            "```\n"
        )
        completed_detail_path = self._completed_detail_page_path(product)
        if complete:
            content = content.replace(
                f"- 전체 합본: {render_result.detail_page_path}\n\n",
                f"- 전체 합본: {render_result.detail_page_path}\n"
                f"- 완료된폴더 상세페이지: {completed_detail_path}\n\n",
            )
        path.write_text(content, encoding="utf-8")
        gpt_attachment_paths = sorted((product.output_dir / "gpt_attachments").glob("*.jpg"))
        brand_logo_dir = product.output_dir / BRAND_LOGO_REFERENCE_DIR_NAME
        brand_logo_manifest_path = brand_logo_dir / "brand_logo_manifest.json"
        brand_logo_check_prompt_path = brand_logo_dir / "brand_logo_check_prompt.txt"
        brand_logo_manifest = self._read_json_file(brand_logo_manifest_path)
        brand_logo_records = brand_logo_manifest.get("records") if isinstance(brand_logo_manifest, dict) else []
        brand_logo_applied_count = (
            sum(1 for record in brand_logo_records if isinstance(record, dict) and record.get("logo_applied"))
            if isinstance(brand_logo_records, list)
            else 0
        )
        metadata = {
            "status": "완료" if complete else incomplete_status,
            "url": product.url,
            "secondary_url": product.secondary_url,
            "gpt_url": GPT_URL,
            "gpt_name": GPT_NAME,
            "product_name": product.product_name,
            "code": product.code,
            "category": product.category,
            "price_text": product.price_text,
            "options_text": product.options_text,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "run_stamp": run_stamp,
            "pipeline_version": DETAIL_PIPELINE_VERSION,
            "review_section_required": False,
            "review_section_style_version": DETAIL_REVIEW_SECTION_STYLE_VERSION,
            "review_section_present": review_section_present,
            "render_mode": render_result.render_mode,
            "image_model": render_result.image_model,
            "require_generated_section_images": REQUIRE_GENERATED_SECTION_IMAGES,
            "latest_image_model_target": LATEST_CODEX_IMAGE_MODEL,
            "chatgpt_image_model_alias": CHATGPT_IMAGE_MODEL_ALIAS,
            "latest_image_size_target": LATEST_CODEX_IMAGE_SIZE,
            "codex_image_prompt_dir": str(product.output_dir / "codex_image_prompts"),
            "imagegen_jobs_path": str(product.output_dir / "codex_image_prompts" / f"imagegen_{LATEST_CODEX_IMAGE_MODEL}_jobs.jsonl"),
            "source_image_paths": [str(path) for path in product.source_image_paths],
            "source_image_counts_by_origin": self._source_image_counts_by_origin(product),
            "source_payloads": self._image_only_source_payloads(product.source_payloads),
            "gpt_attachment_paths": [str(path) for path in gpt_attachment_paths],
            "brand_logo_path": str(self._brand_logo_source_path() or ""),
            "brand_logo_reference_dir": str(brand_logo_dir),
            "brand_logo_manifest_path": str(brand_logo_manifest_path) if brand_logo_manifest_path.exists() else "",
            "brand_logo_check_prompt_path": str(brand_logo_check_prompt_path) if brand_logo_check_prompt_path.exists() else "",
            "brand_logo_applied_count": brand_logo_applied_count,
            "generated_visual_paths": [str(path) for path in render_result.visual_paths],
            "section_paths": [str(path) for path in render_result.section_paths],
            "detail_page_path": str(render_result.detail_page_path),
            "thumbnail_paths": [str(path) for path in thumbnail_result.paths],
            "thumbnail_model": thumbnail_result.image_model,
            "thumbnail_style_version": THUMBNAIL_STYLE_VERSION,
            "thumbnail_prompt_paths": [str(path) for path in thumbnail_result.prompt_paths],
            "thumbnail_count": len(thumbnail_result.paths),
            "copy_manifest_path": str(copy_manifest_path),
            "copy_manifest_valid": copy_manifest_valid,
            "completed_detail_page_path": str(completed_detail_path) if complete else "",
            "result_path": str(path),
            "sections": [
                {
                    "section_key": section.section_key,
                    "section_name": section.section_name,
                    "headline": section.headline,
                    "subheadline": section.subheadline,
                    "body": section.body,
                    "bullets": section.bullets,
                    "image_prompt": section.image_prompt,
                    "overlay_text": section.overlay_text or self._extract_overlay_text_from_image_prompt(section.image_prompt),
                    "source_section_text": section.source_section_text,
                }
                for section in sections
            ],
        }
        (product.output_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        if complete:
            self._publish_completed_detail_page(product, render_result, path)
        return path

    def _save_codex_image_queue_result(
        self,
        product: ProductRecord,
        prompt: str,
        result_text: str,
        sections: list[SectionPlan],
        run_stamp: str,
    ) -> Path:
        prompt_dir = product.output_dir / "codex_image_prompts"
        visual_dir = product.output_dir / "generated_visuals"
        visual_dir.mkdir(parents=True, exist_ok=True)
        review_section_present = self._sections_include_review_points(sections)
        prompt_paths = sorted(prompt_dir.glob("section_*_prompt.txt")) if prompt_dir.exists() else []
        section_lines = []
        for section, prompt_path in zip(sections, prompt_paths):
            display_name = self._display_section_name(section.section_key, section.section_name)
            section_lines.append(
                f"## {display_name} ({section.section_key})\n\n"
                f"- 헤드라인: {section.headline}\n"
                f"- 서브카피: {section.subheadline}\n"
                f"- 이미지 프롬프트 파일: {prompt_path}\n\n"
                f"{section.body}\n\n"
                + "\n".join(f"- {item}" for item in section.bullets)
            )
        path = product.output_dir / "result.md"
        content = (
            f"# {product.product_name} 상세페이지 자동화 결과\n\n"
            "- 상태: 이미지 생성 대기\n"
            f"- URL: {product.url}\n"
            f"- 상품코드: {product.code}\n"
            f"- URL별 폴더: {product.output_dir}\n"
            f"- ChatGPT 첨부 이미지 폴더: {product.output_dir / 'gpt_attachments'}\n"
            f"- 이미지 프롬프트 폴더: {prompt_dir}\n"
            f"- 이미지 생성 대상 모델: {LATEST_CODEX_IMAGE_MODEL}\n"
            f"- 파이프라인 버전: {DETAIL_PIPELINE_VERSION}\n"
            f"- 리뷰 섹션 버전: {DETAIL_REVIEW_SECTION_STYLE_VERSION}\n"
            f"- 리뷰 섹션 포함: {'예' if review_section_present else '아니오'}\n"
            f"- 이미지 생성 배치 파일: {prompt_dir / f'imagegen_{LATEST_CODEX_IMAGE_MODEL}_jobs.jsonl'}\n"
            f"- 생성 이미지 감시 폴더: {visual_dir}\n"
            f"- 저장 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "## 처리 기준\n\n"
            "- ChatGPT에는 상품 URL과 저장된 상품 이미지를 함께 전송했습니다.\n"
            "- 아래 섹션 기획과 이미지 프롬프트는 ChatGPT 답변을 파싱한 결과입니다.\n"
            "- 완료 처리는 GPT가 준 섹션 수만큼 실제 생성 PNG가 있을 때만 가능합니다.\n"
            "- 로컬 더미 이미지나 상품 이미지 반복 템플릿은 완료로 처리하지 않습니다.\n\n"
            "## 섹션 기획\n\n"
            f"{chr(10).join(section_lines)}\n\n"
            "## GPT 요청 프롬프트\n\n"
            "```text\n"
            f"{prompt.strip()}\n"
            "```\n\n"
            "## GPT 원문 결과\n\n"
            "```text\n"
            f"{result_text.strip()}\n"
            "```\n"
        )
        path.write_text(content, encoding="utf-8")
        metadata = {
            "status": "이미지 생성 대기",
            "url": product.url,
            "gpt_url": GPT_URL,
            "gpt_name": GPT_NAME,
            "product_name": product.product_name,
            "code": product.code,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "run_stamp": run_stamp,
            "pipeline_version": DETAIL_PIPELINE_VERSION,
            "review_section_required": False,
            "review_section_style_version": DETAIL_REVIEW_SECTION_STYLE_VERSION,
            "review_section_present": review_section_present,
            "render_mode": "codex_image_pending",
            "latest_image_model_target": LATEST_CODEX_IMAGE_MODEL,
            "latest_image_size_target": LATEST_CODEX_IMAGE_SIZE,
            "imagegen_jobs_path": str(prompt_dir / f"imagegen_{LATEST_CODEX_IMAGE_MODEL}_jobs.jsonl"),
            "source_image_paths": [str(path) for path in product.source_image_paths],
            "gpt_attachment_paths": [str(path) for path in sorted((product.output_dir / "gpt_attachments").glob("*.jpg"))],
            "brand_logo_reference_dir": str(product.output_dir / BRAND_LOGO_REFERENCE_DIR_NAME),
            "codex_image_prompt_paths": [str(path) for path in prompt_paths],
            "generated_visual_dir": str(visual_dir),
            "generated_visual_paths": [],
            "section_paths": [],
            "detail_page_path": "",
            "result_path": str(path),
            "sections": [
                {
                    "section_key": section.section_key,
                    "section_name": section.section_name,
                    "headline": section.headline,
                    "subheadline": section.subheadline,
                    "body": section.body,
                    "bullets": section.bullets,
                    "image_prompt": section.image_prompt,
                    "source_section_text": section.source_section_text,
                }
                for section in sections
            ],
        }
        (product.output_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _send_prompt_to_gpt_page(
        self,
        page,
        prompt: str,
        attachment_paths: list[Path] | None = None,
        image_mode: bool = False,
    ) -> None:
        self._dismiss_chatgpt_blocking_modal(page)
        attachment_paths = [path for path in (attachment_paths or []) if path.exists() and path.stat().st_size > 0]
        self._dismiss_chatgpt_blocking_modal(page)
        if self._page_needs_login(page):
            page.bring_to_front()
            raise RuntimeError("ChatGPT 로그인이 필요합니다.")
        if image_mode:
            self._dismiss_chatgpt_blocking_modal(page)
        self._ensure_chatgpt_thinking_mode(page)
        composer = self._composer_locator(page)
        prompt = prompt.strip()
        previous_user_message_count = self._chatgpt_user_message_count(page)
        click_error = None
        for _ in range(3):
            try:
                composer.click(timeout=10000)
                click_error = None
                break
            except Exception as exc:
                click_error = exc
                self._dismiss_chatgpt_blocking_modal(page)
                self._force_hide_chatgpt_open_sheets(page)
                page.wait_for_timeout(700)
        if click_error is not None:
            raise click_error
        page.wait_for_timeout(300)
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        page.keyboard.insert_text(prompt)
        page.wait_for_timeout(1800)
        if not self._composer_contains_text(page, prompt):
            try:
                composer.fill(prompt, timeout=5000)
            except Exception:
                composer.click(timeout=5000)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.insert_text(prompt)
            page.wait_for_timeout(1000)
        if not self._composer_contains_text(page, prompt):
            raise RuntimeError("ChatGPT 입력창에 프롬프트를 넣지 못했습니다.")
        if attachment_paths:
            self._attach_images_to_gpt_page(page, attachment_paths)
            if not self._composer_contains_text(page, prompt):
                composer = self._composer_locator(page)
                composer.click(timeout=5000)
                page.keyboard.insert_text(prompt)
                page.wait_for_timeout(1000)
            if not self._composer_contains_text(page, prompt):
                raise RuntimeError("ChatGPT 이미지 첨부 후 프롬프트가 입력창에서 사라졌습니다.")

        send_selectors = [
            "#composer-submit-button",
            "button[data-testid='send-button']",
            "button[data-testid='composer-submit-button']",
            "button[data-testid='fruitjuice-send-button']",
            "form button[type='submit']",
            "button:has-text('프롬프트 보내기')",
            "button[aria-label*='Send']",
            "button[aria-label*='전송']",
            "button[aria-label*='프롬프트 보내기']",
            "button[aria-label*='submit']",
            "button[aria-label*='Submit']",
        ]
        sent = self._click_chatgpt_send_button(page, send_selectors, timeout_ms=10000)
        if not sent:
            page.keyboard.press("Enter")
            page.wait_for_timeout(1200)
            _, busy_after_enter = self._latest_gpt_text(page)
            if busy_after_enter:
                sent = True
            if not sent and self._composer_contains_text(page, prompt):
                sent = self._click_chatgpt_send_button(page, send_selectors, timeout_ms=60000)
                if not sent:
                    _, busy_after_retry = self._latest_gpt_text(page)
                    if busy_after_retry:
                        sent = True
        if not sent and self._composer_contains_text(page, prompt):
            try:
                sent = bool(
                    page.evaluate(
                        """() => {
                            const selectors = [
                                "#composer-submit-button",
                                "button[data-testid='send-button']",
                                "button[data-testid='composer-submit-button']",
                                "form button[type='submit']"
                            ];
                            for (const selector of selectors) {
                                const button = document.querySelector(selector);
                                if (button) {
                                    button.click();
                                    return true;
                                }
                            }
                            return false;
                        }"""
                    )
                )
                page.wait_for_timeout(1200)
            except Exception:
                sent = False
        if not sent and self._composer_contains_text(page, prompt):
            for key in ("Control+Enter", "Shift+Enter"):
                try:
                    page.keyboard.press(key)
                    page.wait_for_timeout(1200)
                    _, busy_after_hotkey = self._latest_gpt_text(page)
                    if busy_after_hotkey or not self._composer_contains_text(page, prompt):
                        sent = True
                        break
                except Exception:
                    continue
        if not sent and self._composer_contains_text(page, prompt):
            sent = self._click_chatgpt_retry_button(page, timeout_ms=15000)
            if sent:
                page.wait_for_timeout(2500)
                _, busy_after_retry_button = self._latest_gpt_text(page)
                if not busy_after_retry_button and self._composer_contains_text(page, prompt):
                    sent = self._click_chatgpt_send_button(page, send_selectors, timeout_ms=10000)
        if not sent and self._composer_contains_text(page, prompt):
            latest_text, busy_after_error = self._latest_gpt_text(page)
            if self._is_chatgpt_transient_send_error_text(latest_text):
                sent = self._click_chatgpt_retry_button(page, timeout_ms=12000)
                if sent:
                    page.wait_for_timeout(3000)
            elif busy_after_error:
                sent = True
        if not sent and self._composer_contains_text(page, prompt):
            raise RuntimeError("ChatGPT 전송 버튼을 누르지 못했습니다.")
        if sent and self._composer_contains_text(page, prompt):
            _, busy_after_send = self._latest_gpt_text(page)
            user_message_sent = self._chatgpt_user_message_count(page) > previous_user_message_count
            if not user_message_sent:
                user_message_sent = self._latest_user_message_matches_prompt(page, prompt)
            if not busy_after_send and not user_message_sent:
                raise RuntimeError("ChatGPT 전송 후에도 프롬프트가 입력창에 남아 있습니다.")
        page.wait_for_timeout(1500)

    def _select_chatgpt_image_creation_mode(self, page) -> None:
        try:
            self._wait_for_gpt_idle(page, timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS)
        except RuntimeError as exc:
            if not self._is_retryable_section_plan_wait_error(str(exc)):
                raise
            raise RuntimeError("ChatGPT가 아직 답변 또는 이미지를 생성 중입니다. 완료된 뒤 이어서 실행하세요.") from exc
        self._dismiss_chatgpt_blocking_modal(page)
        self._force_hide_chatgpt_open_sheets(page)
        if self._click_visible_chatgpt_menu_item(page, ("이미지 만들기", "Create image", "Image generation")):
            page.wait_for_timeout(1000)
            return

        if self._open_chatgpt_tools_menu(page) and self._click_visible_chatgpt_menu_item(
            page,
            ("이미지 만들기", "Create image", "Image generation"),
        ):
            page.wait_for_timeout(1000)
            return

        # Custom GPT pages can hide the image tool. Do not navigate away here:
        # thumbnail generation must stay in the detail-page conversation that
        # produced the section plan and images.
        if self._is_chatgpt_section_planner_url(page.url):
            self._force_hide_chatgpt_open_sheets(page)
            raise RuntimeError("현재 상세페이지 ChatGPT 대화에서 이미지 만들기 메뉴를 찾지 못했습니다.")

        self._force_hide_chatgpt_open_sheets(page)
        raise RuntimeError("ChatGPT + 메뉴에서 '이미지 만들기' 항목을 찾지 못했습니다.")

    def _open_chatgpt_tools_menu(self, page) -> bool:
        plus_selectors = (
            "button[data-testid='composer-plus-btn']",
            "button[aria-label*='추가']",
            "button[aria-label*='더 보기']",
            "button[aria-label*='더하기']",
            "button[aria-label*='Add']",
            "button[aria-label*='Attach']",
            "button:has-text('+')",
        )
        opened = False
        last_error: Exception | None = None
        for selector in plus_selectors:
            try:
                locator = page.locator(selector)
                count = min(locator.count(), 5)
            except Exception as exc:
                last_error = exc
                continue
            for item_index in range(count - 1, -1, -1):
                candidate = locator.nth(item_index)
                try:
                    if not candidate.is_visible(timeout=700) or not candidate.is_enabled(timeout=700):
                        continue
                    candidate.click(timeout=3000)
                    page.wait_for_timeout(800)
                    opened = True
                    break
                except Exception as exc:
                    last_error = exc
                    continue
            if opened:
                break

        if not opened:
            try:
                opened = bool(
                    page.evaluate(
                        """() => {
                            const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                            const buttons = Array.from(document.querySelectorAll("button,[role='button']"));
                            const candidates = buttons.filter((el) => {
                                const text = [
                                    el.innerText || "",
                                    el.getAttribute("aria-label") || "",
                                    el.getAttribute("title") || "",
                                    el.getAttribute("data-testid") || ""
                                ].join(" ").toLowerCase();
                                if (!visible(el) || el.disabled || el.getAttribute("aria-disabled") === "true") return false;
                                return text.includes("composer-plus")
                                    || text.includes("추가")
                                    || text.includes("더하기")
                                    || text.includes("add")
                                    || text.trim() === "+";
                            });
                            const button = candidates[candidates.length - 1];
                            if (!button) return false;
                            button.click();
                            return true;
                        }"""
                    )
                )
                page.wait_for_timeout(800)
            except Exception as exc:
                last_error = exc

        if not opened:
            if last_error:
                self._last_chatgpt_menu_open_error = last_error
            return False
        return True

    def _click_visible_chatgpt_menu_item(self, page, labels: tuple[str, ...]) -> bool:
        for label in labels:
            selectors = (
                f"[role='menuitemradio']:has-text('{label}')",
                f"[role='menuitem']:has-text('{label}')",
                f"[role='option']:has-text('{label}')",
                f"button:has-text('{label}')",
                f"div:has-text('{label}')",
            )
            for selector in selectors:
                try:
                    locator = page.locator(selector)
                    count = min(locator.count(), 8)
                except Exception:
                    continue
                for item_index in range(count - 1, -1, -1):
                    item = locator.nth(item_index)
                    try:
                        if not item.is_visible(timeout=500):
                            continue
                        text = item.inner_text(timeout=500).strip()
                        if label not in text:
                            continue
                        item.click(timeout=3000)
                        return True
                    except Exception:
                        continue
        try:
            return bool(
                page.evaluate(
                    """(labels) => {
                        const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                        const nodes = Array.from(document.querySelectorAll("[role='menuitemradio'],[role='menuitem'],[role='option'],button,div"));
                        const candidates = nodes.filter((el) => {
                            if (!visible(el) || el.disabled || el.getAttribute("aria-disabled") === "true") return false;
                            const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                            if (!text) return false;
                            return labels.some((label) => text.includes(label));
                        });
                        const exact = candidates.find((el) => {
                            const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                            return labels.some((label) => text === label);
                        });
                        const roleMatch = candidates.find((el) => {
                            const role = el.getAttribute("role") || "";
                            const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                            return /menuitemradio|menuitem|option/.test(role) && labels.some((label) => text.includes(label));
                        });
                        const node = exact || roleMatch || candidates[candidates.length - 1];
                        if (!node) return false;
                        node.click();
                        return true;
                    }""",
                    list(labels),
                )
            )
        except Exception:
            return False

    def _click_chatgpt_retry_button(self, page, timeout_ms: int = 5000) -> bool:
        deadline = time.time() + max(0.5, timeout_ms / 1000)
        while time.time() < deadline:
            self._dismiss_chatgpt_blocking_modal(page)
            for selector in (
                "[data-testid='regenerate-thread-error-button']",
                "button:has-text('다시 시도')",
                "button[aria-label*='다시 시도']",
                "button:has-text('Retry')",
                "button[aria-label*='Retry']",
            ):
                try:
                    button = page.locator(selector)
                    if button.count() > 0 and button.last.is_visible(timeout=500) and button.last.is_enabled(timeout=500):
                        button.last.click(timeout=5000)
                        return True
                except Exception:
                    continue
            try:
                clicked = page.evaluate(
                    """() => {
                        const buttons = Array.from(document.querySelectorAll("button,[role='button']"));
                        const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                        const candidates = buttons.filter((el) => {
                            const text = ((el.innerText || "") + " " + (el.getAttribute("aria-label") || "")).toLowerCase();
                            if (!visible(el) || el.disabled || el.getAttribute("aria-disabled") === "true") return false;
                            return text.includes("다시 시도") || text.includes("retry");
                        });
                        const button = candidates[candidates.length - 1];
                        if (!button) return false;
                        button.click();
                        return true;
                    }"""
                )
                if clicked:
                    return True
            except Exception:
                pass
            page.wait_for_timeout(500)
        return False

    def _ensure_chatgpt_thinking_mode(self, page) -> bool:
        try:
            active = page.evaluate(
                """() => {
                    const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                    const labels = (el) => [
                        el.innerText || "",
                        el.getAttribute("aria-label") || "",
                        el.getAttribute("title") || "",
                        el.getAttribute("data-testid") || ""
                    ].join(" ").replace(/\\s+/g, " ").trim();
                    const buttons = Array.from(document.querySelectorAll("button,[role='button']"));
                    return buttons.some((button) => {
                        if (!visible(button) || button.disabled || button.getAttribute("aria-disabled") === "true") return false;
                        const text = labels(button);
                        const lower = text.toLowerCase();
                        if (lower.includes("stop") || text.includes("중지")) return false;
                        return lower.includes("thinking") || lower.includes("think") || lower.includes("heavy") || text.includes("띵킹") || text.includes("생각") || text.includes("헤비");
                    });
                }"""
            )
            if active:
                return True
        except Exception:
            pass

        try:
            clicked = page.evaluate(
                """() => {
                    const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                    const labelOf = (el) => [
                        el.innerText || "",
                        el.getAttribute("aria-label") || "",
                        el.getAttribute("title") || "",
                        el.getAttribute("data-testid") || ""
                    ].join(" ").replace(/\\s+/g, " ").trim();
                    const isThinking = (text) => {
                        const lower = text.toLowerCase();
                        return lower.includes("thinking") || lower.includes("think") || lower.includes("heavy") || text.includes("띵킹") || text.includes("생각") || text.includes("헤비");
                    };
                    const nodes = Array.from(document.querySelectorAll("[role='menuitemradio'],[role='menuitem'],[role='option'],button,[role='button']"));
                    const direct = nodes.find((node) => {
                        if (!visible(node) || node.disabled || node.getAttribute("aria-disabled") === "true") return false;
                        const text = labelOf(node);
                        if (!text || text.includes("중지") || text.includes("제거") || text.toLowerCase().includes("stop") || text.toLowerCase().includes("remove")) return false;
                        return isThinking(text);
                    });
                    if (direct) {
                        direct.click();
                        return true;
                    }
                    const buttons = Array.from(document.querySelectorAll("button,[role='button']"));
                    const opener = buttons.find((button) => {
                        if (!visible(button) || button.disabled || button.getAttribute("aria-disabled") === "true") return false;
                        const text = labelOf(button);
                        const lower = text.toLowerCase();
                        if (lower.includes("composer-plus") || lower.includes("attach") || lower.includes("upload") || text.includes("파일") || text.includes("추가")) return false;
                        return lower.includes("mode") || lower.includes("model") || lower.includes("reason") || text.includes("모드") || text.includes("확장") || text.includes("추론");
                    });
                    if (!opener) return false;
                    opener.click();
                    return "opened";
                }"""
            )
            if clicked is True:
                page.wait_for_timeout(800)
                return True
            if clicked == "opened":
                page.wait_for_timeout(800)
                selected = page.evaluate(
                    """() => {
                        const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                        const labelOf = (el) => [
                            el.innerText || "",
                            el.getAttribute("aria-label") || "",
                            el.getAttribute("title") || ""
                        ].join(" ").replace(/\\s+/g, " ").trim();
                        const nodes = Array.from(document.querySelectorAll("[role='menuitemradio'],[role='menuitem'],[role='option'],button,[role='button']"));
                        const target = nodes.find((node) => {
                            if (!visible(node) || node.disabled || node.getAttribute("aria-disabled") === "true") return false;
                            const text = labelOf(node);
                            const lower = text.toLowerCase();
                            return lower.includes("thinking") || lower.includes("think") || lower.includes("heavy") || text.includes("띵킹") || text.includes("생각") || text.includes("헤비");
                        });
                        if (!target) return false;
                        target.click();
                        return true;
                    }"""
                )
                if selected:
                    page.wait_for_timeout(800)
                    return True
        except Exception:
            return False
        return False

    def _click_chatgpt_send_button(self, page, selectors: list[str], timeout_ms: int = 2000) -> bool:
        deadline = time.time() + max(0.5, timeout_ms / 1000)
        while time.time() < deadline:
            self._dismiss_chatgpt_blocking_modal(page)
            for selector in selectors:
                button = page.locator(selector)
                try:
                    if button.count() > 0 and button.last.is_visible(timeout=500) and button.last.is_enabled(timeout=500):
                        button.last.click(timeout=5000)
                        return True
                except Exception:
                    continue
            try:
                clicked = page.evaluate(
                    """() => {
                        const buttons = Array.from(document.querySelectorAll("button,[role='button']"));
                        const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                        const candidates = buttons.filter((el) => {
                            const text = ((el.innerText || "") + " " + (el.getAttribute("aria-label") || "") + " " + (el.getAttribute("data-testid") || "")).toLowerCase();
                            if (!visible(el) || el.disabled || el.getAttribute("aria-disabled") === "true") return false;
                            return text.includes("send-button") || text.includes("composer-submit-button") || text.includes("send") || text.includes("전송") || text.includes("프롬프트 보내기");
                        });
                        const button = candidates[candidates.length - 1];
                        if (!button) return false;
                        button.click();
                        return true;
                    }"""
                )
                if clicked:
                    return True
            except Exception:
                pass
            page.wait_for_timeout(500)
        return False

    def _attach_images_to_gpt_page(self, page, attachment_paths: list[Path]) -> None:
        files = [str(path) for path in attachment_paths if path.exists() and path.stat().st_size > 0]
        if not files:
            return
        self._wait_for_gpt_idle(page, timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS)
        self._dismiss_chatgpt_blocking_modal(page)
        upload_error: Exception | None = None
        file_inputs = page.locator("input[type='file']")
        try:
            if file_inputs.count() > 0:
                supports_multiple = bool(
                    file_inputs.last.evaluate("(el) => !!el.multiple")
                )
                if supports_multiple or len(files) <= 1:
                    file_inputs.last.set_input_files(files, timeout=30000)
                    self._wait_for_gpt_uploads(page)
                else:
                    for file_path in files:
                        file_inputs.last.set_input_files(file_path, timeout=30000)
                        self._wait_for_gpt_uploads(page)
                self._dismiss_chatgpt_blocking_modal(page)
                return
        except Exception as exc:
            upload_error = exc

        if upload_error:
            raise RuntimeError(f"ChatGPT에 상품 이미지를 첨부하지 못했습니다: {upload_error}")
        raise RuntimeError("ChatGPT 이미지 첨부 input을 찾지 못했습니다.")

    def _wait_for_gpt_uploads(self, page) -> None:
        page.wait_for_timeout(1500)
        try:
            page.wait_for_function(
                """() => {
                    const text = document.body ? document.body.innerText : '';
                    return !/Uploading|업로드 중|파일 처리 중|첨부 중/i.test(text);
                }""",
                timeout=120000,
            )
        except Exception:
            page.wait_for_timeout(5000)
        self._dismiss_chatgpt_blocking_modal(page)
        try:
            body = page.locator("body").inner_text(timeout=5000)
        except Exception:
            body = ""
        if self._chatgpt_login_or_upload_blocked_text(body):
            page.bring_to_front()
            raise RuntimeError("ChatGPT 로그인이 필요합니다. 현재 자동화 Chrome에서 파일/이미지 업로드가 차단되어 있습니다.")

    def _force_hide_chatgpt_open_sheets(self, page) -> bool:
        try:
            hidden_count = page.evaluate(
                """() => {
                    let hidden = 0;
                    const selectors = [
                        "[data-sheet-travel-state='opened']",
                        "[data-state='open'][role='dialog']"
                    ];
                    for (const selector of selectors) {
                        for (const el of document.querySelectorAll(selector)) {
                            const text = el.innerText || "";
                            const isKnownBlocker =
                                selector.includes("data-sheet-travel-state") ||
                                /이미 이 파일을 업로드|뭔가 새로운 걸 업로드|이미지 생성 중 오류|이번 요청의 이미지를 만들지 못했습니다|Deciding which images|Cycle|활동|잘 생각하기|Thought for|duplicate|upload something new/i.test(text);
                            if (!isKnownBlocker) continue;
                            el.setAttribute("data-codex-hidden-blocker", "true");
                            el.style.pointerEvents = "none";
                            el.style.display = "none";
                            el.style.visibility = "hidden";
                            hidden += 1;
                        }
                    }
                    return hidden;
                }"""
            )
            if hidden_count:
                page.wait_for_timeout(500)
                return True
        except Exception:
            return False
        return False

    def _disable_chatgpt_heavy_mode(self, page) -> bool:
        try:
            clicked = page.evaluate(
                """() => {
                    const buttons = Array.from(document.querySelectorAll("button"));
                    for (const button of buttons) {
                        const text = (button.innerText || "").trim();
                        const aria = button.getAttribute("aria-label") || "";
                        if (aria.includes("헤비 모드") && aria.includes("제거")) {
                            button.click();
                            return true;
                        }
                        if (text === "헤비 모드" && !button.disabled) {
                            button.click();
                            return true;
                        }
                    }
                    return false;
                }"""
            )
            if clicked:
                page.wait_for_timeout(800)
                return True
        except Exception:
            return False
        return False

    def _dismiss_chatgpt_blocking_modal(self, page) -> bool:
        dismissed = False
        modal_selectors = (
            "#modal-duplicate-file",
            "[data-testid='modal-duplicate-file']",
            "[data-sheet-travel-state='opened']",
            "[role='dialog']",
        )
        modal_signals = (
            "이미 이 파일을 업로드",
            "뭔가 새로운 걸 업로드",
            "이미지 생성 중 오류",
            "이번 요청의 이미지를 만들지 못했습니다",
            "이미지를 선택",
            "Deciding which images",
            "활동",
            "잘 생각하기",
            "Thought for",
            "Cycle",
            "already uploaded",
            "duplicate",
            "upload something new",
        )
        button_labels = ("완료", "확인", "OK", "Ok", "Done", "Got it", "닫기", "Close")
        for selector in modal_selectors:
            try:
                modals = page.locator(selector)
                count = modals.count()
            except Exception:
                continue
            for modal_index in range(count - 1, -1, -1):
                modal = modals.nth(modal_index)
                try:
                    if not modal.is_visible(timeout=500):
                        continue
                except Exception:
                    continue
                try:
                    text = modal.inner_text(timeout=1000)
                except Exception:
                    text = ""
                text_lower = text.lower()
                is_open_sheet = selector == "[data-sheet-travel-state='opened']"
                if selector == "[role='dialog']" and not any(signal in text_lower or signal in text for signal in modal_signals):
                    continue
                clicked = False
                for label in button_labels:
                    try:
                        button = modal.get_by_text(label, exact=True)
                        if button.count() > 0 and button.last.is_visible(timeout=500):
                            button.last.click(timeout=3000)
                            clicked = True
                            break
                    except Exception:
                        continue
                    try:
                        button = modal.get_by_text(label, exact=False)
                        if button.count() > 0 and button.last.is_visible(timeout=500):
                            button.last.click(timeout=3000)
                            clicked = True
                            break
                    except Exception:
                        continue
                if not clicked:
                    try:
                        buttons = modal.locator("button")
                        if buttons.count() > 0:
                            buttons.last.click(timeout=3000)
                            clicked = True
                    except Exception:
                        clicked = False
                if not clicked:
                    try:
                        page.keyboard.press("Escape")
                        clicked = True
                    except Exception:
                        clicked = False
                if not clicked and is_open_sheet:
                    try:
                        page.mouse.click(20, 20)
                        clicked = True
                    except Exception:
                        clicked = False
                if clicked:
                    try:
                        modal.wait_for(state="hidden", timeout=3000)
                    except Exception:
                        if is_open_sheet:
                            self._force_hide_chatgpt_open_sheets(page)
                        else:
                            page.wait_for_timeout(800)
                    dismissed = True
        return dismissed

    def _chatgpt_user_message_count(self, page) -> int:
        try:
            return int(
                page.evaluate(
                    """() => document.querySelectorAll("[data-message-author-role='user']").length"""
                )
            )
        except Exception:
            return 0

    def _latest_user_message_matches_prompt(self, page, prompt: str) -> bool:
        prompt_key = self._normalize_text_key(prompt or "")
        if not prompt_key:
            return False
        try:
            user_texts = page.evaluate(
                """() => Array.from(document.querySelectorAll("[data-message-author-role='user']"))
                    .slice(-5)
                    .map((node) => node.innerText || node.textContent || "")"""
            )
        except Exception:
            return False
        probes: list[str] = []
        if len(prompt_key) <= 500:
            probes.append(prompt_key)
        else:
            for start in (0, len(prompt_key) // 3, (len(prompt_key) * 2) // 3, max(0, len(prompt_key) - 300)):
                chunk = prompt_key[start : start + 300].strip()
                if len(chunk) >= 80 and chunk not in probes:
                    probes.append(chunk)
        marker_keys = [
            self._normalize_text_key(marker)
            for marker in (
                "첨부한 실제 상품 이미지",
                "섹션 11은 만들지 말고",
                "상품 URL",
                "출력 형식",
                "섹션 1. 히어로",
            )
        ]
        for raw_text in reversed(user_texts or []):
            text_key = self._normalize_text_key(str(raw_text or ""))
            if not text_key:
                continue
            if prompt_key[:500] and (prompt_key[:500] in text_key or text_key[:500] in prompt_key):
                return True
            if probes:
                matched = sum(1 for probe in probes if probe and probe in text_key)
                if matched >= 2 or (len(probes) == 1 and matched == 1):
                    return True
            matched_markers = sum(1 for marker in marker_keys if marker and marker in prompt_key and marker in text_key)
            if matched_markers >= 3:
                return True
        return False

    def _composer_contains_text(self, page, expected: str) -> bool:
        expected = expected.strip()
        if not expected:
            return True
        expected_norm = re.sub(r"\s+", " ", expected).strip()
        for selector in (
            "form [contenteditable='true']",
            "div.ProseMirror",
            "#prompt-textarea",
            "[role='textbox']",
            "textarea",
        ):
            locator = page.locator(selector)
            try:
                if locator.count() == 0:
                    continue
                candidate = locator.last
                if not candidate.is_visible(timeout=500):
                    continue
                value = candidate.inner_text(timeout=1000).strip()
                if not value:
                    value = candidate.input_value(timeout=1000).strip()
                value_norm = re.sub(r"\s+", " ", value).strip()
                if expected in value or expected_norm in value_norm:
                    return True
                if len(expected_norm) > 500 and value_norm:
                    probes = [
                        expected_norm[:160],
                        expected_norm[max(0, len(expected_norm) // 2 - 80) : len(expected_norm) // 2 + 80],
                        expected_norm[-160:],
                    ]
                    if any(probe and probe in value_norm for probe in probes):
                        return True
                    anchor_count = sum(
                        1
                        for marker in ("상품 URL", "섹션", "프롬프트", "한글 카피", "필수 기준")
                        if marker in value_norm
                    )
                    if anchor_count >= 2 and len(value_norm) >= min(500, max(160, len(expected_norm) // 4)):
                        return True
            except Exception:
                continue
        return False

    def _url_output_folder(self, index: int, url: str) -> Path:
        stable_folder = self._stable_url_output_folder_path(index, url)
        for candidate in self._url_output_folder_candidates(index, url):
            if not candidate.exists():
                continue
            if candidate == stable_folder:
                folder = candidate
                break
            metadata = self._read_output_metadata(candidate)
            if metadata and self._metadata_matches_task_url(metadata, url):
                folder = candidate
                break
        else:
            folder = stable_folder
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _clear_source_image_files(self, source_root_dir: Path) -> None:
        source_root_dir.mkdir(parents=True, exist_ok=True)
        for old_image in source_root_dir.rglob("*"):
            if old_image.is_file() and old_image.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                old_image.unlink(missing_ok=True)

    def _page_image_records(self, page, page_url: str) -> list[dict[str, str | int]]:
        records = page.evaluate(
            """() => Array.from(document.images).map((img) => {
                const rect = img.getBoundingClientRect();
                const chain = [];
                let el = img;
                for (let i = 0; el && i < 7; i += 1) {
                    const className = typeof el.className === 'string' ? el.className : '';
                    chain.push(`${el.tagName || ''}#${el.id || ''}.${className}`);
                    el = el.parentElement;
                }
                const attr = (name) => img.getAttribute(name) || '';
                const src =
                    img.currentSrc || img.src || attr('data-src') || attr('data-original') ||
                    attr('data-lazy-src') || attr('data-ks-lazyload') || attr('data-img') || '';
                return {
                    src,
                    alt: img.alt || attr('title') || '',
                    width: img.naturalWidth || 0,
                    height: img.naturalHeight || 0,
                    client_width: Math.round(rect.width || 0),
                    client_height: Math.round(rect.height || 0),
                    top: Math.round(rect.top + window.scrollY),
                    parent_chain: chain.join(' > ')
                };
            })"""
        )
        image_candidates: list[dict[str, str | int]] = []
        for record in records:
            src = str(record.get("src") or "").strip()
            if not src:
                continue
            absolute_src = urllib.parse.urljoin(page_url, src)
            width = int(record.get("width") or 0)
            height = int(record.get("height") or 0)
            client_width = int(record.get("client_width") or 0)
            client_height = int(record.get("client_height") or 0)
            if max(width, client_width) < 120 or max(height, client_height) < 80:
                continue
            image_candidates.append(
                {
                    "src": absolute_src,
                    "alt": str(record.get("alt") or ""),
                    "width": width,
                    "height": height,
                    "client_width": client_width,
                    "client_height": client_height,
                    "top": int(record.get("top") or 0),
                    "parent_chain": str(record.get("parent_chain") or ""),
                }
            )
        return image_candidates

    def _download_source_records(
        self,
        records: list[dict[str, str | int]],
        source_dir: Path,
        run_stamp: str,
        referer: str,
        origin: str,
        limit: int = 8,
    ) -> tuple[list[Path], list[dict[str, str | int]]]:
        source_dir.mkdir(parents=True, exist_ok=True)
        source_image_paths: list[Path] = []
        downloaded_records: list[dict[str, str | int]] = []
        seen_sources: set[str] = set()
        image_index = 1
        for record in records:
            src = str(record.get("src") or "").strip()
            if not src or src in seen_sources:
                continue
            seen_sources.add(src)
            role = slugify(str(record.get("role") or origin or "source"), "source")
            ext = Path(urllib.parse.urlparse(src).path).suffix.lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
                ext = ".jpg"
            target = source_dir / f"source_{run_stamp}_{image_index:02d}_{role}{ext}"
            image_index += 1
            try:
                self._download_image_with_headers(src, target, referer=referer)
                if self._is_valid_image_file(target):
                    source_image_paths.append(target)
                    downloaded = dict(record)
                    downloaded["local_path"] = str(target)
                    downloaded["origin"] = origin
                    downloaded_records.append(downloaded)
                elif target.exists():
                    target.unlink(missing_ok=True)
            except Exception:
                if target.exists():
                    target.unlink(missing_ok=True)
                continue
            if len(source_image_paths) >= limit:
                break
        return source_image_paths, downloaded_records

    def _product_source_login_block_reason(
        self,
        requested_url: str,
        loaded_url: str,
        title: str,
        body: str,
        image_records: list[dict[str, str | int]],
    ) -> str:
        loaded_path = urllib.parse.urlparse(loaded_url or "").path.lower()
        if re.search(r"(?:^|/)(?:login|signin|member/login|member/signin|login_form|login\.php)(?:/|$)", loaded_path):
            return "상품 페이지가 로그인 페이지로 이동됨"

        normalized = re.sub(r"\s+", " ", f"{title or ''} {body or ''}").strip()
        lowered = normalized.lower()
        strong_login_markers = (
            "로그인 후 이용",
            "로그인이 필요",
            "로그인 후 사용",
            "로그인 후 확인",
            "로그인해주세요",
            "로그인 해주세요",
            "회원 로그인",
            "로그인 하신 후",
            "접근 권한이 없습니다",
            "비회원은 이용할 수",
            "please login",
            "please sign in",
            "sign in required",
            "captcha",
            "验证",
            "请登录",
            "登录",
        )
        if not any(marker.lower() in lowered for marker in strong_login_markers):
            return ""

        product_markers = ("상품코드", "원산지", "제조사", "상품군", "판매가", "옵션", "상품정보", "상품상세")
        product_marker_count = sum(1 for marker in product_markers if marker in normalized)
        usable_image_count = 0
        for record in image_records:
            try:
                width = int(record.get("width") or record.get("client_width") or 0)
                height = int(record.get("height") or record.get("client_height") or 0)
            except Exception:
                continue
            if width >= 300 and height >= 80:
                usable_image_count += 1
        if product_marker_count < 2 or usable_image_count < 2 or len(normalized) < 500:
            return "상품 페이지 본문이 로그인/권한 안내로 표시됨"
        return ""

    def _scrape_product_page(
        self,
        playwright,
        index: int,
        url: str,
        run_stamp: str,
        browser_context=None,
        secondary_url: str = "",
    ) -> ProductRecord:
        product_dir = self._url_output_folder(index, url)
        source_root_dir = product_dir / "source_images"
        owner_source_dir = source_root_dir / "ownerclan"
        self._clear_source_image_files(source_root_dir)
        owner_source_dir.mkdir(parents=True, exist_ok=True)
        browser = None
        page = None
        close_product_page = False
        page_html = ""
        page_capture_path = owner_source_dir / f"source_{run_stamp}_page_capture.png"
        source_image_paths: list[Path] = []
        try:
            if browser_context is not None:
                page = self._existing_page_for_url(browser_context, url)
                if page is None:
                    page = browser_context.new_page()
                    close_product_page = True
            else:
                browser_path = self._system_browser_executable_path()
                launch_options = {"headless": True}
                if browser_path:
                    launch_options["executable_path"] = str(browser_path)
                browser = playwright.chromium.launch(**launch_options)
                page = browser.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)
            self._expand_product_detail_area(page)
            title = page.title()
            body = page.locator("body").inner_text(timeout=10000)
            image_records = self._page_image_records(page, url)
            login_block_reason = self._product_source_login_block_reason(url, page.url, title, body, image_records)
            if login_block_reason:
                close_product_page = False
                try:
                    page.bring_to_front()
                except Exception:
                    pass
                raise RuntimeError(
                    f"{login_block_reason}. 자동화 Chrome에서 해당 상품 사이트에 로그인한 뒤 다시 실행하세요."
                )
            option_popup_text = self._fetch_domeggook_option_popup_text(url, browser_context=browser_context)
            option_rows = self._parse_domeggook_option_rows(option_popup_text)
            page_html = page.content()
            try:
                page.screenshot(path=str(page_capture_path), full_page=True, timeout=30000)
            except Exception:
                page_capture_path = Path()
        finally:
            try:
                if page is not None and (browser is not None or close_product_page):
                    page.close()
            except Exception:
                pass
            try:
                if browser is not None:
                    browser.close()
            except Exception:
                pass

        code_match = re.search(r"selfcode=([^&]+)", url)
        code = slugify(code_match.group(1) if code_match else f"url_{index + 1}")
        product_name = title.replace(" - 오너클랜", "").strip() or f"상품 {code}"
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        category = next((line for line in lines if "▷" in line), "")
        price_matches = re.findall(r"\d{1,3}(?:,\d{3})+\s*원", body)
        price_text = " / ".join(dict.fromkeys(price_matches[:3]))
        option_lines = [line for line in lines if line.startswith("옵션") or "색상 :" in line or line == "색상"]
        options_text = " / ".join(option_lines[:6])
        if option_rows:
            options_text = self._option_rows_to_options_text(option_rows)
        fact_labels = (
            "상품코드",
            "원산지",
            "제조사/수입사",
            "모델명",
            "상품군",
            "주요소재",
            "크기",
        )
        facts = []
        for line in lines:
            if any(label in line for label in fact_labels):
                facts.append(line)
            if len(facts) >= 12:
                break

        image_candidates: list[dict[str, str | int]] = []
        for record in image_records:
            src = str(record.get("src") or "").strip()
            if not src:
                continue
            absolute_src = urllib.parse.urljoin(url, src)
            width = int(record.get("width") or 0)
            height = int(record.get("height") or 0)
            if width < 300 or height < 80:
                continue
            image_candidates.append(
                {
                    "src": absolute_src,
                    "alt": str(record.get("alt") or ""),
                    "width": width,
                    "height": height,
                    "client_width": int(record.get("client_width") or 0),
                    "client_height": int(record.get("client_height") or 0),
                    "top": int(record.get("top") or 0),
                    "parent_chain": str(record.get("parent_chain") or ""),
                }
            )

        detail_image_urls = self._extract_detail_image_urls(page_html, url)
        main_candidates = sorted(
            [item for item in image_candidates if self._is_primary_product_image_candidate(item)],
            key=lambda item: (int(item.get("top") or 0), -int(item.get("client_width") or 0) * int(item.get("client_height") or 0)),
        )
        # 추천 상품/광고 이미지는 버리고 대표/상세/상품 썸네일 후보를 최대한 많이 저장한다.
        download_candidates: list[dict[str, str | int]] = []
        if main_candidates:
            primary = dict(main_candidates[0])
            primary["role"] = "primary"
            download_candidates.append(primary)
        thumbnail_candidates = sorted(
            [
                item
                for item in image_candidates
                if self._is_product_thumbnail_candidate(item)
            ],
            key=lambda item: (
                int(item.get("top") or 0),
                -int(item.get("width") or 0) * int(item.get("height") or 0),
            ),
        )
        for item in thumbnail_candidates[:GPT_ATTACHMENT_DOMESTIC_THUMBNAIL_LIMIT]:
            thumbnail = dict(item)
            thumbnail["role"] = "thumb"
            download_candidates.append(thumbnail)
        detail_candidates = sorted(
            [
                item
                for item in image_candidates
                if self._is_product_detail_image_candidate(item)
            ],
            key=lambda item: (
                int(item.get("top") or 0),
                -int(item.get("width") or 0) * int(item.get("height") or 0),
            ),
        )
        for item in detail_candidates[:12]:
            detail = dict(item)
            detail["role"] = "detail"
            download_candidates.append(detail)
        if not download_candidates:
            fallback_candidates = [
                item
                for item in image_candidates
                if not self._is_ownerclan_ui_image_src(str(item["src"]))
                and not self._looks_like_recommendation_image(item)
                and int(item.get("client_width") or 0) >= 300
                and int(item.get("client_height") or 0) >= 300
                and int(item.get("height") or 0) / max(1, int(item.get("width") or 1)) <= 1.8
            ][:1]
            for item in fallback_candidates:
                fallback = dict(item)
                fallback["role"] = "primary"
                download_candidates.append(fallback)
        for detail_src in detail_image_urls[:12]:
            download_candidates.append(
                {
                    "src": detail_src,
                    "alt": "detail",
                    "width": 0,
                    "height": 0,
                    "client_width": 0,
                    "client_height": 0,
                    "top": 0,
                    "parent_chain": "",
                    "role": "detail",
                }
            )

        seen_sources: set[str] = set()
        deduped_downloads: list[dict[str, str | int]] = []
        for item in download_candidates:
            src = str(item["src"])
            if src in seen_sources:
                continue
            seen_sources.add(src)
            deduped_downloads.append(item)

        downloaded_records: list[dict[str, str | int]] = []
        for image_index, record in enumerate(deduped_downloads[:12], start=1):
            role = slugify(str(record.get("role") or "source"), "source")
            ext = Path(urllib.parse.urlparse(str(record["src"])).path).suffix.lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
                ext = ".jpg"
            target = owner_source_dir / f"source_{run_stamp}_{image_index:02d}_{role}{ext}"
            try:
                self._download_image_with_headers(str(record["src"]), target, referer=url)
                if self._is_valid_image_file(target):
                    source_image_paths.append(target)
                    downloaded = dict(record)
                    downloaded["local_path"] = str(target)
                    downloaded["origin"] = "ownerclan"
                    downloaded_records.append(downloaded)
                elif target.exists():
                    target.unlink(missing_ok=True)
            except Exception:
                continue

        if page_capture_path and self._is_valid_image_file(page_capture_path) and page_capture_path not in source_image_paths:
            source_image_paths.append(page_capture_path)
            downloaded_records.append(
                {
                    "src": "page_capture",
                    "alt": "page capture detail reference",
                    "width": 0,
                    "height": 0,
                    "client_width": 0,
                    "client_height": 0,
                    "top": 0,
                    "parent_chain": "",
                    "role": "page_capture",
                    "local_path": str(page_capture_path),
                }
            )

        source_image_paths = self._ensure_source_image_variety(owner_source_dir, source_image_paths, run_stamp)

        secondary_payload_raw: dict[str, object] = {}
        secondary_payload: dict[str, object] = {}
        if secondary_url.strip():
            secondary_payload_raw = self._scrape_1688_source(
                browser_context=browser_context,
                product_dir=product_dir,
                secondary_url=secondary_url.strip(),
                run_stamp=run_stamp,
            )
            secondary_paths = [
                Path(str(path))
                for path in secondary_payload_raw.get("source_image_paths", [])
                if str(path).strip()
            ]
            source_image_paths.extend(path for path in secondary_paths if self._is_valid_image_file(path))
            if not self._is_1688_source_payload_usable(secondary_payload_raw):
                raise RuntimeError("1688 보조 링크에서 상품 이미지를 충분히 수집하지 못했습니다. 1688 로그인 후 다시 실행하세요.")
            secondary_payload = self._1688_image_only_payload(secondary_payload_raw)

        source_payload = {
            "url": url,
            "secondary_url": secondary_url.strip(),
            "secondary_usage": SECONDARY_1688_USAGE_NOTE if secondary_url.strip() else "",
            "title": title,
            "product_name": product_name,
            "category": category,
            "price_text": price_text,
            "options_text": options_text,
            "option_rows": option_rows,
            "option_popup_text": option_popup_text[:12000],
            "facts": facts,
            "text": body[:16000],
            "images": image_candidates[:20],
            "detail_image_urls": detail_image_urls,
            "source_image_paths": [str(path) for path in source_image_paths],
            "downloaded_images": downloaded_records,
            "secondary_source": secondary_payload,
        }
        (product_dir / "source.json").write_text(
            json.dumps(source_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return ProductRecord(
            index=index,
            url=url,
            secondary_url=secondary_url.strip(),
            code=code,
            product_name=product_name,
            title=title,
            category=category,
            price_text=price_text,
            options_text=options_text,
            facts=facts,
            source_text="\n\n[Primary URL]\n" + body[:14000],
            image_urls=[str(item["src"]) for item in image_candidates[:20]] + detail_image_urls + [
                str(src) for src in secondary_payload.get("image_urls", []) if str(src).strip()
            ],
            source_image_paths=source_image_paths,
            output_dir=product_dir,
            source_payloads=[source_payload, secondary_payload] if secondary_payload else [source_payload],
        )

    def _domeggook_product_no(self, url: str | object) -> str:
        text = str(url or "")
        match = re.search(r"domeggook\.com/(?:[a-zA-Z0-9_/.-]*?)?(\d{5,})", text)
        return match.group(1) if match else ""

    def _fetch_domeggook_option_popup_text(self, url: str | object, browser_context=None) -> str:
        product_no = self._domeggook_product_no(url)
        if not product_no:
            return ""
        popup_url = f"https://domeggook.com/main/popup/item/popup_itemOptionView.php?no={product_no}&market=dome"
        if browser_context is not None:
            popup_page = None
            try:
                popup_page = browser_context.new_page()
                popup_page.goto(popup_url, wait_until="domcontentloaded", timeout=20000)
                popup_page.wait_for_timeout(800)
                return popup_page.locator("body").inner_text(timeout=10000)
            except Exception:
                pass
            finally:
                try:
                    if popup_page is not None:
                        popup_page.close()
                except Exception:
                    pass
        request = urllib.request.Request(
            popup_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Referer": str(url),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
        except Exception:
            return ""
        for encoding in ("utf-8", "euc-kr", "cp949"):
            try:
                page_html = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                page_html = ""
        if not page_html:
            page_html = raw.decode("utf-8", errors="replace")
        return self._visible_text_from_html(page_html)

    def _visible_text_from_html(self, page_html: str | object) -> str:
        text = str(page_html or "")
        if not text:
            return ""
        text = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</(?:tr|td|th|div|li|p|h[1-6])>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def _parse_domeggook_option_rows(self, text: str | object) -> list[dict[str, object]]:
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        rows: list[dict[str, object]] = []
        option_names = ["옵션"]

        def split_option_names(value: str | object) -> list[str]:
            names = [
                self._normalize_option_group_name(part)
                for part in re.split(r"\s*/\s*", str(value or ""))
                if part.strip()
            ]
            return [name for name in names if name] or ["옵션"]

        def split_option_values(value: str | object, names: list[str]) -> tuple[str, dict[str, str]]:
            raw = str(value or "").strip()
            if len(names) <= 1:
                cleaned = self._clean_option_text(raw)
                return cleaned, ({names[0]: cleaned} if cleaned else {})
            parts = [self._clean_option_text(part) for part in re.split(r"\s*/\s*", raw)]
            parts = [part for part in parts if part]
            option_values: dict[str, str] = {}
            for pos, part in enumerate(parts):
                name = names[pos] if pos < len(names) else f"옵션{pos + 1}"
                option_values[name] = part
            label = " / ".join(f"{name}:{option_values[name]}" for name in option_values)
            return label, option_values

        def price_delta_from_text(value: str | object) -> int:
            text_value = str(value or "")
            if "+" not in text_value:
                return 0
            numbers = [
                int(match.group(0).replace(",", ""))
                for match in re.finditer(r"\d[\d,]*", text_value)
                if match.group(0).replace(",", "").isdigit()
            ]
            return numbers[1] if len(numbers) > 1 else 0

        for index, line in enumerate(lines):
            columns = [col.strip() for col in line.split("\t") if col.strip()]
            if len(columns) >= 2 and columns[0] == "옵션코드":
                option_names = split_option_names(columns[1])
                continue
            if len(columns) < 3:
                continue
            if not re.fullmatch(r"\d+(?:_\d+)*", columns[0]):
                continue
            value, option_values = split_option_values(columns[1], option_names)
            if not value:
                continue
            price = self._market_price_expression_int(columns[2])
            stock = self._positive_int(columns[3]) if len(columns) >= 4 else 0
            row = {
                "code": columns[0],
                "group_name": option_names[0],
                "value": value,
                "source_price": price,
                "price_delta": price_delta_from_text(columns[2]),
                "stock_quantity": stock,
                "source": "domeggook_option_popup",
                "row_index": index,
            }
            if option_values:
                row["option_values"] = option_values
            rows.append(row)
        if rows:
            return rows
        for index, line in enumerate(lines):
            if line == "옵션코드" and index + 1 < len(lines):
                option_names = split_option_names(lines[index + 1])
                break
        for index, line in enumerate(lines):
            if not re.fullmatch(r"\d+(?:_\d+)*", line):
                continue
            if index + 3 >= len(lines):
                continue
            value, option_values = split_option_values(lines[index + 1], option_names)
            price_text = lines[index + 2]
            stock_text = lines[index + 3]
            if not value or "원" not in price_text:
                continue
            price = self._market_price_expression_int(price_text)
            stock = self._positive_int(stock_text)
            row = {
                "code": line,
                "group_name": option_names[0],
                "value": value,
                "source_price": price,
                "price_delta": price_delta_from_text(price_text),
                "stock_quantity": stock,
                "source": "domeggook_option_popup",
                "row_index": index,
            }
            if option_values:
                row["option_values"] = option_values
            rows.append(row)
        return rows

    def _option_rows_to_options_text(self, rows: list[dict[str, object]]) -> str:
        if not rows:
            return ""
        group_name = self._clean_option_text(rows[0].get("group_name")) or "옵션"
        values = self._dedupe_text_items(
            [
                self._clean_option_text(row.get("value"))
                for row in rows
                if isinstance(row, dict) and str(row.get("value") or "").strip()
            ]
        )
        if not values:
            return ""
        return f"{group_name} : {','.join(values[:30])}"

    def _1688_image_only_payload(self, payload: dict[str, object]) -> dict[str, object]:
        downloaded_images = [
            item
            for item in payload.get("downloaded_images", [])
            if isinstance(item, dict)
        ]
        return {
            "origin": "1688",
            "url": str(payload.get("url") or ""),
            "usage": SECONDARY_1688_USAGE_NOTE,
            "image_only": True,
            "title": str(payload.get("title") or ""),
            "text": "",
            "excluded_text_fields": ["body", "shipping", "delivery", "return", "customs", "policy", "a/s"],
            "image_urls": [str(src).strip() for src in payload.get("image_urls", []) if str(src).strip()],
            "source_image_paths": [str(path).strip() for path in payload.get("source_image_paths", []) if str(path).strip()],
            "downloaded_images": downloaded_images,
        }

    def _image_only_source_payloads(self, payloads: list[dict[str, object]]) -> list[dict[str, object]]:
        sanitized: list[dict[str, object]] = []
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            origin = str(payload.get("origin") or "").lower()
            url = str(payload.get("url") or "").lower()
            if origin == "1688" or "1688.com" in url:
                sanitized.append(self._1688_image_only_payload(payload))
                continue
            copied = dict(payload)
            secondary = copied.get("secondary_source")
            if isinstance(secondary, dict):
                copied["secondary_source"] = self._1688_image_only_payload(secondary)
            sanitized.append(copied)
        return sanitized

    def _is_1688_source_payload_usable(self, payload: dict[str, object]) -> bool:
        text = re.sub(r"\s+", " ", str(payload.get("text", "") or "")).strip()
        title = str(payload.get("title", "") or "")
        image_urls = [str(src).strip() for src in payload.get("image_urls", []) if str(src).strip()]
        downloaded_images = [
            item
            for item in payload.get("downloaded_images", [])
            if isinstance(item, dict)
            and str(item.get("role", "")).strip() != "page_capture"
            and self._is_valid_image_file(Path(str(item.get("local_path", ""))))
        ]
        if downloaded_images:
            return True
        if len(image_urls) < 2 or len(text) < 200:
            return False
        product_signal_text = f"{title} {text}".lower()
        blocked_signals = (
            "login",
            "sign in",
            "signin",
            "captcha",
            "验证",
            "登录",
            "请登录",
            "安全验证",
        )
        if any(signal in product_signal_text for signal in blocked_signals) and len(image_urls) < 4:
            return False
        product_signals = (
            "1688",
            "阿里巴巴",
            "价格",
            "商品",
            "详情",
            "规格",
            "颜色",
            "采购",
            "起批",
            "offer",
        )
        return sum(1 for signal in product_signals if signal.lower() in product_signal_text) >= 2

    def _scrape_1688_source(
        self,
        browser_context,
        product_dir: Path,
        secondary_url: str,
        run_stamp: str,
    ) -> dict[str, object]:
        source_dir = product_dir / "source_images" / "1688"
        source_dir.mkdir(parents=True, exist_ok=True)
        page = None
        title = ""
        body = ""
        page_html = ""
        image_candidates: list[dict[str, str | int]] = []
        page_capture_path = source_dir / f"source_{run_stamp}_1688_page_capture.png"
        try:
            if browser_context is None:
                raise RuntimeError("1688 로그인 세션을 사용할 자동화 브라우저 컨텍스트가 없습니다.")
            page = self._existing_page_for_url(browser_context, secondary_url) or browser_context.new_page()
            try:
                page.goto(secondary_url, wait_until="networkidle", timeout=90000)
            except Exception:
                page.goto(secondary_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)
            self._expand_product_detail_area(page)
            title = page.title()
            try:
                body = page.locator("body").inner_text(timeout=15000)
            except Exception:
                body = ""
            image_candidates = self._page_image_records(page, secondary_url)
            page_html = page.content()
            try:
                page.screenshot(path=str(page_capture_path), full_page=True, timeout=45000)
            except Exception:
                page_capture_path = Path()
        except Exception as browser_exc:
            fallback = self._scrape_static_source_with_scrapling(secondary_url)
            title = str(fallback.get("title", ""))
            body = str(fallback.get("text", ""))
            page_html = str(fallback.get("html", ""))
            image_candidates = [
                {
                    "src": src,
                    "alt": "1688",
                    "width": 0,
                    "height": 0,
                    "client_width": 0,
                    "client_height": 0,
                    "top": 0,
                    "parent_chain": "",
                }
                for src in fallback.get("image_urls", [])
            ]
            fallback["browser_error"] = str(browser_exc)
        finally:
            try:
                if page is not None:
                    page.bring_to_front()
            except Exception:
                pass

        image_urls = [str(item.get("src") or "") for item in image_candidates if str(item.get("src") or "").strip()]
        image_urls.extend(self._extract_general_image_urls(page_html, secondary_url))
        ranked_records = self._rank_1688_image_candidates(image_candidates, image_urls)
        source_image_paths, downloaded_records = self._download_source_records(
            ranked_records,
            source_dir,
            run_stamp,
            referer=secondary_url,
            origin="1688",
            limit=10,
        )
        if page_capture_path and self._is_valid_image_file(page_capture_path):
            source_image_paths.append(page_capture_path)
            downloaded_records.append(
                {
                    "src": "1688_page_capture",
                    "alt": "1688 page capture detail reference",
                    "width": 0,
                    "height": 0,
                    "client_width": 0,
                    "client_height": 0,
                    "top": 0,
                    "parent_chain": "",
                    "role": "page_capture",
                    "origin": "1688",
                    "local_path": str(page_capture_path),
                }
            )
        source_image_paths = self._ensure_source_image_variety(source_dir, source_image_paths, run_stamp)
        return {
            "origin": "1688",
            "url": secondary_url,
            "title": title,
            "text": body[:12000],
            "image_urls": list(dict.fromkeys(image_urls))[:40],
            "source_image_paths": [str(path) for path in source_image_paths],
            "downloaded_images": downloaded_records,
        }

    def _scrape_static_source_with_scrapling(self, url: str) -> dict[str, object]:
        try:
            from crawler_adapter import fetch_static_page_snapshot

            return fetch_static_page_snapshot(url)
        except Exception as exc:
            return {"url": url, "title": "", "text": "", "html": "", "image_urls": [], "error": str(exc)}

    def _extract_general_image_urls(self, page_html: str, page_url: str) -> list[str]:
        if not page_html:
            return []
        raw_urls: list[str] = []
        patterns = (
            r"https?:\\?/\\?/[^'\"<>\s)]+?(?:jpg|jpeg|png|webp)(?:_[^'\"<>\s)]*)?",
            r"//[^'\"<>\s)]+?(?:jpg|jpeg|png|webp)(?:_[^'\"<>\s)]*)?",
        )
        for pattern in patterns:
            raw_urls.extend(re.findall(pattern, page_html, flags=re.IGNORECASE))
        image_urls: list[str] = []
        seen: set[str] = set()
        for raw in raw_urls:
            cleaned = html.unescape(raw).replace("\\/", "/").strip()
            cleaned = urllib.parse.unquote(cleaned).rstrip("\\\"' ),;")
            if cleaned.startswith("//"):
                cleaned = "https:" + cleaned
            cleaned = urllib.parse.urljoin(page_url, cleaned)
            lower = cleaned.lower()
            if not any(host in lower for host in ("alicdn.com", "1688.com", "taobao.com", "ownerclan.com", "speedgabia.com")):
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            image_urls.append(cleaned)
        return image_urls

    def _rank_1688_image_candidates(
        self,
        image_candidates: list[dict[str, str | int]],
        image_urls: list[str],
    ) -> list[dict[str, str | int]]:
        records: list[dict[str, str | int]] = []
        for item in image_candidates:
            src = str(item.get("src") or "")
            lower = src.lower()
            if not src or not any(host in lower for host in ("alicdn.com", "1688.com", "taobao.com")):
                continue
            width = int(item.get("width") or 0)
            height = int(item.get("height") or 0)
            client_width = int(item.get("client_width") or 0)
            client_height = int(item.get("client_height") or 0)
            if max(width, client_width) < 240 or max(height, client_height) < 240:
                continue
            record = dict(item)
            record["role"] = "1688"
            records.append(record)
        for src in image_urls:
            lower = src.lower()
            if not any(host in lower for host in ("alicdn.com", "1688.com", "taobao.com")):
                continue
            records.append(
                {
                    "src": src,
                    "alt": "1688",
                    "width": 0,
                    "height": 0,
                    "client_width": 0,
                    "client_height": 0,
                    "top": 999999,
                    "parent_chain": "",
                    "role": "1688",
                }
            )
        deduped: list[dict[str, str | int]] = []
        seen: set[str] = set()
        for item in sorted(
            records,
            key=lambda record: (
                int(record.get("top") or 999999),
                -max(int(record.get("width") or 0), int(record.get("client_width") or 0))
                * max(int(record.get("height") or 0), int(record.get("client_height") or 0)),
            ),
        ):
            src = str(item.get("src") or "")
            if not src or src in seen:
                continue
            seen.add(src)
            deduped.append(item)
        return deduped[:18]

    def _default_detail_sections(self) -> list[tuple[str, str]]:
        return [
            ("hero", SECTION_DISPLAY_NAMES["hero"]),
            ("empathy", SECTION_DISPLAY_NAMES["empathy"]),
            ("solution", SECTION_DISPLAY_NAMES["solution"]),
            ("benefits", SECTION_DISPLAY_NAMES["benefits"]),
            ("how_to_use", SECTION_DISPLAY_NAMES["how_to_use"]),
            ("trust", SECTION_DISPLAY_NAMES["trust"]),
            ("cta", SECTION_DISPLAY_NAMES["cta"]),
        ]

    def _display_section_name(self, section_key: str, section_name: str) -> str:
        canonical = SECTION_DISPLAY_NAMES.get(section_key)
        if canonical:
            return canonical
        cleaned = re.sub(r"[_\-/]+", " ", (section_name or "").strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or section_key.replace("_", " ").strip() or "섹션"

    def _normalize_text_key(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
        return re.sub(r"[^0-9a-z가-힣]+", "", normalized)

    def _dedupe_text_items(self, items: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for item in items:
            text = self._clean_detail_copy_text(item)
            if not text:
                continue
            key = self._normalize_text_key(text)
            if not key or key in seen or self._is_noisy_copy_label(text):
                continue
            seen.add(key)
            deduped.append(text)
        return deduped

    def _clean_detail_copy_text(self, text: str) -> str:
        cleaned = str(text or "").replace("_x000D_", " ")
        cleaned = re.sub(r"\s+", " ", cleaned.strip(" -•\t\r\n"))
        cleaned = re.sub(r"(?i)\b본문\s*/\s*불릿\b", " ", cleaned)
        cleaned = re.sub(r"(?i)\b본문\s*불릿\b", " ", cleaned)
        cleaned = re.sub(r"(?i)\bPOINT\s*\d+\s*[\.:：]?\s*", " ", cleaned)
        cleaned = re.sub(r"체크\s*\d+\s*[\.:：]?\s*", " ", cleaned)
        cleaned = re.sub(r"(상품명\s*표기|상품\s*이미지\s*확인|이미지\s*확인)", " ", cleaned)
        cleaned = re.sub(r"(업로드(?:된)?\s*)?(상품\s*)?상세\s*이미지(에는|에| 기준으로| 기준|에는)?", " ", cleaned)
        cleaned = re.sub(r"(업로드(?:된)?\s*)?이미지\s*(기준으로|기준|표기|에는|에)", " ", cleaned)
        cleaned = re.sub(r"(문구\s*확인|이미지\s*표기|하단\s*표기|확인됩니다|표시됩니다)", " ", cleaned)
        cleaned = re.sub(r"\b(기준|표기)\s*[,，]?\s*", " ", cleaned)
        cleaned = re.sub(r"CTA\s*카피\s*", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(제목|메인 헤드라인|서브 카피|이미지 프롬프트|카피라이팅)\b\s*[:：]?", " ", cleaned)
        cleaned = re.sub(r"\s+([.!?])", r"\1", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -•\t")
        cleaned = cleaned.strip(" ,，、")
        cleaned = self._finish_detail_sentence_fragment(cleaned)
        return cleaned

    def _finish_detail_sentence_fragment(self, text: str) -> str:
        cleaned = str(text or "").strip()
        if not cleaned:
            return ""
        if re.search(r"[.!?。요다]\s*$", cleaned):
            return cleaned
        if cleaned.endswith("책과 파일을"):
            return f"{cleaned} 정리하세요."
        if cleaned.endswith("노트북과 필기 공간을"):
            return f"{cleaned} 확보하세요."
        if cleaned.endswith("자잘한 물건을"):
            return f"{cleaned} 서랍에 정리하세요."
        if cleaned.endswith("필요한 물건을 가까이에"):
            return f"{cleaned} 두세요."
        if cleaned.endswith("책은 쌓이고, 파일은 눕고"):
            return "책과 파일이 흩어지기 쉬운 공간을 정리하세요."
        if cleaned.endswith("냄비와 식재료가 늘고"):
            return "냄비와 식재료가 늘어나는 공간을 정리하세요."
        if cleaned.endswith("손 닿는 곳에") or cleaned.endswith("눈높이에"):
            return f"{cleaned} 두세요."
        if cleaned.endswith("서랍 안에"):
            return f"{cleaned} 보관하세요."
        if cleaned.endswith("펼쳐 쓰고"):
            return cleaned[:-1] + "세요."
        if cleaned.endswith("제작되며"):
            return cleaned[:-1] + "된 상품입니다."
        if cleaned.endswith("원목 냄새"):
            return f"{cleaned}가 느껴질 수 있습니다."
        if cleaned.endswith("작은 홈, 원목 냄새"):
            return f"{cleaned}가 보이거나 느껴질 수 있습니다."
        if cleaned.endswith("무게를 지탱하는"):
            return cleaned + " 구조입니다."
        if cleaned.endswith("위치를 바꿀 때"):
            return f"{cleaned} 편하게 이동하세요."
        if cleaned.endswith("정리할 때"):
            return f"{cleaned} 편하게 사용하세요."
        if cleaned.endswith("을") or cleaned.endswith("를"):
            return f"{cleaned} 정리하세요."
        if cleaned.endswith("에") or cleaned.endswith("에는"):
            return f"{cleaned} 두세요."
        if cleaned.endswith("까지") or cleaned.endswith("부터"):
            return f"{cleaned} 한 번에 정리하세요."
        if cleaned.endswith("고"):
            return cleaned + " 마무리하세요."
        return cleaned

    def _is_noisy_copy_label(self, text: str) -> bool:
        key = self._normalize_text_key(text)
        noisy_keys = {
            "본문",
            "불릿",
            "본문불릿",
            "본문포인트",
            "포인트",
            "핵심포인트",
            "이미지확인",
            "상품이미지확인",
        }
        return key in noisy_keys

    def _fallback_section_body(self, product: ProductRecord, section: SectionPlan) -> str:
        clean_facts = [
            fact
            for fact in product.facts
            if not any(marker in fact for marker in ("공급사", "리뷰", "평점", "배지", "상품 상세정보"))
        ]
        if section.section_key == "hero":
            parts = [product.category, product.price_text, product.options_text]
        elif section.section_key == "empathy":
            parts = [product.options_text, product.price_text, product.category]
        elif section.section_key == "solution":
            parts = [product.category, product.options_text, product.price_text]
        elif section.section_key == "benefits":
            parts = [product.options_text, *clean_facts[:2], product.price_text]
        elif section.section_key == "how_to_use":
            parts = [product.options_text, product.category, "구매 전 옵션과 상세 조건을 함께 확인하세요."]
        elif section.section_key == "trust":
            parts = [*clean_facts[:3], product.price_text, product.options_text]
        else:
            parts = [product.price_text, product.options_text, product.category]
        cleaned = self._dedupe_text_items([item for item in parts if item])
        if cleaned:
            return " / ".join(cleaned[:3])
        return "상품 페이지에서 확인한 정보를 바탕으로 정리한 안내 문구입니다."

    def _section_body_text(self, product: ProductRecord, section: SectionPlan, bullets: list[str]) -> str:
        body = self._clean_detail_copy_text(section.body)
        noisy_markers = (
            "OwnerC",
            "오너클랜",
            "상품 상세 이미지",
            "상세 이미지",
            "본문 옵션",
            "본문/불릿",
            "본문 / 불릿",
            "공급사",
            "리뷰",
            "평점",
            "배지",
            "방금 부족했던 답변",
            "이미지 생성은 하지 말고",
            "GPT 기획 시도",
            "원 요청",
        )
        if any(marker in body for marker in noisy_markers):
            return self._fallback_section_body(product, section)
        blocked = {
            self._normalize_text_key(section.headline),
            self._normalize_text_key(section.subheadline),
        }
        blocked.update(self._normalize_text_key(item) for item in bullets)
        body_key = self._normalize_text_key(body)
        if not body or not body_key or body_key in blocked:
            return self._fallback_section_body(product, section)
        body_sentences = self._dedupe_text_items(re.split(r"(?<=[.!?])\s+|\n+", body))
        if len(body_sentences) == 1 and len(set(blocked)) <= 2:
            return self._fallback_section_body(product, section)
        return " ".join(body_sentences[:3]).strip() or self._fallback_section_body(product, section)

    def _is_valid_image_file(self, path: Path) -> bool:
        if not path.exists() or path.stat().st_size <= 0:
            return False
        try:
            from PIL import Image

            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image.load()
            return True
        except Exception:
            return False

    def _is_valid_thumbnail_file(self, path: Path) -> bool:
        if not self._is_valid_image_file(path):
            return False
        try:
            from PIL import Image

            with Image.open(path) as image:
                return image.size == (1000, 1000)
        except Exception:
            return False

    def _image_average_hash(self, path: Path) -> int | None:
        try:
            from PIL import Image, ImageOps

            with Image.open(path) as image:
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                image = ImageOps.exif_transpose(image).convert("L").resize((8, 8), resample)
                pixels = list(image.getdata())
        except Exception:
            return None
        avg = sum(pixels) / max(1, len(pixels))
        value = 0
        for pixel in pixels:
            value = (value << 1) | (1 if pixel >= avg else 0)
        return value

    def _image_hash_distance(self, left: int | None, right: int | None) -> int:
        if left is None or right is None:
            return 64
        return int((left ^ right).bit_count())

    def _image_file_digest(self, path: Path) -> str:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def _thumbnail_files_are_visually_distinct(self, thumbnail_paths: list[Path]) -> bool:
        digests = [self._image_file_digest(path) for path in thumbnail_paths]
        if len(digests) != REQUIRED_THUMBNAIL_IMAGE_COUNT or any(not value for value in digests):
            return False
        return len(set(digests)) == len(digests)

    def _thumbnail_files_match_source_images(self, thumbnail_paths: list[Path], product_folder: Path) -> bool:
        for thumbnail_path in thumbnail_paths:
            if self._image_matches_reference_sources(thumbnail_path, product_folder):
                return True
        return False

    def _image_matches_reference_sources(self, image_path: Path, product_folder: Path, max_distance: int = 3) -> bool:
        if not self._is_valid_image_file(image_path):
            return True
        reference_dirs = [
            product_folder / "source_images",
            product_folder / "gpt_attachments",
        ]
        reference_paths: list[Path] = []
        for reference_dir in reference_dirs:
            if reference_dir.exists():
                reference_paths.extend(
                    path
                    for path in reference_dir.rglob("*")
                    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
                )
        if not reference_paths:
            return False
        reference_hashes = [
            value
            for value in (self._image_average_hash(path) for path in reference_paths)
            if value is not None
        ]
        if not reference_hashes:
            return False
        image_hash = self._image_average_hash(image_path)
        if image_hash is None:
            return True
        return any(self._image_hash_distance(image_hash, source_hash) <= max_distance for source_hash in reference_hashes)

    def _image_duplicates_existing_paths(self, image_path: Path, existing_paths: list[Path], max_distance: int = 2) -> bool:
        image_digest = self._image_file_digest(image_path)
        if not image_digest:
            return True
        for existing_path in existing_paths:
            if image_digest == self._image_file_digest(existing_path):
                return True
        return False

    def _image_duplicates_other_product_thumbnail(self, image_path: Path, current_product_dir: Path) -> bool:
        image_digest = self._image_file_digest(image_path)
        if not image_digest:
            return True
        try:
            current_dir = current_product_dir.resolve()
        except Exception:
            current_dir = current_product_dir
        search_roots = [OUTPUT_DIR, COMPLETED_DIR]
        for root in search_roots:
            if not root.exists():
                continue
            for folder in root.iterdir():
                if not folder.is_dir():
                    continue
                try:
                    if folder.resolve() == current_dir:
                        continue
                except Exception:
                    pass
                candidate_paths = list((folder / "thumbnails").glob("*.png"))
                candidate_paths.extend(folder.glob("[1-5].png"))
                for candidate_path in candidate_paths:
                    if not candidate_path.is_file():
                        continue
                    try:
                        if candidate_path.resolve() == image_path.resolve():
                            continue
                    except Exception:
                        pass
                    if image_digest == self._image_file_digest(candidate_path):
                        return True
        return False

    def _is_valid_generated_visual_file(self, path: Path) -> bool:
        if not self._is_valid_image_file(path):
            return False
        try:
            from PIL import Image

            with Image.open(path) as image:
                width, height = image.size
            return width >= 700 and height >= 700
        except Exception:
            return False

    def _download_image_with_headers(self, src: str, target: Path, referer: str) -> None:
        request = urllib.request.Request(
            src,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": referer or "https://ownerclan.com/",
            },
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            target.write_bytes(response.read())

    def _expand_product_detail_area(self, page) -> None:
        for selector in ("#lBtnItemContentsMore", "#lBtnItemContentsMoreText"):
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    locator.first.scroll_into_view_if_needed(timeout=2500)
                    locator.first.click(timeout=3500)
                    page.wait_for_timeout(1800)
                    break
            except Exception:
                continue
        for label in ("상품상세 더보기", "상세정보 펼쳐보기", "제품 상세 설명", "제품 상세", "상세 설명"):
            try:
                locator = page.get_by_text(label, exact=False)
                if locator.count() > 0:
                    locator.first.click(timeout=2500)
                    page.wait_for_timeout(1200)
            except Exception:
                continue
        try:
            page.evaluate(
                """async () => {
                    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
                    const total = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
                    const steps = 8;
                    for (let i = 0; i <= steps; i += 1) {
                        window.scrollTo(0, Math.round(total * i / steps));
                        await sleep(450);
                    }
                    window.scrollTo(0, 0);
                    await sleep(500);
                }"""
            )
        except Exception:
            pass

    def _ensure_source_image_variety(self, source_dir: Path, source_image_paths: list[Path], run_stamp: str) -> list[Path]:
        from PIL import Image, ImageOps

        valid_paths = [path for path in source_image_paths if self._is_valid_image_file(path)]
        if len(valid_paths) >= MIN_SOURCE_IMAGE_COUNT:
            return valid_paths

        derivative_index = 1
        capture_paths = [path for path in valid_paths if "page_capture" in path.name.lower()]
        for capture_path in capture_paths:
            try:
                with Image.open(capture_path) as image:
                    capture = ImageOps.exif_transpose(image).convert("RGB")
            except Exception:
                continue
            width, height = capture.size
            if width < 700 or height < 12000:
                continue
            crop_w = max(620, min(width, int(width * 0.62)))
            crop_h = max(720, min(height, int(height * 0.16)))
            center_x = width * 0.50
            left = int(max(0, min(width - crop_w, center_x - crop_w / 2)))
            for ratio in (0.43, 0.55, 0.67, 0.79, 0.88):
                if len(valid_paths) >= MIN_SOURCE_IMAGE_COUNT:
                    break
                top = int(max(0, min(height - crop_h, height * ratio)))
                cropped = capture.crop((left, top, left + crop_w, top + crop_h))
                target = source_dir / f"source_{run_stamp}_capture_derived_{derivative_index:02d}.jpg"
                derivative_index += 1
                try:
                    cropped.save(target, "JPEG", quality=93, optimize=True)
                    if self._is_valid_image_file(target):
                        valid_paths.append(target)
                except Exception:
                    continue
            if len(valid_paths) >= MIN_SOURCE_IMAGE_COUNT:
                return valid_paths

        base_paths: list[Path] = []
        for path in valid_paths:
            if "page_capture" not in path.name.lower():
                base_paths.append(path)
        if not base_paths:
            base_paths = valid_paths[:1]

        crop_specs = [
            (0.50, 0.50, 0.82, 0.82),
            (0.34, 0.50, 0.66, 0.82),
            (0.66, 0.50, 0.66, 0.82),
            (0.50, 0.34, 0.82, 0.66),
            (0.50, 0.66, 0.82, 0.66),
            (0.50, 0.50, 0.58, 0.58),
        ]
        for base_path in base_paths:
            try:
                with Image.open(base_path) as image:
                    source = ImageOps.exif_transpose(image).convert("RGB")
            except Exception:
                continue
            width, height = source.size
            if width < 300 or height < 300:
                continue
            for cx, cy, rw, rh in crop_specs:
                if len(valid_paths) >= MIN_SOURCE_IMAGE_COUNT:
                    return valid_paths
                crop_w = max(260, min(width, int(width * rw)))
                crop_h = max(260, min(height, int(height * rh)))
                left = int(max(0, min(width - crop_w, width * cx - crop_w / 2)))
                top = int(max(0, min(height - crop_h, height * cy - crop_h / 2)))
                cropped = source.crop((left, top, left + crop_w, top + crop_h))
                target = source_dir / f"source_{run_stamp}_derived_{derivative_index:02d}.jpg"
                derivative_index += 1
                try:
                    cropped.save(target, "JPEG", quality=93, optimize=True)
                    if self._is_valid_image_file(target):
                        valid_paths.append(target)
                except Exception:
                    continue
        return valid_paths

    def _extract_detail_image_urls(self, page_html: str, page_url: str) -> list[str]:
        if not page_html:
            return []
        raw_urls: list[str] = []
        patterns = (
            r"https?:\\?/\\?/[^'\"<>\s)]+?\.(?:jpg|jpeg|png|webp)",
            r"//[^'\"<>\s)]+?\.(?:jpg|jpeg|png|webp)",
            r"https?:\\?/\\?/[^'\"<>\s)]+?/upload/item/[^'\"<>\s)]+(?:\?hash=[^'\"<>\s)]*)?",
            r"//[^'\"<>\s)]+?/upload/item/[^'\"<>\s)]+(?:\?hash=[^'\"<>\s)]*)?",
        )
        for pattern in patterns:
            raw_urls.extend(re.findall(pattern, page_html, flags=re.IGNORECASE))

        detail_urls: list[str] = []
        seen_keys: set[str] = set()
        for raw in raw_urls:
            cleaned = html.unescape(raw).replace("\\/", "/").strip()
            cleaned = urllib.parse.unquote(cleaned)
            cleaned = cleaned.rstrip("\\\"' ),;")
            if cleaned.startswith("//"):
                cleaned = "https:" + cleaned
            cleaned = urllib.parse.urljoin(page_url, cleaned)
            lower = cleaned.lower()
            if self._is_ownerclan_ui_image_src(lower):
                continue
            if not any(
                host in lower
                for host in (
                    "speedgabia.com",
                    "image.ownerclan.com/external",
                    "ownerclan.com",
                    "domeggook.com/upload/item",
                    "domeggook.com/upload/editor",
                    "hgodo.com",
                )
            ):
                continue
            if any(
                marker in lower
                for marker in (
                    "recommend",
                    "popular",
                    "banner",
                    "review",
                    "membership",
                    "icon",
                    "logo",
                    "notice",
                    "delivery",
                    "return",
                    "cscenter",
                )
            ):
                continue
            parsed_path = urllib.parse.urlparse(cleaned).path
            ext = Path(parsed_path).suffix.lower()
            is_domeggook_item_image = (
                "domeggook.com/upload/item" in lower
                and not re.search(r"_stt_(?:150|330)(?:\.|$)", Path(parsed_path).name.lower(), flags=re.IGNORECASE)
                and not any(
                    marker in lower
                    for marker in (
                        "recommend",
                        "popular",
                        "banner",
                        "review",
                        "membership",
                        "icon",
                        "logo",
                        "notice",
                        "delivery",
                        "return",
                        "cscenter",
                    )
                )
            )
            if ext not in {".jpg", ".jpeg", ".png", ".webp"} and not is_domeggook_item_image:
                continue
            filename_key = Path(parsed_path).name.lower()
            if re.search(r"_stt_(?:150|330)\.(?:jpg|jpeg|png|webp)$", filename_key, flags=re.IGNORECASE):
                continue
            if not filename_key or filename_key in seen_keys:
                continue
            seen_keys.add(filename_key)
            detail_urls.append(cleaned)
        return detail_urls

    def _is_product_detail_image_candidate(self, record: dict[str, str | int]) -> bool:
        src = str(record.get("src") or "")
        src_lower = src.lower()
        chain = str(record.get("parent_chain") or "").lower()
        if self._is_ownerclan_ui_image_src(src):
            return False
        if self._looks_like_recommendation_image(record):
            return False
        detail_markers = (
            "linfoviewitemcontents",
            "itemcontents",
            "item_contents",
            "product_detail",
            "detail",
            "contents",
            "editor",
        )
        if not any(marker in chain or marker in src_lower for marker in detail_markers):
            return False
        if any(marker in src_lower for marker in ("notice", "delivery", "return", "cscenter", "membership", "banner", "logo")):
            return False
        width = int(record.get("width") or 0)
        height = int(record.get("height") or 0)
        client_width = int(record.get("client_width") or 0)
        client_height = int(record.get("client_height") or 0)
        if max(width, client_width) < 500 or max(height, client_height) < 300:
            return False
        if not any(
            host in src_lower
            for host in (
                "ownerclan.com",
                "domeggook.com",
                "speedgabia.com",
                "hgodo.com",
                "shop-phinf.pstatic.net",
            )
        ):
            return False
        return True

    def _is_ownerclan_ui_image_src(self, src: str) -> bool:
        src_lower = src.lower()
        ui_markers = (
            "/data/banner/",
            "/_skin/",
            "productalert",
            "detail_delivery",
            "delivery",
            "review_operating_rules",
            "membership_btn",
            "iconballoonproduct",
        )
        return any(marker in src_lower for marker in ui_markers)

    def _is_product_thumbnail_candidate(self, record: dict[str, str | int]) -> bool:
        src = str(record.get("src") or "")
        chain = str(record.get("parent_chain") or "").lower()
        width = int(record.get("width") or 0)
        height = int(record.get("height") or 0)
        client_width = int(record.get("client_width") or 0)
        client_height = int(record.get("client_height") or 0)
        top = int(record.get("top") or 0)
        if self._is_ownerclan_ui_image_src(src):
            return False
        if self._looks_like_recommendation_image(record):
            return False
        if "detail_box5" in chain or "popular" in chain or "recommend" in chain:
            return False
        if not any(
            host in src.lower()
            for host in (
                "cdn.ownerclan.com",
                "image.ownerclan.com",
                "speedgabia.com",
                "domeggook.com/upload/item",
            )
        ):
            return False
        if width < 320 or height < 320:
            return False
        if height / max(1, width) > 1.8:
            return False
        if top > 1800 and "showimage" not in chain and "product_information" not in chain:
            return False
        visible_area = client_width * client_height
        if visible_area == 0 and "showimage" not in chain and top > 0:
            return False
        return True

    def _looks_like_recommendation_image(self, record: dict[str, str | int]) -> bool:
        chain = str(record.get("parent_chain") or "").lower()
        src = str(record.get("src") or "").lower()
        if any(marker in chain for marker in ("detail_box5", "recommend", "popular", "list", "product_container")):
            return True
        if "detail_box5" in src or "recommend" in src:
            return True
        top = int(record.get("top") or 0)
        client_width = int(record.get("client_width") or 0)
        client_height = int(record.get("client_height") or 0)
        return top > 1100 and client_width <= 360 and client_height <= 360

    def _is_primary_product_image_candidate(self, record: dict[str, str | int]) -> bool:
        src = str(record.get("src") or "")
        src_lower = src.lower()
        chain = str(record.get("parent_chain") or "").lower()
        if self._is_ownerclan_ui_image_src(src):
            return False
        if self._looks_like_recommendation_image(record):
            return False
        width = int(record.get("width") or 0)
        height = int(record.get("height") or 0)
        client_width = int(record.get("client_width") or 0)
        client_height = int(record.get("client_height") or 0)
        top = int(record.get("top") or 0)
        if "lthumb" in chain or "mainthumb" in chain:
            return width >= 300 and height >= 300 and max(client_width, client_height) >= 300 and top < 1400
        if "/marketize/" not in src_lower:
            return False
        return width >= 300 and height >= 300 and client_width >= 300 and client_height >= 300 and top < 1100

    def _extract_json_payload(self, result_text: str) -> dict:
        fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)```", result_text, flags=re.DOTALL | re.IGNORECASE)
        for block in fenced_blocks:
            candidate = block.strip()
            if not candidate.startswith("{"):
                continue
            try:
                loaded = json.loads(candidate)
                if isinstance(loaded, dict):
                    return loaded
            except json.JSONDecodeError:
                continue

        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", result_text):
            try:
                loaded, _ = decoder.raw_decode(result_text[match.start() :])
                if isinstance(loaded, dict):
                    return loaded
            except json.JSONDecodeError:
                continue
        return {}

    def _gpt_text_is_non_result_noise(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return True
        lowered = normalized.lower()
        noise_exact = {
            "displaying contact sheet image",
            "displaying image",
            "image generated",
            "download image",
        }
        if lowered in noise_exact:
            return True
        if lowered.startswith("displaying ") and " image" in lowered and len(normalized) < 120:
            return True
        return False

    def _is_chatgpt_image_wait_text(self, text: str) -> bool:
        return any(
            marker in (text or "")
            for marker in (
                "더욱 자세한 이미지를 생성",
                "이미지를 생성하고",
                "잠시만 기다려",
                "마지막으로 다듬는 중",
                "마지막으로 다듬",
                "다듬는 중",
                "finalizing",
                "finishing",
            )
        )

    def _latest_gpt_text(self, page) -> tuple[str, bool]:
        text = ""
        fallback_text = ""
        for selector in (
            "[data-message-author-role='assistant']",
            "[data-testid^='conversation-turn-'] .markdown",
            "[data-testid^='conversation-turn-']",
            ".markdown",
        ):
            locator = page.locator(selector)
            try:
                count = locator.count()
                if count > 0:
                    for index in range(count - 1, -1, -1):
                        candidate = locator.nth(index).inner_text(timeout=10000).strip()
                        if candidate and not fallback_text:
                            fallback_text = candidate
                        if candidate and not self._gpt_text_is_non_result_noise(candidate):
                            text = candidate
                            break
                    if text:
                        break
            except Exception:
                continue
        if not text:
            text = fallback_text

        if self._is_chatgpt_image_generation_error_text(text):
            return text, False
        has_stopped_marker = any(marker in text for marker in ("생각 중지됨", "Thinking stopped", "응답이 중지됨"))

        latest_text_busy = any(
            marker in text
            for marker in (
                "Pro 생각 중",
                "스트리밍 중지",
                "생각 중",
                "답변 마무리 중",
                "문서 읽는 중",
                "검색 중",
                "자료 확인 중",
                "내 지식 검색 중",
                "지식 검색 중",
                "Thinking",
                "Generating",
                "Reading",
                "Searching",
                "Requesting image from URL",
                "이미지 요청 중",
                "이미지 생성 중",
                "이미지를 생성하고",
                "잠시만 기다려",
                "마지막으로 다듬는 중",
                "다듬는 중",
            )
        )
        stop_button_busy = False
        for label in ("스트리밍 중지", "답변 중지", "Stop streaming", "Stop generating"):
            for selector in (f"button:has-text('{label}')", f"[role='button']:has-text('{label}')"):
                try:
                    locator = page.locator(selector)
                    if locator.count() > 0 and locator.last.is_visible(timeout=500):
                        stop_button_busy = True
                        break
                except Exception:
                    continue
            if stop_button_busy:
                break
        dom_busy = False
        try:
            dom_busy = bool(
                page.evaluate(
                    """() => {
                        const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                        const textOf = (el) => [
                            el.innerText || "",
                            el.textContent || "",
                            el.getAttribute("aria-label") || "",
                            el.getAttribute("title") || ""
                        ].join(" ").replace(/\\s+/g, " ").trim();
                        const nodes = Array.from(document.querySelectorAll("button,[role='button'],[aria-live],main"));
                        const text = nodes.filter(visible).map(textOf).join("\\n");
                        return /답변 마무리 중|스트리밍 중지|답변 중지|Pro 생각 중|Stop streaming|Stop generating/i.test(text);
                    }"""
                )
            )
        except Exception:
            dom_busy = False
        image_wait_text = self._is_chatgpt_image_wait_text(text)
        text_busy = latest_text_busy and not has_stopped_marker
        if image_wait_text and not stop_button_busy:
            text_busy = False
        return text, stop_button_busy or dom_busy or text_busy

    def _wait_for_gpt_idle(self, page, timeout_seconds: int = 1800) -> None:
        deadline = time.time() + timeout_seconds
        stopped_markers = ("생각 중지됨", "Thinking stopped", "응답이 중지됨")
        while time.time() < deadline:
            self._raise_if_user_requested_stop_or_skip()
            text, busy = self._latest_gpt_text(page)
            if text and any(marker in text for marker in stopped_markers):
                return
            if not busy:
                return
            page.wait_for_timeout(5000)
        raise RuntimeError("ChatGPT 이전 답변 생성이 끝나지 않아 다음 URL을 보낼 수 없습니다.")

    def _wait_for_gpt_result(self, page, previous_text: str = "", timeout_seconds: int = 900) -> str:
        last_text = ""
        last_busy = False
        stable_count = 0
        started_at = time.time()
        deadline = time.time() + timeout_seconds
        previous_text = previous_text.strip()
        stopped_markers = ("생각 중지됨", "Thinking stopped", "응답이 중지됨")
        transient_send_retries = 0
        while time.time() < deadline:
            self._raise_if_user_requested_stop_or_skip()
            page.wait_for_timeout(2500)
            text, busy = self._latest_gpt_text(page)
            if text and text == last_text:
                stable_count += 1
            else:
                stable_count = 0
                last_text = text
            last_busy = busy
            elapsed = time.time() - started_at
            if self._is_chatgpt_transient_send_error_text(text):
                if elapsed < CHATGPT_RETRY_GRACE_SECONDS:
                    continue
                if transient_send_retries < 3 and self._click_chatgpt_retry_button(page, timeout_ms=8000):
                    transient_send_retries += 1
                    page.wait_for_timeout(5000)
                    stable_count = 0
                    last_text = ""
                    continue
                raise RuntimeError(f"GPT 전송 시간초과: {self._compact_error_text(text)}")
            if elapsed >= CHATGPT_RETRY_GRACE_SECONDS and self._is_chatgpt_stream_stalled_text(text):
                if self._gpt_text_has_completed_structured_plan(text):
                    return text
                continue
            if text and any(marker in text for marker in stopped_markers):
                if previous_text and text == previous_text and elapsed < 30:
                    continue
                raise RuntimeError("GPT 응답 대기 제한: 답변 생성이 중지됐습니다.")
            if previous_text and text == previous_text:
                continue
            if text and re.fullmatch(r"https?://\S+", text.strip()):
                continue
            if text and self._gpt_text_is_non_result_noise(text):
                continue
            if text and self._gpt_text_is_incomplete_state(text) and not self._gpt_text_has_structured_section_headings(text):
                continue
            if text and self._gpt_text_has_structured_section_headings(text) and not self._gpt_text_has_completed_structured_plan(text):
                continue
            if (
                text
                and stable_count >= 3
                and self._gpt_text_has_completed_structured_plan(text)
            ):
                return text
            if text and stable_count >= 3 and not busy:
                if self._gpt_text_has_section_plan_signal(text) or (elapsed >= CHATGPT_RETRY_GRACE_SECONDS and len(text) >= 600):
                    return text
                if elapsed >= CHATGPT_RETRY_GRACE_SECONDS and len(text.strip()) >= 40:
                    return text
        if (
            last_text
            and not re.fullmatch(r"https?://\S+", last_text.strip())
            and not self._gpt_text_is_non_result_noise(last_text)
            and (not self._gpt_text_is_incomplete_state(last_text) or self._gpt_text_has_structured_section_headings(last_text))
            and (self._gpt_text_has_section_plan_signal(last_text) or len(last_text) >= 600)
        ):
            return last_text
        raise RuntimeError("GPT 응답이 아직 생성 중이라 제한 시간 안에 최종 답변을 확인하지 못했습니다.")

    def _stop_chatgpt_generation(self, page) -> bool:
        stopped = False
        for label in ("스트리밍 중지", "답변 중지", "Stop streaming", "Stop generating", "생성 중지"):
            for selector in (f"button:has-text('{label}')", f"[role='button']:has-text('{label}')"):
                try:
                    locator = page.locator(selector)
                    if locator.count() > 0 and locator.last.is_visible(timeout=500):
                        locator.last.click(timeout=1500)
                        page.wait_for_timeout(1500)
                        stopped = True
                        return stopped
                except Exception:
                    continue
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
        except Exception:
            pass
        return stopped

    def _set_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def _set_login_panel_status(self, message: str) -> None:
        self.login_status_label.setText(message)
        self.statusBar().showMessage(message)

    def _set_task_status(self, index: int, status: str) -> None:
        if 0 <= index < len(self.link_tasks):
            self.link_tasks[index].status = status
            self.current_link_index = index
            self.current_product_url = self.link_tasks[index].url
            self._refresh_link_table()
            self._refresh_prompt()
            self._save_config()

    def _append_result_text(self, text: str) -> None:
        current = self.result_box.toPlainText().strip()
        self.result_box.setPlainText((current + "\n\n" + text).strip() if current else text.strip())

    def _automation_finished(self) -> None:
        self.automation_running = False
        self.automation_stop_requested = False
        self.automation_skip_requested = False
        self.active_manual_resume_request = None

    def _login_finished(self) -> None:
        self.login_running = False

    def _brief(self) -> ProductBrief:
        return ProductBrief(
            product_name=self._field_text("product_name"),
            category=self._field_text("category"),
            platform=self._field_text("platform"),
            target_customer=self._field_text("target_customer"),
            price_range=self._field_text("price_range"),
            tone=self._field_text("tone"),
            product_url=self._field_text("product_url") or self.current_product_url,
            key_features=self._field_text("key_features"),
            proof_points=self._field_text("proof_points"),
            differentiation=self._field_text("differentiation"),
            usage_context=self._field_text("usage_context"),
            caution=self._field_text("caution"),
            image_paths=self._field_text("image_paths"),
            reference_notes=self._field_text("reference_notes"),
        )

    def _build_prompt(self) -> str:
        brief = self._brief()
        product_name = brief.product_name or "[URL에서 상품명 확인]"
        caution = brief.caution or "검증 불가능한 효능, 최저가/1위/완치 같은 과장 표현은 쓰지 말 것."
        current_status = ""
        if self.current_link_index >= 0 and self.current_link_index < len(self.link_tasks):
            current_status = f"작업 순서: {self.current_link_index + 1} / {len(self.link_tasks)}"
        url_line = brief.product_url or "[엑셀 URL을 먼저 여세요]"

        return f"""[{GPT_NAME} 작업 요청]
공개 확인된 GPT 설명: {GPT_PUBLIC_DESCRIPTION}
공개 확인된 시작 문구 참고: {", ".join(GPT_PROMPT_STARTERS)}

아래 상품 URL에 들어가서 상품명, 이미지, 옵션, 스펙, 상세 설명을 확인한 뒤 쇼핑몰 상세페이지 기획안을 만들어주세요.
{current_status}

상품명: {product_name}
상품 URL: {url_line}

금지/주의 표현:
{caution}

작업 기준:
1. URL 페이지에서 확인 가능한 상품 정보만 근거로 사용
2. 확인 안 되는 수치, 인증, 효능, 순위, 후기 내용은 단정하지 않기
3. 상품 페이지에서 부족한 정보가 있으면 "확인 필요"로 표시
4. 상세페이지 제작자가 바로 이미지/카피 작업할 수 있게 섹션별로 정리

반드시 아래 형식으로 출력해주세요.
1. 히어로 훅 5안
2. 섹션 1~10까지 정확히 10개 섹션
3. 각 섹션마다 자동화용 section_key를 영문 snake_case로 병기
4. 각 섹션마다 목적, 메인 카피, 서브 카피, 본문, 이미지 생성 프롬프트를 포함
5. 이미지 생성 프롬프트는 한글로 작성하고, 제품 위치/배경/조명/분위기/텍스트 여백을 명시
6. 특징은 기능 설명에서 끝내지 말고 고객 혜택으로 바꿔 설명
7. 확인 안 된 수치, 인증, 효능은 단정하지 말고 보수적으로 작성
8. 마지막에 자동화 파싱용 JSON을 code block으로 추가

JSON 스키마:
{{
  "product_name": "{product_name}",
  "hero_hooks": ["..."],
  "sections": [
    {{
      "section_key": "hero",
      "section_name": "히어로",
      "goal": "...",
      "headline": "...",
      "subcopy": "...",
      "body": "...",
      "image_prompt_ko": "...",
      "production_note": "..."
    }}
  ]
}}
"""

    def _refresh_prompt(self) -> None:
        if not hasattr(self, "prompt_box"):
            return
        self.prompt_box.blockSignals(True)
        self.prompt_box.setPlainText(self._build_prompt())
        cursor = self.prompt_box.textCursor()
        cursor.setPosition(0)
        self.prompt_box.setTextCursor(cursor)
        self.prompt_box.blockSignals(False)
        self.statusBar().showMessage("현재 URL 갱신됨")

    def _open_gpt(self) -> None:
        self._open_url_in_automation_browser(GPT_URL, "자동화 브라우저에서 GPT 링크를 열었습니다.")

    def _copy_gpt_url(self) -> None:
        QApplication.clipboard().setText(GPT_URL)
        self.statusBar().showMessage("GPT 링크를 클립보드에 복사했습니다.")

    def _copy_prompt(self) -> None:
        self._refresh_prompt()
        QApplication.clipboard().setText(self.prompt_box.toPlainText())
        self.statusBar().showMessage("프롬프트를 클립보드에 복사했습니다.")

    def _save_result(self) -> None:
        text = self.result_box.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "저장 불가", "저장할 GPT 결과가 비어 있습니다.")
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        product = slugify(self._field_text("product_name"))
        path = OUTPUT_DIR / f"{product}_{now_stamp()}.md"

        content = (
            f"# {self._field_text('product_name') or '상세페이지 결과'}\n\n"
            f"- GPT: {GPT_NAME}\n"
            f"- GPT URL: {GPT_URL}\n"
            f"- 저장 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "## 입력 프롬프트\n\n"
            "```text\n"
            f"{self.prompt_box.toPlainText().strip()}\n"
            "```\n\n"
            "## GPT 결과\n\n"
            f"{text}\n"
        )
        path.write_text(content, encoding="utf-8")
        self.statusBar().showMessage(f"결과 저장 완료: {path}")
        QMessageBox.information(self, "저장 완료", f"결과를 저장했습니다.\n\n{path}")

    def _field_text(self, key: str) -> str:
        if key == "product_url" and key not in self.fields:
            return self.current_product_url.strip()
        field = self.fields.get(key)
        if isinstance(field, QLineEdit):
            return field.text().strip()
        if isinstance(field, QTextEdit):
            return field.toPlainText().strip()
        if isinstance(field, QComboBox):
            return field.currentText().strip()
        return ""

    def _set_field_text(self, key: str, value: str) -> None:
        if key == "product_url":
            self.current_product_url = value.strip()
        field = self.fields.get(key)
        if isinstance(field, QLineEdit):
            field.setText(value)
        elif isinstance(field, QTextEdit):
            field.setPlainText(value)
        elif isinstance(field, QComboBox):
            index = field.findText(value)
            if index >= 0:
                field.setCurrentIndex(index)

    def _data(self) -> dict[str, object]:
        data = {key: self._field_text(key) for key in self.fields}
        data["_chatgpt_email"] = self.login_email_field.text().strip()
        data["_theme"] = self.theme
        data["_excel_path"] = str(self.excel_path or "")
        data["_brand_logo_path"] = str(getattr(self, "brand_logo_path", "") or "")
        data["_current_link_index"] = str(self.current_link_index)
        data["_current_product_url"] = self.current_product_url
        data["_market_settings"] = self._market_settings_for_config()
        data["_link_tasks"] = [
            {
                "row_number": task.row_number,
                "url": task.url,
                "secondary_url": task.secondary_url,
                "status": task.status,
            }
            for task in self.link_tasks
        ]
        return data

    def _write_config_file(self, save_secrets: bool = True) -> None:
        if save_secrets:
            self._save_market_secrets_to_keyring(show_message=False)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(self._data(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_config(self) -> None:
        self._write_config_file()
        self.statusBar().showMessage(f"입력 저장 완료: {CONFIG_PATH}")

    def _migrate_legacy_config_file(self) -> None:
        if CONFIG_PATH.exists():
            return
        candidates = [
            ROOT_DIR / "detail_page_gui_config.json",
            ROOT_DIR.parent / "detail_page_gui_config.json",
            ROOT_DIR.parent.parent / "detail_page_gui_config.json",
            ROOT_DIR.parent.parent / "상세페이지 자동화 GUI" / "detail_page_gui_config.json",
            Path.cwd() / "detail_page_gui_config.json",
            Path.cwd().parent / "detail_page_gui_config.json",
            Path.cwd().parent.parent / "detail_page_gui_config.json",
            Path.cwd().parent.parent / "상세페이지 자동화 GUI" / "detail_page_gui_config.json",
        ]
        seen: set[Path] = set()
        readable: list[tuple[float, dict[str, object]]] = []
        for path in candidates:
            path = path.resolve()
            if path in seen or path == CONFIG_PATH or not path.exists():
                continue
            seen.add(path)
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                mtime = path.stat().st_mtime
            except Exception:
                continue
            if isinstance(data, dict):
                readable.append((mtime, data))
        if not readable:
            return
        readable.sort(key=lambda item: item[0])
        merged_market_settings: dict[str, str] = {}
        for _, data in readable:
            market_settings = data.get("_market_settings", {})
            if not isinstance(market_settings, dict):
                continue
            for key, value in market_settings.items():
                cleaned = str(value or "").strip()
                if cleaned and not self._is_auto_lookup_value(cleaned):
                    merged_market_settings[str(key)] = cleaned
        migrated = dict(readable[-1][1])
        migrated["_market_settings"] = merged_market_settings
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(migrated, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_config(self, silent: bool = False) -> None:
        self._migrate_legacy_config_file()
        if not CONFIG_PATH.exists():
            if not silent:
                QMessageBox.information(self, "불러오기", "저장된 입력값이 아직 없습니다.")
            return
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            QMessageBox.warning(self, "불러오기 실패", f"설정 파일을 읽지 못했습니다.\n{exc}")
            return
        theme = str(data.get("_theme", self.theme)).lower()
        if theme in {"dark", "light"}:
            self.theme = theme
        self.excel_path = str(data.get("_excel_path", ""))
        self.brand_logo_path = str(data.get("_brand_logo_path", "")).strip()
        try:
            self.current_link_index = int(data.get("_current_link_index", -1))
        except (TypeError, ValueError):
            self.current_link_index = -1
        self.current_product_url = str(
            data.get("_current_product_url", data.get("product_url", ""))
        ).strip()
        chatgpt_email = str(data.get("_chatgpt_email", "")).strip()
        self.login_email_field.setText(chatgpt_email)
        market_settings = data.get("_market_settings", {})
        if isinstance(market_settings, dict):
            for key, value in market_settings.items():
                if key in self.market_fields and key not in self.market_secret_keys:
                    self._set_market_field_text(key, str(value))
                elif key not in self.market_secret_keys and str(value or "").strip() and not self._is_auto_lookup_value(value):
                    self.market_resolved_settings[key] = str(value).strip()
        self._load_market_secrets_from_keyring()
        self._apply_market_default_values()
        task_data = data.get("_link_tasks", [])
        if isinstance(task_data, list):
            self.link_tasks = []
            for raw in task_data:
                if not isinstance(raw, dict):
                    continue
                url = str(raw.get("url", "")).strip()
                if not self._is_url(url):
                    continue
                try:
                    row_number = int(raw.get("row_number", 0))
                except (TypeError, ValueError):
                    row_number = 0
                status = self._normalize_loaded_task_status(raw.get("status", "대기"))
                secondary_url = str(raw.get("secondary_url", "")).strip()
                if not self._is_url(secondary_url):
                    secondary_url = ""
                self.link_tasks.append(
                    LinkTask(row_number=row_number, url=url, secondary_url=secondary_url, status=status)
                )
        for key, value in data.items():
            if key.startswith("_"):
                continue
            self._set_field_text(key, str(value))
        self._ensure_output_dirs()
        fast_startup = bool(silent and getattr(self, "_startup_fast_load", False))
        reconciled = False if fast_startup else self._reconcile_link_task_statuses()
        self._apply_style()
        self._refresh_link_table(validate_outputs=not fast_startup)
        self._refresh_prompt()
        self._sync_brand_logo_status_label()
        self.market_settings_status_label.setText("마켓 설정 저장됨")
        if reconciled:
            self._write_config_file()
        if not silent:
            message = "입력값을 불러왔습니다."
            if reconciled:
                message += " 실제 결과 파일이 없는 완료/진행 항목은 대기로 되돌렸습니다."
            self.statusBar().showMessage(message)

    def _toggle_theme(self) -> None:
        self.theme = "light" if self.theme == "dark" else "dark"
        self._apply_style()
        self._save_config()
        self.statusBar().showMessage(
            "라이트 모드로 전환했습니다." if self.theme == "light" else "다크 모드로 전환했습니다."
        )

    def _sync_theme_controls(self) -> None:
        if self.theme_btn is not None:
            self.theme_btn.setText("라이트 모드" if self.theme == "dark" else "다크 모드")
        if self.theme_action is not None:
            self.theme_action.setText(
                "라이트 모드로 전환" if self.theme == "dark" else "다크 모드로 전환"
            )

    def _apply_style(self) -> None:
        QApplication.instance().setFont(QFont("Malgun Gothic", 10))
        dark = self.theme == "dark"
        colors = {
            "bg": "#0B1017" if dark else "#F4F7FB",
            "surface": "#111821" if dark else "#FFFFFF",
            "surface_alt": "#182231" if dark else "#EDF2F7",
            "input_bg": "#121B27" if dark else "#FFFFFF",
            "selected": "#203A62" if dark else "#E8F0FF",
            "text": "#F5F7FA" if dark else "#111827",
            "secondary": "#C8D1DC" if dark else "#475467",
            "muted": "#AAB6C5" if dark else "#667085",
            "border": "#2E3B4D" if dark else "#D0D7E2",
            "border_strong": "#506176" if dark else "#98A2B3",
            "accent": "#6EA8FF" if dark else "#1463FF",
            "accent_hover": "#93BDFF" if dark else "#0F52D6",
            "button_text": "#F5F7FA" if dark else "#111827",
            "primary_text": "#0E1116" if dark else "#FFFFFF",
            "scroll_handle": "#506176" if dark else "#98A2B3",
        }
        self._sync_theme_controls()
        self.setStyleSheet(
            """
            QMainWindow {{
                background: {bg};
                color: {text};
                font-family: "Malgun Gothic", "Segoe UI";
            }}
            QMenuBar {{
                background: {bg};
                color: {text};
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                padding: 4px 8px;
            }}
            QMenuBar::item:selected {{
                background: {surface_alt};
                border-radius: 6px;
            }}
            QMenu {{
                background: {surface};
                color: {text};
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                border: 1px solid {border};
            }}
            QMenu::item:selected {{
                background: {selected};
            }}
            QFrame#Header, QFrame#Panel {{
                background: {surface};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QLabel {{
                color: {text};
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#Title {{
                font-size: 24px;
                font-weight: 700;
                color: {text};
            }}
            QLabel#Subtitle {{
                font-size: 13px;
                color: {secondary};
            }}
            QLabel#Evidence {{
                font-size: 12px;
                color: {muted};
                font-weight: 500;
            }}
            QLabel#LoginStatus {{
                font-size: 12px;
                color: {secondary};
                font-weight: 500;
            }}
            QLabel#SectionTitle {{
                font-size: 16px;
                font-weight: 700;
                color: {text};
            }}
            QLabel#PreviewImage {{
                background: {input_bg};
                border: 1px solid {border};
                border-radius: 10px;
                color: {muted};
                font-size: 12px;
                font-weight: 500;
                padding: 10px;
            }}
            QTabWidget::pane {{
                border: 0;
                padding-top: 8px;
            }}
            QTabBar::tab {{
                min-height: 32px;
                padding: 6px 18px;
                margin-right: 6px;
                border: 1px solid {border};
                border-radius: 8px;
                background: {surface_alt};
                color: {secondary};
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                font-weight: 700;
            }}
            QTabBar::tab:selected {{
                background: {selected};
                color: {text};
                border-color: {accent};
            }}
            QLineEdit, QComboBox {{
                min-height: 38px;
                background: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 0 12px;
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                selection-background-color: {accent};
                selection-color: {primary_text};
            }}
            QTextEdit {{
                background: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 10px 12px;
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                selection-background-color: {accent};
                selection-color: {primary_text};
            }}
            QLineEdit::placeholder, QTextEdit::placeholder {{
                color: {muted};
            }}
            QComboBox QAbstractItemView {{
                background: {surface};
                color: {text};
                border: 1px solid {border};
                selection-background-color: {selected};
            }}
            QTextEdit#TextArea {{
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid {accent};
            }}
            QPushButton {{
                min-height: 38px;
                padding: 0 14px;
                border-radius: 8px;
                border: 1px solid {border};
                background: {surface_alt};
                color: {button_text};
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {selected};
                border-color: {border_strong};
            }}
            QPushButton#PrimaryButton {{
                border: 1px solid {accent};
                background: {accent};
                color: {primary_text};
            }}
            QPushButton#PrimaryButton:hover {{
                background: {accent_hover};
                border-color: {accent_hover};
            }}
            QMessageBox {{
                background: {surface};
                color: {text};
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
            }}
            QMessageBox QLabel {{
                color: {text};
                background: transparent;
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                font-weight: 600;
                padding: 2px 4px;
            }}
            QMessageBox QLabel#qt_msgbox_label,
            QMessageBox QLabel#qt_msgbox_informativelabel {{
                min-width: 460px;
            }}
            QMessageBox QPushButton {{
                min-width: 72px;
                min-height: 36px;
                padding: 0 16px;
                border-radius: 8px;
                border: 1px solid {border};
                background: {surface_alt};
                color: {button_text};
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                font-weight: 700;
            }}
            QMessageBox QPushButton:hover {{
                background: {selected};
                border-color: {border_strong};
            }}
            QTableWidget {{
                background: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                gridline-color: {border};
                alternate-background-color: {surface_alt};
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 13px;
                selection-background-color: {selected};
                selection-color: {text};
            }}
            QTableWidget::item {{
                padding: 6px 8px;
                border: none;
            }}
            QHeaderView::section {{
                background: {surface};
                color: {secondary};
                border: 0;
                border-right: 1px solid {border};
                border-bottom: 1px solid {border};
                padding: 8px 10px;
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 12px;
                font-weight: 700;
            }}
            QStatusBar {{
                background: {bg};
                color: {secondary};
                font-family: "Malgun Gothic", "Segoe UI";
                font-size: 12px;
            }}
            QScrollBar:vertical {{
                background: {surface};
                width: 12px;
                margin: 4px 2px 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                border-radius: 5px;
                min-height: 24px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            """.format(**colors)
        )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    window = DetailPageGui()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
