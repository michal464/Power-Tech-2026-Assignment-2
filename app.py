
from typing import Optional

from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

app = FastAPI()

deliveries = {}
next_id = 1

VALID_STATUSES = {"created", "in_transit", "delivered"}

NEXT_STATUS = {
    "created": "in_transit",
    "in_transit": "delivered",
}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    message = exc.detail
    if not isinstance(message, str):
        message = "Request failed"

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": message},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body"},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/deliveries", status_code=201)
def create_delivery(data: dict = Body(...)):
    global next_id

    recipient = data.get("recipient")
    address = data.get("address")

    if not isinstance(recipient, str) or not recipient.strip():
        raise HTTPException(400, "recipient must be a non-empty string")

    if not isinstance(address, str) or not address.strip():
        raise HTTPException(400, "address must be a non-empty string")

    delivery = {
        "id": next_id,
        "recipient": recipient,
        "address": address,
        "status": "created",
    }

    deliveries[next_id] = delivery
    next_id += 1

    return delivery


@app.get("/deliveries")
def list_deliveries(status: Optional[str] = None):
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(400, "Unknown delivery status")

    result = list(deliveries.values())

    if status is not None:
        result = [
            delivery for delivery in result
            if delivery["status"] == status
        ]

    return result


@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    delivery = deliveries.get(delivery_id)

    if delivery is None:
        raise HTTPException(404, "Delivery not found")

    return delivery


@app.patch("/deliveries/{delivery_id}/status")
def update_delivery_status(
    delivery_id: int,
    data: dict = Body(...),
):
    if "status" not in data:
        raise HTTPException(400, "Missing status")

    new_status = data["status"]

    if not isinstance(new_status, str) or new_status not in VALID_STATUSES:
        raise HTTPException(400, "Unknown delivery status")

    delivery = deliveries.get(delivery_id)

    if delivery is None:
        raise HTTPException(404, "Delivery not found")

    expected_status = NEXT_STATUS.get(delivery["status"])

    if new_status != expected_status:
        raise HTTPException(409, "Invalid status transition")

    delivery["status"] = new_status
    return delivery


@app.delete("/deliveries/{delivery_id}", status_code=204)
def delete_delivery(delivery_id: int):
    delivery = deliveries.get(delivery_id)

    if delivery is None:
        raise HTTPException(404, "Delivery not found")

    if delivery["status"] != "created":
        raise HTTPException(
            409,
            "Only created deliveries can be deleted",
        )

    del deliveries[delivery_id]
    return Response(status_code=204)
