"""API.

This is the main API code that reaches out to the PIWIGO server to get and set the values.
"""

from dataclasses import dataclass
from enum import StrEnum
import logging
from typing import Any

import requests

_LOGGER = logging.getLogger(__name__)


class DeviceType(StrEnum):
    """Device types."""

    SOCKET = "socket"
    SELECT = "select"


@dataclass
class Device:
    """API device."""

    device_unique_id: str
    device_type: DeviceType
    entity_id: str
    name: str
    state: int | bool
    piwigo_type: str
    simple_name: str
    piwigo_id: int = 0
    piwigo_parent_id: int = 0
    device_id: int = 1


class API:
    """Class for example API."""

    def __init__(self, host: str, user: str, pwd: str) -> None:
        """Initialise."""
        self.host = host
        self.user = user
        self.pwd = pwd
        self.connected: bool = False
        self.session = requests.Session()

    @property
    def controller_name(self) -> str:
        """Return the name of the controller."""
        return (
            self.host.replace(".", "_")
            .replace("https", "")
            .replace("http", "")
            .replace("://", "")
        )

    def connect(self) -> bool:
        """Connect to api."""
        login_data = {"username": self.user, "password": self.pwd}
        r = self.session.post(
            self.host + "/ws.php?format=json&method=pwg.session.login", data=login_data
        )
        if r.json()["stat"] == "ok":
            self.connected = True
            return True
        raise APIAuthError("Error connecting to api. Invalid username or password.")

    def disconnect(self) -> bool:
        """Disconnect from api."""
        self.connected = False
        return True

    def get_devices(self) -> list[Device]:
        """Get devices on api."""
        return self.getData()

    def set_data(self, device: Device, value: Any) -> bool:
        """Set api data."""
        full_url = (
            self.host
            + f"/plugins/WallDisplay/api_wall_display.inc.php?api=edit_options&type={device.piwigo_type}&id={device.piwigo_id}&enabled={value}"
        )
        result = self.session.get(full_url)
        if result.text == "Not Logged In":
            connected = self.connect()
            result - self.session.get(full_url)
        return False

    def getData(self):
        """Return 2 dictionaris of name:id.  First is albums, 2nd is tags."""
        album_list = []
        tag_list = []
        full_list = []
        full_url = (
            self.host + "/plugins/WallDisplay/api_wall_display.inc.php?api=full_table"
        )
        full_list = self.session.get(full_url)
        if full_list.text == "Not Logged In":
            connected = self.connect()
            full_list = self.session.get(full_url)

        full_list_dict = full_list.json()
        album_dict = full_list_dict["cats"]
        tag_dict = full_list_dict["tags"]
        mode = full_list_dict["mode"]
        album_list = self.flattenAlbums(album_dict.values(), "")
        tag_list = []
        for device in list(tag_dict.values()):
            device_id = 2000 + int(device.get("id"))
            tag_list.append(
                Device(
                    #                    device_id=1,  # device_id,
                    device_unique_id=f"{self.controller_name}_tag_ID{device_id}",
                    device_type=DeviceType.SOCKET,
                    name=f"Piwigo_tag_{device.get("name")}",
                    entity_id=f"{self.controller_name}_tag_{device.get("name")}",
                    state=device.get("Enabled") != "0",
                    piwigo_type="tag",
                    simple_name=device.get("name"),
                )
            )
        album_list.extend(tag_list)
        album_list.append(
            Device(
                #                device_id=1,
                device_unique_id=f"{self.controller_name}_mode",
                device_type=DeviceType.SELECT,
                name="Piwigo_mode",
                entity_id=f"{self.controller_name}_mode",
                state=mode,
                piwigo_type="mode",
                simple_name="Mode",
            )
        )
        return album_list

    def flattenAlbums(self, album_dict, parent):
        """Strip everything except Album name and ID.  Sub-Albums are de-nested."""
        out_list = []
        children_list = []
        parent_break = parent.find(" / ")
        partial_parent = ""
        if parent_break > 0:
            partial_parent = f"{parent[parent_break+2:]}=>"
            partial_parent.replace(" / ", "=>")
        for album in list(album_dict):
            if parent != "":
                full_name = parent + " / " + album.get("name")
            else:
                full_name = album.get("name")
            device_id = 1000 + int(album.get("id"))
            out_list.append(
                Device(
                    #                    device_id=1,  # device_id,
                    device_unique_id=f"{self.controller_name}_cat_ID{device_id}",
                    device_type=DeviceType.SOCKET,
                    name=f"Piwigo_album_{full_name}",
                    entity_id=f"{self.controller_name}_cat_{album.get("name")}",
                    state=album.get("Enabled") != "0",
                    piwigo_type="cat",
                    simple_name=f"{partial_parent}{album.get("name")}",
                    piwigo_id=album.get("id"),
                    piwigo_parent_id=0 if parent == "" else album.get("id_uppercat"),
                )
            )
            children_dict = dict(album.get("children"))
            children_list = self.flattenAlbums(children_dict.values(), full_name)
            out_list.extend(children_list)
        return out_list


class APIAuthError(Exception):
    """Exception class for auth error."""


class APIConnectionError(Exception):
    """Exception class for connection error."""
