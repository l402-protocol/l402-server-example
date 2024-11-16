import replit

# Initialize db with error handling
try:
    db = replit.db
    db = {}
except Exception as e:
    # Fallback to in-memory dictionary if DB initialization fails
    db = {}