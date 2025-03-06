# analysis.py
import pandas as pd
import json
import os
import logging
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("analysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define paths
CONTENT_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\extracted_content"
VALIDATION_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\validation_results"
ANALYSIS_OUTPUT_DIR = r"D:\RS_AI\ALL DOCS\Dreambot Api Docs- Classes_Enums\analysis_results"

# Ensure output directory exists
os.makedirs(ANALYSIS_OUTPUT_DIR, exist_ok=True)

def analyze_validation_results():
    """Analyze validation results to understand the specific issues"""
    # Load files needing attention
    files_needing_attention = pd.read_csv(os.path.join(VALIDATION_DIR, 'files_needing_attention.csv'))
    
    # Count issues by type
    issue_counter = Counter()
    for issue_str in files_needing_attention['Missing Elements'].dropna():
        for issue in issue_str.split(', '):
            issue_counter[issue] += 1
    
    # Count issues by entity type
    type_counter = Counter(files_needing_attention['Type'])
    
    # Analyze completeness distribution
    completeness_ranges = {
        '0.0-0.2': 0,
        '0.2-0.4': 0,
        '0.4-0.6': 0,
        '0.6-0.8': 0,
        '0.8-1.0': 0
    }
    
    for completeness in files_needing_attention['Completeness']:
        if completeness < 0.2:
            completeness_ranges['0.0-0.2'] += 1
        elif completeness < 0.4:
            completeness_ranges['0.2-0.4'] += 1
        elif completeness < 0.6:
            completeness_ranges['0.4-0.6'] += 1
        elif completeness < 0.8:
            completeness_ranges['0.6-0.8'] += 1
        else:
            completeness_ranges['0.8-1.0'] += 1
    
    # Sample problematic files for deeper analysis
    sample_files = []
    for _, row in files_needing_attention.sort_values('Completeness').head(5).iterrows():
        file_path = os.path.join(CONTENT_DIR, row['File'])
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                sample_files.append({
                    "file": row['File'],
                    "issues": row['Missing Elements'],
                    "completeness": row['Completeness'],
                    "content_structure": {
                        "has_description": bool(data.get("description")),
                        "method_count": len(data.get("methods", [])),
                        "field_count": len(data.get("fields", [])),
                        "constructor_count": len(data.get("constructors", [])),
                        "enum_constant_count": len(data.get("enum_constants", [])) if "enum_constants" in data else 0
                    }
                })
            except Exception as e:
                logger.error(f"Error analyzing sample file {file_path}: {str(e)}")
    
    # Gather HTML structure analysis
    html_analysis = pd.read_csv(os.path.join(VALIDATION_DIR, 'html_analysis.csv'))
    html_equiv_count = sum(html_analysis['Has JSON Equivalent'] == 'True')
    html_no_equiv_count = sum(html_analysis['Has JSON Equivalent'] == 'False')
    
    # Prepare analysis output
    analysis_results = {
        "total_files_needing_attention": len(files_needing_attention),
        "issues_by_type": dict(issue_counter.most_common()),
        "entity_types": dict(type_counter.most_common()),
        "completeness_distribution": completeness_ranges,
        "html_files": {
            "with_json_equivalent": html_equiv_count,
            "without_json_equivalent": html_no_equiv_count
        },
        "sample_problematic_files": sample_files
    }
    
    # Save analysis results
    with open(os.path.join(ANALYSIS_OUTPUT_DIR, 'analysis_results.json'), 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2)
    
    # Print summary
    logger.info("Analysis Results:")
    logger.info(f"Total files needing attention: {len(files_needing_attention)}")
    logger.info("\nTop issues:")
    for issue, count in issue_counter.most_common(5):
        logger.info(f"  {issue}: {count}")
    
    logger.info("\nEntity types with issues:")
    for entity_type, count in type_counter.most_common():
        logger.info(f"  {entity_type}: {count}")
    
    logger.info("\nCompleteness distribution:")
    for range_name, count in completeness_ranges.items():
        logger.info(f"  {range_name}: {count}")
    
    logger.info(f"\nDetailed analysis saved to {os.path.join(ANALYSIS_OUTPUT_DIR, 'analysis_results.json')}")
    
    return analysis_results

def analyze_html_content():
    """Analyze the HTML content for extraction patterns"""
    html_analysis = pd.read_csv(os.path.join(VALIDATION_DIR, 'html_analysis.csv'))
    
    # Select 3 HTML files for structure analysis
    structure_samples = []
    for entity_type in ['class', 'interface', 'enum']:
        sample_rows = html_analysis[html_analysis['Entity Type'] == entity_type].head(1)
        if not sample_rows.empty:
            for _, row in sample_rows.iterrows():
                html_file = os.path.join(CONTENT_DIR, row['File'])
                if os.path.exists(html_file):
                    structure_samples.append({
                        "file": row['File'],
                        "entity_type": row['Entity Type'],
                        "html_path": html_file
                    })
    
    logger.info(f"Selected {len(structure_samples)} HTML files for structure analysis:")
    for sample in structure_samples:
        logger.info(f"  {sample['file']} ({sample['entity_type']})")
    
    # Optional: Extract structure patterns from HTML files
    # This would require BeautifulSoup and more complex parsing
    # For now, we'll just list the sample files
    
    return structure_samples

if __name__ == "__main__":
    logger.info("Starting DreamBot API documentation analysis")
    analysis_results = analyze_validation_results()
    structure_samples = analyze_html_content()
    logger.info("Analysis complete")