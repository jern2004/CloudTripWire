import requests
import time
import sys

API_BASE = "http://127.0.0.1:8000/api"

# Sample incidents matching your frontend mock data
SAMPLE_INCIDENTS = [
    {
        "cloud": "AWS",
        "principal": "arn:aws:iam::123456789012:user/honeypot-user",
        "trigger_type": "S3 Access",
        "region": "us-east-1",
        "severity": "High",
        "ip_address": "203.45.67.89",
        "user_agent": "aws-cli/2.13.5 Python/3.11.4",
        "resource_arn": "arn:aws:s3:::honeypot-bucket-prod/sensitive-data.zip"
    },
    {
        "cloud": "Azure",
        "principal": "decoy-service-principal@contoso.com",
        "trigger_type": "Key Vault Access",
        "region": "eastus",
        "severity": "Critical",
        "ip_address": "45.123.78.210",
        "user_agent": "Azure-CLI/2.50.0",
        "resource_arn": "/subscriptions/xxxxx/resourceGroups/honeytokens/vaults/honeypot-vault"
    },
    {
        "cloud": "AWS",
        "principal": "arn:aws:iam::123456789012:role/trap-role",
        "trigger_type": "DynamoDB Query",
        "region": "eu-west-1",
        "severity": "Medium",
        "ip_address": "102.34.56.178",
        "user_agent": "Boto3/1.28.25",
        "resource_arn": "arn:aws:dynamodb:eu-west-1:123456789012:table/honeypot-table"
    },
    {
        "cloud": "Azure",
        "principal": "honeypot-app@tenant.onmicrosoft.com",
        "trigger_type": "Storage Blob Read",
        "region": "westus2",
        "severity": "Low",
        "ip_address": "78.92.145.23",
        "user_agent": "azure-storage-python/12.0",
        "resource_arn": "/subscriptions/xxxxx/resourceGroups/honeytokens/storageAccounts/honeypot-storage"
    },
    {
        "cloud": "AWS",
        "principal": "arn:aws:iam::987654321098:user/decoy-admin",
        "trigger_type": "Lambda Invocation",
        "region": "ap-southeast-1",
        "severity": "High",
        "ip_address": "156.78.90.234",
        "user_agent": "python-requests/2.31.0",
        "resource_arn": "arn:aws:lambda:ap-southeast-1:987654321098:function:honeypot-function"
    }
]


def create_sample_incidents():
    """Create sample incidents via API"""
    print("=" * 60)
    print("📝 CloudTripwire - Creating Sample Incidents")
    print("=" * 60)
    print(f"🔗 Connecting to: {API_BASE}")
    print()
    
    # Check if backend is running
    try:
        response = requests.get(f"http://127.0.0.1:8000/health", timeout=2)
        if response.status_code == 200:
            print("✅ Backend is running!")
            print()
        else:
            print("❌ Backend returned unexpected status")
            return
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to backend!")
        print("   Make sure backend is running:")
        print("   python3 -m uvicorn app.main:app --reload")
        print()
        return
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return
    
    created = 0
    failed = 0
    
    for i, incident_data in enumerate(SAMPLE_INCIDENTS, 1):
        try:
            print(f"[{i}/{len(SAMPLE_INCIDENTS)}] Creating incident: {incident_data['trigger_type']}...", end=" ")
            
            response = requests.post(
                f"{API_BASE}/incidents", 
                json=incident_data, 
                timeout=5
            )
            
            if response.status_code == 201:
                incident = response.json()
                print(f"✅ {incident['id']}")
                created += 1
            else:
                print(f"❌ Failed ({response.status_code})")
                print(f"   Response: {response.text[:100]}")
                failed += 1
                
        except requests.exceptions.Timeout:
            print("❌ Timeout")
            failed += 1
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"🎉 Done! Created {created}/{len(SAMPLE_INCIDENTS)} incidents")
    if failed > 0:
        print(f"⚠️  {failed} incidents failed")
    print("=" * 60)
    print()
    print("🌐 Next steps:")
    print("   1. Start frontend: cd frontend && npm run dev")
    print("   2. Open: http://localhost:5173")
    print("   3. Click 'Mock Data' → 'Live API' button")
    print("   4. See your incidents! 🚀")
    print()


if __name__ == "__main__":
    print()
    print("⏳ Waiting 1 second for server to be ready...")
    time.sleep(1)
    create_sample_incidents()
