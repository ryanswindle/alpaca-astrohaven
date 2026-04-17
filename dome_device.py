from datetime import datetime, timezone
from threading import Event, Thread
import time

from pymodbus.client import ModbusTcpClient

from config import DeviceConfig
from log import get_logger


logger = get_logger()


class ShutterState:
    OPEN = 0
    CLOSED = 1
    OPENING = 2
    CLOSING = 3
    ERROR = 4


###########################################################
# Modbus coil / register addresses for the AstroHaven PLC #
###########################################################
class AH_ADDRESS:
    """Modbus bit addresses (user manual version T4 + reverse engineering)."""

    # Left inner
    L_INNER_JOG_UP = 9
    L_INNER_JOG_DOWN = 10
    L_INNER_CLOSE = 13
    L_INNER_OPEN = 14
    L_INNER_MFAULT = 42
    L_INNER_SFAULT = 43
    L_INNER_MPTO = 84
    L_INNER_SPTO = 85
    L_INNER_GOTO = 17
    L_INNER_TARGET_ANG = 5
    L_INNER_CURRENT_ANG = 31

    # Left outer
    L_OUTER_JOG_UP = 0
    L_OUTER_JOG_DOWN = 1
    L_OUTER_CLOSE = 4
    L_OUTER_OPEN = 5
    L_OUTER_MFAULT = 46
    L_OUTER_SFAULT = 47
    L_OUTER_MPTO = 82
    L_OUTER_SPTO = 83
    L_OUTER_GOTO = 8
    L_OUTER_TARGET_ANG = 4
    L_OUTER_CURRENT_ANG = 29

    # Right inner
    R_INNER_JOG_UP = 18
    R_INNER_JOG_DOWN = 19
    R_INNER_CLOSE = 22
    R_INNER_OPEN = 23
    R_INNER_MFAULT = 44
    R_INNER_SFAULT = 45
    R_INNER_MPTO = 86
    R_INNER_SPTO = 87
    R_INNER_GOTO = 26
    R_INNER_TARGET_ANG = 6
    R_INNER_CURRENT_ANG = 33

    # Right outer
    R_OUTER_JOG_UP = 27
    R_OUTER_JOG_DOWN = 28
    R_OUTER_CLOSE = 31
    R_OUTER_OPEN = 32
    R_OUTER_MFAULT = 48
    R_OUTER_SFAULT = 49
    R_OUTER_MPTO = 88
    R_OUTER_SPTO = 89
    R_OUTER_GOTO = 35
    R_OUTER_TARGET_ANG = 23
    R_OUTER_CURRENT_ANG = 35

    # Fifth shutter
    F_JOG_UP = 111
    F_JOG_DOWN = 112
    F_CLOSE = 115
    F_OPEN = 116
    F_MFAULT = 50
    F_SFAULT = 120
    F_MPTO = 51
    F_SPTO = 121
    F_GOTO = 119
    F_TARGET_ANG = 64
    F_CURRENT_ANG = 22

    # Stop all — toggles brakes / gears the motors
    STOP_ALL = 55


# Fault coil addresses (all motor and sensor faults)
_FAULT_ADDRESSES = [
    AH_ADDRESS.L_INNER_MFAULT,
    AH_ADDRESS.L_INNER_SFAULT,
    AH_ADDRESS.L_OUTER_MFAULT,
    AH_ADDRESS.L_OUTER_SFAULT,
    AH_ADDRESS.R_INNER_MFAULT,
    AH_ADDRESS.R_INNER_SFAULT,
    AH_ADDRESS.R_OUTER_MFAULT,
    AH_ADDRESS.R_OUTER_SFAULT,
    AH_ADDRESS.F_MFAULT,
    AH_ADDRESS.F_SFAULT,
]

# Coil addresses for opening / closing all shutters
_OPEN_ADDRESSES = [
    (AH_ADDRESS.L_INNER_OPEN, "left inner"),
    (AH_ADDRESS.R_INNER_OPEN, "right inner"),
    (AH_ADDRESS.L_OUTER_OPEN, "left outer"),
    (AH_ADDRESS.R_OUTER_OPEN, "right outer"),
    (AH_ADDRESS.F_OPEN, "fifth"),
]

_CLOSE_ADDRESSES = [
    (AH_ADDRESS.L_INNER_CLOSE, "left inner"),
    (AH_ADDRESS.R_INNER_CLOSE, "right inner"),
    (AH_ADDRESS.L_OUTER_CLOSE, "left outer"),
    (AH_ADDRESS.R_OUTER_CLOSE, "right outer"),
    (AH_ADDRESS.F_CLOSE, "fifth"),
]


class DomeDevice:
    """Low-level driver for the AstroHaven dome (Modbus TCP)."""

    def __init__(self, device_config: DeviceConfig):
        self._config = device_config

        # Connection state
        self._client: ModbusTcpClient | None = None
        self._connected = False
        self._connecting = False

        # Brake monitor
        self._brake_stop = Event()

        # Motion tracking
        self._last_status: int | None = None
        self._motion_start_time: datetime | None = None


    #######################################
    # ASCOM Methods Common To All Devices #
    #######################################
    def connect(self):
        """Establish Modbus TCP connection and start brake monitor."""
        if self._connecting or self._connected:
            return

        self._connecting = True
        try:
            self._client = ModbusTcpClient(
                host=self._config.modbus_host,
                port=self._config.modbus_port,
            )
            self._client.connect()
            self._connected = True
            logger.info(f"Connected to dome: {self._config.entity}")

            # Start brake monitor thread
            self._brake_stop.clear()
            t = Thread(target=self._brake_monitor_loop, name="BrakeMonitor", daemon=True)
            t.start()
        except Exception as e:
            logger.error(f"Connect error: {e}")
            self._connected = False
            raise
        finally:
            self._connecting = False

    @property
    def connected(self) -> bool:
        return self._connected

    @connected.setter
    def connected(self, value: bool):
        if value and not self._connected:
            self.connect()
        elif not value and self._connected:
            self.disconnect()

    @property
    def connecting(self) -> bool:
        return self._connecting

    def disconnect(self):
        """Disable brake monitor, close the Modbus TCP connection."""
        self._brake_stop.set()
        try:
            if self._client:
                self._client.close()
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
        self._connected = False
        logger.info(f"Disconnected from dome: {self._config.entity}")

    @property
    def entity(self) -> str:
        return self._config.entity


    ####################
    # IDome properties #
    ####################
    @property
    def can_find_home(self) -> bool:
        return False

    @property
    def can_park(self) -> bool:
        return False

    @property
    def can_set_altitude(self) -> bool:
        return False

    @property
    def can_set_azimuth(self) -> bool:
        return False

    @property
    def can_set_park(self) -> bool:
        return False

    @property
    def can_set_shutter(self) -> bool:
        return True

    @property
    def can_slave(self) -> bool:
        return False

    @property
    def can_sync_azimuth(self) -> bool:
        return False

    @property
    def shutter_status(self) -> int:
        """Determine current shutter state from PLC registers/coils.

        The AstroHaven PLC does not expose a single "state" register.
        We infer state from the fifth-shutter encoder angle, then fall
        back to checking the open/close command coils and faults.
        """
        try:
            # Read fifth shutter angle
            result = self._client.read_holding_registers(AH_ADDRESS.F_CURRENT_ANG)
            if result.isError():
                logger.error(f"Error reading fifth shutter angle register {AH_ADDRESS.F_CURRENT_ANG}")
                return ShutterState.ERROR

            angle = result.registers[0]

            # Fully open
            if angle > self._config.fifth_open_angle:
                new_status = ShutterState.OPEN
            # Fully closed
            elif angle < self._config.fifth_closed_angle:
                new_status = ShutterState.CLOSED
            else:
                new_status = None  # mid-travel — check coils

            # If definitively OPEN or CLOSED, clear motion timer
            if new_status in (ShutterState.OPEN, ShutterState.CLOSED):
                if self._last_status != new_status:
                    self._last_status = new_status
                    self._motion_start_time = None
                return new_status

            # Check open command coils → OPENING
            for addr, _name in _OPEN_ADDRESSES:
                res = self._client.read_coils(addr)
                if res.isError():
                    continue
                if res.bits[0]:
                    new_status = ShutterState.OPENING
                    break

            # Check close command coils → CLOSING
            if new_status is None:
                for addr, _name in _CLOSE_ADDRESSES:
                    res = self._client.read_coils(addr)
                    if res.isError():
                        continue
                    if res.bits[0]:
                        new_status = ShutterState.CLOSING
                        break

            # Handle motion states with timeout
            if new_status in (ShutterState.OPENING, ShutterState.CLOSING):
                now = datetime.now(timezone.utc)
                if self._last_status != new_status:
                    self._motion_start_time = now
                    self._last_status = new_status
                elif self._motion_start_time:
                    elapsed = (now - self._motion_start_time).total_seconds()
                    if elapsed > self._config.timeout:
                        logger.error("Dome motion timeout")
                        return ShutterState.ERROR
                return new_status

            # Fallback: check faults
            if self._read_faults():
                return ShutterState.ERROR

            return ShutterState.ERROR  # undefined state

        except Exception as e:
            logger.error(f"Exception determining shutter status: {e}")
            return ShutterState.ERROR

    @property
    def slaved(self) -> bool:
        return False

    @property
    def slewing(self) -> bool:
        return self.shutter_status in (ShutterState.OPENING, ShutterState.CLOSING)

    @property
    def timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


    #################
    # IDome methods #
    #################
    def open_shutter(self):
        """Command all shutters to open (returns immediately)."""
        status = self.shutter_status
        if status in (ShutterState.OPEN, ShutterState.OPENING):
            logger.debug("Shutters already open/opening, ignoring OpenShutter")
            return

        logger.info("Opening shutters")
        self._enable_motors()
        self._write_coils_batch(_OPEN_ADDRESSES, True, "open")
        # PLC doesn't auto-reset command coils — reset them after the
        # motion interval in a background thread so we return immediately.
        Thread(target=self._reset_coils_after_delay,
               args=(_OPEN_ADDRESSES, "open"),
               name="ResetOpenCoils", daemon=True).start()

    def close_shutter(self):
        """Command all shutters to close (returns immediately)."""
        status = self.shutter_status
        if status in (ShutterState.CLOSED, ShutterState.CLOSING):
            logger.debug("Shutters already closed/closing, ignoring CloseShutter")
            return

        logger.info("Closing shutters")
        self._enable_motors()
        self._write_coils_batch(_CLOSE_ADDRESSES, True, "close")
        Thread(target=self._reset_coils_after_delay,
               args=(_CLOSE_ADDRESSES, "close"),
               name="ResetCloseCoils", daemon=True).start()

    def abort_slew(self):
        """Emergency stop — engage brakes."""
        try:
            result = self._client.write_coil(AH_ADDRESS.STOP_ALL, False)
            if result.isError():
                raise RuntimeError("Cannot write STOP_ALL coil")
            logger.info("AbortSlew: motors stopped")
        except Exception as e:
            logger.error(f"AbortSlew error: {e}")
            raise RuntimeError("Cannot disable motors") from e


    ####################
    # Internal helpers #
    ####################
    def _reset_coils_after_delay(self, addresses: list, operation: str):
        """Sleep for open_close_time then reset the command coils."""
        try:
            time.sleep(self._config.open_close_time)
            self._write_coils_batch(addresses, False, f"reset {operation}")
            logger.debug(f"Shutters {operation} coils reset")
        except Exception as e:
            logger.error(f"Error resetting {operation} coils: {e}")

    def _read_faults(self) -> bool:
        """Return True if any fault coil is set."""
        try:
            for addr in _FAULT_ADDRESSES:
                result = self._client.read_coils(addr)
                if result.isError():
                    logger.error(f"Error reading fault address {addr}")
                    return True
                if result.bits[0]:
                    logger.warning(f"Fault detected at address {addr}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error reading faults: {e}")
            return True

    def _enable_motors(self):
        """Check faults and disengage brakes if needed."""
        if self._read_faults():
            raise RuntimeError("Dome fault detected")

        try:
            result = self._client.read_coils(AH_ADDRESS.STOP_ALL)
            if result.isError():
                raise RuntimeError("Cannot read STOP_ALL coil")
            if result.bits[0]:
                wr = self._client.write_coil(AH_ADDRESS.STOP_ALL, False)
                if wr.isError():
                    raise RuntimeError("Cannot write STOP_ALL coil")
                logger.debug("Motors enabled (brakes released)")
                time.sleep(1)
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Motor enable communication error: {e}") from e

        if self._read_faults():
            raise RuntimeError("Dome fault after enabling motors")

    def _brake_monitor_loop(self):
        """Keep motors enabled — the AstroHaven PLC engages brakes after ~2 min of inactivity."""
        interval = self._config.brake_monitor_interval
        while self._connected and not self._brake_stop.is_set():
            try:
                self._enable_motors()
            except Exception as e:
                logger.warning(f"Brake monitor: {e}")
            self._brake_stop.wait(timeout=interval)

    def _write_coils_batch(self, addresses: list, value: bool, operation: str):
        """Write to multiple coils with unified error handling."""
        for addr, name in addresses:
            result = self._client.write_coil(addr, value)
            if result.isError():
                raise RuntimeError(f"Cannot {operation} {name} (address {addr})")