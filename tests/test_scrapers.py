"""
Unit tests for IdeaHunter scrapers.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.scrapers.reddit_scraper import run as reddit_run
from backend.scrapers.hn_scraper import run as hn_run
from backend.scrapers.ph_scraper import run as ph_run
from backend.scrapers.trends_scraper import run as trends_run


class TestRedditScraper:
    """Test Reddit scraper."""

    @patch('backend.scrapers.reddit_scraper.requests.get')
    def test_reddit_scraper_success(self, mock_get):
        """Test successful Reddit scraping."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'data': {
                            'id': 'test1',
                            'title': 'Test post 1',
                            'selftext': 'Test content 1',
                            'subreddit': 'test',
                            'score': 100,
                            'created_utc': 1234567890
                        }
                    },
                    {
                        'data': {
                            'id': 'test2',
                            'title': 'Test post 2',
                            'selftext': 'Test content 2',
                            'subreddit': 'test',
                            'score': 50,
                            'created_utc': 1234567891
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        posts = reddit_run()

        assert len(posts) == 2
        assert posts[0]['source'] == 'reddit'
        assert posts[0]['id'] == 'test1'
        assert 'Test post 1' in posts[0]['content']

    @patch('backend.scrapers.reddit_scraper.requests.get')
    def test_reddit_scraper_api_error(self, mock_get):
        """Test Reddit scraper API error handling."""
        mock_get.side_effect = Exception("API Error")

        posts = reddit_run()

        # Should return empty list on error
        assert posts == []

    @patch('backend.scrapers.reddit_scraper.requests.get')
    def test_reddit_scraper_rate_limiting(self, mock_get):
        """Test Reddit scraper rate limiting."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': {'children': []}}
        mock_get.return_value = mock_response

        # Make multiple calls
        for _ in range(5):
            reddit_run()

        # Verify rate limiting was applied
        assert mock_get.call_count <= 5


class TestHNScraper:
    """Test Hacker News scraper."""

    @patch('backend.scrapers.hn_scraper.requests.get')
    def test_hn_scraper_success(self, mock_get):
        """Test successful HN scraping."""
        # Mock story IDs response
        mock_ids_response = Mock()
        mock_ids_response.status_code = 200
        mock_ids_response.json.return_value = [1, 2, 3]

        # Mock story details response
        mock_story_response = Mock()
        mock_story_response.status_code = 200
        mock_story_response.json.return_value = {
            'id': 1,
            'title': 'Test story',
            'text': 'Test text',
            'score': 100,
            'by': 'test_user',
            'time': 1234567890
        }

        mock_get.side_effect = [mock_ids_response, mock_story_response, mock_story_response, mock_story_response]

        posts = hn_run()

        assert len(posts) > 0
        assert posts[0]['source'] == 'hn'
        assert 'Test story' in posts[0]['content']

    @patch('backend.scrapers.hn_scraper.requests.get')
    def test_hn_scraper_api_error(self, mock_get):
        """Test HN scraper API error handling."""
        mock_get.side_effect = Exception("API Error")

        posts = hn_run()

        # Should return empty list on error
        assert posts == []

    @patch('backend.scrapers.hn_scraper.requests.get')
    def test_hn_scraper_empty_response(self, mock_get):
        """Test HN scraper with empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        posts = hn_run()

        assert posts == []


class TestProductHuntScraper:
    """Test Product Hunt scraper."""

    @patch('backend.scrapers.ph_scraper.settings')
    @patch('backend.scrapers.ph_scraper.requests.post')
    def test_ph_scraper_success(self, mock_post, mock_settings):
        """Test successful Product Hunt scraping."""
        mock_settings.PRODUCTHUNT_TOKEN = 'test_token'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'posts': {
                    'edges': [
                        {
                            'node': {
                                'id': '1',
                                'name': 'Test Product',
                                'tagline': 'Test tagline',
                                'description': 'Test description',
                                'votesCount': 100,
                                'website': 'https://example.com'
                            }
                        }
                    ]
                }
            }
        }
        mock_post.return_value = mock_response

        posts = ph_run()

        assert len(posts) == 1
        assert posts[0]['source'] == 'producthunt'
        assert 'Test Product' in posts[0]['content']

    @patch('backend.scrapers.ph_scraper.settings')
    def test_ph_scraper_no_token(self, mock_settings):
        """Test Product Hunt scraper without token."""
        mock_settings.PRODUCTHUNT_TOKEN = None

        posts = ph_run()

        # Should return empty list when no token
        assert posts == []

    @patch('backend.scrapers.ph_scraper.settings')
    @patch('backend.scrapers.ph_scraper.requests.post')
    def test_ph_scraper_api_error(self, mock_post, mock_settings):
        """Test Product Hunt scraper API error handling."""
        mock_settings.PRODUCTHUNT_TOKEN = 'test_token'
        mock_post.side_effect = Exception("API Error")

        posts = ph_run()

        # Should return empty list on error
        assert posts == []


class TestTrendsScraper:
    """Test Google Trends scraper."""

    @patch('backend.scrapers.trends_scraper.TrendReq')
    def test_trends_scraper_success(self, mock_trend_req):
        """Test successful Google Trends scraping."""
        # Mock pytrends instance
        mock_pytrends = MagicMock()
        mock_trend_req.return_value = mock_pytrends

        # Mock related queries response
        import pandas as pd
        mock_df = pd.DataFrame({
            'query': ['test query 1', 'test query 2'],
            'value': ['Breakout', '100']
        })

        mock_pytrends.related_queries.return_value = {
            'test keyword': {
                'rising': mock_df
            }
        }

        posts = trends_run()

        assert len(posts) > 0
        assert posts[0]['source'] == 'trends'
        assert 'Rising search query' in posts[0]['content']

    @patch('backend.scrapers.trends_scraper.TrendReq')
    def test_trends_scraper_init_error(self, mock_trend_req):
        """Test Google Trends scraper initialization error."""
        mock_trend_req.side_effect = Exception("Init Error")

        posts = trends_run()

        # Should return empty list on error
        assert posts == []

    @patch('backend.scrapers.trends_scraper.TrendReq')
    def test_trends_scraper_empty_results(self, mock_trend_req):
        """Test Google Trends scraper with empty results."""
        mock_pytrends = MagicMock()
        mock_trend_req.return_value = mock_pytrends

        # Mock empty response
        mock_pytrends.related_queries.return_value = {
            'test keyword': {
                'rising': None
            }
        }

        posts = trends_run()

        # Should return empty list when no results
        assert posts == []


class TestScraperValidation:
    """Test scraper output validation."""

    @patch('backend.scrapers.reddit_scraper.requests.get')
    def test_reddit_post_validation(self, mock_get):
        """Test Reddit post output validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'data': {
                            'id': 'test1',
                            'title': 'Test post',
                            'selftext': 'Test content',
                            'subreddit': 'test',
                            'score': 100,
                            'created_utc': 1234567890
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        posts = reddit_run()

        # Validate post structure
        assert all('id' in post for post in posts)
        assert all('source' in post for post in posts)
        assert all('content' in post for post in posts)
        assert all('metadata' in post for post in posts)

    @patch('backend.scrapers.reddit_scraper.requests.get')
    def test_reddit_post_sanitization(self, mock_get):
        """Test Reddit post content sanitization."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'data': {
                            'id': 'test1',
                            'title': '<script>alert("xss")</script> Test post',
                            'selftext': 'Test content',
                            'subreddit': 'test',
                            'score': 100,
                            'created_utc': 1234567890
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        posts = reddit_run()

        # Content should be sanitized
        assert '<script>' not in posts[0]['content']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])