from mistune.renderers.markdown import MarkdownRenderer


class ScientificMarkdownRenderer(MarkdownRenderer):
    """Emitter for Scientific Markdown following 2026 aesthetics."""

    def uri_header(self, token, state):
        """Renders the mandatory URI header."""
        return f"uri: {token['attrs']['value']}\n\n"

    def coordinate(self, token, state):
        """Renders section coordinates."""
        return f" {{:{token['attrs']['value']}}}"

    def heading(self, token, state):
        """Override heading to handle potential coordinates."""
        # Simplified: just return the heading text for now
        level = token["attrs"]["level"]
        text = token.get("text", "")
        return f"{'#' * level} {text}\n\n"
