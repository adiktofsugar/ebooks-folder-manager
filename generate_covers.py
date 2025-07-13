#!/usr/bin/env python3
import argparse
import hashlib
import random
from datetime import datetime
from pathlib import Path
import shutil
import colorsys

from efm.metadata import generate_cover_image

usage = """
Generate random book covers using the same function used by EFM and display them in an HTML gallery.

Usage: python generate_covers.py [options]

Options:
  -n, --number       Number of covers to generate (default: 20)
  -o, --output       Output directory (default: generated_covers)
  --seed             Random seed for reproducibility
  -h, --help         Show this help message
"""


def generate_html_gallery(output_dir, covers_info, timestamp, total_covers):
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
        <p><strong>Cover Size:</strong> 600x800px (fixed by EFM)</p>
        <p><strong>Patterns:</strong> Triangles, Gradient, Mondrian, Mario</p>
        <p><strong>Note:</strong> These covers use the same generation function as EFM</p>
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
                    <span class="info-label">Title:</span> {info['title']}
                </div>
                <div class="info-row">
                    <span class="info-label">Author:</span> {info['author']}
                </div>
                <div class="info-row">
                    <span class="info-label">Pattern:</span> {info['pattern']}
                </div>
                <div class="info-row">
                    <span class="info-label">Colors:</span> {color_swatches}
                </div>
                <div class="info-row">
                    <span class="info-label">Hash:</span> {info['hash'][:16]}...
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
    parser = argparse.ArgumentParser(description='Generate random book covers using EFM function', add_help=False)
    parser.add_argument('-n', '--number', type=int, default=20, help='Number of covers to generate')
    parser.add_argument('-o', '--output', type=str, default='generated_covers', help='Output directory')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('-h', '--help', action='store_true', help='Show help message')
    
    args = parser.parse_args()
    
    if args.help:
        print(usage)
        return
    
    # Create output directory
    output_dir = Path(args.output)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    
    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)
    
    covers_info = []
    
    # Sample titles and authors for generation
    titles = [
        "The Quantum Garden", "Echoes of Tomorrow", "Digital Dreams",
        "The Last Algorithm", "Parallel Worlds", "Code of the Ancients",
        "The Pattern Maker", "Infinite Loop", "Binary Stars",
        "The Data Weaver", "Virtual Reality", "The Pixel Prophet",
        "Algorithmic Tales", "The Memory Palace", "Synthetic Dreams",
        "Neural Networks", "The Cloud Walker", "Data Streams",
        "The Code Keeper", "Quantum Entanglement"
    ]
    
    authors = [
        "Sarah Chen", "Marcus Johnson", "Elena Rodriguez", "James Patterson",
        "Lisa Montgomery", "Robert Kim", "Maria Silva", "David Thompson",
        "Jennifer Liu", "Michael Brown", "Ana Martinez", "Kevin Zhang",
        "Rachel Green", "Steven White", "Isabel Garcia", "Thomas Lee",
        "Emma Wilson", "Daniel Park", "Sophia Adams", "Christopher Moore"
    ]
    
    print(f"Generating {args.number} covers...")
    
    for i in range(args.number):
        # Generate a random hash for this cover
        random_data = f"cover_{i}_{random.random()}".encode()
        book_hash = hashlib.sha256(random_data).hexdigest()
        
        # Pick random title and author
        title = random.choice(titles)
        author = random.choice(authors)
        
        # Determine pattern type from hash (same logic as in generate_cover_image)
        pattern_type = int(book_hash[2:4], 16) % 4
        pattern_names = ["Triangles", "Gradient", "Mondrian", "Mario"]
        pattern_name = pattern_names[pattern_type]
        
        # Extract colors from hash (same logic as in generate_cover_image)
        hue = int(book_hash[:2], 16) / 255.0
        base_color = colorsys.hsv_to_rgb(hue, 0.7, 0.8)
        base_color = tuple(int(c * 255) for c in base_color)
        
        comp_hue = (hue + 0.5) % 1.0
        comp_color = colorsys.hsv_to_rgb(comp_hue, 0.6, 0.9)
        comp_color = tuple(int(c * 255) for c in comp_color)
        
        colors = [base_color, comp_color]
        if pattern_type == 2:  # Mondrian also uses white and black
            colors.extend([(255, 255, 255), (0, 0, 0)])
        
        # Generate cover using the same function as EFM
        cover_data = generate_cover_image(book_hash, title, author)
        
        # Save cover
        filename = f"cover_{i+1:03d}.png"
        filepath = output_dir / filename
        filepath.write_bytes(cover_data)
        
        # Store info
        covers_info.append({
            'index': i + 1,
            'filename': filename,
            'title': title,
            'author': author,
            'hash': book_hash,
            'pattern': pattern_name,
            'colors': colors[:2]  # Only show the two main colors
        })
        
        print(f"  Generated cover {i+1}/{args.number} ({pattern_name})")
    
    # Generate HTML gallery
    html_content = generate_html_gallery(
        output_dir, 
        covers_info,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        total_covers=args.number
    )
    
    html_path = output_dir / 'index.html'
    html_path.write_text(html_content)
    
    print(f"\nSuccess! Generated {args.number} covers in '{output_dir}'")
    print(f"View the gallery by opening: {html_path.absolute()}")


if __name__ == '__main__':
    main()