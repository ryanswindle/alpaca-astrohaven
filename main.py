"""
ASCOM Alpaca AstroHaven Dome Server – Main FastAPI Application

Entrypoint that:
  - Creates the FastAPI application
  - Configures logging (loguru + stdlib intercept)
  - Instantiates DomeDevice instances from config.yaml
  - Starts the Alpaca discovery responder (UDP 32227)
  - Includes management, setup, and dome routers
  - Handles graceful shutdown (disconnects all devices)
"""

from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import config
from discovery import DiscoveryResponder
import dome
from dome_device import DomeDevice
from log import get_logger, setup_logging
import management
import setup


setup_logging()
logger = get_logger()

# Device registry: device_number → DomeDevice
devices: Dict[int, DomeDevice] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager – startup and shutdown."""
    logger.info(f"Starting {config.entity} on {config.server.host}:{config.server.port}")

    # Instantiate devices from config
    for device_config in config.devices:
        dev = DomeDevice(device_config)
        devices[device_config.device_number] = dev
        logger.info(f"Registered device: {device_config.entity}")

    # Share devices dict with routers
    dome.set_devices(devices)
    management.set_devices(devices)

    # Start Alpaca discovery responder
    try:
        DiscoveryResponder(config.server.host, config.server.port)
    except Exception as e:
        logger.warning(f"Could not start discovery responder: {e}")

    yield

    # Shutdown: disconnect all devices
    for dev in devices.values():
        if dev.connected:
            try:
                dev.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting {config.entity}: {e}")
    logger.info("Server shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="ASCOM Alpaca AstroHaven Dome Server",
    description="ASCOM Alpaca API for the AstroHaven dome (Modbus TCP)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def _alpaca_validation_handler(request: Request, exc: RequestValidationError):
    """Alpaca clients (e.g. ConformU) expect HTTP 400 for malformed
    parameters; FastAPI defaults to 422. Remap so we match the spec."""
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


# Include routers
app.include_router(management.router)
app.include_router(setup.router)
app.include_router(dome.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=False,
        access_log=False,
    )