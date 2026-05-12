"""
User model: MongoDB operations + Flask-Login adapter.
"""
import bcrypt
from bson import ObjectId
from datetime import datetime
from flask_login import UserMixin


class UserModel:

    @staticmethod
    def create(db, data: dict) -> ObjectId:
        """Create a new user. Returns the inserted ObjectId."""
        password_hash = bcrypt.hashpw(
            data["password"].encode("utf-8"), bcrypt.gensalt()
        )
        user_doc = {
            "name":          data["name"],
            "email":         data["email"].lower().strip(),
            "password_hash": password_hash,
            "role":          data.get("role", "user"),
            "subscription":  data.get("subscription", "free"),
            "created_at":    datetime.utcnow(),
            "profile": {
                "target_roles": [],
                "yoe":          0,
                "industry":     "",
            },
        }
        result = db.users.insert_one(user_doc)
        return result.inserted_id

    @staticmethod
    def find_by_email(db, email: str) -> dict | None:
        return db.users.find_one({"email": email.lower().strip()})

    @staticmethod
    def find_by_id(db, user_id: str) -> dict | None:
        try:
            return db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

    @staticmethod
    def verify_password(user_doc: dict, password: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), user_doc["password_hash"]
            )
        except Exception:
            return False

    @staticmethod
    def update(db, user_id: str, data: dict):
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": data})

    @staticmethod
    def update_subscription(db, user_id: str, plan: str):
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"subscription": plan}}
        )

    @staticmethod
    def get_all(db, limit: int = 100) -> list:
        docs = list(db.users.find().sort("created_at", -1).limit(limit))
        for d in docs:
            d["_id"] = str(d["_id"])
            d.pop("password_hash", None)
        return docs


class FlaskLoginUser(UserMixin):
    """Flask-Login adapter that wraps a raw MongoDB user document."""

    def __init__(self, user_doc: dict):
        self._doc = user_doc

    # Flask-Login requires get_id()
    def get_id(self) -> str:
        return str(self._doc["_id"])

    @property
    def id(self) -> str:
        return str(self._doc["_id"])

    @property
    def name(self) -> str:
        return self._doc.get("name", "User")

    @property
    def email(self) -> str:
        return self._doc.get("email", "")

    @property
    def role(self) -> str:
        return self._doc.get("role", "user")

    @property
    def subscription(self) -> str:
        return self._doc.get("subscription", "free")

    @property
    def profile(self) -> dict:
        return self._doc.get("profile", {})

    @property
    def is_admin(self) -> bool:
        return self._doc.get("role") == "admin"

    @property
    def is_pro(self) -> bool:
        return self._doc.get("subscription") in ("pro", "recruiter")
