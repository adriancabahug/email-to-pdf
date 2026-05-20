"""
Relevance Scoring Engine - Scores emails and threads for relevance to SMSF evidence packs.
"""

from src.search_rule_engine import SearchRuleEngine, RelevanceLevel


class RelevanceScoringEngine:
    def __init__(self, search_engine: SearchRuleEngine):
        self._search_engine = search_engine

    def score_email(self, email, context) -> RelevanceLevel:
        return self._search_engine.is_relevant(email, context)

    def score_thread(self, thread, context) -> RelevanceLevel:
        if not thread.emails:
            return RelevanceLevel.NONE

        max_level = RelevanceLevel.NONE
        for email in thread.emails:
            level = self.score_email(email, context)
            if level == RelevanceLevel.STRONG:
                return RelevanceLevel.STRONG
            if level.value > max_level.value:
                max_level = level

        return max_level

    def is_strong_match(self, email, context) -> bool:
        return self.score_email(email, context) == RelevanceLevel.STRONG

    def should_exclude(self, email, context) -> bool:
        level = self.score_email(email, context)
        return level in (RelevanceLevel.WEAK, RelevanceLevel.NONE)