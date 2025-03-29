# fetcher.py
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
from datetime import datetime
import re

class PubMedFetcher:
    ACADEMIC_KEYWORDS = {
        'university', 'college', 'institute', 'school', 
        'hospital', 'lab', 'faculty', 'academy', 'research center',
        'medical center', 'clinic'
    }
    
    COMPANY_KEYWORDS = {
        'pharma', 'biotech', 'pharmaceutical', 'pharmaceuticals','inc', 'ltd',
        'llc', 'corp', 'company', 'laboratories', 'healthcare',
        'holdings', 'group', 'therapeutics', 'vaccines', 'genetics',
        'innovation', 'sciences', 'research'
    }
    
    def __init__(self, api_key: str = None, debug: bool = False):
        self.api_key = api_key
        self.debug = debug
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        
    def fetch_papers(self, query: str, max_results: int = 50) -> List[Dict]:
        """Fetch papers from PubMed with company affiliations"""
        try:
            # Search PubMed
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'retmode': 'json',
                'api_key': self.api_key
            }
            
            search_url = f"{self.base_url}/esearch.fcgi"
            response = requests.get(search_url, params=search_params)
            response.raise_for_status()
            
            id_list = response.json().get('esearchresult', {}).get('idlist', [])
            if not id_list:
                if self.debug:
                    print("No papers found for query")
                return []
            
            # Fetch details
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(id_list),
                'retmode': 'xml',
                'api_key': self.api_key
            }
            
            fetch_url = f"{self.base_url}/efetch.fcgi"
            fetch_response = requests.get(fetch_url, params=fetch_params)
            fetch_response.raise_for_status()
            
            return self._parse_papers(fetch_response.text)
            
        except Exception as e:
            if self.debug:
                print(f"Error fetching papers: {str(e)}")
            raise
    
    def _parse_papers(self, xml_content: str) -> List[Dict]:
        """Parse PubMed XML into structured data"""
        try:
            # First try lxml's XML parser
            soup = BeautifulSoup(xml_content, 'lxml-xml')
        except Exception as e:
            if self.debug:
                print(f"XML parsing error with lxml: {e}")
            try:
                # Fallback to html parser
                soup = BeautifulSoup(xml_content, 'html.parser')
            except Exception as e:
                if self.debug:
                    print(f"HTML parsing failed: {e}")
                return []
        
        papers = []
        
        for article in soup.find_all('PubmedArticle'):
            paper = {
                'pubmed_id': self._get_text(article, 'PMID'),
                'title': self._get_text(article, 'ArticleTitle'),
                'pub_date': self._get_pub_date(article),
                'authors': [],
                'non_academic_authors': set(),
                'company_affiliations': set(),
                'corresponding_emails': set()
            }
            
            # Process authors
            for author in article.find_all('Author'):
                author_data = self._parse_author(author)
                if author_data:
                    paper['authors'].append(author_data)
                    
                    # Track non-academic authors
                    if author_data.get('is_non_academic', False):
                        paper['non_academic_authors'].add(author_data['name'])
                    
                    # Track company affiliations
                    if author_data.get('companies'):
                        paper['company_affiliations'].update(author_data['companies'])
                    
                    # Track corresponding author emails
                    if author_data.get('is_corresponding', False) and author_data.get('email'):
                        paper['corresponding_emails'].add(author_data['email'])
            
            # Only include papers with company affiliations
            if paper['company_affiliations']:
                # Convert sets to lists for JSON serialization
                paper['non_academic_authors'] = sorted(paper['non_academic_authors'])
                paper['company_affiliations'] = sorted(paper['company_affiliations'])
                paper['corresponding_emails'] = sorted(paper['corresponding_emails'])
                papers.append(paper)
        
        return papers
    
    def _parse_author(self, author) -> Optional[Dict]:
        """Parse author information with academic/company classification"""
        last_name = self._get_text(author, 'LastName')
        fore_name = self._get_text(author, 'ForeName')
        
        if not last_name:
            return None
            
        author_data = {
            'name': f"{fore_name} {last_name}".strip(),
            'is_corresponding': self._is_corresponding_author(author),
            'is_non_academic': False,
            'companies': set(),
            'email': self._extract_author_email(author)
        }
        
        # Process affiliations
        affil_texts = [affil.text.strip() for affil in author.find_all('Affiliation') if affil.text.strip()]
        
        # Check all affiliations for company/academic status
        academic_affils = 0
        for affil_text in affil_texts:
            company = self._identify_company(affil_text)
            if company:
                author_data['companies'].add(company)
            elif not self._is_academic_affiliation(affil_text):
                author_data['is_non_academic'] = True
        
        # If any company affiliation found, mark as non-academic
        if author_data['companies']:
            author_data['is_non_academic'] = True
        
        # If no email found in author element, check affiliations
        if not author_data['email']:
            for affil_text in affil_texts:
                if '@' in affil_text:
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+', affil_text)
                    if email_match:
                        author_data['email'] = email_match.group(0)
                        break
        
        # Convert companies set to list
        author_data['companies'] = list(author_data['companies'])
        
        return author_data
    
    def _is_corresponding_author(self, author) -> bool:
        """Check if author is marked as corresponding"""
        # Check for ValidYN flag
        if author.get('ValidYN', 'N') == 'Y':
            return True
        
        # Check for AffiliationInfo with corresponding marker
        for affil in author.find_all('AffiliationInfo'):
            if affil.get('Corresp', 'N') == 'Y':
                return True
        
        return False
    
    def _extract_author_email(self, author) -> Optional[str]:
        """Extract email from author element"""
        email = author.find('Email')
        if email and email.text:
            return email.text.strip()
        return None
    
    def _is_academic_affiliation(self, affiliation: str) -> bool:
        """Check if affiliation appears to be academic"""
        affil_lower = affiliation.lower()
        return any(
            re.search(rf'\b{re.escape(keyword)}\b', affil_lower)
            for keyword in self.ACADEMIC_KEYWORDS
        )
    
    def _identify_company(self, affiliation: str) -> Optional[str]:
        """Identify pharmaceutical/biotech companies with better heuristics"""
        # Skip academic affiliations
        if self._is_academic_affiliation(affiliation):
            return None
            
        # Check for company patterns
        affil_lower = affiliation.lower()
        if any(
            re.search(rf'\b{re.escape(keyword)}\b', affil_lower)
            for keyword in self.COMPANY_KEYWORDS
        ):
            return self._clean_company_name(affiliation)
        
        return None
    
    def _clean_company_name(self, name: str) -> str:
        """Clean up company name with better patterns"""
        patterns_to_remove = [
            r'\b(inc|ltd|llc|corp|corporation|company|gmbh|co|kg)\b.*$',
            r'\b(pharma|pharmaceuticals?|biotech|healthcare|therapeutics|vaccines|genetics)\b.*$',
            r',.*$',
            r'\(.*\)',
            r'\b\d+\b',
            r'[^\w\s-]',
            r'\b(division|department|unit|center|centre)\b.*$'
        ]
        
        cleaned = name.strip()
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Additional cleaning steps
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Collapse multiple spaces
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _get_text(self, element, tag_name: str) -> str:
        """Helper to get text from XML element"""
        if element is None:
            return ''
        tag = element.find(tag_name)
        return tag.text.strip() if tag else ''
    
    def _get_pub_date(self, article) -> str:
        """Extract publication date in YYYY-MM-DD format"""
        pub_date = article.find('PubDate')
        if not pub_date:
            return ''
            
        year = self._get_text(pub_date, 'Year') or ''
        month = self._get_text(pub_date, 'Month') or '01'
        day = self._get_text(pub_date, 'Day') or '01'
        
        # Handle month abbreviations
        if len(month) == 3 and month.isalpha():
            try:
                month = str(datetime.strptime(month, '%b').month).zfill(2)
            except ValueError:
                month = '01'
        
        return f"{year}-{month}-{day}" if year else ''