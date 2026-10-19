# MealKit 문서 Sphinx 설정 (영어 원문, 한국어는 locale/ko/LC_MESSAGES의 gettext 번역).
# 빌드: python tools/build.py html  (영어 _build/html/en, 한국어 _build/html/ko)

import os

project = "MealKit"
author = "KingProtea99"
copyright = "2026, KingProtea99 and MealKit contributors. CC BY 4.0"

# 이 문서가 설명하는 엔진 MINOR 버전 (엔진 VERSION과 tools/build.py check가 비교한다)
with open(os.path.join(os.path.dirname(__file__), "ENGINE_VERSION"), encoding="utf-8") as f:
    version = f.read().strip()
release = version

extensions = [
    "myst_parser",
    "sphinx.ext.extlinks",
]

# 원본 Markdown(MyST)만 문서로 읽는다
source_suffix = {".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", ".venv", "README.md", "LICENSE.md", "tools", "locale", ".github", ".claude"]

myst_enable_extensions = ["deflist", "colon_fence"]
myst_heading_anchors = 3

# 엔진 저장소가 정본인 파일(CODING_MODEL, VERSIONS.txt 등)은 엔진 저장소로 링크한다
engine_repo = "https://github.com/KingProtea99/MealKit"
extlinks = {
    "engine": (engine_repo + "/blob/master/%s", "%s"),
}

# 번역: 영어 원문, 한국어 gettext. 문서마다 카탈로그 하나, 줄 위치는 남기지 않는다(번역 파일 diff를 줄인다)
language = "en"
locale_dirs = ["locale/"]
gettext_compact = False
gettext_location = False
gettext_uuid = False
# 코드 블록 안의 주석도 번역한다. gettext 빌더만 코드 블록을 뽑고(아래 setup), 번역은 LiteralBlockTranslator가 한다.
# Sphinx 자체의 코드 블록 번역은 번역문을 reST("::")로 다시 읽어 MyST 문서에서는 내용이 사라지기 때문이다.
gettext_additional_targets = []

html_theme = "sphinx_rtd_theme"
html_title = f"MealKit {version} documentation"
html_static_path = ["_static"]
html_theme_options = {"navigation_depth": 3}

# 엔진 저장소는 공개 전이라 링크 검사에서 뺀다 (공개하면 지운다)
linkcheck_ignore = [engine_repo + r"(/.*)?$"]
linkcheck_timeout = 20


# ---- 코드 블록 번역 (MyST)
from docutils import nodes
from sphinx.locale import init as init_locale
from sphinx.transforms import SphinxTransform
from sphinx.util.i18n import docname_to_domain


class LiteralBlockTranslator(SphinxTransform):
    default_priority = 21  # Sphinx의 Locale 변환(20) 바로 뒤

    def apply(self, **kwargs):
        if not self.config.language or self.config.language == "en":
            return
        domain = docname_to_domain(self.env.docname, self.config.gettext_compact)
        dirs = [os.path.join(self.env.srcdir, d) for d in self.config.locale_dirs]
        catalog, has_catalog = init_locale(dirs, self.config.language, domain)
        if not has_catalog:
            return
        for node in self.document.findall(nodes.literal_block):
            msg = node.rawsource
            translated = catalog.gettext(msg)
            if msg and translated != msg:
                node.rawsource = translated
                node.children = [nodes.Text(translated)]


def _gettext_targets(app):
    if app.builder.name == "gettext":
        app.config.gettext_additional_targets = ["literal-block"]


def setup(app):
    app.add_transform(LiteralBlockTranslator)
    app.connect("builder-inited", _gettext_targets)
