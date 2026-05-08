"""
Integration tests for IdeaHunter pipeline.
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.database import (
    init_db, save_raw_posts, get_unprocessed_posts, mark_posts_processed,
    save_ideas, get_all_ideas, get_idea_by_id, toggle_idea_saved,
    log_run, save_research, get_research, save_demand_metrics, get_demand_metrics,
    save_gsc_metrics, get_gsc_metrics, get_saved_ideas, get_dashboard_stats
)
from backend.validators.validator import validate_ideas


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Override database path
    import backend.db.database as db_module
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = Path(db_path)

    # Initialize database
    init_db()

    yield db_path

    # Cleanup
    os.unlink(db_path)
    db_module.DB_PATH = original_db_path


class TestPipelineIntegration:
    """Test complete pipeline integration."""

    def test_full_pipeline_flow(self, temp_db):
        """Test complete pipeline from raw posts to validated ideas."""
        # Step 1: Save raw posts
        raw_posts = [
            {
                "id": "test_1",
                "source": "reddit",
                "content": "Looking for a productivity app that helps with time management",
                "metadata": {"subreddit": "productivity", "score": 100}
            },
            {
                "id": "test_2",
                "source": "hn",
                "content": "What tools do you use for project management?",
                "metadata": {"score": 50}
            }
        ]

        save_raw_posts(raw_posts)

        # Step 2: Get unprocessed posts
        unprocessed = get_unprocessed_posts(limit=10)
        assert len(unprocessed) == 2

        # Step 3: Process posts (simulate AI processing)
        ideas = [
            {
                "name": "Time Management App",
                "description": "A productivity app for time management",
                "pain_point": "Users struggle with time management",
                "source": "reddit",
                "keywords": ["time management", "productivity"],
                "score_overall": 7.5,
                "score_demand": 80,
                "score_competition": 30,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        # Step 4: Save ideas
        save_ideas(ideas)

        # Step 5: Mark posts as processed
        mark_posts_processed(['test_1', 'test_2'])

        # Step 6: Verify posts are processed
        unprocessed = get_unprocessed_posts(limit=10)
        assert len(unprocessed) == 0

        # Step 7: Get and validate ideas
        all_ideas = get_all_ideas(min_score=0.0)
        assert len(all_ideas) == 1
        assert all_ideas[0]['name'] == 'Time Management App'

    def test_idea_lifecycle(self, temp_db):
        """Test complete idea lifecycle from creation to research."""
        # Create idea
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test description",
                "pain_point": "Test pain point",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 8.0,
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

        # Save research data
        save_research(idea_id, 'competitors', 'Competitor analysis data')
        save_research(idea_id, 'market', 'Market research data')

        # Get research
        research = get_research(idea_id)
        assert len(research) == 2

        # Save demand metrics
        save_demand_metrics(idea_id, 1000, 30, 0.5)

        # Get demand metrics
        metrics = get_demand_metrics(idea_id)
        assert metrics['search_volume'] == 1000

        # Save GSC metrics
        save_gsc_metrics(idea_id, 1000, 50, 5.5, 5.0)

        # Get GSC metrics
        gsc_metrics = get_gsc_metrics(idea_id)
        assert gsc_metrics['impressions'] == 1000

        # Toggle saved status
        success, saved = toggle_idea_saved(idea_id)
        assert success is True
        assert saved is True

        # Verify saved ideas
        saved_ideas = get_saved_ideas()
        assert len(saved_ideas) == 1

    def test_validation_integration(self, temp_db):
        """Test validation integration with database."""
        # Create ideas
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test description",
                "pain_point": "Test pain point",
                "source": "reddit",
                "keywords": ["test", "keyword"],
                "score_demand": 80,
                "score_competition": 40,
                "score_trend": 70,
                "score_uniqueness": 60
            }
        ]

        # Validate ideas (this will modify scores)
        validated_ideas = validate_ideas(ideas)

        # Save validated ideas
        save_ideas(validated_ideas)

        # Verify ideas were saved with validated scores
        all_ideas = get_all_ideas(min_score=0.0)
        assert len(all_ideas) == 1
        assert 'score_overall' in all_ideas[0]

    def test_dashboard_stats_integration(self, temp_db):
        """Test dashboard statistics with real data."""
        # Create multiple ideas with different scores
        ideas = [
            {
                "name": f"Test Idea {i}",
                "description": f"Test description {i}",
                "pain_point": f"Test pain point {i}",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 5.0 + i,
                "score_demand": 50 + i * 5,
                "score_competition": 30 + i * 2,
                "score_trend": 60 + i * 3,
                "score_uniqueness": 50 + i * 2
            }
            for i in range(1, 6)
        ]

        save_ideas(ideas)

        # Log a run
        log_run('reddit', 100, 50, 'ok', None)

        # Get dashboard stats
        stats = get_dashboard_stats()

        assert stats['total'] == 5
        assert stats['high_score'] >= 1  # At least one high score idea
        assert 'last_run' in stats
        assert 'scrapers' in stats

    def test_error_recovery_integration(self, temp_db):
        """Test error recovery in pipeline."""
        # Try to save invalid posts
        invalid_posts = [
            {
                "id": "",  # Invalid empty ID
                "source": "reddit",
                "content": "Test content",
                "metadata": {}
            },
            {
                "id": "valid_1",
                "source": "invalid_source",  # Invalid source
                "content": "Test content",
                "metadata": {}
            }
        ]

        save_raw_posts(invalid_posts)

        # Should only save valid posts
        unprocessed = get_unprocessed_posts(limit=10)
        assert len(unprocessed) == 0  # No valid posts

        # Try to save invalid ideas
        invalid_ideas = [
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
            }
        ]

        save_ideas(invalid_ideas)

        # Should not save invalid ideas
        all_ideas = get_all_ideas(min_score=0.0)
        assert len(all_ideas) == 0

    def test_concurrent_operations(self, temp_db):
        """Test concurrent database operations."""
        # Save multiple posts
        posts = [
            {
                "id": f"test_{i}",
                "source": "reddit",
                "content": f"Test content {i}",
                "metadata": {}
            }
            for i in range(10)
        ]

        save_raw_posts(posts)

        # Get unprocessed posts
        unprocessed = get_unprocessed_posts(limit=10)
        assert len(unprocessed) == 10

        # Mark some as processed
        mark_posts_processed(['test_0', 'test_1', 'test_2'])

        # Verify remaining posts
        unprocessed = get_unprocessed_posts(limit=10)
        assert len(unprocessed) == 7

    def test_data_consistency(self, temp_db):
        """Test data consistency across operations."""
        # Create idea
        ideas = [
            {
                "name": "Test Idea",
                "description": "Test description",
                "pain_point": "Test pain point",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 8.0,
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

        # Save multiple research entries
        save_research(idea_id, 'competitors', 'Data 1')
        save_research(idea_id, 'competitors', 'Data 2')
        save_research(idea_id, 'market', 'Data 3')

        # Verify all research is saved
        research = get_research(idea_id)
        assert len(research) == 3

        # Verify data integrity
        idea = get_idea_by_id(idea_id)
        assert idea is not None
        assert idea['name'] == 'Test Idea'


class TestPerformanceIntegration:
    """Test performance characteristics."""

    def test_large_dataset_handling(self, temp_db):
        """Test handling of large datasets."""
        # Create large number of posts
        large_posts = [
            {
                "id": f"test_{i}",
                "source": "reddit",
                "content": f"Test content {i}",
                "metadata": {}
            }
            for i in range(100)
        ]

        start_time = time.time()
        save_raw_posts(large_posts)
        save_time = time.time() - start_time

        # Should complete in reasonable time
        assert save_time < 5.0  # Less than 5 seconds

        # Verify all posts saved
        unprocessed = get_unprocessed_posts(limit=200)
        assert len(unprocessed) == 100

    def test_query_performance(self, temp_db):
        """Test query performance with filters."""
        # Create ideas with different scores
        ideas = [
            {
                "name": f"Test Idea {i}",
                "description": f"Test description {i}",
                "pain_point": f"Test pain point {i}",
                "source": "reddit",
                "keywords": ["test"],
                "score_overall": 5.0 + i * 0.5,
                "score_demand": 50 + i * 5,
                "score_competition": 30 + i * 2,
                "score_trend": 60 + i * 3,
                "score_uniqueness": 50 + i * 2
            }
            for i in range(50)
        ]

        save_ideas(ideas)

        # Test query performance
        start_time = time.time()
        high_score_ideas = get_all_ideas(min_score=7.0)
        query_time = time.time() - start_time

        # Should complete in reasonable time
        assert query_time < 1.0  # Less than 1 second
        assert len(high_score_ideas) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])