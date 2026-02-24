curl -X POST http://localhost:7173/send-it \
-H "Content-Type: application/json" \
-d '{
    "first_name": "Test",
    "surname": "User",
    "number": "0400000000",
    "email": "test@example.com",
    "issue": "Test Issue",
    "address_line_1": "123 Test St",
    "suburb": "Testville",
    "escooter_make": "TestMake",
    "escooter_model": "TestModel"
}'
