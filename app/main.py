from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form
from fastapi.responses import FileResponse as fastapi_file_response, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, timedelta
import os
import shutil
from pathlib import Path
import json

from app.auth import (
    get_password_hash, authenticate_user, create_access_token,
    get_current_user, get_current_admin_user, get_user_storage_usage,
    check_storage_limit, STORAGE_LIMIT_BYTES, ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Bucket as a Service", version="2.0.0")

# Configuration
STORAGE_PATH = os.getenv("STORAGE_PATH", "/app/storage")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
DB_NAME = os.getenv("DB_NAME", "bucket_service")

# Initialize MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
buckets_collection = db["buckets"]
files_collection = db["files"]
users_collection = db["users"]

# Create storage directory
Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)

# Mount static files
static_path = Path(__file__).parent.parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
try:
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
except Exception as e:
    print(f"Warning: Could not mount static files: {e}")


# Initialize admin user on startup
@app.on_event("startup")
async def init_admin():
    """Create default admin user if it doesn't exist"""
    admin = users_collection.find_one({"username": "admin"})
    if not admin:
        users_collection.insert_one({
            "username": "admin",
            "email": "admin@example.com",
            "hashed_password": get_password_hash("admin123"),
            "is_admin": True,
            "created_at": datetime.utcnow().isoformat(),
            "full_name": "Administrator"
        })
        print("Default admin user created: username=admin, password=admin123")


# Dependency to get database connection
def get_db():
    return db


# Authentication Endpoints
@app.post("/api/auth/register", status_code=201)
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: Optional[str] = Form(None)
):
    """Register a new user"""
    # Check if username already exists
    if users_collection.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email already exists
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_doc = {
        "username": username,
        "email": email,
        "hashed_password": get_password_hash(password),
        "is_admin": False,
        "created_at": datetime.utcnow().isoformat(),
        "full_name": full_name or username
    }
    
    try:
        result = users_collection.insert_one(user_doc)
        return {
            "message": "User registered successfully",
            "user_id": str(result.inserted_id),
            "username": username
        }
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="User already exists")


@app.post("/api/auth/login")
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    """Login and get access token"""
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user.get("email"),
            "is_admin": user.get("is_admin", False),
            "full_name": user.get("full_name")
        }
    }


@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    storage_used = get_user_storage_usage(str(current_user["_id"]))
    return {
        "id": str(current_user["_id"]),
        "username": current_user["username"],
        "email": current_user.get("email"),
        "is_admin": current_user.get("is_admin", False),
        "full_name": current_user.get("full_name"),
        "storage_used": storage_used,
        "storage_limit": STORAGE_LIMIT_BYTES,
        "storage_used_gb": round(storage_used / (1024**3), 2),
        "storage_limit_gb": STORAGE_LIMIT_BYTES / (1024**3)
    }


# Admin Endpoints
@app.get("/api/admin/users")
async def list_all_users(current_user: dict = Depends(get_current_admin_user)):
    """List all users (admin only)"""
    users = []
    for user in users_collection.find({}, {"hashed_password": 0}):
        storage_used = get_user_storage_usage(str(user["_id"]))
        users.append({
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user.get("email"),
            "is_admin": user.get("is_admin", False),
            "full_name": user.get("full_name"),
            "created_at": user.get("created_at"),
            "storage_used": storage_used,
            "storage_limit": STORAGE_LIMIT_BYTES,
            "storage_used_gb": round(storage_used / (1024**3), 2),
            "storage_limit_gb": round(STORAGE_LIMIT_BYTES / (1024**3), 2),
            "storage_percentage": round((storage_used / STORAGE_LIMIT_BYTES) * 100, 2)
        })
    return {"users": users, "count": len(users)}


@app.get("/api/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_admin_user)):
    """Get admin statistics"""
    total_users = users_collection.count_documents({})
    total_buckets = buckets_collection.count_documents({})
    total_files = files_collection.count_documents({})
    
    # Calculate total storage used
    pipeline = [
        {"$group": {"_id": None, "total_size": {"$sum": "$size"}}}
    ]
    result = list(files_collection.aggregate(pipeline))
    total_storage = result[0]["total_size"] if result else 0
    
    return {
        "total_users": total_users,
        "total_buckets": total_buckets,
        "total_files": total_files,
        "total_storage_bytes": total_storage,
        "total_storage_gb": round(total_storage / (1024**3), 2)
    }


# Root and Health endpoints
@app.get("/")
async def root():
    return FileResponse(str(static_path / "index.html"))


@app.get("/admin")
async def admin_page():
    return FileResponse(str(static_path / "admin.html"))


@app.get("/health")
async def health_check():
    try:
        client.admin.command('ping')
        return {"status": "healthy", "mongodb": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# Bucket Operations (Protected)
@app.post("/api/buckets", status_code=201)
async def create_bucket(
    name: str,
    description: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new bucket"""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Bucket name is required")
    
    # Validate bucket name
    if not name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="Bucket name can only contain alphanumeric characters, hyphens, and underscores"
        )
    
    user_id = current_user["_id"]
    bucket_path = os.path.join(STORAGE_PATH, str(user_id), name)
    
    # Check if bucket already exists for this user
    existing = buckets_collection.find_one({"name": name, "user_id": user_id})
    if existing:
        raise HTTPException(status_code=409, detail="Bucket already exists")
    
    try:
        # Create bucket directory
        os.makedirs(bucket_path, exist_ok=False)
        
        # Create bucket document
        bucket_doc = {
            "name": name,
            "description": description,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "file_count": 0,
            "total_size": 0
        }
        
        result = buckets_collection.insert_one(bucket_doc)
        
        return {
            "id": str(result.inserted_id),
            "name": name,
            "description": description,
            "created_at": bucket_doc["created_at"],
            "file_count": 0,
            "total_size": 0,
            "message": "Bucket created successfully"
        }
    except Exception as e:
        if os.path.exists(bucket_path):
            shutil.rmtree(bucket_path)
        raise HTTPException(status_code=500, detail=f"Error creating bucket: {str(e)}")


@app.get("/api/buckets")
async def list_buckets(current_user: dict = Depends(get_current_user)):
    """List all buckets for current user"""
    user_id = current_user["_id"]
    buckets = []
    for bucket in buckets_collection.find({"user_id": user_id}):
        buckets.append({
            "id": str(bucket["_id"]),
            "name": bucket["name"],
            "description": bucket.get("description"),
            "created_at": bucket["created_at"],
            "file_count": bucket.get("file_count", 0),
            "total_size": bucket.get("total_size", 0)
        })
    return {"buckets": buckets, "count": len(buckets)}


@app.get("/api/buckets/{bucket_name}")
async def get_bucket(
    bucket_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Get bucket details"""
    user_id = current_user["_id"]
    bucket = buckets_collection.find_one({"name": bucket_name, "user_id": user_id})
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    return {
        "id": str(bucket["_id"]),
        "name": bucket["name"],
        "description": bucket.get("description"),
        "created_at": bucket["created_at"],
        "file_count": bucket.get("file_count", 0),
        "total_size": bucket.get("total_size", 0)
    }


@app.delete("/api/buckets/{bucket_name}")
async def delete_bucket(
    bucket_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a bucket and all its files"""
    user_id = current_user["_id"]
    bucket = buckets_collection.find_one({"name": bucket_name, "user_id": user_id})
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    bucket_id = bucket["_id"]
    bucket_path = os.path.join(STORAGE_PATH, str(user_id), bucket_name)
    
    try:
        # Delete all files from database
        files_collection.delete_many({"bucket_id": bucket_id})
        
        # Delete bucket directory
        if os.path.exists(bucket_path):
            shutil.rmtree(bucket_path)
        
        # Delete bucket from database
        buckets_collection.delete_one({"_id": bucket_id})
        
        return {"message": f"Bucket '{bucket_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting bucket: {str(e)}")


# File Operations (Protected)
@app.post("/api/buckets/{bucket_name}/files")
async def upload_file(
    bucket_name: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a file to a bucket"""
    user_id = current_user["_id"]
    bucket = buckets_collection.find_one({"name": bucket_name, "user_id": user_id})
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    # Read file size first
    file_content = await file.read()
    file_size = len(file_content)
    
    # Check storage limit
    if not check_storage_limit(str(user_id), file_size):
        raise HTTPException(
            status_code=413,
            detail=f"Storage limit exceeded. You have {STORAGE_LIMIT_BYTES / (1024**3):.2f}GB limit."
        )
    
    bucket_id = bucket["_id"]
    bucket_path = os.path.join(STORAGE_PATH, str(user_id), bucket_name)
    
    # Save file
    file_path = os.path.join(bucket_path, file.filename)
    
    # Check if file already exists
    if os.path.exists(file_path):
        raise HTTPException(status_code=409, detail="File already exists")
    
    try:
        # Write file to disk
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Save file metadata
        file_doc = {
            "filename": file.filename,
            "bucket_id": bucket_id,
            "bucket_name": bucket_name,
            "user_id": user_id,
            "size": file_size,
            "content_type": file.content_type or "application/octet-stream",
            "uploaded_at": datetime.utcnow().isoformat(),
            "file_path": file_path
        }
        
        result = files_collection.insert_one(file_doc)
        
        # Update bucket statistics
        buckets_collection.update_one(
            {"_id": bucket_id},
            {
                "$inc": {
                    "file_count": 1,
                    "total_size": file_size
                }
            }
        )
        
        return {
            "id": str(result.inserted_id),
            "filename": file.filename,
            "bucket_id": str(bucket_id),
            "size": file_size,
            "content_type": file.content_type,
            "uploaded_at": file_doc["uploaded_at"],
            "message": "File uploaded successfully"
        }
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@app.get("/api/buckets/{bucket_name}/files")
async def list_files(
    bucket_name: str,
    current_user: dict = Depends(get_current_user)
):
    """List all files in a bucket"""
    user_id = current_user["_id"]
    bucket = buckets_collection.find_one({"name": bucket_name, "user_id": user_id})
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    bucket_id = bucket["_id"]
    files = []
    
    for file in files_collection.find({"bucket_id": bucket_id}):
        files.append({
            "id": str(file["_id"]),
            "filename": file["filename"],
            "bucket_id": str(bucket_id),
            "size": file["size"],
            "content_type": file.get("content_type", "application/octet-stream"),
            "uploaded_at": file["uploaded_at"]
        })
    
    return {"files": files, "count": len(files)}


@app.get("/api/buckets/{bucket_name}/files/{filename}")
async def download_file(
    bucket_name: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Download a file from a bucket"""
    user_id = current_user["_id"]
    bucket = buckets_collection.find_one({"name": bucket_name, "user_id": user_id})
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    bucket_id = bucket["_id"]
    file_doc = files_collection.find_one({"bucket_id": bucket_id, "filename": filename})
    
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = file_doc.get("file_path") or os.path.join(STORAGE_PATH, str(user_id), bucket_name, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return fastapi_file_response(
        path=file_path,
        filename=filename,
        media_type=file_doc.get("content_type", "application/octet-stream")
    )


@app.delete("/api/buckets/{bucket_name}/files/{filename}")
async def delete_file(
    bucket_name: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a file from a bucket"""
    user_id = current_user["_id"]
    bucket = buckets_collection.find_one({"name": bucket_name, "user_id": user_id})
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    bucket_id = bucket["_id"]
    file_doc = files_collection.find_one({"bucket_id": bucket_id, "filename": filename})
    
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = file_doc.get("file_path") or os.path.join(STORAGE_PATH, str(user_id), bucket_name, filename)
    
    try:
        # Delete file from disk
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            os.remove(file_path)
        else:
            file_size = file_doc.get("size", 0)
        
        # Delete file from database
        files_collection.delete_one({"_id": file_doc["_id"]})
        
        # Update bucket statistics
        buckets_collection.update_one(
            {"_id": bucket_id},
            {
                "$inc": {
                    "file_count": -1,
                    "total_size": -file_size
                }
            }
        )
        
        return {"message": f"File '{filename}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
