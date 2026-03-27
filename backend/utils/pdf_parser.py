"""
PDF parser utility for extracting text and URLs from PDF files.
Uses pdfplumber for robust PDF text extraction.
"""

import re
import logging
from typing import List
from io import BytesIO
import pdfplumber
from ..models.candidate import PDFExtraction

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import fitz  # pymupdf
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF parser for extracting text and URLs from resume PDFs."""

    @staticmethod
    def extract_from_pdf(pdf_content: bytes) -> PDFExtraction:
        """
        Extract raw text and all URLs from a PDF file.

        Args:
            pdf_content: Raw PDF file content as bytes

        Returns:
            PDFExtraction model with raw text and URLs

        Raises:
            Exception: If PDF extraction fails
        """
        try:
            raw_text = ""
            urls = []

            # Create a BytesIO object from the PDF content
            pdf_stream = BytesIO(pdf_content)

            # Extract text using pdfplumber with improved options
            with pdfplumber.open(pdf_stream) as pdf:
                logger.info(f"Processing PDF with {len(pdf.pages)} pages")

                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Method 1: Try advanced text extraction with layout preservation
                        page_text = PDFParser._extract_text_advanced(page)

                        # Method 2: Fallback to basic extraction if advanced fails
                        if not page_text or len(page_text.strip()) < 50:
                            page_text = page.extract_text()

                        # Method 3: Last resort - extract words and reconstruct
                        if not page_text or len(page_text.strip()) < 50:
                            page_text = PDFParser._extract_words_and_reconstruct(page)

                        if page_text:
                            # Clean and normalize the text
                            cleaned_text = PDFParser._clean_extracted_text(page_text)
                            raw_text += cleaned_text + "\n\n"

                            logger.debug(f"Page {page_num}: extracted {len(cleaned_text)} characters")

                        # Extract hyperlinks if available
                        try:
                            logger.debug(f"Starting hyperlink extraction for page {page_num}")

                            # Method 1: Try to extract hyperlinks from page annotations
                            if hasattr(page, 'hyperlinks') and page.hyperlinks:
                                logger.debug(f"Found {len(page.hyperlinks)} hyperlinks via method 1")
                                for link in page.hyperlinks:
                                    if 'url' in link and link['url']:
                                        urls.append(link['url'])
                                        logger.info(f"Extracted hyperlink via method 1: {link['url']}")

                            # Method 2: Extract hyperlinks from page annotations directly
                            if hasattr(page, 'annots') and page.annots:
                                logger.debug(f"Found {len(page.annots)} annotations via method 2")
                                for annot in page.annots:
                                    if annot.get('A') and annot.get('A').get('URI'):
                                        url = annot.get('A').get('URI')
                                        if url:
                                            urls.append(url)
                                            logger.info(f"Extracted hyperlink via method 2: {url}")

                            # Method 3: Check for URI annotations in the page object
                            page_obj = page.page_obj
                            if page_obj and hasattr(page_obj, 'get'):
                                annots = page_obj.get('/Annots')
                                if annots:
                                    logger.debug(f"Found {len(annots)} annotations via method 3")
                                    for annot_ref in annots:
                                        try:
                                            annot = annot_ref.resolve()
                                            if annot.get('/Subtype') == '/Link':
                                                action = annot.get('/A')
                                                if action and action.get('/S') == '/URI':
                                                    uri = action.get('/URI')
                                                    if uri:
                                                        urls.append(str(uri))
                                                        logger.info(f"Extracted hyperlink via method 3: {uri}")
                                        except Exception as e:
                                            logger.debug(f"Error processing annotation: {str(e)}")
                                            continue

                            # Method 4: Try to extract from text objects with coordinates
                            try:
                                page_obj = page.page_obj
                                if page_obj and '/Annots' in page_obj:
                                    for annot in page_obj['/Annots']:
                                        annot_obj = annot.get_object()
                                        if '/A' in annot_obj:
                                            action = annot_obj['/A']
                                            if '/URI' in action:
                                                uri = action['/URI']
                                                urls.append(str(uri))
                                                logger.info(f"Extracted hyperlink via method 4: {uri}")
                            except Exception as e:
                                logger.debug(f"Method 4 failed: {str(e)}")

                        except Exception as e:
                            logger.debug(f"Error extracting hyperlinks from page {page_num}: {str(e)}")
                            pass

                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                        continue

            # Clean the final text
            raw_text = PDFParser._final_text_cleanup(raw_text)

            # Write raw text to dump.txt for debugging
            try:
                with open("dump.txt", "w", encoding="utf-8") as dump_file:
                    dump_file.write(raw_text.strip())
                logger.info("Raw extracted text written to dump.txt for debugging")
            except Exception as e:
                logger.warning(f"Failed to write dump.txt: {str(e)}")

            # Comprehensive hyperlink extraction using multiple PDF libraries
            hyperlink_urls = PDFParser._extract_hyperlinks_comprehensive(pdf_content)
            urls.extend(hyperlink_urls)

            # Additional URL extraction from text using regex
            text_urls = PDFParser._extract_urls_from_text(raw_text)
            urls.extend(text_urls)

            # Remove duplicates and filter URLs
            urls = list(set(urls))
            urls = PDFParser._filter_urls(urls)

            logger.info(f"Extracted {len(raw_text)} characters and {len(urls)} URLs")

            return PDFExtraction(
                raw_text=raw_text.strip(),
                urls=urls
            )

        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            raise Exception(f"Failed to extract content from PDF: {str(e)}")

    @staticmethod
    def _extract_text_advanced(page) -> str:
        """
        Advanced text extraction preserving layout and word boundaries.

        Args:
            page: pdfplumber page object

        Returns:
            Extracted text with better formatting
        """
        try:
            # Try to extract text with layout preservation
            text = page.extract_text(
                x_tolerance=3,  # Horizontal tolerance for combining chars
                y_tolerance=3,  # Vertical tolerance for combining chars
                layout=True,   # Preserve layout
                x_density=7.25,  # Character spacing
                y_density=13     # Line spacing
            )
            return text if text else ""
        except Exception:
            return ""

    @staticmethod
    def _extract_words_and_reconstruct(page) -> str:
        """
        Extract words and reconstruct text with proper spacing.

        Args:
            page: pdfplumber page object

        Returns:
            Reconstructed text
        """
        try:
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False
            )

            if not words:
                return ""

            # Group words by lines based on y-coordinates
            lines = {}
            for word in words:
                y = round(word['top'], 1)  # Round to avoid small variations
                if y not in lines:
                    lines[y] = []
                lines[y].append(word)

            # Sort lines by y-coordinate (top to bottom)
            sorted_lines = []
            for y in sorted(lines.keys()):
                # Sort words in each line by x-coordinate (left to right)
                line_words = sorted(lines[y], key=lambda w: w['x0'])
                line_text = ' '.join(word['text'] for word in line_words)
                sorted_lines.append(line_text)

            return '\n'.join(sorted_lines)

        except Exception:
            return ""

    @staticmethod
    def _clean_extracted_text(text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace while preserving structure
        lines = []
        for line in text.split('\n'):
            # Fix broken words (spaces within words)
            line = PDFParser._fix_broken_words(line)

            # Clean up spacing
            line = re.sub(r' +', ' ', line.strip())  # Multiple spaces to single

            if line:  # Only add non-empty lines
                lines.append(line)

        return '\n'.join(lines)

    @staticmethod
    def _fix_broken_words(line: str) -> str:
        """
        Fix words that got broken during extraction (like "Sim ple" -> "Simple").

        Args:
            line: Line of text with potentially broken words

        Returns:
            Line with fixed words
        """
        # Common patterns that indicate broken words
        patterns = [
            # Fix single letter separations: "S imple" -> "Simple"
            (r'\b([A-Z]) ([a-z]{2,})', r'\1\2'),

            # Fix mid-word breaks: "sim ple" -> "simple"
            (r'\b([a-z]+) ([a-z]{1,3})\b', r'\1\2'),

            # Fix specific known broken words from the output
            (r'\bSim ple\b', 'Simple'),
            (r'\bN oob\b', 'Noob'),
            (r'\bCh ef\b', 'Chef'),
            (r'\bAd min\b', 'Admin'),

            # Fix technology names that might get broken
            (r'\bNext JS\b', 'NextJS'),
            (r'\bFast API\b', 'FastAPI'),
            (r'\bPy Qt\b', 'PyQt'),

            # Fix common word breaks
            (r'\bwe ather\b', 'weather'),
            (r'\bap plication\b', 'application'),
            (r'\bpro ject\b', 'project'),
        ]

        for pattern, replacement in patterns:
            line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)

        return line

    @staticmethod
    def _final_text_cleanup(text: str) -> str:
        """
        Final cleanup of the entire extracted text.

        Args:
            text: Combined text from all pages

        Returns:
            Final cleaned text
        """
        if not text:
            return ""

        # Split into lines and clean each
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) > 2:  # Skip very short lines that are likely artifacts
                lines.append(line)

        # Remove excessive blank lines
        cleaned_text = '\n'.join(lines)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)  # Max 2 consecutive newlines

        return cleaned_text.strip()

    @staticmethod
    def _extract_urls_from_text(text: str) -> List[str]:
        """
        Extract URLs from text using comprehensive regex patterns.

        Args:
            text: Text content to search for URLs

        Returns:
            List of found URLs
        """
        # Comprehensive URL patterns
        url_patterns = [
            # Complete URLs
            r'https?://(?:www\.)?github\.com/[\w\-\.]+/?[\w\-\.]*/?',
            r'https?://(?:www\.)?linkedin\.com/in/[\w\-\.]+/?',
            r'https?://[\w\.-]+\.[\w]{2,}(?:/[\w\.-]*)*/?',

            # URLs without protocol
            r'github\.com/[\w\-\.]+/?[\w\-\.]*/?',
            r'linkedin\.com/in/[\w\-\.]+/?',
            r'www\.[\w\.-]+\.[\w]{2,}(?:/[\w\.-]*)*/?',

            # Domain patterns (common in resumes)
            r'[\w\.-]+\.(?:com|org|net|edu|io|dev|co|me|tech)(?:/[\w\.-]*)*',

            # Email addresses (sometimes formatted as contact info)
            r'\b\w+@\w+\.\w{2,}\b',

            # GitHub-specific patterns (handle various formats)
            r'(?:github|GitHub)(?:\s*:\s*|\s+)(?:https?://)?(?:www\.)?github\.com/[\w\-\.]+',

            # LinkedIn-specific patterns
            r'(?:linkedin|LinkedIn)(?:\s*:\s*|\s+)(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-\.]+',

            # Portfolio/website patterns
            r'(?:portfolio|website|site)(?:\s*:\s*|\s+)(?:https?://)?(?:www\.)?[\w\.-]+\.[\w]{2,}',
        ]

        urls = []
        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean up the match
                clean_url = PDFParser._clean_extracted_url(match)
                if clean_url:
                    urls.append(clean_url)

        return list(set(urls))  # Remove duplicates

    @staticmethod
    def _clean_extracted_url(url: str) -> str:
        """
        Clean and normalize an extracted URL.

        Args:
            url: Raw extracted URL

        Returns:
            Cleaned URL or empty string if invalid
        """
        if not url:
            return ""

        # Remove common prefixes from resume formatting
        url = re.sub(r'^(github|linkedin|portfolio|website|site)\s*:\s*', '', url, flags=re.IGNORECASE)

        # Clean whitespace
        url = url.strip()

        # Skip if too short or obviously not a URL
        if len(url) < 5 or '@' in url and '.' not in url:
            return ""

        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        return url

    @staticmethod
    def _filter_urls(urls: List[str]) -> List[str]:
        """
        Filter and validate URLs, prioritizing relevant ones.

        Args:
            urls: List of URLs to filter

        Returns:
            Filtered list of relevant URLs
        """
        filtered_urls = []

        for url in urls:
            # Normalize URL
            url = url.strip().lower()

            # Skip invalid or irrelevant URLs
            if not url or len(url) < 5:
                continue

            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = f"https://{url}"
                else:
                    url = f"https://{url}"

            # Skip common non-relevant domains
            skip_domains = [
                'google.com',
                'facebook.com',
                'twitter.com',
                'instagram.com',
                'youtube.com',
                'example.com',
                'test.com',
                'localhost',
            ]

            skip_url = False
            for domain in skip_domains:
                if domain in url:
                    skip_url = True
                    break

            if skip_url:
                continue

            # Prioritize relevant professional URLs
            relevant_domains = ['github.com', 'linkedin.com', 'gitlab.com', 'bitbucket.org']
            if any(domain in url for domain in relevant_domains):
                filtered_urls.insert(0, url)  # Add to beginning
            else:
                filtered_urls.append(url)

        # Remove duplicates while preserving order
        seen = set()
        result = []
        for url in filtered_urls:
            if url not in seen:
                seen.add(url)
                result.append(url)

        return result[:10]  # Limit to first 10 URLs

    @staticmethod
    def _extract_hyperlinks_comprehensive(pdf_content: bytes) -> List[str]:
        """
        Comprehensive hyperlink extraction using multiple PDF libraries.

        Args:
            pdf_content: Raw PDF file content as bytes

        Returns:
            List of extracted hyperlink URLs
        """
        urls = []

        # Method 1: PyPDF2 extraction
        if PyPDF2:
            try:
                logger.info("Attempting hyperlink extraction with PyPDF2")
                pdf_stream = BytesIO(pdf_content)
                reader = PyPDF2.PdfReader(pdf_stream)

                for page_num, page in enumerate(reader.pages):
                    if '/Annots' in page:
                        logger.debug(f"PyPDF2: Found annotations on page {page_num + 1}")
                        for annot in page['/Annots']:
                            try:
                                annot_obj = annot.get_object()
                                if '/A' in annot_obj:
                                    action = annot_obj['/A']
                                    if '/URI' in action:
                                        uri = str(action['/URI'])
                                        urls.append(uri)
                                        logger.info(f"PyPDF2 extracted: {uri}")
                            except Exception as e:
                                logger.debug(f"PyPDF2 annotation error: {str(e)}")
                                continue

            except Exception as e:
                logger.debug(f"PyPDF2 hyperlink extraction failed: {str(e)}")

        # Method 2: PyMuPDF (fitz) extraction
        if fitz:
            try:
                logger.info("Attempting hyperlink extraction with PyMuPDF")
                doc = fitz.open(stream=pdf_content, filetype="pdf")

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    links = page.get_links()

                    if links:
                        logger.debug(f"PyMuPDF: Found {len(links)} links on page {page_num + 1}")
                        for link in links:
                            if 'uri' in link and link['uri']:
                                uri = str(link['uri'])
                                urls.append(uri)
                                logger.info(f"PyMuPDF extracted: {uri}")

                doc.close()

            except Exception as e:
                logger.debug(f"PyMuPDF hyperlink extraction failed: {str(e)}")

        # Method 3: Look for URL patterns in hyperlink text zones
        # If we have text that says "LinkedIn | Github" but no hyperlinks,
        # try to correlate with actual URLs in the document
        try:
            logger.info("Attempting contextual hyperlink detection")
            if fitz:
                doc = fitz.open(stream=pdf_content, filetype="pdf")

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text_blocks = page.get_text("dict")

                    for block in text_blocks.get("blocks", []):
                        if "lines" in block:
                            for line in block["lines"]:
                                for span in line.get("spans", []):
                                    text = span.get("text", "").lower()

                                    # Look for LinkedIn or Github mentions
                                    if "linkedin" in text or "github" in text:
                                        logger.debug(f"Found social media mention: {text} on page {page_num + 1}")

                                        # Get bounding box and check for nearby links
                                        bbox = span.get("bbox")
                                        if bbox:
                                            # Check for links in nearby areas
                                            links = page.get_links()
                                            for link in links:
                                                link_rect = link.get("from")
                                                if link_rect and 'uri' in link:
                                                    # Simple proximity check
                                                    if (abs(bbox[1] - link_rect.y0) < 20 and  # Same line roughly
                                                        abs(bbox[0] - link_rect.x0) < 200):    # Nearby horizontally
                                                        uri = str(link['uri'])
                                                        urls.append(uri)
                                                        logger.info(f"Contextual extraction: {uri}")

                doc.close()

        except Exception as e:
            logger.debug(f"Contextual hyperlink detection failed: {str(e)}")

        # Remove duplicates and return
        unique_urls = list(dict.fromkeys(urls))  # Preserves order while removing duplicates
        logger.info(f"Comprehensive hyperlink extraction found {len(unique_urls)} URLs")

        return unique_urls


# Instance for easy importing
pdf_parser = PDFParser()