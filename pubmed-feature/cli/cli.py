import argparse
import sys
from typing import Optional
from pathlib import Path
from backend.fetcher import PubMedFetcher
import csv

def main():
    parser = argparse.ArgumentParser(
        description="Fetch PubMed papers with pharmaceutical/biotech company affiliations"
    )
    parser.add_argument('query', type=str, help='PubMed search query')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('-f', '--file', type=str, help='Output CSV file path')
    
    args = parser.parse_args()
    
    try:
        fetcher = PubMedFetcher(api_key="f41c8f35f5f1a7ea643e4b54c7423c09df08", debug=args.debug)
        papers = fetcher.fetch_papers(args.query)
        
        if not papers:
            print("No papers found with company affiliations", file=sys.stderr)
            sys.exit(1)
            
        output = format_output(papers)
        
        if args.file:
            save_to_csv(output, args.file)
            print(f"Results saved to {args.file}", file=sys.stderr)
        else:
            print(output)
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

def format_output(papers: list) -> str:
    """Format papers as CSV string"""
    output = []
    headers = [
        "PubmedID", "Title", "Publication Date", 
        "Non-academic Author(s)", "Company Affiliation(s)", 
        "Corresponding Author Email"
    ]
    output.append(",".join(headers))
    
    for paper in papers:
        row = [
            paper['pubmed_id'],
            f'"{paper["title"]}"' if paper['title'] else '',
            paper['pub_date'] or '',
            "; ".join(paper['non_academic_authors']) if paper['non_academic_authors'] else '',
            "; ".join(paper['company_affiliations']) if paper['company_affiliations'] else '',
            "; ".join(paper['corresponding_emails']) if paper.get('corresponding_emails') else ''
        ]
        output.append(",".join(row))
    
    return "\n".join(output)

def save_to_csv(data: str, filepath: str):
    """Save data to CSV file"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(data)

if __name__ == '__main__':
    main()