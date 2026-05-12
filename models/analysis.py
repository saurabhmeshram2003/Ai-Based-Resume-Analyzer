"""
Analysis model: MongoDB CRUD operations for resume analysis documents.
"""
from bson import ObjectId
from datetime import datetime


class AnalysisModel:

    @staticmethod
    def save(db, data: dict) -> ObjectId:
        """Insert a new analysis document. Returns inserted ObjectId."""
        result = db.analyses.insert_one(data)
        return result.inserted_id

    @staticmethod
    def find_by_id(db, analysis_id: str) -> dict | None:
        """Retrieve a single analysis by its string ID."""
        try:
            doc = db.analyses.find_one({"_id": ObjectId(analysis_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                if doc.get("user_id"):
                    doc["user_id"] = str(doc["user_id"])
            return doc
        except Exception:
            return None

    @staticmethod
    def find_by_user(db, user_id: str, limit: int = 100) -> list:
        """Return all analyses for a user, newest first."""
        docs = list(
            db.analyses
            .find({"user_id": ObjectId(user_id)})
            .sort("created_at", -1)
            .limit(limit)
        )
        for d in docs:
            d["_id"] = str(d["_id"])
            if d.get("user_id"):
                d["user_id"] = str(d["user_id"])
        return docs

    @staticmethod
    def delete(db, analysis_id: str, user_id: str) -> bool:
        """Delete an analysis owned by user_id. Returns True on success."""
        try:
            result = db.analyses.delete_one({
                "_id":     ObjectId(analysis_id),
                "user_id": ObjectId(user_id),
            })
            return result.deleted_count > 0
        except Exception:
            return False

    @staticmethod
    def get_all(db, limit: int = 100) -> list:
        """Admin: return most-recent analyses across all users."""
        docs = list(db.analyses.find().sort("created_at", -1).limit(limit))
        for d in docs:
            d["_id"] = str(d["_id"])
            if d.get("user_id"):
                d["user_id"] = str(d["user_id"])
        return docs

    @staticmethod
    def daily_count_for_user(db, user_id: str) -> int:
        """Count analyses created today for a given user (free-tier gate)."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return db.analyses.count_documents({
            "user_id":    ObjectId(user_id),
            "created_at": {"$gte": today_start},
        })
