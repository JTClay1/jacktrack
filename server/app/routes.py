from flask import Blueprint, jsonify

api = Blueprint("api", __name__, url_prefix="/api")

@api.get("/health")
def health():
    return jsonify(ok=True, service="jacktrack-api")