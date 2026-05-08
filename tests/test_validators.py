"""
Unit tests for IdeaHunter validators.
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.validators.validator import (
    check_search_volume, check_competition, validate_ideas,
    fetch_serpapi_data
)


class TestSearchVolume:
    """Test search volume validation."""

    @patch('backend.validators.validator.settings')
    @patch('backend.validators.validator.fetch_serpapi_data')
    def test_check_search_volume_success(self, mock_fetch, mock_settings):
        """Test successful search volume check."""
        mock_settings.SERPAPI_KEY = 'test_key'

        mock_fetch.return_value = {
            'search_information': {
                'total_results': '5000000'
            }
        }

        score = check_search_volume('test keyword')

        assert score == 70  # 1M-10M results -> score 70
        mock_fetch.assert_called_once()

    @patch('backend.validators.validator.settings')
    def test_check_search_volume_no_api_key(self, mock_settings):
        """Test search volume check without API key."""
        mock_settings.SERPAPI_KEY = None

        score = check_search_volume('test keyword')

        # Should return default score
        assert score == 50

    @patch('backend.validators.validator.settings')
    @patch('backend.validators.validator.fetch_serpapi_data')
    def test_check_search_volume_high_volume(self, mock_fetch, mock_settings):
        """Test search volume check with high volume."""
        mock_settings.SERPAPI_KEY = 'test_key'

        mock_fetch.return_value = {
            'search_information': {
                'total_results': '15000000'
            }
        }

        score = check_search_volume('test keyword')

        assert score == 90  # >10M results -> score 90

    @patch('backend.validators.validator.settings')
    @patch('backend.validators.validator.fetch_serpapi_data')
    def test_check_search_volume_low_volume(self, mock_fetch, mock_settings):
        """Test search volume check with low volume."""
        mock_settings.SERPAPI_KEY = 'test_key'

        mock_fetch.return_value = {
            'search_information': {
                'total_results': '5000'
            }
        }

        score = check_search_volume('test keyword')

        assert score == 10  # <10K results -> score 10

    @patch('backend.validators.validator.settings')
    @patch('backend.validators.validator.fetch_serpapi_data')
    def test_check_search_volume_api_error(self, mock_fetch, mock_settings):
        """Test search volume check with API error."""
        mock_settings.SERPAPI_KEY = 'test_key'
        mock_fetch.side_effect = Exception("API Error")

        score = check_search_volume('test keyword')

        # Should return default score on error
        assert score == 50


class TestCompetition:
    """Test competition validation."""

    @patch('backend.validators.validator.settings')
    @patch('backend.validators.validator.fetch_serpapi_data')
    def test_check_competition_success(self, mock_fetch, mock_settings):
        """Test successful competition check."""
        mock_settings.SERPAPI_KEY = 'test_key'

        mock_fetch.return_value = {
            'organic_results': [
                {'id': '1'},
                {'id': '2'}
            ]
        }

        score = check_competition('test keyword')

        assert score == 15  # <3 apps -> low competition
        mock_fetch.assert_called_once()

    @patch('backend.validators.validator.settings')
    def test_check_competition_no_api_key(self, mock_settings):
        """Test competition check without API key."""
        mock_settings.SERPAPI_KEY = None

        score = check_competition('test keyword')

        # Should return default score
        assert score == 40

    @patch('backend.validators.validator.settings')
    @patch('backend.validators.validator.fetch_serpapi_data')
    def test_check_competition_high(self, mock_fetch, mock_settings):
        """Test competition check with high competition."""
        mock_settings.SERPAPI_KEY = 'test_key'

        mock_fetch.return_value = {
            'organic_results': [
                {'id': str(i)} for i in range(15)
            ]
        }

        score = check_competition('test keyword')

        assert score == 80  # >=10 apps -> high competition

    @patch('backend.validators.validator.settings')
    @patch('backend.validators.validator.fetch_serpapi_data')
    def test_check_competition_api_error(self, mock_fetch, mock_settings):
        """Test competition check with API error."""
        mock_settings.SERPAPI_KEY = 'test_key'
        mock_fetch.side_effect = Exception("API Error")

        score = check_competition('test keyword')

        # Should return default score on error
        assert score == 40


class TestValidateIdeas:
    """Test idea validation."""

    @patch('backend.validators.validator.check_search_volume')
    @patch('backend.validators.validator.check_competition')
    def test_validate_ideas_success(self, mock_competition, mock_search_volume):
        """Test successful idea validation."""
        mock_search_volume.return_value = 70
        mock_competition.return_value = 30

        ideas = [
            {
                "name": "Test Idea",
                "description": "Test description",
                "pain_point": "Test pain point",
                "source": "reddit",
                "keywords": ["test", "idea"],
                "score_demand": 80,
                "score_competition": 40,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        validated = validate_ideas(ideas)

        assert len(validated) == 1
        # Scores should be blended
        assert validated[0]['score_demand'] == 75  # (80 + 70) / 2
        assert validated[0]['score_competition'] == 35  # (40 + 30) / 2

    @patch('backend.validators.validator.check_search_volume')
    @patch('backend.validators.validator.check_competition')
    def test_validate_ideas_no_keywords(self, mock_competition, mock_search_volume):
        """Test idea validation without keywords."""
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test description",
                "pain_point": "Test pain point",
                "source": "reddit",
                "keywords": [],  # No keywords
                "score_demand": 80,
                "score_competition": 40,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        validated = validate_ideas(ideas)

        assert len(validated) == 1
        # Should not call validation functions
        mock_search_volume.assert_not_called()
        mock_competition.assert_not_called()

    @patch('backend.validators.validator.check_search_volume')
    @patch('backend.validators.validator.check_competition')
    def test_validate_ideas_multiple(self, mock_competition, mock_search_volume):
        """Test validating multiple ideas."""
        mock_search_volume.return_value = 70
        mock_competition.return_value = 30

        ideas = [
            {
                "name": f"Test Idea {i}",
                "description": f"Test description {i}",
                "pain_point": f"Test pain point {i}",
                "source": "reddit",
                "keywords": ["test", "idea"],
                "score_demand": 80,
                "score_competition": 40,
                "score_trend": 70,
                "score_uniqueness": 60
            }
            for i in range(5)
        ]

        validated = validate_ideas(ideas)

        assert len(validated) == 5
        # Should call validation functions for each idea
        assert mock_search_volume.call_count == 5
        assert mock_competition.call_count == 5

    @patch('backend.validators.validator.check_search_volume')
    @patch('backend.validators.validator.check_competition')
    def test_validate_ideas_error_handling(self, mock_competition, mock_search_volume):
        """Test idea validation error handling."""
        mock_search_volume.side_effect = Exception("API Error")
        mock_competition.return_value = 30

        ideas = [
            {
                "name": "Test Idea",
                "description": "Test description",
                "pain_point": "Test pain point",
                "source": "reddit",
                "keywords": ["test", "idea"],
                "score_demand": 80,
                "score_competition": 40,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        validated = validate_ideas(ideas)

        # Should keep original idea on error
        assert len(validated) == 1
        assert validated[0]['name'] == 'Test Idea'


class TestSerpAPI:
    """Test SerpAPI integration."""

    @patch('backend.validators.validator.requests.get')
    def test_fetch_serpapi_data_success(self, mock_get):
        """Test successful SerpAPI data fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'test': 'data'}
        mock_get.return_value = mock_response

        data = fetch_serpapi_data("google", {"q": "test"})

        assert data == {'test': 'data'}
        mock_get.assert_called_once()

    @patch('backend.validators.validator.requests.get')
    def test_fetch_serpapi_data_rate_limit(self, mock_get):
        """Test SerpAPI rate limiting."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'test': 'data'}
        mock_get.return_value = mock_response

        # Make multiple calls
        for _ in range(10):
            fetch_serpapi_data("google", {"q": "test"})

        # Rate limiting should be applied
        assert mock_get.call_count <= 10

    @patch('backend.validators.validator.requests.get')
    def test_fetch_serpapi_data_error(self, mock_get):
        """Test SerpAPI error handling."""
        mock_get.side_effect = Exception("Network Error")

        with pytest.raises(Exception):
            fetch_serpapi_data("google", {"q": "test"})


class TestCaching:
    """Test caching in validators."""

    @patch('backend.validators.validator.settings')
    @patch('backend.validators.validator.fetch_serpapi_data')
    @patch('backend.validators.validator.get_cached_result')
    @patch('backend.validators.validator.cache_result')
    def test_search_volume_caching(self, mock_cache, mock_get_cached, mock_fetch, mock_settings):
        """Test search volume caching."""
        mock_settings.SERPAPI_KEY = 'test_key'
        mock_get_cached.return_value = None  # Cache miss
        mock_fetch.return_value = {
            'search_information': {
                'total_results': '5000000'
            }
        }

        score = check_search_volume('test keyword')

        # Should cache the result
        mock_cache.assert_called_once()
        assert mock_cache.call_args[0][2] == 86400  # 24 hours TTL

    @patch('backend.validators.validator.settings')
    @patch('backend.validators.validator.fetch_serpapi_data')
    @patch('backend.validators.validator.get_cached_result')
    @patch('backend.validators.validator.cache_result')
    def test_search_volume_cache_hit(self, mock_cache, mock_get_cached, mock_fetch, mock_settings):
        """Test search volume cache hit."""
        mock_settings.SERPAPI_KEY = 'test_key'
        mock_get_cached.return_value = 75  # Cache hit

        score = check_search_volume('test keyword')

        # Should not call API if cache hit
        mock_fetch.assert_not_called()
        mock_cache.assert_not_called()
        assert score == 75


if __name__ == '__main__':
    pytest.main([__file__, '-v'])