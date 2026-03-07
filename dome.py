from typing import Annotated, Dict

from fastapi import APIRouter, Depends, Form, HTTPException

from dome_device import DomeDevice
from exceptions import (
    DriverException,
    NotConnectedException,
    NotImplementedException,
)
from log import get_logger
from responses import MethodResponse, PropertyResponse, StateValue
from shr import AlpacaGetParams, AlpacaPutParams, to_bool


logger = get_logger()

router = APIRouter(prefix="/api/v1/dome", tags=["Dome"])

devices: Dict[int, DomeDevice] = {}


def set_devices(dev_dict: Dict[int, DomeDevice]):
    global devices
    devices = dev_dict


def get_device(devnum: int) -> DomeDevice:
    if devnum not in devices:
        raise HTTPException(
            status_code=400,
            detail=f"Device number {devnum} does not exist.",
        )
    return devices[devnum]


##################################
# High-level device/library info #
##################################
class DeviceMetadata:
    Name = "AstroHaven"
    Version = "1.0.0"
    Description = "AstroHaven Dome ASCOM Alpaca Driver via Modbus"
    DeviceType = "Dome"
    Info = "Alpaca Device\nImplements IDomeV3\nASCOM Initiative"
    InterfaceVersion = 3


def _connected_property(device: DomeDevice, value, params):
    """Helper for simple properties that require connection."""
    if not device.connected:
        return PropertyResponse.create(
            value=None,
            client_transaction_id=params.client_transaction_id,
            error=NotConnectedException(),
        ).model_dump()
    return PropertyResponse.create(
        value=value,
        client_transaction_id=params.client_transaction_id,
    ).model_dump()


#######################################
# ASCOM Methods Common To All Devices #
#######################################
@router.put("/{devnum}/action", summary="")
async def action(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("Action"),
    ).model_dump()


@router.put("/{devnum}/commandblind", summary="")
async def commandblind(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("CommandBlind"),
    ).model_dump()


@router.put("/{devnum}/commandbool", summary="")
async def commandbool(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("CommandBool"),
    ).model_dump()


@router.put("/{devnum}/commandstring", summary="")
async def commandstring(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("CommandString"),
    ).model_dump()


@router.put("/{devnum}/connect", summary="")
async def connect(devnum: int, params: AlpacaPutParams = Depends()):
    device = get_device(devnum)
    try:
        device.connect()
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
        ).model_dump()
    except Exception as ex:
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
            error=DriverException(0x500, "Dome.Connect failed", ex),
        ).model_dump()


@router.get("/{devnum}/connected", summary="")
async def connected_get(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return PropertyResponse.create(
        value=device.connected,
        client_transaction_id=params.client_transaction_id,
    ).model_dump()


@router.put("/{devnum}/connected", summary="")
async def connected_put(devnum: int, Connected: Annotated[str, Form()], params: AlpacaPutParams = Depends()):
    device = get_device(devnum)
    conn = to_bool(Connected)
    try:
        device.connected = conn
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
        ).model_dump()
    except HTTPException:
        raise
    except Exception as ex:
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
            error=DriverException(0x500, "Dome.Connected failed", ex),
        ).model_dump()


@router.get("/{devnum}/connecting", summary="")
async def connecting_get(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return PropertyResponse.create(
        value=device.connecting,
        client_transaction_id=params.client_transaction_id,
    ).model_dump()


@router.get("/{devnum}/description", summary="")
async def description(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=DeviceMetadata.Description,
        client_transaction_id=params.client_transaction_id,
    ).model_dump()


@router.get("/{devnum}/devicestate", summary="")
async def devicestate(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    if not device.connected:
        return PropertyResponse.create(
            value=None,
            client_transaction_id=params.client_transaction_id,
            error=NotConnectedException(),
        ).model_dump()
    try:
        val = [
            StateValue(Name="ShutterStatus", Value=device.shutterstatus).model_dump(),
            StateValue(Name="Slewing", Value=device.slewing).model_dump(),
            StateValue(Name="TimeStamp", Value=device.timestamp).model_dump(),
        ]
        return PropertyResponse.create(
            value=val,
            client_transaction_id=params.client_transaction_id,
        ).model_dump()
    except Exception as ex:
        return PropertyResponse.create(
            value=None,
            client_transaction_id=params.client_transaction_id,
            error=DriverException(0x500, "Dome.DeviceState failed", ex),
        ).model_dump()


@router.put("/{devnum}/disconnect", summary="")
async def disconnect(devnum: int, params: AlpacaPutParams = Depends()):
    device = get_device(devnum)
    try:
        device.disconnect()
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
        ).model_dump()
    except Exception as ex:
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
            error=DriverException(0x500, "Dome.Disconnect failed", ex),
        ).model_dump()


@router.get("/{devnum}/driverinfo", summary="")
async def driverinfo(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=DeviceMetadata.Info,
        client_transaction_id=params.client_transaction_id,
    ).model_dump()


@router.get("/{devnum}/driverversion", summary="")
async def driverversion(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=DeviceMetadata.Version,
        client_transaction_id=params.client_transaction_id,
    ).model_dump()


@router.get("/{devnum}/interfaceversion", summary="")
async def interfaceversion(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=DeviceMetadata.InterfaceVersion,
        client_transaction_id=params.client_transaction_id,
    ).model_dump()


@router.get("/{devnum}/name", summary="")
async def name(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=DeviceMetadata.Name,
        client_transaction_id=params.client_transaction_id,
    ).model_dump()


@router.get("/{devnum}/supportedactions", summary="")
async def supportedactions(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=[],
        client_transaction_id=params.client_transaction_id,
    ).model_dump()


####################
# IDome properties #
####################
@router.get("/{devnum}/altitude", summary="")
async def altitude(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=None,
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("Altitude"),
    ).model_dump()


@router.get("/{devnum}/athome", summary="")
async def athome(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=None,
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("AtHome"),
    ).model_dump()


@router.get("/{devnum}/atpark", summary="")
async def atpark(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=None,
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("AtPark"),
    ).model_dump()


@router.get("/{devnum}/azimuth", summary="")
async def azimuth(devnum: int, params: AlpacaGetParams = Depends()):
    return PropertyResponse.create(
        value=None,
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("Azimuth"),
    ).model_dump()


@router.get("/{devnum}/canfindhome", summary="")
async def canfindhome(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return _connected_property(device, device.can_find_home, params)


@router.get("/{devnum}/canpark", summary="")
async def canpark(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return _connected_property(device, device.can_park, params)


@router.get("/{devnum}/cansetaltitude", summary="")
async def cansetaltitude(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return _connected_property(device, device.can_set_altitude, params)


@router.get("/{devnum}/cansetazimuth", summary="")
async def cansetazimuth(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return _connected_property(device, device.can_set_azimuth, params)


@router.get("/{devnum}/cansetpark", summary="")
async def cansetpark(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return _connected_property(device, device.can_set_park, params)


@router.get("/{devnum}/cansetshutter", summary="")
async def cansetshutter(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return _connected_property(device, device.can_set_shutter, params)


@router.get("/{devnum}/canslave", summary="")
async def canslave(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return _connected_property(device, device.can_slave, params)


@router.get("/{devnum}/cansyncazimuth", summary="")
async def cansyncazimuth(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return _connected_property(device, device.can_sync_azimuth, params)


@router.get("/{devnum}/shutterstatus", summary="")
async def shutterstatus_get(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    if not device.connected:
        return PropertyResponse.create(
            value=None,
            client_transaction_id=params.client_transaction_id,
            error=NotConnectedException(),
        ).model_dump()
    try:
        return PropertyResponse.create(
            value=device.shutter_status,
            client_transaction_id=params.client_transaction_id,
        ).model_dump()
    except Exception as ex:
        return PropertyResponse.create(
            value=None,
            client_transaction_id=params.client_transaction_id,
            error=DriverException(0x500, "Dome.ShutterStatus failed", ex),
        ).model_dump()


@router.get("/{devnum}/slaved", summary="")
async def slaved_get(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    return _connected_property(device, device.slaved, params)


@router.put("/{devnum}/slaved", summary="")
async def slaved_put(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("Slaved"),
    ).model_dump()


@router.get("/{devnum}/slewing", summary="")
async def slewing_get(devnum: int, params: AlpacaGetParams = Depends()):
    device = get_device(devnum)
    if not device.connected:
        return PropertyResponse.create(
            value=None,
            client_transaction_id=params.client_transaction_id,
            error=NotConnectedException(),
        ).model_dump()
    try:
        return PropertyResponse.create(
            value=device.slewing,
            client_transaction_id=params.client_transaction_id,
        ).model_dump()
    except Exception as ex:
        return PropertyResponse.create(
            value=None,
            client_transaction_id=params.client_transaction_id,
            error=DriverException(0x500, "Dome.Slewing failed", ex),
        ).model_dump()


#################
# IDome methods #
#################
@router.put("/{devnum}/abortslew", summary="")
async def abortslew(devnum: int, params: AlpacaPutParams = Depends()):
    device = get_device(devnum)
    if not device.connected:
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
            error=NotConnectedException(),
        ).model_dump()
    try:
        device.abort_slew()
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
        ).model_dump()
    except Exception as ex:
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
            error=DriverException(0x500, "Dome.AbortSlew failed", ex),
        ).model_dump()


@router.put("/{devnum}/closeshutter", summary="")
async def closeshutter(devnum: int, params: AlpacaPutParams = Depends()):
    device = get_device(devnum)
    if not device.connected:
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
            error=NotConnectedException(),
        ).model_dump()
    try:
        device.close_shutter()
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
        ).model_dump()
    except Exception as ex:
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
            error=DriverException(0x500, "Dome.CloseShutter failed", ex),
        ).model_dump()


@router.put("/{devnum}/findhome", summary="")
async def findhome(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("FindHome"),
    ).model_dump()


@router.put("/{devnum}/openshutter", summary="")
async def openshutter(devnum: int, params: AlpacaPutParams = Depends()):
    device = get_device(devnum)
    if not device.connected:
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
            error=NotConnectedException(),
        ).model_dump()
    try:
        device.open_shutter()
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
        ).model_dump()
    except Exception as ex:
        return MethodResponse.create(
            client_transaction_id=params.client_transaction_id,
            error=DriverException(0x500, "Dome.OpenShutter failed", ex),
        ).model_dump()


@router.put("/{devnum}/park", summary="")
async def park(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("Park"),
    ).model_dump()


@router.put("/{devnum}/setpark", summary="")
async def setpark(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("SetPark"),
    ).model_dump()


@router.put("/{devnum}/slewtoaltitude", summary="")
async def slewtoaltitude(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("SlewToAltitude"),
    ).model_dump()


@router.put("/{devnum}/slewtoazimuth", summary="")
async def slewtoazimuth(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("SlewToAzimuth"),
    ).model_dump()


@router.put("/{devnum}/synctoazimuth", summary="")
async def synctoazimuth(devnum: int, params: AlpacaPutParams = Depends()):
    return MethodResponse.create(
        client_transaction_id=params.client_transaction_id,
        error=NotImplementedException("SyncToAzimuth"),
    ).model_dump()