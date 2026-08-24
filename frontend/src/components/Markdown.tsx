import { useMemo } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";

// Renders assistant answers (bold, headings, lists, GFM tables, etc.) as real HTML.
// Sanitized with DOMPurify -- agent answers can quote retrieved ticket/document text
// verbatim, which is untrusted data and must never be allowed to inject markup/scripts.
export function Markdown({ content }: { content: string }) {
  const html = useMemo(() => {
    const parsed = marked.parse(content, { async: false, breaks: true });
    return DOMPurify.sanitize(parsed);
  }, [content]);

  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />;
}
