import logging
from pathlib import Path
from typing import LiteralString
from dataclasses import dataclass
import hashlib
import io
import zipfile
import random
from PIL import Image, ImageDraw, ImageFont
import colorsys

import pymupdf
from lxml import etree

from efm.exceptions import GetMetadataError


logger = logging.getLogger(__name__)


@dataclass
class Metadata:
    format: str | None
    encryption: str | None
    title: str | None
    author: str | None
    subject: str | None
    keywords: list[LiteralString] | None
    creator: str | None
    producer: str | None
    creation_date: str | None
    mod_date: str | None
    is_k2pdfopt_version: bool
    cover_image_hash: str | None = None

    def __post_init__(self):
        self.is_pdf = self.format is not None and self.format.lower() == "pdf"


def get_metadata(filepath: Path) -> Metadata | None:
    supported_formats = [
        "PDF",
        "XPS",
        "EPUB",
        "MOBI",
        "FB2",
        "CBZ",
        "SVG",
        "TXT",
    ]
    ext = filepath.suffix[1:].upper()
    if ext not in supported_formats:
        logger.info(
            f"{filepath} is not a supported format for pymupdf. Format is {ext}."
        )
        return None
    try:
        f: pymupdf.Document = pymupdf.open(filepath)
        if f.metadata is None:
            logger.info(f"{filepath} has no metadata.")
            return None
        format = f.metadata.get("format")
        keywords_raw = f.metadata.get("keywords")
        keywords = keywords_raw.split(",") if keywords_raw is not None else []
        return Metadata(
            format=format,
            encryption=f.metadata.get("encryption"),
            title=f.metadata.get("title"),
            author=f.metadata.get("author"),
            subject=f.metadata.get("subject"),
            keywords=keywords,
            creator=f.metadata.get("creator"),
            producer=f.metadata.get("producer"),
            creation_date=f.metadata.get("creationDate"),
            mod_date=f.metadata.get("modDate"),
            is_k2pdfopt_version=(
                format.lower().startswith("pdf")
                and "__ebooks-folder-manager.json" in f.embfile_names()
                if format is not None
                else False
            ),
        )
    except pymupdf.FileDataError as e:
        raise GetMetadataError(filepath, original_error=e)


def extract_epub_cover(filepath: Path) -> bytes | None:
    """Extract cover image from EPUB following W3C spec."""
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            # Parse container.xml to find OPF
            container_xml = z.read("META-INF/container.xml")
            container = etree.fromstring(container_xml)
            
            # Find OPF path
            namespaces = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
            rootfile = container.xpath("//c:rootfile", namespaces=namespaces)[0]
            opf_path = rootfile.get("full-path")
            
            # Parse OPF
            opf_content = z.read(opf_path)
            opf = etree.fromstring(opf_content)
            opf_namespaces = {"opf": "http://www.idpf.org/2007/opf"}
            
            # Look for EPUB 3 cover (properties="cover-image")
            cover_item = opf.xpath("//opf:item[@properties='cover-image']", 
                                  namespaces=opf_namespaces)
            
            if not cover_item:
                # Look for EPUB 2 cover
                cover_meta = opf.xpath("//opf:meta[@name='cover']", 
                                      namespaces=opf_namespaces)
                if cover_meta:
                    cover_id = cover_meta[0].get("content")
                    cover_item = opf.xpath(f"//opf:item[@id='{cover_id}']", 
                                          namespaces=opf_namespaces)
            
            if cover_item:
                cover_href = cover_item[0].get("href")
                # Handle relative paths
                import os
                if opf_path.count('/') > 0:
                    base_path = '/'.join(opf_path.split('/')[:-1])
                    cover_path = f"{base_path}/{cover_href}"
                else:
                    cover_path = cover_href
                
                return z.read(cover_path)
                
    except Exception as e:
        logger.debug(f"Failed to extract EPUB cover using manifest: {e}")
    
    return None


def extract_pdf_cover(filepath: Path) -> bytes | None:
    """Extract cover image from PDF by looking for embedded images."""
    try:
        doc = pymupdf.open(filepath)
        if doc.page_count == 0:
            return None
            
        # Check first page for images
        page = doc[0]
        image_list = page.get_images()
        
        if image_list:
            # Get the largest image (likely the cover)
            largest_img = None
            largest_size = 0
            
            for img in image_list:
                xref = img[0]
                try:
                    img_dict = doc.extract_image(xref)
                    size = len(img_dict["image"])
                    if size > largest_size:
                        largest_size = size
                        largest_img = img_dict
                except:
                    continue
                    
            if largest_img:
                doc.close()
                return largest_img["image"]
        
        doc.close()
    except Exception as e:
        logger.debug(f"Failed to extract PDF cover: {e}")
    
    return None


def generate_cover_image(book_hash: str, title: str | None = None, 
                        author: str | None = None) -> bytes:
    """Generate a unique cover image based on book hash."""
    # Use book hash as random seed for reproducibility
    seed = int(book_hash[:8], 16)
    random.seed(seed)
    
    # Cover dimensions
    width, height = 600, 800
    
    # Create base image
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Generate color scheme based on hash
    hue = int(book_hash[:2], 16) / 255.0
    base_color = colorsys.hsv_to_rgb(hue, 0.7, 0.8)
    base_color = tuple(int(c * 255) for c in base_color)
    
    # Generate complementary color
    comp_hue = (hue + 0.5) % 1.0
    comp_color = colorsys.hsv_to_rgb(comp_hue, 0.6, 0.9)
    comp_color = tuple(int(c * 255) for c in comp_color)
    
    # Choose pattern type based on hash
    pattern_type = int(book_hash[2:4], 16) % 3
    
    if pattern_type == 0:
        # Geometric triangles
        for i in range(20):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = x1 + random.randint(-200, 200)
            y2 = y1 + random.randint(-200, 200)
            x3 = x1 + random.randint(-200, 200)
            y3 = y1 + random.randint(-200, 200)
            
            color = base_color if i % 2 == 0 else comp_color
            alpha = random.randint(50, 150)
            
            # Create translucent overlay
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.polygon([(x1, y1), (x2, y2), (x3, y3)], 
                               fill=(*color, alpha))
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            
    elif pattern_type == 1:
        # Gradient with circles
        for y in range(height):
            # Gradient background
            ratio = y / height
            r = int(base_color[0] * (1-ratio) + comp_color[0] * ratio)
            g = int(base_color[1] * (1-ratio) + comp_color[1] * ratio)
            b = int(base_color[2] * (1-ratio) + comp_color[2] * ratio)
            draw.rectangle([(0, y), (width, y+1)], fill=(r, g, b))
        
        # Add circles
        for i in range(15):
            x = random.randint(0, width)
            y = random.randint(0, height)
            radius = random.randint(20, 100)
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                        outline=comp_color, width=3)
            
    elif pattern_type == 2:
        # Mondrian-style blocks
        draw.rectangle([(0, 0), (width, height)], fill=base_color)
        
        # Add random rectangles
        for i in range(8):
            x1 = random.randint(0, width-50)
            y1 = random.randint(0, height-50)
            x2 = x1 + random.randint(50, 200)
            y2 = y1 + random.randint(50, 200)
            
            colors = [base_color, comp_color, (255, 255, 255), (0, 0, 0)]
            color = random.choice(colors)
            
            draw.rectangle([(x1, y1), (x2, y2)], fill=color, outline=(0, 0, 0), width=3)
    
    # Add title and author text if provided
    if title or author:
        # Create text overlay with semi-transparent background
        text_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_overlay)
        
        # Add semi-transparent rectangle for text background
        text_draw.rectangle([(0, height-200), (width, height)], 
                           fill=(255, 255, 255, 200))
        
        # Try to use a nice font, fallback to default
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 36)
            author_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            author_font = ImageFont.load_default()
        
        y_offset = height - 180
        
        if title:
            # Wrap long titles
            max_width = width - 40
            words = title.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = text_draw.textbbox((0, 0), test_line, font=title_font)
                if bbox[2] - bbox[0] > max_width:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)
                else:
                    current_line.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw title lines
            for line in lines[:2]:  # Limit to 2 lines
                text_draw.text((20, y_offset), line, fill=(0, 0, 0), font=title_font)
                y_offset += 45
        
        if author:
            text_draw.text((20, y_offset + 10), f"by {author}", 
                          fill=(64, 64, 64), font=author_font)
        
        # Composite text overlay
        img = Image.alpha_composite(img.convert('RGBA'), text_overlay).convert('RGB')
    
    # Convert to bytes
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    return output.getvalue()


def extract_cover_image(filepath: Path, metadata: Metadata | None, 
                       cache_dir: Path) -> str | None:
    """Extract or generate cover image and return hash.
    
    Args:
        filepath: Path to the ebook file
        metadata: Book metadata (for title/author in generated covers)
        cache_dir: Directory to save cover images
        
    Returns:
        Hash string of the cover image, or None if failed
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cover_data = None
    
    # Try format-specific extraction first
    ext = filepath.suffix.lower()
    
    if ext == '.epub':
        cover_data = extract_epub_cover(filepath)
    elif ext == '.pdf':
        cover_data = extract_pdf_cover(filepath)
    else:
        # Try generic extraction with PyMuPDF
        try:
            doc = pymupdf.open(filepath)
            if doc.page_count > 0:
                page = doc[0]
                image_list = page.get_images()
                
                if image_list:
                    # Get first image
                    xref = image_list[0][0]
                    try:
                        img_dict = doc.extract_image(xref)
                        cover_data = img_dict["image"]
                    except:
                        pass
                        
            doc.close()
        except Exception as e:
            logger.debug(f"Failed to extract cover with PyMuPDF: {e}")
    
    # If no cover found, generate one
    if not cover_data:
        # Use file hash as seed
        file_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
        
        # Extract title and author from metadata
        title = metadata.title if metadata else None
        author = metadata.author if metadata else None
        
        # If no metadata, use filename
        if not title:
            title = filepath.stem
            
        logger.info(f"Generating cover for {filepath.name}")
        cover_data = generate_cover_image(file_hash, title, author)
    
    # Calculate hash and save
    cover_hash = hashlib.sha256(cover_data).hexdigest()
    cover_path = cache_dir / f"{cover_hash}.png"
    
    if not cover_path.exists():
        cover_path.write_bytes(cover_data)
        logger.info(f"Saved cover image to {cover_path}")
    
    return cover_hash
