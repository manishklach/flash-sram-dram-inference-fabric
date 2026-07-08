from enum import Enum


class InterfaceMode(Enum):
    RAM_EMULATION = "ram_emulation"
    STREAM_TO_SCRATCHPAD = "stream_to_scratchpad"
    HYBRID = "hybrid"
