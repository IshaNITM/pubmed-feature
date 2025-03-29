import pytest
from unittest.mock import patch
from backend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"PubMed Paper Fetcher" in response.data

def test_search_api(client):
    with patch('backend.app.fetcher.fetch_papers') as mock_fetch:
        mock_fetch.return_value = [{
            'pubmed_id': '123',
            'title': 'Test',
            'pub_date': '2023-01-01',
            'non_academic_authors': [],
            'company_affiliations': ['Pfizer'],
            'corresponding_emails': []
        }]
        
        response = client.post('/api/search', json={'query': 'cancer'})
        assert response.status_code == 200
        assert b"Pfizer" in response.data