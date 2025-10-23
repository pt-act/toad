import os
from importlib.metadata import version
import platform

from string import Template


from toad.app import ToadApp

ABOUT_TEMPLATE = Template("""\
# About Toad v${TOAD_VERSION}

© Will McGugan.
                          
Toad is licensed under the terms of the [GNU AFFERO GENERAL PUBLIC LICENSE](https://www.gnu.org/licenses/agpl-3.0.txt).
                          
settings: `$SETTINGS_PATH`

| System | Version |
| --- | --- |
| Python | $PYTHON |
| OS | $PLATFORM |
                                                 
| Library | Version |
| --- | --- | 
| Textual | ${TEXTUAL_VERSION} |
| Rich | ${RICH_VERSION} |

| Environment variable | Value |                
| --- | --- |
| `TERM` | $TERM |
| `COLORTERM` | $COLORTERM |
| `TERM_PROGRAM` | $TERM_PROGRAM |
| `TERM_PROGRAM_VERSION` | $TERM_PROGRAM_VERSION |
""")


def render(app: ToadApp) -> str:
    """Render about markdown.

    Returns:
        Markdown string.
    """

    template_data = {
        "TOAD_VERSION": version("toad"),
        "TEXTUAL_VERSION": version("textual"),
        "RICH_VERSION": version("rich"),
        "PYTHON": f"{platform.python_implementation()} {platform.python_version()}",
        "PLATFORM": platform.platform(),
        "TERM": os.environ.get("TERM", ""),
        "COLORTERM": os.environ.get("COLORTERM", ""),
        "TERM_PROGRAM": os.environ.get("TERM_PROGRAM", ""),
        "TERM_PROGRAM_VERSION": os.environ.get("TERM_PROGRAM_VERSION", ""),
        "SETTINGS_PATH": str(app.settings_path),
    }
    return ABOUT_TEMPLATE.safe_substitute(template_data)


if __name__ == "__main__":
    print(render())
