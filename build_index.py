#!/usr/bin/env python3
"""
Generate an index.html linking to all HTML files in a directory tree.
Supports nested folder structure for GitHub Pages hosting.
"""

from pathlib import Path
import argparse
import os
from collections import defaultdict
from datetime import datetime

# Configuration constants
SECTION_ORDER = ["archipelago", "wwrando", "Root"]
SUBSECTION_ORDER = ["single-player", "p1", "p2", "p3", "combined", "Files"]

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg: #0d1117;
            --card-bg: #161b22;
            --card-hover: #21262d;
            --text: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --border: #30363d;
            --section-bg: #0d1117;
        }}
        
        * {{ box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            background: var(--bg);
            color: var(--text);
        }}
        
        h1 {{
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.75rem;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: var(--text-muted);
            margin-bottom: 2rem;
        }}
        
        .section {{
            margin-bottom: 2.5rem;
        }}
        
        .section-title {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .section-title::before {{
            content: "📁";
        }}
        
        .subsection {{
            margin-left: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        
        .subsection-title {{
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
            color: var(--text);
        }}
        
        .file-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 0.75rem;
        }}
        
        .file-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            transition: all 0.2s ease;
        }}
        
        .file-card:hover {{
            background: var(--card-hover);
            border-color: var(--accent);
            transform: translateY(-2px);
        }}
        
        .file-link {{
            display: block;
            padding: 1rem;
            text-decoration: none;
            color: var(--text);
        }}
        
        .file-name {{
            font-weight: 500;
            margin-bottom: 0.25rem;
        }}
        
        .file-type {{
            display: inline-block;
            font-size: 0.7rem;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            margin-right: 0.5rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .type-heatmap {{ background: #238636; color: #fff; }}
        .type-dashboard {{ background: #8957e5; color: #fff; }}
        .type-stats {{ background: #1f6feb; color: #fff; }}
        .type-other {{ background: var(--border); color: var(--text); }}
        
        .file-meta {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
        }}
        
        footer {{
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.85rem;
            text-align: center;
        }}
        
        a {{ color: var(--accent); }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="subtitle">Interactive visualizations of item placement distributions across randomizer seeds.</p>
    
    {content}

    <footer>
        Generated {timestamp} by build_index.py
    </footer>
</body>
</html>
"""

SECTION_TEMPLATE = """
<div class="section">
    <div class="section-title">{section_name}</div>
    {subsections}
</div>
"""

SUBSECTION_TEMPLATE = """
<div class="subsection">
    <div class="subsection-title">{subsection_name}</div>
    <div class="file-grid">
        {cards}
    </div>
</div>
"""

CARD_TEMPLATE = """
<div class="file-card">
    <a href="{href}" class="file-link">
        <div class="file-name">
            <span class="file-type {type_class}">{file_type}</span>
            {display_name}
        </div>
        <div class="file-meta">{size_kb:.1f} KB</div>
    </a>
</div>
"""


def get_file_type(filename: str) -> tuple[str, str]:
    """Return (type_name, css_class) for a file."""
    name = filename.lower()
    if "-heatmap" in name and name.endswith(".html"):
        return "Heatmap", "type-heatmap"
    elif "-items" in name and name.endswith(".html"):
        return "Items", "type-dashboard"
    elif "-locations" in name and name.endswith(".html"):
        return "Locations", "type-stats"
    else:
        return "View", "type-other"


def get_display_name(filename: str) -> str:
    """Generate a human-readable display name from filename."""
    name = Path(filename).stem.lower()
    
    if "-heatmap" in name:
        return "Overview Heatmap"
    elif "-items" in name:
        return "By Item"
    elif "-locations" in name:
        return "By Location"
    
    return Path(filename).stem.replace("-", " ").replace("_", " ").title()


def format_section_name(name: str) -> str:
    """Format a folder name into a display name."""
    replacements = {
        "archipelago": "Archipelago (MultiworldGG)",
        "wwrando": "WWRando (Standalone)",
        "single-player": "Single Player (1P)",
        "combined": "3-Player Combined",
        "p1": "3-Player: Player 1",
        "p2": "3-Player: Player 2", 
        "p3": "3-Player: Player 3",
    }
    return replacements.get(name.lower(), name.replace("-", " ").replace("_", " ").title())


def build_file_tree(base_dir: Path) -> dict[str, dict[str, list[Path]]]:
    """
    Build a nested dictionary of HTML/CSV files organized by directory.
    Returns: {section: {subsection: [file_paths]}}
    """
    tree = defaultdict(lambda: defaultdict(list))
    
    for file in sorted(base_dir.rglob("*.html")):
            if file.name == "index.html":
                continue
            
            # Get relative path from base_dir
            rel_path = file.relative_to(base_dir)
            parts = rel_path.parts
            
            if len(parts) == 1:
                # File directly in base_dir
                tree["Root"]["Files"].append(file)
            elif len(parts) == 2:
                # One level deep: section/file.html
                section = parts[0]
                tree[section]["Files"].append(file)
            else:
                # Two+ levels: section/subsection/file.html
                section = parts[0]
                subsection = parts[1]
                tree[section][subsection].append(file)

    return tree


def generate_cards(files: list[Path], base_dir: Path, output_dir: Path) -> str:
    """Generate HTML cards for a list of files."""
    cards = []
    
    # Sort: heatmap first, then items, then locations, then other
    def sort_key(f):
        name = f.name.lower()
        if "-heatmap" in name:
            return (0, name)
        elif "-items" in name:
            return (1, name)
        elif "-locations" in name:
            return (2, name)
        else:
            return (3, name)
    
    for f in sorted(files, key=sort_key):
        # Only show HTML files
        if f.suffix.lower() != ".html":
            continue
            
        file_type, type_class = get_file_type(f.name)
        display_name = get_display_name(f.name)
        size_kb = f.stat().st_size / 1024
        
        # Calculate relative href from output directory to file
        try:
            href = f.relative_to(output_dir).as_posix()
        except ValueError:
            # File is not under output_dir, compute relative path
            href = Path(os.path.relpath(f, output_dir)).as_posix()
        
        cards.append(CARD_TEMPLATE.format(
            href=href,
            type_class=type_class,
            file_type=file_type,
            display_name=display_name,
            size_kb=size_kb
        ))
    
    return "\n".join(cards)


def main():
    parser = argparse.ArgumentParser(description="Build index.html for nested HTML file structure")
    parser.add_argument(
        "target_dir", nargs="?", default="./item-distributions",
        help="Directory to scan"
    )
    parser.add_argument(
        "--title", default="TWW Randomizer Item Distributions",
        help="Page title"
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output index.html path (default: target_dir/index.html)"
    )
    args = parser.parse_args()
    
    base_dir = Path(args.target_dir).resolve()
    output_path = Path(args.output).resolve() if args.output else base_dir / "index.html"
    
    print(f"Scanning {base_dir}...")
    tree = build_file_tree(base_dir)
    
    # Generate content sections
    sections_html = []
    total_files = 0
    
    for section in SECTION_ORDER:
        if section not in tree:
            continue
            
        subsections = tree[section]
        subsections_html = []
        
        for subsection in SUBSECTION_ORDER:
            if subsection not in subsections:
                continue
                
            files = subsections[subsection]
            if not files:
                continue
            
            cards_html = generate_cards(files, base_dir, output_path.parent)
            if not cards_html.strip():
                continue
                
            total_files += len([f for f in files if f.suffix.lower() == ".html"])
            
            subsection_name = format_section_name(subsection) if subsection != "Files" else ""
            
            if subsection == "Files":
                # No subsection header for direct files
                subsections_html.append(f'<div class="file-grid">{cards_html}</div>')
            else:
                subsections_html.append(SUBSECTION_TEMPLATE.format(
                    subsection_name=subsection_name,
                    cards=cards_html
                ))
        
        if subsections_html:
            if section == "Root":
                sections_html.append("\n".join(subsections_html))
            else:
                sections_html.append(SECTION_TEMPLATE.format(
                    section_name=format_section_name(section),
                    subsections="\n".join(subsections_html)
                ))
    
    # Generate final HTML
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    output_html = TEMPLATE.format(
        title=args.title,
        content="\n".join(sections_html) if sections_html else "<p>No reports found.</p>",
        timestamp=timestamp
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    
    print(f"Generated {output_path} with {total_files} files in {len(tree)} sections.")


if __name__ == "__main__":
    main()
