from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo import MongoClient
import os

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
STORAGE_LIMIT_GB = 1
STORAGE_LIMIT_BYTES = STORAGE_LIMIT_GB * 1024 * 1024 * 1024  # 1GB in bytes

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
DB_NAME = os.getenv("DB_NAME", "bucket_service")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_collection = db["users"]

# Create unique index on username
users_collection.create_index("username", unique=True)
users_collection.create_index("email", unique=True)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Handle both string and bytes
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_username(username: str):
    """Get user by username"""
    return users_collection.find_one({"username": username})


def get_user_by_email(email: str):
    """Get user by email"""
    return users_collection.find_one({"email": email})


def get_user_by_id(user_id: str):
    """Get user by ID"""
    from bson import ObjectId
    try:
        return users_collection.find_one({"_id": ObjectId(user_id)})
    except:
        return None


def authenticate_user(username: str, password: str):
    """Authenticate a user"""
    user = get_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user


def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """Get current user and verify admin status"""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_user_storage_usage(user_id) -> int:
    """Calculate total storage used by a user"""
    from bson import ObjectId
    files_collection = db["files"]
    # Convert to ObjectId if it's a string
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total_size": {"$sum": "$size"}}}
    ]
    result = list(files_collection.aggregate(pipeline))
    return result[0]["total_size"] if result else 0


def check_storage_limit(user_id, file_size: int) -> bool:
    """Check if user can upload a file of given size"""
    current_usage = get_user_storage_usage(user_id)
    return (current_usage + file_size) <= STORAGE_LIMIT_BYTES

