import pytest
from unittest.mock import patch
from io import StringIO
import sys
from cli.cli import main, format_output

def test_format_output():
    papers = [{
        'pubmed_id': '123',
        'title': 'Test Paper',
        'pub_date': '2023-01-01',
        'non_academic_authors': ['John Doe'],
        'company_affiliations': ['Pfizer'],
        'corresponding_emails': ['john@example.com']
    }]
    output = format_output(papers)
    assert "123" in output
    assert "Test Paper" in output
    assert "Pfizer" in output

def test_main_success(tmp_path):
    test_file = tmp_path / "output.csv"
    with patch('cli.cli.PubMedFetcher') as mock_fetcher:
        mock_instance = mock_fetcher.return_value
        mock_instance.fetch_papers.return_value = [{
            'pubmed_id': '123',
            'title': 'Test',
            'pub_date': '2023-01-01',
            'non_academic_authors': [],
            'company_affiliations': ['Pfizer'],
            'corresponding_emails': []
        }]
        
        sys.argv = ['cli.py', 'cancer', '-f', str(test_file)]
        main()
        
        assert test_file.exists()
        content = test_file.read_text()
        assert "123" in content
        assert "Pfizer" in content