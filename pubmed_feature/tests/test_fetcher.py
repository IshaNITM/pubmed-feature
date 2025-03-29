import pytest
from unittest.mock import patch, Mock
from backend.fetcher import PubMedFetcher
from bs4 import BeautifulSoup

@pytest.fixture
def fetcher():
    return PubMedFetcher(api_key="test_key", debug=True)

def test_fetch_papers_success(fetcher):
    with patch('requests.get') as mock_get:
        # Mock search response
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            'esearchresult': {'idlist': ['123', '456']}
        }
        mock_search_response.raise_for_status.return_value = None
        
        # Mock fetch response
        mock_fetch_response = Mock()
        mock_fetch_response.text = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation Status="MEDLINE" Owner="NLM">
                    <PMID Version="1">123</PMID>
                    <Article>
                        <ArticleTitle>Test Paper</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_fetch_response.raise_for_status.return_value = None
        
        mock_get.side_effect = [mock_search_response, mock_fetch_response]
        
        papers = fetcher.fetch_papers("test query")
        assert len(papers) == 0  # No company affiliations in this test XML

def test_parse_author_with_company(fetcher):
    xml = """
    <Author ValidYN="Y">
        <LastName>Doe</LastName>
        <ForeName>John</ForeName>
        <Affiliation>Pfizer Inc., New York</Affiliation>
        <Email>john@example.com</Email>
    </Author>
    """
    soup = BeautifulSoup(xml, 'lxml-xml')
    author = fetcher._parse_author(soup)
    assert author['name'] == "John Doe"
    assert "Pfizer" in author['companies']
    assert author['is_non_academic'] is True
    assert author['email'] == "john@example.com"

def test_identify_company(fetcher):
    assert fetcher._identify_company("Pfizer Inc.") == "Pfizer"
    assert fetcher._identify_company("Harvard University") is None
    assert fetcher._identify_company("Novartis Pharmaceuticals") == "Novartis"
    assert fetcher._identify_company("Bayer Healthcare LLC") == "Bayer"
    assert fetcher._identify_company("MIT Department of Biology") is None