"""
Unit tests for IdeaHunter database functions.
"""

import pytest
import tempfile
import os
import time
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.database import (
    init_db, save_raw_posts, get_unprocessed_posts, mark_posts_processed,
    save_ideas, get_all_ideas, get_idea_by_id, toggle_idea_saved,
    log_run, save_research, get_research, save_demand_metrics, get_demand_metrics,
    save_gsc_metrics, get_gsc_metrics, get_saved_ideas, get_dashboard_stats
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    # Create temporary database
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Override database path
    import backend.db.database as db_module
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = Path(db_path)

    # Initialize database
    init_db()

    yield db_path

    # Cleanup - close any connections and delete file
    try:
        # Force garbage collection to close connections
        import gc
        gc.collect()
        # Try to delete with retry for Windows file locking
        for _ in range(3):
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
                break
            except PermissionError:
                time.sleep(0.1)
    finally:
        db_module.DB_PATH = original_db_path


class TestDatabaseFunctions:
    """Test database functions."""

    def test_init_db(self, temp_db):
        """Test database initialization."""
        assert os.path.exists(temp_db)
        assert os.path.getsize(temp_db) > 0

    def test_save_raw_posts(self, temp_db):
        """Test saving raw posts."""
        posts = [
            {
                "id": "test_1",
                "source": "reddit",
                "content": "Test content",
                "metadata": {"test": "data"}
            },
            {
                "id": "test_2",
                "source": "hn",
                "content": "Another test",
                "metadata": {"key": "value"}
            }
        ]

        save_raw_posts(posts)

        # Verify posts were saved
        unprocessed = get_unprocessed_posts(limit=10)
        assert len(unprocessed) == 2
        assert unprocessed[0]['id'] == 'test_1'
        assert unprocessed[1]['id'] == 'test_2'

    def test_save_raw_posts_validation(self, temp_db):
        """Test raw posts validation."""
        posts = [
            {
                "id": "valid_1",
                "source": "reddit",
                "content": "Valid content",
                "metadata": {"test": "data"}
            },
            {
                "id": "",  # Invalid empty ID
                "source": "reddit",
                "content": "Invalid content",
                "metadata": {}
            },
            {
                "id": "invalid_source",
                "source": "invalid_source",  # Invalid source
                "content": "Content",
                "metadata": {}
            }
        ]

        save_raw_posts(posts)

        # Only valid post should be saved
        unprocessed = get_unprocessed_posts(limit=10)
        assert len(unprocessed) == 1
        assert unprocessed[0]['id'] == 'valid_1'

    def test_mark_posts_processed(self, temp_db):
        """Test marking posts as processed."""
        posts = [
            {
                "id": "test_1",
                "source": "reddit",
                "content": "Test content",
                "metadata": {}
            }
        ]

        save_raw_posts(posts)
        mark_posts_processed(['test_1'])

        # Post should no longer be unprocessed
        unprocessed = get_unprocessed_posts(limit=10)
        assert len(unprocessed) == 0

    def test_save_ideas(self, temp_db):
        """Test saving ideas."""
        ideas = [
            {
                "name": "Test Idea",
                "description": "A test idea description",
                "pain_point": "Test pain point",
                "source": "reddit",
                "keywords": ["test", "idea"],
                "score_overall": 7.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        save_ideas(ideas)

        # Verify idea was saved
        all_ideas = get_all_ideas(min_score=0.0)
        assert len(all_ideas) == 1
        assert all_ideas[0]['name'] == 'Test Idea'
        assert all_ideas[0]['score_overall'] == 7.5

    def test_save_ideas_validation(self, temp_db):
        """Test ideas validation."""
        ideas = [
            {
                "name": "",  # Invalid empty name
                "description": "Valid description",
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 7.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            },
            {
                "name": "Valid Idea",
                "description": "",  # Invalid empty description
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 7.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            },
            {
                "name": "Valid Idea 2",
                "description": "Valid description",
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 15.0,  # Invalid score above max
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        save_ideas(ideas)

        # Only valid idea should be saved (with clamped score)
        all_ideas = get_all_ideas(min_score=0.0)
        assert len(all_ideas) == 1
        assert all_ideas[0]['name'] == 'Valid Idea 2'
        assert all_ideas[0]['score_overall'] <= 10.0  # Score should be clamped

    def test_get_all_ideas_with_filter(self, temp_db):
        """Test getting ideas with score filter."""
        ideas = [
            {
                "name": "High Score Idea",
                "description": "High score",
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 8.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            },
            {
                "name": "Low Score Idea",
                "description": "Low score",
                "pain_point": "Test",
                "source": "hn",
                "keywords": ["test"],
                "score_overall": 5.0,
                "score_demand": 50,
                "score_competition": 50,
                "score_trend": 50,
                "score_uniqueness": 50
            }
        ]

        save_ideas(ideas)

        # Test with high score filter
        high_score_ideas = get_all_ideas(min_score=7.0)
        assert len(high_score_ideas) == 1
        assert high_score_ideas[0]['name'] == 'High Score Idea'

        # Test with low score filter
        all_ideas = get_all_ideas(min_score=0.0)
        assert len(all_ideas) == 2

    def test_get_idea_by_id(self, temp_db):
        """Test getting idea by ID."""
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test",
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 7.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        save_ideas(ideas)

        # Get idea by ID
        all_ideas = get_all_ideas(min_score=0.0)
        idea_id = all_ideas[0]['id']
        idea = get_idea_by_id(idea_id)

        assert idea is not None
        assert idea['name'] == 'Test Idea'

        # Test invalid ID
        invalid_idea = get_idea_by_id('invalid')
        assert invalid_idea is None

    def test_toggle_idea_saved(self, temp_db):
        """Test toggling idea saved status."""
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test",
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 7.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        save_ideas(ideas)

        # Get idea ID
        all_ideas = get_all_ideas(min_score=0.0)
        idea_id = all_ideas[0]['id']

        # Toggle to saved
        success, saved_status = toggle_idea_saved(idea_id)
        assert success is True
        assert saved_status is True

        # Verify saved status
        saved_ideas = get_saved_ideas()
        assert len(saved_ideas) == 1

        # Toggle back to unsaved
        success, saved_status = toggle_idea_saved(idea_id)
        assert success is True
        assert saved_status is False

        # Verify unsaved status
        saved_ideas = get_saved_ideas()
        assert len(saved_ideas) == 0

    def test_log_run(self, temp_db):
        """Test logging pipeline runs."""
        log_run('reddit', 100, 50, 'ok', None)

        # Verify log was created
        # (This would require checking the run_log table)

    def test_save_research(self, temp_db):
        """Test saving research data."""
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test",
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 7.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        save_ideas(ideas)
        all_ideas = get_all_ideas(min_score=0.0)
        idea_id = all_ideas[0]['id']

        # Save research
        save_research(idea_id, 'competitors', 'Test research content')

        # Get research
        research = get_research(idea_id)
        assert len(research) == 1
        assert research[0]['type'] == 'competitors'
        assert research[0]['content'] == 'Test research content'

    def test_save_demand_metrics(self, temp_db):
        """Test saving demand metrics."""
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test",
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 7.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        save_ideas(ideas)
        all_ideas = get_all_ideas(min_score=0.0)
        idea_id = all_ideas[0]['id']

        # Save demand metrics
        save_demand_metrics(idea_id, 1000, 30, 0.5)

        # Get demand metrics
        metrics = get_demand_metrics(idea_id)
        assert metrics is not None
        assert metrics['search_volume'] == 1000
        assert metrics['keyword_difficulty'] == 30
        assert metrics['cpc'] == 0.5

    def test_save_gsc_metrics(self, temp_db):
        """Test saving GSC metrics."""
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test",
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 7.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        save_ideas(ideas)
        all_ideas = get_all_ideas(min_score=0.0)
        idea_id = all_ideas[0]['id']

        # Save GSC metrics
        save_gsc_metrics(idea_id, 1000, 50, 5.5, 5.0)

        # Get GSC metrics
        metrics = get_gsc_metrics(idea_id)
        assert metrics is not None
        assert metrics['impressions'] == 1000
        assert metrics['clicks'] == 50
        assert metrics['position'] == 5.5
        assert metrics['ctr'] == 5.0

    def test_get_dashboard_stats(self, temp_db):
        """Test getting dashboard statistics."""
        # Add some test data
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test",
                "pain_point": "Test",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 8.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        save_ideas(ideas)

        # Get dashboard stats
        stats = get_dashboard_stats()
        assert stats['total'] >= 1
        assert stats['high_score'] >= 1
        assert 'last_run' in stats
        assert 'scrapers' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])