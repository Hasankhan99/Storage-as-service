#!/bin/bash

# Bucket as a Service - API Test Script
# Make sure the services are running: docker-compose up -d

API_URL="http://localhost:8000"

echo "=== Testing Bucket as a Service API ==="
echo ""

# Health check
echo "1. Health Check:"
curl -s "$API_URL/health" | python3 -m json.tool
echo -e "\n"

# Create a bucket
echo "2. Creating bucket 'test-bucket':"
curl -s -X POST "$API_URL/api/buckets?name=test-bucket&description=Test%20bucket" | python3 -m json.tool
echo -e "\n"

# List buckets
echo "3. Listing all buckets:"
curl -s "$API_URL/api/buckets" | python3 -m json.tool
echo -e "\n"

# Get bucket details
echo "4. Getting bucket details:"
curl -s "$API_URL/api/buckets/test-bucket" | python3 -m json.tool
echo -e "\n"

# Create a test file
echo "5. Creating test file:"
echo "Hello, Bucket Service!" > /tmp/test_file.txt

# Upload file
echo "6. Uploading file to bucket:"
curl -s -X POST "$API_URL/api/buckets/test-bucket/files" \
  -F "file=@/tmp/test_file.txt" | python3 -m json.tool
echo -e "\n"

# List files
echo "7. Listing files in bucket:"
curl -s "$API_URL/api/buckets/test-bucket/files" | python3 -m json.tool
echo -e "\n"

# Download file
echo "8. Downloading file:"
curl -s "$API_URL/api/buckets/test-bucket/files/test_file.txt"
echo -e "\n\n"

# Delete file
echo "9. Deleting file:"
curl -s -X DELETE "$API_URL/api/buckets/test-bucket/files/test_file.txt" | python3 -m json.tool
echo -e "\n"

# Delete bucket
echo "10. Deleting bucket:"
curl -s -X DELETE "$API_URL/api/buckets/test-bucket" | python3 -m json.tool
echo -e "\n"

echo "=== Test Complete ==="

