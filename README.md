# Bucket as a Service

A cloud storage service that provides bucket-based file storage similar to AWS S3 or Google Cloud Storage. Built with FastAPI, MongoDB, and Docker Compose.

## Features

- ✅ **User Authentication & Registration** - Secure JWT-based authentication system
- ✅ **Storage Limits** - 1GB storage limit per user with real-time usage tracking
- ✅ **User Dashboard** - Beautiful web UI for managing buckets and files
- ✅ **Admin Dashboard** - Admin panel to view all users and their storage usage
- ✅ Create, list, and delete buckets (per user)
- ✅ Upload, download, and delete files within buckets
- ✅ MongoDB for metadata storage
- ✅ RESTful API with FastAPI
- ✅ Docker Compose for easy deployment
- ✅ Health check endpoints
- ✅ File metadata tracking (size, content type, upload date)

## Architecture

- **API Service**: FastAPI application running on port 8000
- **MongoDB**: NoSQL database for storing bucket and file metadata
- **File Storage**: Local filesystem storage (can be replaced with object storage for production)

## Prerequisites

- Docker and Docker Compose installed
- At least 2GB of free disk space

## Quick Start

### 1. Clone or navigate to the project directory

```bash
cd "cloud computing"
```

### 2. Start the services using Docker Compose

```bash
docker-compose up -d
```

This will start:
- API service on `http://localhost:8000`
- MongoDB on `localhost:27017`

### 3. Access the Web Interface

- **User Dashboard**: http://localhost:8000/
- **Admin Dashboard**: http://localhost:8000/admin

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`

### 4. Verify the services are running

```bash
# Check API health
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs
```

## Web Interface

### User Dashboard (`/`)
- Register new account or login
- View storage usage (1GB limit per user)
- Create and manage buckets
- Upload, download, and delete files
- Real-time storage tracking

### Admin Dashboard (`/admin`)
- View all registered users
- Monitor storage usage per user
- View system statistics (total users, buckets, files, storage)
- User management interface

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
  ```bash
  curl -X POST "http://localhost:8000/api/auth/register" \
    -F "username=myuser" \
    -F "email=user@example.com" \
    -F "password=mypassword" \
    -F "full_name=My Name"
  ```

- `POST /api/auth/login` - Login and get access token
  ```bash
  curl -X POST "http://localhost:8000/api/auth/login" \
    -F "username=myuser" \
    -F "password=mypassword"
  ```

- `GET /api/auth/me` - Get current user information
  ```bash
  curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/auth/me
  ```

### Admin Endpoints (Requires Admin Role)

- `GET /api/admin/users` - List all users
  ```bash
  curl -H "Authorization: Bearer ADMIN_TOKEN" http://localhost:8000/api/admin/users
  ```

- `GET /api/admin/stats` - Get system statistics
  ```bash
  curl -H "Authorization: Bearer ADMIN_TOKEN" http://localhost:8000/api/admin/stats
  ```

### Bucket Operations (Requires Authentication)

- `POST /api/buckets` - Create a new bucket
  ```bash
  curl -X POST "http://localhost:8000/api/buckets?name=my-bucket&description=My%20first%20bucket" \
    -H "Authorization: Bearer YOUR_TOKEN"
  ```

- `GET /api/buckets` - List all buckets for current user
  ```bash
  curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/buckets
  ```

- `GET /api/buckets/{bucket_name}` - Get bucket details
  ```bash
  curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/buckets/my-bucket
  ```

- `DELETE /api/buckets/{bucket_name}` - Delete a bucket
  ```bash
  curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/buckets/my-bucket
  ```

### File Operations (Requires Authentication)

- `POST /api/buckets/{bucket_name}/files` - Upload a file (checks storage limit)
  ```bash
  curl -X POST "http://localhost:8000/api/buckets/my-bucket/files" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -F "file=@/path/to/your/file.txt"
  ```

- `GET /api/buckets/{bucket_name}/files` - List all files in a bucket
  ```bash
  curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/buckets/my-bucket/files
  ```

- `GET /api/buckets/{bucket_name}/files/{filename}` - Download a file
  ```bash
  curl -H "Authorization: Bearer YOUR_TOKEN" \
    -O http://localhost:8000/api/buckets/my-bucket/files/file.txt
  ```

- `DELETE /api/buckets/{bucket_name}/files/{filename}` - Delete a file
  ```bash
  curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" \
    http://localhost:8000/api/buckets/my-bucket/files/file.txt
  ```

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
.
├── app/
│   ├── __init__.py      # Application package
│   ├── main.py          # FastAPI application
│   └── auth.py          # Authentication module
├── static/              # Web UI files
│   ├── index.html       # User dashboard
│   ├── admin.html       # Admin dashboard
│   ├── style.css        # Stylesheet
│   ├── app.js           # User dashboard JavaScript
│   └── admin.js         # Admin dashboard JavaScript
├── docker-compose.yml   # Docker Compose configuration
├── Dockerfile           # API service Docker image
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Development

### Running without Docker

1. Install Python 3.11+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start MongoDB locally or use Docker:
   ```bash
   docker run -d -p 27017:27017 --name mongodb mongo:7.0
   ```
4. Set environment variables:
   ```bash
   export MONGO_URI=mongodb://localhost:27017/
   export STORAGE_PATH=./storage
   ```
5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View API logs only
docker-compose logs -f api

# View MongoDB logs only
docker-compose logs -f mongodb
```

## Stopping the Services

```bash
# Stop services
docker-compose down

# Stop and remove volumes (deletes all data)
docker-compose down -v
```

## Deployment to Cloud Server

### Prerequisites for Cloud Deployment

1. **Cloud Server Instance** (AWS EC2, Google Cloud Compute, Azure VM, etc.)
2. **Docker and Docker Compose** installed on the server
3. **Domain name** (optional, for custom domain)
4. **SSL Certificate** (optional, for HTTPS)

### Deployment Steps

1. **SSH into your cloud server**
   ```bash
   ssh user@your-server-ip
   ```

2. **Clone or upload the project**
   ```bash
   git clone <your-repo-url>
   cd "cloud computing"
   ```

3. **Update docker-compose.yml for production**
   - Consider adding:
     - Reverse proxy (nginx) for HTTPS
     - Resource limits
     - Environment-specific configurations
     - Backup volumes

4. **Start the services**
   ```bash
   docker-compose up -d
   ```

5. **Configure firewall**
   ```bash
   # Allow port 8000 (or your chosen port)
   sudo ufw allow 8000/tcp
   ```

6. **Set up reverse proxy (optional but recommended)**
   - Use nginx or Traefik for HTTPS
   - Configure domain name pointing to your server

### Production Considerations

- **Security**: 
  - Change default admin password
  - Use strong SECRET_KEY environment variable for JWT tokens
  - Enable HTTPS/SSL
  - Implement rate limiting
- **Backup**: Set up regular MongoDB backups
- **Monitoring**: Add logging and monitoring tools
- **Scalability**: Consider using object storage (S3, MinIO) instead of local filesystem
- **Load Balancing**: Add multiple API instances behind a load balancer
- **SSL/TLS**: Use HTTPS with proper certificates

## Database Schema

### Users Collection
```json
{
  "_id": ObjectId,
  "username": "user123",
  "email": "user@example.com",
  "hashed_password": "bcrypt_hash",
  "is_admin": false,
  "full_name": "User Name",
  "created_at": "2024-01-01T00:00:00"
}
```

### Buckets Collection
```json
{
  "_id": ObjectId,
  "name": "bucket-name",
  "description": "Optional description",
  "user_id": ObjectId("user_id"),
  "created_at": "2024-01-01T00:00:00",
  "file_count": 0,
  "total_size": 0
}
```

### Files Collection
```json
{
  "_id": ObjectId,
  "filename": "file.txt",
  "bucket_id": ObjectId("bucket_id"),
  "bucket_name": "bucket-name",
  "user_id": ObjectId("user_id"),
  "size": 1024,
  "content_type": "text/plain",
  "uploaded_at": "2024-01-01T00:00:00",
  "file_path": "/app/storage/user_id/bucket-name/file.txt"
}
```

## Storage Limits

- Each user has a **1GB storage limit**
- Storage usage is tracked in real-time
- Uploads are blocked if they would exceed the limit
- Storage usage is displayed in both user and admin dashboards

## License

This project is for educational purposes.

## Contributing

Feel free to submit issues and enhancement requests!

