"""
Test helpers for inventory app tests.
"""
# No imports needed currently

# This file previously contained a MockFeedStock class and patch_feedstock_for_tests decorator
# These have been removed as they're no longer needed after updating the database schema
# The FeedStock model now properly uses UpdatedModelMixin with an updated_at field
# instead of TimestampedModelMixin with created_at and updated_at fields
