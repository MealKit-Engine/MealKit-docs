# Sphinx configuration for the MealKit docs (English source, Korean via gettext translations in locale/ko/LC_MESSAGES).
# Build: python tools/build.py html  (English _build/html/en, Korean _build/html/ko)

import os

project = "MealKit"
author = "KingProtea99"
copyright = "2026, KingProtea99 and MealKit contributors. CC BY 4.0"

# The engine MINOR version these docs describe (compared with the engine VERSION by tools/build.py check)
with open(os.path.join(os.path.dirname(__file__), "ENGINE_VERSION"), encoding="utf-8") as f:
    version = f.read().strip()
release = version

extensions = [
    "myst_parser",
    "sphinx.ext.extlinks",
]

# Only source Markdown (MyST) is read as documents
source_suffix = {".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", ".venv", "README.md", "LICENSE.md", "CLAUDE.md", "tools", "locale", ".github", ".claude"]

myst_enable_extensions = ["deflist", "colon_fence"]
myst_heading_anchors = 3

# Files whose source of truth is the engine repo (CODING_MODEL, VERSIONS.txt etc.) link to the engine repo
engine_repo = "https://github.com/MealKit-Engine/MealKit"
extlinks = {
    "engine": (engine_repo + "/blob/master/%s", "%s"),
}

# Translation: English source, Korean gettext. One catalog per document, no line locations kept (reduces diffs of translation files)
language = "en"
locale_dirs = ["locale/"]
gettext_compact = False
gettext_location = False
gettext_uuid = False
# Comments inside code blocks are translated too. Only the gettext builder extracts code blocks (setup below), and LiteralBlockTranslator does the translation.
# Because Sphinx's own code block translation rereads the translation as reST ("::"), the content disappears in MyST documents.
gettext_additional_targets = []

html_theme = "sphinx_rtd_theme"
html_title = f"MealKit {version} documentation"
html_static_path = ["_static"]
html_theme_options = {"navigation_depth": 3}

# The engine repo isn't public yet, so it's excluded from link checks (remove once public)
linkcheck_ignore = [engine_repo + r"(/.*)?$"]
linkcheck_timeout = 20


# ---- Code block translation (MyST)
from docutils import nodes
from sphinx.locale import init as init_locale
from sphinx.transforms import SphinxTransform
from sphinx.util.i18n import docname_to_domain


class LiteralBlockTranslator(SphinxTransform):
    default_priority = 21  # right after Sphinx's Locale transform (20)

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
