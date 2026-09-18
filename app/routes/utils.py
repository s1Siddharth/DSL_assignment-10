"""
OmniShield AI — Shared API Utilities
"""
from flask import jsonify
from typing import Any, Optional


def success_response(data: Any = None, message: str = "Operation completed successfully.", status_code: int = 200):
    return jsonify({"success": True, "data": data, "message": message}), status_code


def error_response(code: str, message: str, status_code: int = 400):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status_code
