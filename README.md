# AstroHaven – ASCOM Alpaca Server for AstroHaven domes (Modbus TCP)

A FastAPI-based server, implementing the ASCOM **IDomeV3** interface.  Communication is via Modbus TCP to the
AstroHaven PLC using coil and register addresses provided by the vendor (unique to each dome).

---

## Implemented IDomeV3 capabilities as of this driver version

| Property/Method | Supported |
|-----------------|-----------|
| Altitude        | ✘         |
| AtHome          | ✘         |
| AtPark          | ✘         |
| Azimuth         | ✘         |
| CanFindHome     | ✘         |
| CanPark         | ✘         |
| CanSetAltitude  | ✘         |
| CanSetAzimuth   | ✘         |
| CanSetPark      | ✘         |
| CanSetShutter   | ✔         |
| CanSlave        | ✘         |
| CanSyncAzimuth  | ✘         |
| ShutterStatus   | ✔         |
| Slaved          | ✘         |
| Slewing         | ✔         |
| AbortSlew       | ✔         |
| CloseShutter    | ✔         |
| FindHome        | ✘         |
| OpenShutter     | ✔         |
| Park            | ✘         |
| SetPark         | ✘         |
| SlewToAltitude  | ✘         |
| SlewToAzimuth   | ✘         |
| SyncToAzimuth   | ✘         |

Tested on the AstroHaven 16-X2T-2D, which is a clamshell dome with five shutter panels (left inner/outer, right
inner/outer, fifth).  Shutter state is inferred from the fifth-shutter encoder angle and the PLC command coils.

---

## Architecture

| File              | Purpose                                     |
|-------------------|---------------------------------------------|
| `main.py`         | FastAPI app, lifespan, router wiring        |
| `config.py`       | Pydantic config models, YAML loader         |
| `config.yaml`     | User-editable configuration                 |
| `dome.py`         | FastAPI router – IDomeV3 endpoints          |
| `dome_device.py`  | Low-level Modbus TCP driver                 |
| `management.py`   | `/management` Alpaca management endpoints   |
| `setup.py`        | `/setup` HTML stub pages                    |
| `discovery.py`    | UDP Alpaca discovery responder (port 32227) |
| `responses.py`    | Pydantic response models                    |
| `exceptions.py`   | ASCOM Alpaca error classes                  |
| `shr.py`          | Shared FastAPI dependencies / helpers       |
| `log.py`          | Loguru config + stdlib intercept handler    |
| `test.py`         | Quick smoke-test script                     |
| `requirements.txt`| Python package dependencies                 |
| `Dockerfile`      | Container build                             |

---

## Configuration

Edit `config.yaml` to match your dome setup.

Multiple AstroHaven domes can be registered by adding further entries under
`devices:` with distinct `device_number` values.


---

## Quick start

```bash
pip install -r requirements.txt
python main.py
```

The server starts on `0.0.0.0:5000` by default (configurable in `config.yaml`).

---

## Smoke test

```bash
# Requires hardware connected, i.e. will move dome
python test.py
```

---

## Docker

```bash
docker build -t alpaca-astrohaven .
docker run -d --name alpaca-astrohaven \
    --network host \
    --restart unless-stopped \
    alpaca-astrohaven
docker logs -f alpaca-astrohaven
```

---

## PLC notes

The AstroHaven PLC has some quirks that this driver accommodates:

- **No state register** — shutter state is inferred from the fifth-shutter
  encoder angle (holding register 22) and the open/close command coils.
- **Sticky command coils** — the PLC does not auto-reset the open/close
  command bits after motion completes, so the driver waits `open_close_time`
  seconds then clears them manually.
- **Brake auto-engage** — the PLC engages motor brakes after ~2 minutes of
  inactivity.  A background thread periodically re-enables the motors while
  the device is connected.
