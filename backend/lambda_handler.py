"""
LLM Orchestration Engine - AWS Lambda Handler
Uses Mangum to adapt FastAPI for Lambda + API Gateway
"""

from mangum import Mangum

from app.main import app


# Create Lambda handler
handler = Mangum(app, lifespan="off")


# Optional: Add Lambda-specific warmup handling
def lambda_handler(event, context):
    """
    AWS Lambda entry point
    
    Handles:
    - API Gateway events (HTTP requests)
    - CloudWatch scheduled events (warmup)
    - Direct Lambda invocations
    """
    
    # Handle warmup events (CloudWatch scheduled)
    if event.get("source") == "aws.events" or event.get("detail-type") == "Scheduled Event":
        return {
            "statusCode": 200,
            "body": "Warmup successful"
        }
    
    # Handle direct invocations for async processing
    if event.get("type") == "async_generate":
        # Process async generation request
        from app.services import get_router
        from app.models import GenerateRequest
        import asyncio
        
        request_data = event.get("request", {})
        request = GenerateRequest(**request_data)
        
        router = get_router()
        # Run async code in Lambda
        loop = asyncio.get_event_loop()
        model, decision = loop.run_until_complete(router.select_model(request))
        response = loop.run_until_complete(
            router.execute_request(request, model, decision)
        )
        
        return {
            "success": response.success,
            "content": response.content,
            "model": response.model_used,
        }
    
    # Default: Handle HTTP requests via Mangum
    return handler(event, context)