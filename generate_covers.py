#!/usr/bin/env python3
import argparse
import hashlib
import os
import random
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import colorsys

usage = """
Generate random book covers with various patterns and display them in an HTML gallery.

Usage: python generate_covers.py [options]

Options:
  -n, --number       Number of covers to generate (default: 20)
  -o, --output       Output directory (default: generated_covers)
  -s, --size         Cover size as WIDTHxHEIGHT (default: 600x900)
  -p, --patterns     Patterns to use (default: all)
                     Available: triangles, gradient, mondrian
  --seed             Random seed for reproducibility
  -h, --help         Show this help message
"""


def generate_color_scheme(seed):
    """Generate a color scheme based on a seed."""
    random.seed(seed)
    base_hue = random.random()
    
    scheme_type = random.choice(['analogous', 'complementary', 'triadic', 'monochromatic'])
    
    colors = []
    if scheme_type == 'analogous':
        for i in range(3):
            hue = (base_hue + i * 0.1) % 1.0
            saturation = 0.6 + random.random() * 0.4
            lightness = 0.4 + random.random() * 0.3
            rgb = colorsys.hsv_to_rgb(hue, saturation, lightness)
            colors.append(tuple(int(c * 255) for c in rgb))
    elif scheme_type == 'complementary':
        colors.append(tuple(int(c * 255) for c in colorsys.hsv_to_rgb(base_hue, 0.8, 0.7)))
        colors.append(tuple(int(c * 255) for c in colorsys.hsv_to_rgb((base_hue + 0.5) % 1.0, 0.8, 0.7)))
    elif scheme_type == 'triadic':
        for i in range(3):
            hue = (base_hue + i * 0.333) % 1.0
            saturation = 0.7 + random.random() * 0.3
            lightness = 0.5 + random.random() * 0.2
            rgb = colorsys.hsv_to_rgb(hue, saturation, lightness)
            colors.append(tuple(int(c * 255) for c in rgb))
    else:  # monochromatic
        for i in range(3):
            saturation = 0.3 + i * 0.2
            lightness = 0.3 + i * 0.2
            rgb = colorsys.hsv_to_rgb(base_hue, saturation, lightness)
            colors.append(tuple(int(c * 255) for c in rgb))
    
    return colors, scheme_type


def generate_triangles_pattern(img, draw, colors, seed):
    """Generate a geometric triangles pattern."""
    random.seed(seed)
    width, height = img.size
    triangle_size = 60
    
    for y in range(0, height, triangle_size):
        for x in range(0, width, triangle_size):
            color = random.choice(colors)
            if random.random() > 0.5:
                points = [(x, y), (x + triangle_size, y), (x, y + triangle_size)]
            else:
                points = [(x + triangle_size, y), (x + triangle_size, y + triangle_size), (x, y + triangle_size)]
            draw.polygon(points, fill=color)


def generate_gradient_pattern(img, draw, colors, seed):
    """Generate a gradient with circles pattern."""
    random.seed(seed)
    width, height = img.size
    
    # Create gradient background
    for y in range(height):
        ratio = y / height
        r = int(colors[0][0] * (1 - ratio) + colors[1][0] * ratio)
        g = int(colors[0][1] * (1 - ratio) + colors[1][1] * ratio)
        b = int(colors[0][2] * (1 - ratio) + colors[1][2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # Add circles
    for _ in range(random.randint(5, 15)):
        x = random.randint(0, width)
        y = random.randint(0, height)
        radius = random.randint(20, 100)
        color = random.choice(colors) + (random.randint(50, 150),)  # Add alpha
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)
        img.paste(overlay, (0, 0), overlay)


def generate_mondrian_pattern(img, draw, colors, seed):
    """Generate a Mondrian-style pattern."""
    random.seed(seed)
    width, height = img.size
    
    # Background
    draw.rectangle([0, 0, width, height], fill=(240, 240, 240))
    
    # Generate random divisions
    divisions = []
    for _ in range(random.randint(4, 8)):
        x1 = random.randint(0, width - 50)
        y1 = random.randint(0, height - 50)
        x2 = x1 + random.randint(50, min(200, width - x1))
        y2 = y1 + random.randint(50, min(300, height - y1))
        divisions.append((x1, y1, x2, y2))
    
    # Draw rectangles
    for x1, y1, x2, y2 in divisions:
        if random.random() > 0.3:
            color = random.choice(colors + [(255, 255, 255)])
        else:
            color = (0, 0, 0)
        draw.rectangle([x1, y1, x2, y2], fill=color, outline=(0, 0, 0), width=3)


def add_text_overlay(img, title, subtitle=None):
    """Add text overlay to the cover."""
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    # Try to use a nice font, fall back to default if not available
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 48)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 32)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # Add semi-transparent overlay for text
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([0, height - 200, width, height], fill=(0, 0, 0, 180))
    img.paste(overlay, (0, 0), overlay)
    
    # Draw title
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, height - 150), title, fill=(255, 255, 255), font=title_font)
    
    # Draw subtitle if provided
    if subtitle:
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (width - subtitle_width) // 2
        draw.text((subtitle_x, height - 80), subtitle, fill=(200, 200, 200), font=subtitle_font)


def generate_cover(width, height, pattern, seed, title=None, subtitle=None):
    """Generate a single cover with the specified pattern."""
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    colors, scheme_type = generate_color_scheme(seed)
    
    pattern_generators = {
        'triangles': generate_triangles_pattern,
        'gradient': generate_gradient_pattern,
        'mondrian': generate_mondrian_pattern
    }
    
    if pattern in pattern_generators:
        pattern_generators[pattern](img, draw, colors, seed)
    
    if title:
        add_text_overlay(img, title, subtitle)
    
    return img, colors, scheme_type


def generate_html_gallery(output_dir, covers_info, timestamp, total_covers, width, height, patterns):
    """Generate an HTML page to display all covers."""
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Book Covers Gallery</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .cover-item {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .cover-item:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }}
        .cover-image {{
            width: 100%;
            height: auto;
            border-radius: 4px;
            margin-bottom: 15px;
        }}
        .cover-info {{
            font-size: 14px;
            color: #666;
            line-height: 1.5;
        }}
        .cover-info h3 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 18px;
        }}
        .info-row {{
            margin: 5px 0;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
        }}
        .color-swatch {{
            display: inline-block;
            width: 20px;
            height: 20px;
            margin: 0 4px;
            border: 1px solid #ddd;
            border-radius: 3px;
            vertical-align: middle;
        }}
        .metadata {{
            background: #f8f8f8;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            max-width: 1400px;
            margin-left: auto;
            margin-right: auto;
        }}
        .metadata h2 {{
            margin-top: 0;
            color: #333;
        }}
    </style>
</head>
<body>
    <h1>Generated Book Covers Gallery</h1>
    
    <div class="metadata">
        <h2>Generation Settings</h2>
        <p><strong>Generated:</strong> {timestamp}</p>
        <p><strong>Total Covers:</strong> {total_covers}</p>
        <p><strong>Cover Size:</strong> {width}x{height}px</p>
        <p><strong>Patterns Used:</strong> {patterns}</p>
    </div>
    
    <div class="gallery">
"""
    
    for info in covers_info:
        color_swatches = ''.join([
            f'<span class="color-swatch" style="background-color: rgb{color}"></span>'
            for color in info['colors']
        ])
        
        html_content += f"""
        <div class="cover-item">
            <img src="{info['filename']}" alt="Cover {info['index']}" class="cover-image">
            <div class="cover-info">
                <h3>Cover #{info['index']}</h3>
                <div class="info-row">
                    <span class="info-label">Pattern:</span> {info['pattern']}
                </div>
                <div class="info-row">
                    <span class="info-label">Color Scheme:</span> {info['scheme_type']}
                </div>
                <div class="info-row">
                    <span class="info-label">Colors:</span> {color_swatches}
                </div>
                <div class="info-row">
                    <span class="info-label">Seed:</span> {info['seed']}
                </div>
            </div>
        </div>
"""
    
    html_content += """
    </div>
</body>
</html>
"""
    
    return html_content


def main():
    parser = argparse.ArgumentParser(description='Generate random book covers', add_help=False)
    parser.add_argument('-n', '--number', type=int, default=20, help='Number of covers to generate')
    parser.add_argument('-o', '--output', type=str, default='generated_covers', help='Output directory')
    parser.add_argument('-s', '--size', type=str, default='600x900', help='Cover size as WIDTHxHEIGHT')
    parser.add_argument('-p', '--patterns', type=str, nargs='+', 
                        choices=['triangles', 'gradient', 'mondrian'],
                        help='Patterns to use (default: all)')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('-h', '--help', action='store_true', help='Show help message')
    
    args = parser.parse_args()
    
    if args.help:
        print(usage)
        return
    
    # Parse size
    try:
        width, height = map(int, args.size.split('x'))
    except ValueError:
        print(f"Error: Invalid size format '{args.size}'. Use WIDTHxHEIGHT (e.g., 600x900)")
        return
    
    # Set up patterns
    all_patterns = ['triangles', 'gradient', 'mondrian']
    patterns = args.patterns if args.patterns else all_patterns
    
    # Create output directory
    output_dir = Path(args.output)
    if output_dir.exists():
        print(f"Warning: Output directory '{output_dir}' already exists. Continue? [y/N] ", end='')
        if input().lower() != 'y':
            return
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    
    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)
    
    covers_info = []
    
    print(f"Generating {args.number} covers...")
    
    for i in range(args.number):
        # Choose random pattern
        pattern = random.choice(patterns)
        
        # Generate seed for this cover
        cover_seed = random.randint(0, 1000000)
        
        # Generate random title and subtitle
        titles = [
            "The Quantum Garden", "Echoes of Tomorrow", "Digital Dreams",
            "The Last Algorithm", "Parallel Worlds", "Code of the Ancients",
            "The Pattern Maker", "Infinite Loop", "Binary Stars",
            "The Data Weaver", "Virtual Reality", "The Pixel Prophet"
        ]
        subtitles = [
            "A Journey Through Time", "Tales of the Future", "An Epic Adventure",
            "The Complete Series", "A Novel", "Volume One",
            "The Chronicles", "A Mystery", "The Saga Continues"
        ]
        
        title = random.choice(titles) if random.random() > 0.3 else None
        subtitle = random.choice(subtitles) if title and random.random() > 0.5 else None
        
        # Generate cover
        img, colors, scheme_type = generate_cover(width, height, pattern, cover_seed, title, subtitle)
        
        # Save cover
        filename = f"cover_{i+1:03d}.png"
        filepath = output_dir / filename
        img.save(filepath, 'PNG')
        
        # Store info
        covers_info.append({
            'index': i + 1,
            'filename': filename,
            'pattern': pattern,
            'colors': colors,
            'scheme_type': scheme_type,
            'seed': cover_seed,
            'title': title,
            'subtitle': subtitle
        })
        
        print(f"  Generated cover {i+1}/{args.number} ({pattern})")
    
    # Generate HTML gallery
    html_content = generate_html_gallery(
        output_dir, 
        covers_info,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        total_covers=args.number,
        width=width,
        height=height,
        patterns=', '.join(patterns)
    )
    
    html_path = output_dir / 'index.html'
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    print(f"\nSuccess! Generated {args.number} covers in '{output_dir}'")
    print(f"View the gallery by opening: {html_path.absolute()}")


if __name__ == '__main__':
    main()