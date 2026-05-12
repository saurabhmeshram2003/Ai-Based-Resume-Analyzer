"""
Subscription model: plan definitions and feature gates.
"""


class SubscriptionModel:
    PLANS = {
        "free": {
            "label":          "Free",
            "price":          "$0",
            "daily_analyses": 3,
            "pdf_reports":    False,
            "ai_rewrite":     False,
            "bulk_upload":    False,
            "csv_export":     False,
            "history":        True,
        },
        "pro": {
            "label":          "Pro",
            "price":          "$9/mo",
            "daily_analyses": -1,       # unlimited
            "pdf_reports":    True,
            "ai_rewrite":     True,
            "bulk_upload":    False,
            "csv_export":     False,
            "history":        True,
        },
        "recruiter": {
            "label":          "Recruiter",
            "price":          "$29/mo",
            "daily_analyses": -1,
            "pdf_reports":    True,
            "ai_rewrite":     True,
            "bulk_upload":    True,
            "csv_export":     True,
            "history":        True,
        },
    }

    @classmethod
    def get_limits(cls, plan: str) -> dict:
        return cls.PLANS.get(plan, cls.PLANS["free"])

    @classmethod
    def can_analyze(cls, plan: str, daily_used: int) -> bool:
        limits = cls.get_limits(plan)
        if limits["daily_analyses"] == -1:
            return True
        return daily_used < limits["daily_analyses"]

    @classmethod
    def can_download_pdf(cls, plan: str) -> bool:
        return cls.get_limits(plan)["pdf_reports"]

    @classmethod
    def can_use_ai_rewrite(cls, plan: str) -> bool:
        return cls.get_limits(plan)["ai_rewrite"]
